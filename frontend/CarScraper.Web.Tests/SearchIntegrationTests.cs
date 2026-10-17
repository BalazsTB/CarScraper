using System.Diagnostics;
using System.Text.Json;
using CarScraper.Web.Configuration;
using CarScraper.Web.Data;
using CarScraper.Web.Models;
using CarScraper.Web.Services;
using Microsoft.Data.Sqlite;
using Microsoft.Extensions.Logging.Abstractions;

namespace CarScraper.Web.Tests;

public sealed class SearchIntegrationTests : IDisposable
{
    private static SearchDefinition ValidDefinition() => new()
    {
        Postcode = "LS1 2AD", MaxPages = 10, DelaySeconds = 5,
        YearFrom = 2010, YearTo = 2014,
        Cars = [new() { Make = "Toyota", Model = "Yaris" }]
    };

    private readonly string _directory = Path.Combine(Path.GetTempPath(), "carscraper-test-" + Guid.NewGuid());
    private readonly ScraperOptions _options;
    private readonly DatabaseConnectionFactory _factory;
    private readonly SearchRepository _repository;

    public SearchIntegrationTests()
    {
        var root = new DirectoryInfo(AppContext.BaseDirectory);
        while (root is not null && !Directory.Exists(Path.Combine(root.FullName, "carscraper"))) root = root.Parent;
        _options = new ScraperOptions { RepositoryRoot = root!.FullName, DatabasePath = Path.Combine(_directory, "test.sqlite3") };
        _options.ResolvePaths(root.FullName);
        _factory = new DatabaseConnectionFactory(_options);
        new DatabaseInitializer(_factory, _options).Initialize();
        _repository = new SearchRepository(_factory);
    }

    [Fact]
    public void BrandsAreSeededOnceAndReturnedAlphabetically()
    {
        var brands = _repository.GetCarBrands();
        Assert.Equal(151, brands.Count);
        Assert.Equal(brands.OrderBy(brand => brand, StringComparer.OrdinalIgnoreCase), brands);
        Assert.Equal("Abarth", brands[0]);
        Assert.Equal("XPENG", brands[^1]);
        Assert.Contains("DS AUTOMOBILES", brands);
        Assert.Contains("Mills Extreme Vehicles (MEV)", brands);
        Assert.DoesNotContain(brands, brand => brand.Contains("logo", StringComparison.OrdinalIgnoreCase));
        new DatabaseInitializer(_factory, _options).Initialize();
        Assert.Equal(brands, _repository.GetCarBrands());
    }

    [Fact]
    public void SaveAndQueueUseOneSearchAndRejectDuplicateStarts()
    {
        var searchId = _repository.Create(ValidDefinition());
        Assert.Equal("draft", _repository.Get(searchId)!.Status);
        var queue = new SearchQueue(_repository);
        Assert.True(queue.Start(searchId));
        Assert.False(queue.Start(searchId));
        Assert.Equal("queued", _repository.Get(searchId)!.Status);
        Assert.Single(_repository.GetAll());
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task PythonReadsDotNetSearchAndWritesLinkedResults(bool isAnyAge)
    {
        var definition = ValidDefinition();
        definition.Postcode = "SW1A 1AA";
        definition.PriceTo = 9000;
        definition.MaxPages = 1;
        definition.IsHeadless = true;
        if (isAnyAge)
        {
            definition.YearFrom = null;
            definition.YearTo = null;
        }
        var searchId = _repository.Create(definition);
        Assert.True(_repository.TryQueue(searchId));
        var script = """
            import sys
            from carscraper.jobs import worker
            from carscraper.scraping.urls import search_url
            from urllib.parse import parse_qs, urlsplit
            def fake_scrape(config, **settings):
                assert config['criteria']['postcode'] == 'SW1A 1AA'
                assert config['criteria']['price_to'] == 9000
                assert config['cars'][0]['make'] == 'Toyota'
                assert settings['headless']
                query = parse_qs(urlsplit(search_url(config['cars'][0], config['criteria'])).query)
                if sys.argv[3] == 'any':
                    assert 'year_from' not in config['criteria']
                    assert 'year_to' not in config['criteria']
                    assert 'year-from' not in query and 'year-to' not in query
                else:
                    assert query['year-from'] == ['2010'] and query['year-to'] == ['2014']
                rows = [{'name': 'Test Yaris', 'link': 'https://www.autotrader.co.uk/car-details/123', 'price': 8000}]
                settings['on_page'](rows, 'First page saved')
                return rows
            worker.scrape = fake_scrape
            worker.run(int(sys.argv[1]), sys.argv[2])
            """;
        var info = new ProcessStartInfo(_options.PythonExecutable) { WorkingDirectory = _options.RepositoryRoot, RedirectStandardError = true, UseShellExecute = false, CreateNoWindow = true };
        foreach (var argument in new[] { "-c", script, searchId.ToString(), _options.DatabasePath, isAnyAge ? "any" : "range" }) info.ArgumentList.Add(argument);
        using var process = Process.Start(info)!;
        var error = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(30));
        Assert.True(process.ExitCode == 0, error);
        Assert.Equal("completed", _repository.Get(searchId)!.Status);
        Assert.Equal(8000, Assert.Single(_repository.GetResults(searchId)).Price);
        Assert.Single(_repository.GetAll());
    }

    [Fact]
    public async Task RealRunnerPassesSearchIdAndReportsPythonFailure()
    {
        var searchId = _repository.Create(ValidDefinition());
        using (var connection = _factory.Open())
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "UPDATE searches SET cars_json='[]' WHERE id=$id";
            command.Parameters.AddWithValue("$id", searchId);
            command.ExecuteNonQuery();
        }
        _repository.TryQueue(searchId);
        var runner = new PythonSearchRunner(_options, NullLogger<PythonSearchRunner>.Instance);
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await Assert.ThrowsAsync<InvalidOperationException>(() => runner.RunAsync(searchId, cancellation.Token));
        Assert.Equal("failed", _repository.Get(searchId)!.Status);
        Assert.Contains("at least one", _repository.Get(searchId)!.ErrorMessage);
        Assert.Empty(_repository.GetResults(searchId));
    }

    [Fact]
    public void InvalidSearchCannotBeSaved()
    {
        var definition = ValidDefinition();
        definition.PriceFrom = 10000;
        definition.PriceTo = 1;
        Assert.Throws<System.ComponentModel.DataAnnotations.ValidationException>(() => _repository.Create(definition));
        Assert.Empty(_repository.GetAll());
    }

    [Theory]
    [InlineData("draft")]
    [InlineData("completed")]
    [InlineData("failed")]
    public void DeleteRemovesOnlySelectedSearchAndItsResults(string status)
    {
        var selectedId = _repository.Create(ValidDefinition());
        var otherId = _repository.Create(ValidDefinition());
        using (var connection = _factory.Open())
        using (var command = connection.CreateCommand())
        {
            command.CommandText = """
                UPDATE searches SET status=$status WHERE id=$id;
                INSERT INTO search_results (search_id, link) VALUES ($id, 'selected'), ($other, 'other');
                """;
            command.Parameters.AddWithValue("$status", status);
            command.Parameters.AddWithValue("$id", selectedId);
            command.Parameters.AddWithValue("$other", otherId);
            command.ExecuteNonQuery();
        }
        Assert.True(_repository.TryDelete(selectedId));
        Assert.Null(_repository.Get(selectedId));
        Assert.Empty(_repository.GetResults(selectedId));
        Assert.NotNull(_repository.Get(otherId));
        Assert.Single(_repository.GetResults(otherId));
        Assert.False(_repository.TryDelete(selectedId));
        Assert.Equal(151, _repository.GetCarBrands().Count);
    }

    [Theory]
    [InlineData("queued")]
    [InlineData("running")]
    public void ActiveSearchCannotBeDeleted(string status)
    {
        var id = _repository.Create(ValidDefinition());
        using (var connection = _factory.Open())
        using (var command = connection.CreateCommand())
        {
            command.CommandText = "UPDATE searches SET status=$status WHERE id=$id";
            command.Parameters.AddWithValue("$status", status);
            command.Parameters.AddWithValue("$id", id);
            command.ExecuteNonQuery();
        }
        Assert.False(_repository.TryDelete(id));
        Assert.Equal(status, _repository.Get(id)!.Status);
    }

    public void Dispose()
    {
        SqliteConnection.ClearAllPools();
        if (Directory.Exists(_directory)) Directory.Delete(_directory, true);
    }
}
