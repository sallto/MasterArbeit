from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BENCH_DIR = ROOT / "data" / "bench-res"
OUTPUT_PATH = ROOT / "plots" / "output" / "spec_tpde_components.csv"

FILES = {
    "aarch64": BENCH_DIR / "res-spec-raw-ct-o1ir-aarch64",
    "x86_64": BENCH_DIR / "res-spec-raw-ct-o1ir-x86_64",
}

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

COMPONENTS = {
    "tpde": [
        "analysis",
        "emit_obj",
        "global_gen",
        "prepass",
        "tpde_cg",
        "tpde_pl",
        "tpde_spill",
    ],
    "tpde_old": [
        "analysis",
        "emit_obj",
        "global_gen",
        "prepass",
        "tpde_cg",
    ],
}


def column_name(arch: str, tool: str, component: str) -> str:
    return f"{arch}_{tool}_{component}"


def build_columns() -> list[str]:
    columns = ["benchmark"]
    for arch in FILES:
        for tool in ("tpde", "tpde_old"):
            for component in COMPONENTS[tool]:
                columns.append(column_name(arch, tool, component))
            columns.append(column_name(arch, tool, "remainder"))
    return columns


COLUMNS = build_columns()


def parse_compile_components(path: Path) -> dict[str, dict[str, dict[str, float]]]:
    values: dict[str, dict[str, dict[str, float]]] = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue

        benchmark_id, stage, tool, raw_value = parts
        if tool not in COMPONENTS:
            continue
        if stage not in {"codegen", *COMPONENTS["tpde"], *COMPONENTS["tpde_old"]}:
            continue

        benchmark_values = values.setdefault(benchmark_id, {})
        tool_values = benchmark_values.setdefault(tool, {})
        tool_values[stage] = float(raw_value)
    return values


def format_value(value: float | None) -> str:
    return "nan" if value is None else f"{value:.5f}"


def geometric_mean(values: list[float | None]) -> float | None:
    valid_values = [value for value in values if value is not None and value > 0]
    if not valid_values:
        return None
    return math.exp(sum(math.log(value) for value in valid_values) / len(valid_values))


def component_value(
    data: dict[str, dict[str, dict[str, dict[str, float]]]],
    benchmark_id: str,
    arch: str,
    tool: str,
    component: str,
) -> float | None:
    tool_values = data.get(arch, {}).get(benchmark_id, {}).get(tool)
    if tool_values is None:
        return None

    if component == "analysis":
        analysis = tool_values.get("analysis")
        if analysis is None:
            return None
        if tool != "tpde":
            return analysis
        tpde_pl = tool_values.get("tpde_pl")
        tpde_spill = tool_values.get("tpde_spill")
        if tpde_pl is None or tpde_spill is None:
            return None
        return analysis - tpde_pl - tpde_spill

    if component == "remainder":
        codegen = tool_values.get("codegen")
        if codegen is None:
            return None
        remainder = codegen
        for part in COMPONENTS[tool]:
            part_value = component_value(data, benchmark_id, arch, tool, part)
            if part_value is None:
                return None
            remainder -= part_value
        return remainder

    return tool_values.get(component)


def build_rows() -> list[dict[str, str]]:
    data = {
        arch: parse_compile_components(path)
        for arch, path in FILES.items()
    }

    benchmark_ids = sorted(
        {
            benchmark_id
            for arch_values in data.values()
            for benchmark_id in arch_values
        },
        key=int,
    )

    rows: list[dict[str, str]] = []
    column_values: dict[str, list[float | None]] = {column: [] for column in COLUMNS[1:]}

    for benchmark_id in benchmark_ids:
        row = {"benchmark": BENCHMARK_NAMES.get(benchmark_id, benchmark_id)}
        for arch in FILES:
            for tool in ("tpde", "tpde_old"):
                for component in [*COMPONENTS[tool], "remainder"]:
                    column = column_name(arch, tool, component)
                    value = component_value(data, benchmark_id, arch, tool, component)
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
