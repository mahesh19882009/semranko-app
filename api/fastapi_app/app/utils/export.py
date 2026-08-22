"""Small, domain-neutral CSV/XLSX response helpers.

The utility accepts only column names, row values, and a download filename. It
has no knowledge of projects, keywords, users, credits, or provider calls.
"""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Iterable, Sequence
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape

from fastapi.responses import Response


def _safe_filename(filename: str, extension: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", str(filename or "export")).strip(".-") or "export"
    if not stem.lower().endswith(extension):
        stem = f"{stem}{extension}"
    return stem


def _content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename}"'


def export_csv(columns: Sequence[str], rows: Iterable[Sequence[Any]], filename: str = "export.csv") -> Response:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow([str(column) for column in columns])
    for row in rows:
        writer.writerow(["" if value is None else value for value in row])
    safe_name = _safe_filename(filename, ".csv")
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": _content_disposition(safe_name)},
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell(reference: str, value: Any) -> str:
    text = "" if value is None else str(value)
    return f'<c r="{reference}" t="inlineStr"><is><t xml:space="preserve">{escape(text)}</t></is></c>'


def _xlsx_bytes(columns: Sequence[str], rows: Iterable[Sequence[Any]]) -> bytes:
    sheet_rows = [list(columns), *[list(row) for row in rows]]
    xml_rows = []
    for row_number, row in enumerate(sheet_rows, start=1):
        cells = "".join(
            _cell(f"{_column_name(column_number)}{row_number}", value)
            for column_number, value in enumerate(row, start=1)
        )
        xml_rows.append(f'<row r="{row_number}">{cells}</row>')

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Export" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return output.getvalue()


def export_xlsx(columns: Sequence[str], rows: Iterable[Sequence[Any]], filename: str = "export.xlsx") -> Response:
    safe_name = _safe_filename(filename, ".xlsx")
    return Response(
        content=_xlsx_bytes(columns, rows),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": _content_disposition(safe_name)},
    )
