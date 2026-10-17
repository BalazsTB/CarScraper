using System.ComponentModel.DataAnnotations;

namespace CarScraper.Web.Models;

public sealed class SearchDefinition : IValidatableObject
{
    [Required, StringLength(12)] public string Postcode { get; set; } = "";
    [Range(0, 100000)] public int? Radius { get; set; }
    [Range(1900, 2100)] public int? YearFrom { get; set; }
    [Range(1900, 2100)] public int? YearTo { get; set; }
    [Range(0, int.MaxValue)] public int? PriceFrom { get; set; }
    [Range(0, int.MaxValue)] public int? PriceTo { get; set; }
    [Required, Range(1, 100)] public int? MaxPages { get; set; }
    [Required, Range(1, 3600)] public double? DelaySeconds { get; set; }
    public bool IsHeadless { get; set; }
    public List<CarSelection> Cars { get; set; } = [new()];

    public IEnumerable<ValidationResult> Validate(ValidationContext validationContext)
    {
        if (PriceFrom > PriceTo)
            yield return new("Minimum price must not exceed maximum price.");
        if (YearFrom > YearTo)
            yield return new("Earliest year must not exceed latest year.");
        if (Cars.Count == 0 || Cars.Any(car => string.IsNullOrWhiteSpace(car.Make) || string.IsNullOrWhiteSpace(car.Model)))
            yield return new("Enter a make and model for every car.");
    }
}
