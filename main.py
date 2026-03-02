"""tablers-benchmark: PDF table extraction benchmark on ICDAR 2013.

Compares tablers, pymupdf, pdfplumber, and camelot across two dimensions:
  - Speed  : total processing time (shown relative to the fastest)
  - Accuracy: table detection F1, TEDS score, and structure accuracy

Usage
-----
    uv run python main.py                              # uses bundled dataset
    uv run python main.py --max-docs 10               # quick smoke-test
    uv run python main.py --dataset path/to/icdar2013 # custom dataset path
    uv run python main.py --output results.png        # custom output path
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

from benchmark.datasets import load_icdar2013
from benchmark.extractors import EXTRACTORS
from benchmark.metrics import BenchmarkResult, compute_benchmark_result

# Colour palette (tablers / pymupdf / pdfplumber / camelot)
_COLORS = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0']

# Number of runs for tablers; average time is used for comparison (it is much faster than others)
_TABLERS_RUNS = 10


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

def run_benchmark(
    dataset_root: str,
    max_docs: int | None = None,
) -> list[BenchmarkResult]:
    print(f"Loading ICDAR 2013 from: {dataset_root}")
    documents = load_icdar2013(dataset_root)

    if not documents:
        print(
            "No documents found.  Check the path and make sure the PDFs are "
            "present alongside the ground-truth XMLs."
        )
        sys.exit(1)

    if max_docs:
        documents = documents[:max_docs]

    print(f"Loaded {len(documents)} document(s).\n")

    # Build GT dict  {pdf_path_str: {page_num: [grid, ...]}}
    gt_per_doc: dict[str, dict[int, list]] = {}
    for doc in documents:
        key = str(doc.pdf_path)
        gt_per_doc[key] = {}
        for table in doc.tables:
            gt_per_doc[key].setdefault(table.page, []).append(table.to_grid())

    results: list[BenchmarkResult] = []
    for lib_name, extractor in EXTRACTORS.items():
        print(f"Running {lib_name} …")
        if lib_name == 'tablers':
            print(f"  (each document × {_TABLERS_RUNS} runs, using average time for comparison)")
        pred_per_doc: dict[str, dict[int, list]] = {}
        total_time = 0.0
        errors = 0

        for doc in documents:
            key = str(doc.pdf_path)
            try:
                if lib_name == 'tablers':
                    # Run tablers _TABLERS_RUNS times and use average time for fair comparison
                    run_times: list[float] = []
                    for _ in range(_TABLERS_RUNS):
                        page_tables, elapsed = extractor(doc.pdf_path)  # type: ignore[operator]
                        run_times.append(elapsed)
                    elapsed = sum(run_times) / len(run_times)
                    pred_per_doc[key] = page_tables
                    total_time += elapsed
                else:
                    page_tables, elapsed = extractor(doc.pdf_path)  # type: ignore[operator]
                    pred_per_doc[key] = page_tables
                    total_time += elapsed
            except Exception as exc:
                print(f"  [warn] {doc.pdf_path.name}: {exc}")
                pred_per_doc[key] = {}
                errors += 1

        result = compute_benchmark_result(
            library=lib_name,
            pred_per_doc=pred_per_doc,
            gt_per_doc=gt_per_doc,
            processing_time=total_time,
        )
        results.append(result)

        print(f"  time      : {result.processing_time:.2f} s")
        print(f"  det F1    : {result.detection_f1:.3f}  "
              f"(P={result.detection_precision:.3f}  R={result.detection_recall:.3f})")
        print(f"  TEDS      : {result.teds_score:.3f}")
        print(f"  rows/cols : {result.row_accuracy:.3f} / {result.col_accuracy:.3f}")
        if errors:
            print(f"  errors    : {errors}")
        print()

    return results


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def _bar(ax: plt.Axes, libs: list[str], values: list[float],
         title: str, ylabel: str, fmt: str = '.3f',
         ylim_top: float | None = None) -> None:
    bars = ax.bar(libs, values, color=_COLORS[:len(libs)], alpha=0.85, zorder=3)
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=9)
    top = ylim_top if ylim_top is not None else max(values) * 1.25 if max(values) > 0 else 1
    ax.set_ylim(0, top)
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    ax.tick_params(axis='x', labelsize=9)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + top * 0.02,
            f'{val:{fmt}}',
            ha='center', va='bottom', fontsize=8,
        )


def _grouped_bar(ax: plt.Axes, libs: list[str],
                 series: list[tuple[str, list[float], str]],
                 title: str, ylabel: str) -> None:
    """Multiple series side-by-side."""
    x = np.arange(len(libs))
    n = len(series)
    width = 0.8 / n
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(libs, fontsize=9)
    ax.set_ylim(0, 1.25)
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    for i, (label, vals, colour) in enumerate(series):
        offset = (i - (n - 1) / 2) * width
        bars = ax.bar(x + offset, vals, width, label=label, color=colour, alpha=0.85, zorder=3)
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f'{val:.3f}', ha='center', va='bottom', fontsize=7,
            )
    ax.legend(fontsize=8)


def plot_results(results: list[BenchmarkResult], output_path: str) -> None:
    libs = [r.library for r in results]

    fig = plt.figure(figsize=(18, 11))
    fig.suptitle(
        'PDF Table Extraction Benchmark  ·  ICDAR 2013 Dataset\n'
        'Speed (lower is better)  ·  Accuracy metrics (higher is better)',
        fontsize=13, fontweight='bold', y=0.98,
    )
    gs = gridspec.GridSpec(2, 4, figure=fig, hspace=0.45, wspace=0.38)

    # ── Row 0 ───────────────────────────────────────────────────────────────

    # 1. Relative time
    times = [r.processing_time for r in results]
    base = min(times)
    rel = [t / base for t in times]
    ax0 = fig.add_subplot(gs[0, 0])
    _bar(ax0, libs, rel, 'Processing Time\n(relative to fastest)', '× baseline', fmt='.2f')

    # 2. TEDS
    ax1 = fig.add_subplot(gs[0, 1])
    _bar(ax1, libs, [r.teds_score for r in results],
         'TEDS Score\n(structure + content)', 'TEDS', ylim_top=1.15)

    # 3. Detection F1
    ax2 = fig.add_subplot(gs[0, 2])
    _bar(ax2, libs, [r.detection_f1 for r in results],
         'Table Detection F1', 'F1', ylim_top=1.15)

    # 4. Structure accuracy (rows vs cols)
    ax3 = fig.add_subplot(gs[0, 3])
    _grouped_bar(ax3, libs, [
        ('Row accuracy', [r.row_accuracy for r in results], '#42A5F5'),
        ('Col accuracy', [r.col_accuracy for r in results], '#EF5350'),
    ], 'Structure Accuracy\n(row / col count match)', 'Accuracy')

    # ── Row 1 ───────────────────────────────────────────────────────────────

    # 5. Detection precision & recall
    ax4 = fig.add_subplot(gs[1, 0:2])
    _grouped_bar(ax4, libs, [
        ('Precision', [r.detection_precision for r in results], '#66BB6A'),
        ('Recall',    [r.detection_recall    for r in results], '#FFA726'),
        ('F1',        [r.detection_f1        for r in results], '#AB47BC'),
    ], 'Table Detection  —  Precision / Recall / F1', 'Score')

    # 6. Absolute processing times
    ax5 = fig.add_subplot(gs[1, 2])
    _bar(ax5, libs, times, 'Processing Time\n(absolute seconds)', 'seconds', fmt='.2f')

    # 7. Summary table
    ax6 = fig.add_subplot(gs[1, 3])
    ax6.axis('off')
    col_labels = ['Library', 'Time (s)', 'F1', 'TEDS', 'Row acc.', 'Col acc.']
    rows_data = [
        [
            r.library,
            f'{r.processing_time:.2f}',
            f'{r.detection_f1:.3f}',
            f'{r.teds_score:.3f}',
            f'{r.row_accuracy:.3f}',
            f'{r.col_accuracy:.3f}',
        ]
        for r in results
    ]
    tbl = ax6.table(cellText=rows_data, colLabels=col_labels, loc='center', cellLoc='center')
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)
    tbl.auto_set_column_width(col=list(range(len(col_labels))))
    tbl.scale(1.0, 2.0)
    ax6.set_title('Summary', fontsize=10, fontweight='bold')

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Chart saved to: {output_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _print_summary(results: list[BenchmarkResult]) -> None:
    sep = '─' * 68
    print(sep)
    print(f"{'Library':<12} {'Time(s)':>8} {'Prec':>7} {'Rec':>7} {'F1':>7} "
          f"{'TEDS':>7} {'RowAcc':>7} {'ColAcc':>7}")
    print(sep)
    for r in results:
        print(
            f"{r.library:<12} {r.processing_time:>8.2f} "
            f"{r.detection_precision:>7.3f} {r.detection_recall:>7.3f} "
            f"{r.detection_f1:>7.3f} {r.teds_score:>7.3f} "
            f"{r.row_accuracy:>7.3f} {r.col_accuracy:>7.3f}"
        )
    print(sep)
    print(f"GT tables: {results[0].total_gt_tables}  "
          f"(matched per library: "
          + "  ".join(f"{r.library}={r.total_matched_tables}" for r in results)
          + ")")


def main() -> None:
    # Default dataset path: <project_root>/icdar2013-competition-dataset-with-gt
    _here = Path(__file__).parent
    _default_dataset = _here / 'icdar2013-competition-dataset-with-gt'

    parser = argparse.ArgumentParser(
        description='PDF table extraction benchmark — ICDAR 2013 dataset',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--dataset', '-d',
        default=str(_default_dataset),
        help=(
            'Path to the ICDAR 2013 dataset root '
            f'(default: {_default_dataset})'
        ),
    )
    parser.add_argument(
        '--max-docs', '-n', type=int, default=None,
        help='Limit to first N documents (default: all)',
    )
    parser.add_argument(
        '--output', '-o', default='table_extraction_benchmark.png',
        help='Output chart path (default: table_extraction_benchmark.png)',
    )
    args = parser.parse_args()

    results = run_benchmark(args.dataset, args.max_docs)
    _print_summary(results)
    plot_results(results, args.output)


if __name__ == '__main__':
    main()
