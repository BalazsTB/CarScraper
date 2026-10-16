using System.Text.RegularExpressions;
using CarScraper.Web.Configuration;

namespace CarScraper.Web.Data;

public sealed class DatabaseInitializer(DatabaseConnectionFactory factory, ScraperOptions options)
{
    public void Initialize()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(options.DatabasePath)!);
        using var connection = factory.Open();
        using var command = connection.CreateCommand();
        command.CommandText = "PRAGMA journal_mode=WAL;";
        command.ExecuteNonQuery();
        var schemaDirectory = Path.Combine(options.RepositoryRoot, "carscraper", "storage");
        command.CommandText = File.ReadAllText(Path.Combine(schemaDirectory, "schema.sql"));
        command.ExecuteNonQuery();
        command.CommandText = "PRAGMA table_info(searches)";
        var columns = new HashSet<string>();
        using (var reader = command.ExecuteReader())
            while (reader.Read()) columns.Add(reader.GetString(1));
        using var transaction = connection.BeginTransaction();
        command.Transaction = transaction;
        foreach (var statement in File.ReadAllText(Path.Combine(schemaDirectory, "search_lifecycle.sql")).Split(';'))
        {
            var match = Regex.Match(statement, @"ADD COLUMN (\w+)");
            if (!match.Success || columns.Contains(match.Groups[1].Value)) continue;
            command.CommandText = statement;
            command.ExecuteNonQuery();
        }
        transaction.Commit();
    }
}
