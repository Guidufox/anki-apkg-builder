from __future__ import annotations

import csv
import io


COLUMNS = (
    "japanese",
    "reading",
    "meaning",
    "example",
    "translation",
    "context",
    "tags",
)

HEADER_NAMES = {
    "japanese",
    "reading",
    "meaning",
    "example",
    "translation",
    "context",
    "tags",
}


def parse_bulk(text: str, file_format: str = "auto") -> list[dict]:
    text = text.lstrip("\ufeff").strip("\r\n")
    if not text.strip():
        return []
    if file_format not in {"auto", "tsv", "csv"}:
        raise ValueError("Formato no soportado")

    if file_format == "tsv":
        dialect: str | csv.Dialect = "excel-tab"
    elif file_format == "csv":
        dialect = "excel"
    else:
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,;")
        except csv.Error:
            dialect = "excel-tab" if "\t" in sample else "excel"

    reader = csv.reader(io.StringIO(text), dialect=dialect)
    raw_rows = [row for row in reader if any(cell.strip() for cell in row)]
    if raw_rows and {cell.strip().lower() for cell in raw_rows[0]} >= HEADER_NAMES:
        raw_rows.pop(0)

    parsed = []
    for line_number, row in enumerate(raw_rows, start=1):
        if len(row) != len(COLUMNS):
            raise ValueError(
                f"Fila {line_number}: se esperaban 7 columnas y se encontraron {len(row)}"
            )
        parsed.append(
            {
                **{column: value.strip() for column, value in zip(COLUMNS, row)},
                "cloze": "",
                "cloze_answer": "",
            }
        )
    return parsed

