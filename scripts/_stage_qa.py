from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from _project_paths import ensure_stage_dirs


def write_basic_stage_qa(
    df: pd.DataFrame,
    stage_no: int,
    dataset_name: str,
    group_cols: Iterable[str] | None = None,
    numeric_cols: Iterable[str] | None = None,
) -> None:
    """Write basic row-count, missingness, counts, and numeric summaries."""
    dirs = ensure_stage_dirs(stage_no)
    tables_dir = dirs["01_descriptive_tables"]

    summary = pd.DataFrame(
        [
            {
                "dataset": dataset_name,
                "n_rows": len(df),
                "n_columns": df.shape[1],
                "n_duplicate_rows": int(df.duplicated().sum()),
            }
        ]
    )
    summary.to_csv(tables_dir / f"{dataset_name}_summary.csv", index=False)

    missing = (
        df.isna()
        .sum()
        .reset_index()
        .rename(columns={"index": "variable", 0: "n_missing"})
    )
    missing["pct_missing"] = 100 * missing["n_missing"] / max(len(df), 1)
    missing.to_csv(tables_dir / f"{dataset_name}_missingness.csv", index=False)

    if group_cols:
        for col in group_cols:
            if col not in df.columns:
                continue

            counts = (
                df[col]
                .astype("object")
                .where(df[col].notna(), "missing")
                .value_counts(dropna=False)
                .reset_index()
            )
            counts.columns = [col, "n_rows"]
            counts.to_csv(tables_dir / f"{dataset_name}_counts_by_{col}.csv", index=False)

    if numeric_cols:
        valid_numeric = [col for col in numeric_cols if col in df.columns]
        if valid_numeric:
            (
                df[valid_numeric]
                .apply(pd.to_numeric, errors="coerce")
                .describe()
                .T
                .to_csv(tables_dir / f"{dataset_name}_numeric_descriptive_statistics.csv")
            )


def write_input_output_audit(
    stage_no: int,
    script_name: str,
    inputs: Iterable[Path],
    outputs: Iterable[Path],
    notes: str = "",
) -> None:
    """Write a simple input/output audit table for the script run."""
    dirs = ensure_stage_dirs(stage_no)
    report_dir = dirs["03_stage_report"]

    rows = []

    for path in inputs:
        p = Path(path)
        rows.append(
            {
                "script_name": script_name,
                "io_type": "input",
                "path": str(p),
                "exists": p.exists(),
                "is_file": p.is_file(),
                "is_dir": p.is_dir(),
                "notes": notes,
            }
        )

    for path in outputs:
        p = Path(path)
        rows.append(
            {
                "script_name": script_name,
                "io_type": "output",
                "path": str(p),
                "exists": p.exists(),
                "is_file": p.is_file(),
                "is_dir": p.is_dir(),
                "notes": notes,
            }
        )

    audit = pd.DataFrame(rows)
    audit.to_csv(report_dir / f"{Path(script_name).stem}_input_output_audit.csv", index=False)
