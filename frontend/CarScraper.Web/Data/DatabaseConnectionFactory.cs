using CarScraper.Web.Configuration;
using Microsoft.Data.Sqlite;

namespace CarScraper.Web.Data;

public sealed class DatabaseConnectionFactory(ScraperOptions options)
{
    public SqliteConnection Open()
    {
        var connection = new SqliteConnection(new SqliteConnectionStringBuilder
        {
            DataSource = options.DatabasePath,
            ForeignKeys = true,
            DefaultTimeout = 30
        }.ToString());
        connection.Open();
        return connection;
    }
}
