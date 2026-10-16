using System.Diagnostics;
using CarScraper.Web.Configuration;

namespace CarScraper.Web.Services;

public sealed class PythonSearchRunner(ScraperOptions options, ILogger<PythonSearchRunner> logger) : IPythonSearchRunner
{
    public async Task RunAsync(long searchId, CancellationToken cancellationToken)
    {
        if (!File.Exists(options.PythonExecutable))
            throw new FileNotFoundException("Python was not found. Create .venv or set Scraper:PythonExecutable.", options.PythonExecutable);
        var startInfo = new ProcessStartInfo
        {
            FileName = options.PythonExecutable,
            WorkingDirectory = options.RepositoryRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true
        };
        foreach (var argument in new[] { "-u", "-m", "carscraper.jobs.worker", "--search-id", searchId.ToString(System.Globalization.CultureInfo.InvariantCulture), "--database", options.DatabasePath })
            startInfo.ArgumentList.Add(argument);
        using var process = Process.Start(startInfo) ?? throw new InvalidOperationException("Could not start Python.");
        try
        {
            var stdout = ReadLogAsync(process.StandardOutput, searchId);
            var stderr = ReadLogAsync(process.StandardError, searchId);
            await process.WaitForExitAsync(cancellationToken);
            await Task.WhenAll(stdout, stderr);
            if (process.ExitCode != 0)
                throw new InvalidOperationException($"Python exited with code {process.ExitCode}. See the server log for details.");
        }
        finally
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
                await process.WaitForExitAsync(CancellationToken.None);
            }
        }
    }

    private async Task ReadLogAsync(StreamReader reader, long searchId)
    {
        while (await reader.ReadLineAsync() is { } line)
            logger.LogInformation("Search {SearchId}: {Message}", searchId, line);
    }
}
