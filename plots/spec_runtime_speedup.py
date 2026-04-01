from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "data" / "bench-res"
OUTPUT_PATH = ROOT / "plots" / "output" / "spec_runtime_speedup.csv"

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

# The repository only contains runtime files for these configurations.
# Each speedup is computed relative to the matching clang O1 runtime on the
# same architecture: speedup = runtime(o1-<arch>-clang) / runtime(config).
FILES = {
    "o1-aarch64-clang": "res-spec-raw-rt-o1-aarch64-clang",
    "o1-x86_64-clang": "res-spec-raw-rt-o1-x86_64-clang",
    "o1ir-aarch64-clang": "res-spec-raw-rt-o1ir-aarch64-clang",
    "o1ir-aarch64-tpde": "res-spec-raw-rt-o1ir-aarch64-tpde",
    "o1ir-aarch64-tpde-old": "res-spec-raw-rt-o1ir-aarch64-tpde-old",
    "o1ir-x86_64-clang": "res-spec-raw-rt-o1ir-x86_64-clang",
    "o1ir-x86_64-tpde": "res-spec-raw-rt-o1ir-x86_64-tpde",
    "o1ir-x86_64-tpde-old": "res-spec-raw-rt-o1ir-x86_64-tpde-old",
}

BASELINES = {
    "aarch64": "o1-aarch64-clang",
    "x86_64": "o1-x86_64-clang",
}


def parse_runtime_file(path: Path) -> dict[str, float | None]:
    values: dict[str, float | None] = {}
    for line in path.read_text().splitlines():
        benchmark, runtime = line.split(":", 1)
        runtime = runtime.strip()
        values[benchmark.strip()] = float(runtime) if runtime else None
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


def build_rows() -> list[dict[str, str]]:
    runtimes = {
        config: parse_runtime_file(BENCH_DIR / filename)
        for config, filename in FILES.items()
    }

    benchmark_ids = sorted(
        {
            benchmark_id
            for values in runtimes.values()
            for benchmark_id, runtime in values.items()
            if runtime is not None
        },
        key=int,
    )

    rows: list[dict[str, str]] = []
    for benchmark_id in benchmark_ids:
        row = {"benchmark": BENCHMARK_NAMES.get(benchmark_id, benchmark_id)}
        for column in COLUMNS[1:]:
            row[column] = format_value(speedup(runtimes, benchmark_id, column))
        rows.append(row)
    
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
