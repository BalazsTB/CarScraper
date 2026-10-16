namespace CarScraper.Web.Models;

public sealed class Listing
{
    public string? Name { get; init; }
    public string Link { get; init; } = "";
    public int? Price { get; init; }
    public int? Year { get; init; }
    public int? Mileage { get; init; }
    public int? MilesPerYear { get; init; }
    public int? Owners { get; init; }
    public double? Distance { get; init; }
    public string? Location { get; init; }
    public string? Engine { get; init; }
    public string? Transmission { get; init; }
    public string? Fuel { get; init; }
}
