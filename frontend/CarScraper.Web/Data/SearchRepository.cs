using System.ComponentModel.DataAnnotations;
using System.Text.Json;
using CarScraper.Web.Models;

namespace CarScraper.Web.Data;

public sealed partial class SearchRepository(DatabaseConnectionFactory factory) : ISearchRepository
{
    public long Create(SearchDefinition definition)
    {
        ArgumentNullException.ThrowIfNull(definition);
        Validator.ValidateObject(definition, new ValidationContext(definition), true);
        using var connection = factory.Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            INSERT INTO searches (started_at, completed_at, created_at, status,
                postcode, radius, year_from, year_to, price_from, price_to,
                cars_json, max_pages, delay_seconds, headless)
            VALUES ('', '', $created, 'draft', $postcode, $radius, $yearFrom, $yearTo,
                $priceFrom, $priceTo, $cars, $pages, $delay, $headless);
            SELECT last_insert_rowid();
            """;
        command.Parameters.AddWithValue("$created", DateTimeOffset.UtcNow.ToString("O"));
        command.Parameters.AddWithValue("$postcode", definition.Postcode.Trim());
        command.Parameters.AddWithValue("$radius", (object?)definition.Radius ?? DBNull.Value);
        command.Parameters.AddWithValue("$yearFrom", (object?)definition.YearFrom ?? DBNull.Value);
        command.Parameters.AddWithValue("$yearTo", (object?)definition.YearTo ?? DBNull.Value);
        command.Parameters.AddWithValue("$priceFrom", (object?)definition.PriceFrom ?? DBNull.Value);
        command.Parameters.AddWithValue("$priceTo", (object?)definition.PriceTo ?? DBNull.Value);
        command.Parameters.AddWithValue("$cars", JsonSerializer.Serialize(definition.Cars));
        command.Parameters.AddWithValue("$pages", definition.MaxPages);
        command.Parameters.AddWithValue("$delay", definition.DelaySeconds);
        command.Parameters.AddWithValue("$headless", definition.IsHeadless);
        return (long)command.ExecuteScalar()!;
    }

    public bool TryQueue(long searchId)
    {
        using var connection = factory.Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            UPDATE searches SET status='queued', error_message=NULL, progress_message='Waiting to start'
            WHERE id=$id AND status IN ('draft', 'completed', 'failed')
            """;
        command.Parameters.AddWithValue("$id", searchId);
        return command.ExecuteNonQuery() == 1;
    }

    public void Fail(long searchId, string message)
    {
        using var connection = factory.Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            UPDATE searches SET status='failed', error_message=$message,
                progress_message='Search failed; collected results may be partial', completed_at=$now
            WHERE id=$id AND status IN ('queued', 'running')
            """;
        command.Parameters.AddWithValue("$id", searchId);
        command.Parameters.AddWithValue("$message", message);
        command.Parameters.AddWithValue("$now", DateTimeOffset.UtcNow.ToString("O"));
        command.ExecuteNonQuery();
    }

    public List<long> GetQueuedIds() => GetAll().Where(search => search.Status == "queued").Select(search => search.Id).ToList();

    public void RecoverInterrupted()
    {
        foreach (var search in GetAll().Where(search => search.Status == "running"))
            Fail(search.Id, "The app stopped before this search finished. You can retry the search.");
    }
}
