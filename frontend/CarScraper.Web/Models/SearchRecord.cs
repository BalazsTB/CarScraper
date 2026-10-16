namespace CarScraper.Web.Models;

public sealed class SearchRecord
{
    public long Id { get; init; }
    public string CreatedAt { get; init; } = "";
    public string StartedAt { get; init; } = "";
    public string CompletedAt { get; init; } = "";
    public string Status { get; init; } = "";
    public string? ErrorMessage { get; init; }
    public string? ProgressMessage { get; init; }
    public int ResultCount { get; init; }
    public SearchDefinition Definition { get; init; } = new();
    public bool CanStart => Status is "draft" or "completed" or "failed";
    public bool IsActive => Status is "queued" or "running";
    public string Description => string.Join(", ", Definition.Cars.Select(car => $"{car.Make} {car.Model}"));
}
