"""ICDAR 2013 Table Recognition Dataset parser.

The ICDAR 2013 competition is the industry-standard benchmark for PDF table
extraction, cited in thousands of papers.

Actual dataset directory layout (flat — PDF and XMLs share the same folder)::

    <dataset_root>/
    ├── competition-dataset-eu/
    │   ├── eu-001.pdf
    │   ├── eu-001-reg.xml   # table *region* bounding boxes (Track A)
    │   ├── eu-001-str.xml   # table *structure* + cell content (Track B/C) ← used here
    │   ├── eu-002.pdf
    │   └── ...
    └── competition-dataset-us/
        ├── us-001.pdf
        ├── us-001-reg.xml
        ├── us-001-str.xml
        └── ...

``*-reg.xml``  — records only table-region bounding boxes (no cell detail).
``*-str.xml``  — records full table structure: every cell's row/col position,
                 rowspan/colspan, bounding box, and text content.
                 This is the file used for accuracy evaluation.

Actual *-str.xml cell format (differs from naive expectation)::

    <table id="1">
      <region col-increment="0" row-increment="0" page="1" id="1">
        <cell start-row="0" start-col="1" end-col="3" id="1">
          <bounding-box x1="316" y1="533" x2="441" y2="543"/>
          <content>THRESHOLD FOR RELEASES</content>
        </cell>
        ...
      </region>
    </table>

Key encoding rules:
- ``start-row`` / ``start-col`` are 0-indexed.
- ``end-col`` (optional): last column index, inclusive. Absent → colspan = 1.
- No ``end-row`` attribute; rowspan is always 1 in this dataset.
- ``row-increment`` / ``col-increment`` on <region>: offset added to all cell
  coordinates in that region (used for multi-page / multi-region tables).
- PDF name is derived from the XML filename: ``eu-001-str.xml`` → ``eu-001.pdf``.

Download the dataset from:
    https://www.tamirhassan.com/html/dataset.html
    or search "ICDAR 2013 table competition dataset" for mirrors.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CellGT:
    row: int      # 1-indexed
    col: int      # 1-indexed
    rowspan: int
    colspan: int
    content: str
    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) in PDF pts


@dataclass
class TableGT:
    page: int     # 1-indexed
    bbox: tuple[float, float, float, float]
    cells: list[CellGT] = field(default_factory=list)

    @property
    def num_rows(self) -> int:
        if not self.cells:
            return 0
        return max(c.row + c.rowspan - 1 for c in self.cells)

    @property
    def num_cols(self) -> int:
        if not self.cells:
            return 0
        return max(c.col + c.colspan - 1 for c in self.cells)

    def to_grid(self) -> list[list[str]]:
        """Convert to 2-D text grid; merged-cell slots carry the same text."""
        nr, nc = self.num_rows, self.num_cols
        if nr == 0 or nc == 0:
            return []
        grid: list[list[str]] = [['' for _ in range(nc)] for _ in range(nr)]
        for cell in self.cells:
            r0, c0 = cell.row - 1, cell.col - 1
            for r in range(r0, min(r0 + cell.rowspan, nr)):
                for c in range(c0, min(c0 + cell.colspan, nc)):
                    grid[r][c] = cell.content
        return grid


@dataclass
class DocumentGT:
    pdf_path: Path
    tables: list[TableGT] = field(default_factory=list)

    def tables_on_page(self, page: int) -> list[TableGT]:
        return [t for t in self.tables if t.page == page]

    @property
    def pages_with_tables(self) -> set[int]:
        return {t.page for t in self.tables}


def _safe_float(s: str | int | float, default: float = 0.0) -> float:
    """Parse a float, stripping any non-numeric trailing garbage characters."""
    try:
        return float(s)
    except (ValueError, TypeError):
        # Remove every character that is not a digit, dot, minus, or plus
        cleaned = re.sub(r'[^\d.\-+]', '', str(s))
        try:
            return float(cleaned) if cleaned else default
        except ValueError:
            return default


def _parse_cell_bbox(elem: ET.Element | None) -> tuple[float, float, float, float]:
    """Parse <bounding-box x1=.. y1=.. x2=.. y2=..> element."""
    if elem is None:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        _safe_float(elem.attrib.get('x1', 0)),
        _safe_float(elem.attrib.get('y1', 0)),
        _safe_float(elem.attrib.get('x2', 0)),
        _safe_float(elem.attrib.get('y2', 0)),
    )


def parse_icdar2013_xml(xml_path: Path) -> DocumentGT:
    """Parse one ICDAR 2013 structure XML (*-str.xml) file.

    The PDF name is derived from the XML stem:
        eu-001-str.xml  →  eu-001.pdf
    Both files live in the same flat directory.

    Multi-page tables (multiple <region> elements) are split into one
    TableGT per region/page so they can be compared with per-page extractor
    output.
    """
    # Derive PDF filename from XML stem (strip trailing "-str")
    pdf_name = re.sub(r'-str$', '', xml_path.stem) + '.pdf'
    pdf_path = xml_path.parent / pdf_name

    tree = ET.parse(xml_path)
    root = tree.getroot()

    tables: list[TableGT] = []
    for table_elem in root.findall('table'):
        for region_elem in table_elem.findall('region'):
            page = int(region_elem.attrib.get('page', 1))
            # row/col-increment: offset applied to all cells in this region
            # (used when a table spans multiple pages/regions)
            row_inc = max(0, int(region_elem.attrib.get('row-increment', 0)))
            col_inc = max(0, int(region_elem.attrib.get('col-increment', 0)))

            cells: list[CellGT] = []
            for cell_elem in region_elem.findall('cell'):
                start_row = int(cell_elem.attrib.get('start-row', 0)) + row_inc
                start_col = int(cell_elem.attrib.get('start-col', 0)) + col_inc
                end_col = int(cell_elem.attrib.get(
                    'end-col', cell_elem.attrib.get('start-col', 0)
                )) + col_inc

                colspan = max(1, end_col - start_col + 1)
                rowspan = 1  # no end-row attribute in this dataset

                content_elem = cell_elem.find('content')
                content = (
                    ''.join(content_elem.itertext()).strip()
                    if content_elem is not None else ''
                )

                bbox = _parse_cell_bbox(cell_elem.find('bounding-box'))

                # Convert 0-indexed to 1-indexed (matches TableGT.to_grid() logic)
                cells.append(CellGT(
                    row=start_row + 1,
                    col=start_col + 1,
                    rowspan=rowspan,
                    colspan=colspan,
                    content=content,
                    bbox=bbox,
                ))

            if cells:
                tables.append(TableGT(page=page, bbox=(0.0, 0.0, 0.0, 0.0), cells=cells))

    return DocumentGT(pdf_path=pdf_path, tables=tables)


def load_icdar2013(dataset_root: str | Path) -> list[DocumentGT]:
    """Load all ICDAR 2013 documents that have a matching PDF on disk.

    Parameters
    ----------
    dataset_root:
        Root directory that contains ``competition-dataset-eu/`` and/or
        ``competition-dataset-us/``.  Each subdirectory must use the flat
        layout where PDF and XML files share the same folder.

    Returns
    -------
    list[DocumentGT]
        Documents for which the PDF file exists locally, sorted by name.
    """
    root = Path(dataset_root)
    documents: list[DocumentGT] = []

    # Support both the original competition folder names and common rename conventions
    candidates = (
        'competition-dataset-eu',
        'competition-dataset-us',
        'eu-dataset',
        'us-dataset',
    )

    for subset in candidates:
        subset_dir = root / subset
        if not subset_dir.exists():
            continue

        for xml_path in sorted(subset_dir.glob('*-str.xml')):
            try:
                doc = parse_icdar2013_xml(xml_path)
                if doc.pdf_path.exists() and doc.tables:
                    documents.append(doc)
            except Exception as exc:
                msg = f"  [warn] Skipping {xml_path.name}: {exc}"
                print(msg.encode('ascii', errors='replace').decode('ascii'))

    return documents
