# tablers-benchmark

Benchmark comparing **tablers**, **PyMuPDF**, **pdfplumber**, and **camelot** for PDF table extraction.

Two dimensions are measured:

| Dimension | Metrics |
|-----------|---------|
| **Speed** | Total processing time (absolute + relative to fastest) |
| **Accuracy** | Table detection F1 · TEDS score · Structure accuracy (row/col) |

---

## Libraries compared

| Library | Description |
|---------|-------------|
| [tablers](https://github.com/monchin/tablers) | Rust-backed PDF table extractor with edge-detection algorithm |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | General-purpose PDF library with built-in table finder |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | PDF parsing library built on pdfminer, with table extraction |
| [camelot](https://github.com/camelot-dev/camelot) | Dedicated table extraction library; uses `lattice` flavor here |

---

## Dataset — ICDAR 2013

### What it is

The benchmark uses the **ICDAR 2013 Table Recognition Competition** dataset —
the industry-standard ground-truth corpus for born-digital PDF table extraction,
cited in thousands of publications.

It contains **67 PDFs** (158 annotated tables) drawn from two sources:

| Subset | Source | Table style |
|--------|--------|-------------|
| `competition-dataset-eu` | European Union official publications | Complex layout, frequent merged cells |
| `competition-dataset-us` | US government reports (e.g. GAO) | Simpler, mostly regular row/col grids |

Each PDF ships with two XML files:

| File | Purpose | Used here |
|------|---------|-----------|
| `*-reg.xml` | Table region bounding boxes only (Track A) | No |
| `*-str.xml` | Full cell structure + text content (Track B/C) | **Yes** |

### Where to download

The dataset is available at:

- **Official site**: <https://www.tamirhassan.com/html/competition.html>
- **Alternative**: search academic mirrors for `ICDAR 2013 table competition dataset`

### Location in this project

Place (or keep) the extracted dataset at:

```
tablers-benchmark/
└── icdar2013-competition-dataset-with-gt/   ← dataset root
    ├── competition-dataset-eu/
    │   ├── eu-001.pdf
    │   ├── eu-001-reg.xml
    │   ├── eu-001-str.xml
    │   └── …
    └── competition-dataset-us/
        ├── us-001.pdf
        ├── us-001-reg.xml
        ├── us-001-str.xml
        └── …
```

`main.py` looks for the dataset at this path by default.
The benchmark automatically skips any document whose PDF is absent,
so a partial download works too.

---

## Metrics explained

### Table Detection F1
Counts how many tables were found on each page and compares to ground truth.
Predicted tables are matched to GT tables in order of appearance.

- **Precision** = matched / predicted
- **Recall** = matched / ground-truth
- **F1** = harmonic mean

### TEDS (Tree-Edit-Distance Similarity)
The standard accuracy metric for table structure recognition, introduced in
*PubTabNet* (Zhong et al., 2020). Captures both structural correctness
(row/column layout) and cell-content accuracy in a single 0–1 score.

This implementation uses sequence-matching similarity on HTML table
representations as an efficient approximation of the exact tree-edit-distance
TEDS, correlating strongly with the original metric without requiring
external C++ dependencies.

### Structure Accuracy
Exact row-count and column-count match rates over all matched table pairs.

---

## How to run

```bash
# 1. Install uv  (https://github.com/astral-sh/uv)
# 2. Clone the repo and enter it
uv sync

# Full benchmark — reads dataset from icdar2013-competition-dataset-with-gt/
uv run python main.py

# Quick smoke-test with the first 10 documents
uv run python main.py --max-docs 10

# Custom dataset path or output path
uv run python main.py --dataset path/to/icdar2013 --output my_results.png
```

Results are printed to stdout and saved as `table_extraction_benchmark.png`.

---

## Output chart panels

| Panel | Description |
|-------|-------------|
| Processing Time (relative) | Speed normalised to the fastest library |
| TEDS Score | Combined structure + content accuracy |
| Table Detection F1 | Whether the right number of tables was found |
| Structure Accuracy | Row-count and column-count exact match rates |
| Detection P / R / F1 | Full breakdown of detection metrics |
| Processing Time (absolute) | Raw wall-clock seconds |
| Summary table | All key numbers in one view |
