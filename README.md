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

All libraries are used in default settings. `camelot` uses the `lattice` flavor.

---

## Dataset — ICDAR 2013 Table Competition

This benchmark uses the **ICDAR 2013 Table Competition dataset**, released as part of the table detection and structure recognition competition at the International Conference on Document Analysis and Recognition (ICDAR 2013).

It is important to note that ICDAR 2013 hosted multiple independent competitions (e.g., Robust Reading for scene text and Table Competition for document tables). The dataset used in this benchmark corresponds specifically to the **Table Competition track**, not to the scene text datasets from the same conference.

### Scope and Purpose

The ICDAR 2013 Table Competition dataset was designed to evaluate algorithms for:

- **Table region detection** (localizing table areas in PDF documents)
- **Table structure recognition** (recovering row/column structure and cell boundaries)

The documents are **born-digital PDFs** (not scanned images), making the dataset particularly relevant for PDF-native table extraction systems.

### Data Sources

The dataset consists of government and institutional PDF documents collected from two public sources:

- European Union (EU) publications
- United States (US) government publications

The competition organizers did not define or publish any formal comparison of structural complexity between these two subsets. Therefore, no claims regarding relative difficulty or layout complexity (e.g., “EU tables are more complex than US tables”) should be made unless supported by independent quantitative analysis.

### Dataset Size

The dataset contains:

- 67 PDF documents
- 158 annotated tables in total

The documents are divided into EU and US subsets according to their source, as originally released by the competition organizers.

### Annotation Format

Each document is accompanied by ground-truth XML files:

- `*-reg.xml` — Table region annotations (bounding boxes)
- `*-str.xml` — Full structural annotations (rows, columns, cells, and content)

This separation enables evaluation at two levels:

1. **Detection-level evaluation** (table localization only)
2. **Structure-level evaluation** (full table reconstruction)

### Benchmark Relevance

The ICDAR 2013 Table Competition dataset remains one of the earliest standardized benchmarks for born-digital PDF table extraction. It is frequently used in research and engineering comparisons due to:

- Public availability
- Structured ground truth
- Clear evaluation protocol
- Manageable dataset size for reproducible benchmarking

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
