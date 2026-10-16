import unittest
from pathlib import Path
from zipfile import ZipFile
from carscraper.exports.excel import export_excel
from carscraper.scraping.parsing import parse_listings


class ExcelTests(unittest.TestCase):
    def test_excel_empty_and_formula_like_text(self):
        # Keep test output in the workspace, including in restricted environments.
        path = Path("test-output.xlsx")
        try:
            export_excel([], path)
            with ZipFile(path) as archive:
                self.assertIn("xl/worksheets/sheet1.xml", archive.namelist())
            rows, _ = parse_listings(
                """<article><h2>=1+1</h2>
                <a href="/car-details/123">View</a></article>""",
                {"make": "Honda", "model": "Jazz"},
            )
            export_excel(rows, path)
            with ZipFile(path) as archive:
                xml = archive.read("xl/worksheets/sheet1.xml").decode()
                self.assertNotIn("<f>", xml)
                self.assertIn("hyperlink", xml)
        finally:
            path.unlink(missing_ok=True)
