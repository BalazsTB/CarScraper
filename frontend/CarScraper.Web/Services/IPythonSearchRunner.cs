namespace CarScraper.Web.Services;

public interface IPythonSearchRunner
{
    Task RunAsync(long searchId, CancellationToken cancellationToken);
}
