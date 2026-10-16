using System.Text.Json.Serialization;

namespace CarScraper.Web.Models;

public sealed class CarSelection
{
    [JsonPropertyName("make")]
    public string Make { get; set; } = "";

    [JsonPropertyName("model")]
    public string Model { get; set; } = "";
}
