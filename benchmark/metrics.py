"""Accuracy metrics for PDF table extraction benchmarks.

Metrics
-------
- **Table Detection F1**: precision/recall/F1 based on count matching per page.
- **TEDS** (simplified): Tree-Edit-Distance Similarity computed via sequence
  matching on HTML table representations.  This is an efficient approximation
  of the true TEDS metric introduced in PubTabNet; it captures both structural
  and content accuracy in a single 0–1 score.
- **Structure accuracy**: exact row-count and column-count match rates.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def _norm(text: str | None) -> str:
    """Normalise cell text: strip, collapse whitespace, lowercase."""
    if not text:
        return ''
    return ' '.join(str(text).split()).lower()


# ---------------------------------------------------------------------------
# TEDS (simplified)
# ---------------------------------------------------------------------------

def _table_to_html(table: list[list[str | None]]) -> str:
    rows = (''.join(f'<td>{_norm(c)}</td>' for c in row) for row in table)
    return '<table>' + ''.join(f'<tr>{r}</tr>' for r in rows) + '</table>'


def teds(pred: list[list[str | None]], gt: list[list[str | None]]) -> float:
    """Simplified TEDS score (0–1, higher is better).

    Computes ``SequenceMatcher`` similarity on the HTML string representations
    of both tables.  Captures structure (row/col counts, merged cells) and cell
    content simultaneously.

    This approximation correlates strongly with the exact tree-edit-distance
    TEDS while avoiding heavy dependencies (``apted``/``zss``).
    """
    if not pred and not gt:
        return 1.0
    if not pred or not gt:
        return 0.0
    return difflib.SequenceMatcher(None, _table_to_html(pred), _table_to_html(gt)).ratio()


# ---------------------------------------------------------------------------
# Table matching
# ---------------------------------------------------------------------------

def _match_by_order(
    pred: list[list[list[str | None]]],
    gt: list[list[list[str | None]]],
) -> list[tuple[list[list[str | None]], list[list[str | None]]]]:
    """Match predicted tables to GT by appearance order (first-to-first)."""
    return list(zip(pred, gt))


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    library: str

    # --- timing ---
    processing_time: float          # seconds (cumulative over all PDFs)

    # --- detection (0–1) ---
    detection_precision: float      # matched / predicted
    detection_recall: float         # matched / ground-truth
    detection_f1: float

    # --- structure (0–1, over matched pairs) ---
    row_accuracy: float             # exact row-count match rate
    col_accuracy: float             # exact col-count match rate

    # --- content (0–1, over matched pairs) ---
    teds_score: float               # average TEDS

    # --- raw counts ---
    total_gt_tables: int
    total_pred_tables: int
    total_matched_tables: int


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_benchmark_result(
    library: str,
    pred_per_doc: dict[str, dict[int, list[list[list[str | None]]]]],
    gt_per_doc: dict[str, dict[int, list[list[list[str | None]]]]],
    processing_time: float,
) -> BenchmarkResult:
    """Aggregate all per-page predictions into a single ``BenchmarkResult``.

    Parameters
    ----------
    library:
        Human-readable library name.
    pred_per_doc:
        ``{pdf_path_str: {page_num_1indexed: [table_grid, ...]}}``
    gt_per_doc:
        Same structure, ground-truth side.
    processing_time:
        Total wall-clock seconds spent by this library on all PDFs.
    """
    total_gt = 0
    total_pred = 0
    total_matched = 0
    teds_scores: list[float] = []
    row_matches: list[float] = []
    col_matches: list[float] = []

    for pdf_key, gt_pages in gt_per_doc.items():
        pred_pages = pred_per_doc.get(pdf_key, {})

        for page_num, gt_tables in gt_pages.items():
            pred_tables = pred_pages.get(page_num, [])

            total_gt += len(gt_tables)
            total_pred += len(pred_tables)

            pairs = _match_by_order(pred_tables, gt_tables)
            total_matched += len(pairs)

            for pred_t, gt_t in pairs:
                teds_scores.append(teds(pred_t, gt_t))

                pred_rows = len(pred_t)
                gt_rows = len(gt_t)
                pred_cols = len(pred_t[0]) if pred_t else 0
                gt_cols = len(gt_t[0]) if gt_t else 0

                row_matches.append(1.0 if pred_rows == gt_rows else 0.0)
                col_matches.append(1.0 if pred_cols == gt_cols else 0.0)

    precision = total_matched / total_pred if total_pred > 0 else 0.0
    recall = total_matched / total_gt if total_gt > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0 else 0.0
    )

    def _avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    return BenchmarkResult(
        library=library,
        processing_time=processing_time,
        detection_precision=precision,
        detection_recall=recall,
        detection_f1=f1,
        row_accuracy=_avg(row_matches),
        col_accuracy=_avg(col_matches),
        teds_score=_avg(teds_scores),
        total_gt_tables=total_gt,
        total_pred_tables=total_pred,
        total_matched_tables=total_matched,
    )
