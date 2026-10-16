"""Optional command-line Excel report generation."""

from pathlib import Path

import xlsxwriter

from carscraper.listings import COLUMNS


def export_excel(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda row: (row["distance"] is None, row["distance"] or 0))
    with xlsxwriter.Workbook(
        str(path), {"strings_to_formulas": False, "strings_to_urls": False}
    ) as workbook:
        sheet = workbook.add_worksheet("Cars")
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
        for col, name in enumerate(COLUMNS):
            sheet.write(0, col, name, header)
        for index, row in enumerate(rows, 1):
            for col, name in enumerate(COLUMNS):
                if name == "link":
                    sheet.write_url(index, col, row[name], string="View listing")
                else:
                    sheet.write(index, col, row.get(name))
        sheet.freeze_panes(1, 2)
        sheet.autofilter(0, 0, len(rows), len(COLUMNS) - 1)
        sheet.set_column(0, 0, 32)
        sheet.set_column(1, 1, 16)
        sheet.set_column(2, 7, 14)
        sheet.set_column(8, 11, 24)
        if rows:
            for col in (2, 3, 4, 5, 6, 7):
                reverse = col == 3
                sheet.conditional_format(
                    1,
                    col,
                    len(rows),
                    col,
                    {
                        "type": "3_color_scale",
                        "min_color": "#F96A6C" if reverse else "#63BE7B",
                        "mid_color": "#FFDC81",
                        "max_color": "#63BE7B" if reverse else "#F96A6C",
                    },
                )
