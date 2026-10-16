using System.Threading.Channels;
using CarScraper.Web.Data;

namespace CarScraper.Web.Services;

public sealed class SearchQueue(ISearchRepository repository)
{
    private readonly Channel<long> _channel = Channel.CreateUnbounded<long>(new UnboundedChannelOptions { SingleReader = true });

    public bool Start(long searchId)
    {
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(searchId);
        if (!repository.TryQueue(searchId)) return false;
        _channel.Writer.TryWrite(searchId);
        return true;
    }

    public void RestoreQueued()
    {
        foreach (var searchId in repository.GetQueuedIds()) _channel.Writer.TryWrite(searchId);
    }

    public IAsyncEnumerable<long> ReadAll(CancellationToken cancellationToken) => _channel.Reader.ReadAllAsync(cancellationToken);
}
