using System.Text.Json;
using CarScraper.Web.Models;
using Microsoft.Data.Sqlite;

namespace CarScraper.Web.Data;

public sealed partial class SearchRepository
{
    public List<string> GetCarBrands()
    {
        using var connection = factory.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT brand_name FROM car_brands ORDER BY brand_name COLLATE NOCASE";
        using var reader = command.ExecuteReader();
        var brands = new List<string>();
        while (reader.Read()) brands.Add(reader.GetString(0));
        return brands;
    }

    public List<SearchRecord> GetAll() => ReadSearches(null);
    public SearchRecord? Get(long searchId) => ReadSearches(searchId).FirstOrDefault();

    private List<SearchRecord> ReadSearches(long? searchId)
    {
        using var connection = factory.Open();
        using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT s.*, (SELECT COUNT(*) FROM search_results r WHERE r.search_id=s.id) AS result_count
            FROM searches s WHERE ($id IS NULL OR s.id=$id) ORDER BY s.id DESC
            """;
        command.Parameters.AddWithValue("$id", (object?)searchId ?? DBNull.Value);
        using var reader = command.ExecuteReader();
        var searches = new List<SearchRecord>();
        while (reader.Read())
        {
            searches.Add(new SearchRecord
            {
                Id = reader.GetInt64(reader.GetOrdinal("id")),
                CreatedAt = Text(reader, "created_at") ?? "",
                StartedAt = Text(reader, "started_at") ?? "",
                CompletedAt = Text(reader, "completed_at") ?? "",
                Status = Text(reader, "status") ?? "completed",
                ErrorMessage = Text(reader, "error_message"),
                ProgressMessage = Text(reader, "progress_message"),
                ResultCount = Number(reader, "result_count") ?? 0,
                Definition = new SearchDefinition
                {
                    Postcode = Text(reader, "postcode") ?? "",
                    Radius = Number(reader, "radius"),
                    YearFrom = Number(reader, "year_from"),
                    YearTo = Number(reader, "year_to"),
                    PriceFrom = Number(reader, "price_from"),
                    PriceTo = Number(reader, "price_to"),
                    MaxPages = Number(reader, "max_pages") ?? 10,
                    DelaySeconds = reader.GetDouble(reader.GetOrdinal("delay_seconds")),
                    IsHeadless = Number(reader, "headless") == 1,
                    Cars = JsonSerializer.Deserialize<List<CarSelection>>(Text(reader, "cars_json") ?? "[]") ?? []
                }
            });
        }
        return searches;
    }

    public List<Listing> GetResults(long searchId)
    {
        using var connection = factory.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM search_results WHERE search_id=$id ORDER BY distance IS NULL, distance, id";
        command.Parameters.AddWithValue("$id", searchId);
        using var reader = command.ExecuteReader();
        var listings = new List<Listing>();
        while (reader.Read())
        {
            listings.Add(new Listing
            {
                Name = Text(reader, "name"),
                Link = Text(reader, "link") ?? "",
                Price = Number(reader, "price"),
                Year = Number(reader, "year"),
                Mileage = Number(reader, "mileage"),
                MilesPerYear = Number(reader, "miles_pa"),
                Owners = Number(reader, "owners"),
                Distance = reader.IsDBNull(reader.GetOrdinal("distance")) ? null : reader.GetDouble(reader.GetOrdinal("distance")),
                Location = Text(reader, "location"),
                Engine = Text(reader, "engine"),
                Transmission = Text(reader, "transmission"),
                Fuel = Text(reader, "fuel")
            });
        }
        return listings;
    }

    private static string? Text(SqliteDataReader reader, string name) => reader.IsDBNull(reader.GetOrdinal(name)) ? null : reader.GetString(reader.GetOrdinal(name));
    private static int? Number(SqliteDataReader reader, string name) => reader.IsDBNull(reader.GetOrdinal(name)) ? null : reader.GetInt32(reader.GetOrdinal(name));
}
