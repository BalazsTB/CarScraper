namespace CarScraper.Web.Configuration;

public sealed class ScraperOptions
{
    public string RepositoryRoot { get; set; } = "../..";
    public string DatabasePath { get; set; } = "Database/cars.sqlite3";
    public string PythonExecutable { get; set; } = OperatingSystem.IsWindows()
        ? ".venv/Scripts/python.exe" : ".venv/bin/python";

    public void ResolvePaths(string contentRoot)
    {
        RepositoryRoot = Path.GetFullPath(RepositoryRoot, contentRoot);
        DatabasePath = Path.GetFullPath(DatabasePath, RepositoryRoot);
        PythonExecutable = Path.GetFullPath(PythonExecutable, RepositoryRoot);
    }
}
