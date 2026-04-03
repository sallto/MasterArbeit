from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "data" / "bench-res"
OUTPUT_PATH = ROOT / "plots" / "output" / "spec_compile_speedup.csv"

BENCHMARK_NAMES = {
    "600": "600.perl",
    "602": "602.gcc",
    "605": "605.mcf",
    "620": "620.omnetpp",
    "623": "623.xalanc",
    "625": "625.x264",
    "631": "631.deepsjeng",
    "641": "641.leela",
    "648": "648.exchange2",
    "657": "657.xz",
}

COLUMNS = [
    "benchmark",
    "aarch64-clang",
    "aarch64-tpde",
    "o1-aarch64-clang",
    "o1-aarch64-tpde",
    "o1ir-aarch64-clang",
    "o1ir-aarch64-tpde",
    "o1ir-aarch64-tpde-old",
    "x86_64-clang",
    "x86_64-tpde",
    "o1-x86_64-clang",
    "o1-x86_64-tpde",
    "o1ir-x86_64-clang",
    "o1ir-x86_64-tpde",
    "o1ir-x86_64-tpde-old",
]

# Compile-time speedups are derived from the `codegen` stage in the ct files.
# The repository only contains an O1 clang baseline for x86_64, so every
# computed speedup is relative to that configuration.
FILES = {
    "o1-x86_64-clang": ("res-spec-raw-ct-o1-x86_64", "clang"),
    "o1-x86_64-tpde": ("res-spec-raw-ct-o1-x86_64", "tpde"),
    "o1-aarch64-clang": ("res-spec-raw-ct-o1-aarch64", "clang"),
    "o1ir-aarch64-clang": ("res-spec-raw-ct-o1ir-aarch64", "clang"),
    "o1ir-aarch64-tpde": ("res-spec-raw-ct-o1ir-aarch64", "tpde"),
    "o1ir-aarch64-tpde-old": ("res-spec-raw-ct-o1ir-aarch64", "tpde_old"),
    "o1ir-x86_64-clang": ("res-spec-raw-ct-o1ir-x86_64", "clang"),
    "o1ir-x86_64-tpde": ("res-spec-raw-ct-o1ir-x86_64", "tpde"),
    "o1ir-x86_64-tpde-old": ("res-spec-raw-ct-o1ir-x86_64", "tpde_old"),
}


BASELINES = {
    "aarch64": "o1-aarch64-clang",
    "x86_64": "o1-x86_64-clang",
}


def parse_compile_file(path: Path, tool: str) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue

        benchmark_id, stage, entry_tool, value = parts
        if stage != "codegen" or entry_tool != tool:
            continue

        values[benchmark_id] = float(value)
    return values


def format_value(value: float | None) -> str:
    return "nan" if value is None else f"{value:.5f}"


def speedup(
    runtimes: dict[str, dict[str, float | None]],
    benchmark_id: str,
    column: str,
) -> float | None:
    if column == "benchmark":
        return None

    arch = "aarch64" if "aarch64" in column else "x86_64"
    baseline_key = BASELINES[arch]
    baseline_runtime = runtimes.get(baseline_key, {}).get(benchmark_id)
    runtime = runtimes.get(column, {}).get(benchmark_id)
    if baseline_runtime is None or runtime is None:
        return None
    return baseline_runtime / runtime


def geometric_mean(values: list[float | None]) -> float | None:
    valid_values = [value for value in values if value is not None and value > 0]
    if not valid_values:
        return None
    return math.exp(sum(math.log(value) for value in valid_values) / len(valid_values))


def build_rows() -> list[dict[str, str]]:
    compile_times = {
        config: parse_compile_file(BENCH_DIR / filename, tool)
        for config, (filename, tool) in FILES.items()
    }

    benchmark_ids = sorted(
        {
            benchmark_id
            for values in compile_times.values()
            for benchmark_id, compile_time in values.items()
            if compile_time is not None
        },
        key=int,
    )

    rows: list[dict[str, str]] = []
    column_values: dict[str, list[float | None]] = {column: [] for column in COLUMNS[1:]}
    for benchmark_id in benchmark_ids:
        row = {"benchmark": BENCHMARK_NAMES.get(benchmark_id, benchmark_id)}
        for column in COLUMNS[1:]:
            value = speedup(compile_times, benchmark_id, column)
            column_values[column].append(value)
            row[column] = format_value(value)
        rows.append(row)

    geomean_row = {"benchmark": "geomean"}
    for column in COLUMNS[1:]:
        geomean_row[column] = format_value(geometric_mean(column_values[column]))
    rows.append(geomean_row)

    return rows


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    with OUTPUT_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
