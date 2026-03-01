"""Standardised table extractors for each library.

Every extractor accepts a PDF file path and returns::

    (result, elapsed_seconds)

where ``result`` is::

    dict[page_num_1indexed, list[table_grid]]

and each ``table_grid`` is ``list[list[str | None]]``.
"""

from __future__ import annotations

import time
from io import BytesIO
from pathlib import Path


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _norm_cell(cell: object) -> str | None:
    if cell is None:
        return None
    s = str(cell).strip()
    return s if s else None


def _norm_table(raw: list[list]) -> list[list[str | None]]:
    return [[_norm_cell(c) for c in row] for row in raw]


# ---------------------------------------------------------------------------
# tablers
# ---------------------------------------------------------------------------

def extract_tablers(
    pdf_path: str | Path,
) -> tuple[dict[int, list[list[list[str | None]]]], float]:
    """Extract tables with **tablers**."""
    from tablers import Document as TabDoc, find_tables

    pdf_bytes = Path(pdf_path).read_bytes()
    result: dict[int, list[list[list[str | None]]]] = {}

    tic = time.perf_counter()
    with TabDoc(bytes=pdf_bytes) as doc:
        for page_num, page in enumerate(doc.pages(), start=1):
            tables_raw = find_tables(page, extract_text=True)
            grids: list[list[list[str | None]]] = []
            for table in tables_raw:
                # table.to_list() → list[list[TableCellValue]]
                # TableCellValue.text is str | None
                rows = table.to_list()
                grids.append([[_norm_cell(cell.text) for cell in row] for row in rows])
            if grids:
                result[page_num] = grids
    elapsed = time.perf_counter() - tic

    return result, elapsed


# ---------------------------------------------------------------------------
# PyMuPDF
# ---------------------------------------------------------------------------

def extract_pymupdf(
    pdf_path: str | Path,
) -> tuple[dict[int, list[list[list[str | None]]]], float]:
    """Extract tables with **PyMuPDF**."""
    from pymupdf import Document as MuDoc

    pdf_bytes = Path(pdf_path).read_bytes()
    result: dict[int, list[list[list[str | None]]]] = {}

    tic = time.perf_counter()
    with MuDoc(stream=pdf_bytes) as doc:
        for page in doc:
            page_num = page.number + 1  # 0-indexed → 1-indexed
            finder = page.find_tables()
            grids = [_norm_table(t.extract()) for t in finder.tables]
            if grids:
                result[page_num] = grids
    elapsed = time.perf_counter() - tic

    return result, elapsed


# ---------------------------------------------------------------------------
# pdfplumber
# ---------------------------------------------------------------------------

def extract_pdfplumber(
    pdf_path: str | Path,
) -> tuple[dict[int, list[list[list[str | None]]]], float]:
    """Extract tables with **pdfplumber**."""
    import pdfplumber

    pdf_bytes = Path(pdf_path).read_bytes()
    result: dict[int, list[list[list[str | None]]]] = {}

    tic = time.perf_counter()
    with pdfplumber.open(BytesIO(pdf_bytes)) as doc:
        for page_num, page in enumerate(doc.pages, start=1):
            grids = [_norm_table(t.extract()) for t in page.find_tables()]
            page.close()  # avoid memory leak
            if grids:
                result[page_num] = grids
    elapsed = time.perf_counter() - tic

    return result, elapsed


# ---------------------------------------------------------------------------
# camelot
# ---------------------------------------------------------------------------

def extract_camelot(
    pdf_path: str | Path,
) -> tuple[dict[int, list[list[list[str | None]]]], float]:
    """Extract tables with **camelot** (lattice flavor).

    Uses ``flavor='lattice'``, which works best for PDFs with visible grid
    lines — the dominant style in the ICDAR 2013 dataset.
    """
    import camelot as _camelot

    result: dict[int, list[list[list[str | None]]]] = {}

    tic = time.perf_counter()
    tables = _camelot.read_pdf(
        str(pdf_path),
        pages='all',
        flavor='lattice',
        suppress_stdout=True,
    )
    for table in tables:
        page_num: int = table.page  # already 1-indexed
        grid = _norm_table(table.data)
        result.setdefault(page_num, []).append(grid)
    elapsed = time.perf_counter() - tic

    return result, elapsed


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

EXTRACTORS: dict[str, object] = {
    'tablers': extract_tablers,
    'pymupdf': extract_pymupdf,
    'pdfplumber': extract_pdfplumber,
    'camelot': extract_camelot,
}
