using CarScraper.Web.Data;

namespace CarScraper.Web.Services;

public sealed class SearchWorkerService(SearchQueue queue, ISearchRepository repository,
    IPythonSearchRunner runner, ILogger<SearchWorkerService> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        queue.RestoreQueued();
        try
        {
            await foreach (var searchId in queue.ReadAll(stoppingToken))
            {
                if (repository.Get(searchId)?.Status != "queued") continue;
                try
                {
                    await runner.RunAsync(searchId, stoppingToken);
                    if (repository.Get(searchId)?.Status is "queued" or "running")
                        repository.Fail(searchId, "Python stopped without completing the search.");
                }
                catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
                {
                    repository.Fail(searchId, "The application stopped during this search. Retry to run it again.");
                }
                catch (Exception exception)
                {
                    logger.LogError(exception, "Search {SearchId} failed", searchId);
                    repository.Fail(searchId, exception.Message);
                }
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { }
    }
}
