using CarScraper.Web.Components;
using CarScraper.Web.Configuration;
using CarScraper.Web.Data;
using CarScraper.Web.Services;

var builder = WebApplication.CreateBuilder(args);
var scraperOptions = new ScraperOptions();
builder.Configuration.GetSection("Scraper").Bind(scraperOptions);
scraperOptions.ResolvePaths(builder.Environment.ContentRootPath);
builder.Services.AddSingleton(scraperOptions);
builder.Services.AddSingleton<DatabaseConnectionFactory>();
builder.Services.AddSingleton<DatabaseInitializer>();
builder.Services.AddSingleton<ISearchRepository, SearchRepository>();
builder.Services.AddSingleton<SearchQueue>();
builder.Services.AddSingleton<IPythonSearchRunner, PythonSearchRunner>();
builder.Services.AddHostedService<SearchWorkerService>();

// Add services to the container.
builder.Services.AddRazorComponents()
    .AddInteractiveServerComponents();

var app = builder.Build();
app.Services.GetRequiredService<DatabaseInitializer>().Initialize();
app.Services.GetRequiredService<ISearchRepository>().RecoverInterrupted();

// Configure the HTTP request pipeline.
if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
}
app.UseStatusCodePagesWithReExecute("/not-found", createScopeForStatusCodePages: true);
app.UseAntiforgery();

app.MapStaticAssets();
app.MapRazorComponents<App>()
    .AddInteractiveServerRenderMode();

app.Run();
