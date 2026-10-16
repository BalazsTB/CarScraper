using System.ComponentModel.DataAnnotations;

namespace CarScraper.Web.Models;

public sealed class SearchDefinition : IValidatableObject
{
    [Required, StringLength(12)] public string Postcode { get; set; } = "LS1 2AD";
    [Range(0, 100000)] public int? Radius { get; set; } = 20;
    [Range(1900, 2100)] public int? YearFrom { get; set; } = 2010;
    [Range(1900, 2100)] public int? YearTo { get; set; } = 2014;
    [Range(0, int.MaxValue)] public int? PriceFrom { get; set; } = 3000;
    [Range(0, int.MaxValue)] public int? PriceTo { get; set; } = 6500;
    [Range(1, 100)] public int MaxPages { get; set; } = 10;
    [Range(1, 3600)] public double DelaySeconds { get; set; } = 5;
    public bool IsHeadless { get; set; }
    public List<CarSelection> Cars { get; set; } = [new() { Make = "Toyota", Model = "Yaris" }];

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
