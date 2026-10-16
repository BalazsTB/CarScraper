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
    public void SaveAndQueueUseOneSearchAndRejectDuplicateStarts()
    {
        var searchId = _repository.Create(new SearchDefinition());
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
        var definition = new SearchDefinition { Postcode = "SW1A 1AA", PriceTo = 9000, MaxPages = 1, IsHeadless = true };
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
        var searchId = _repository.Create(new SearchDefinition());
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
        Assert.Throws<System.ComponentModel.DataAnnotations.ValidationException>(() => _repository.Create(new SearchDefinition { PriceFrom = 10000, PriceTo = 1 }));
        Assert.Empty(_repository.GetAll());
    }

    public void Dispose()
    {
        SqliteConnection.ClearAllPools();
        if (Directory.Exists(_directory)) Directory.Delete(_directory, true);
    }
}
