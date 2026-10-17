using CarScraper.Web.Models;

namespace CarScraper.Web.Data;

public interface ISearchRepository
{
    List<string> GetCarBrands();
    long Create(SearchDefinition definition);
    List<SearchRecord> GetAll();
    SearchRecord? Get(long searchId);
    List<Listing> GetResults(long searchId);
    bool TryQueue(long searchId);
    bool TryDelete(long searchId);
    void Fail(long searchId, string message);
    List<long> GetQueuedIds();
    void RecoverInterrupted();
}
