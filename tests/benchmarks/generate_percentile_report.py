"""Generate percentile report (p50/p95/p99) from benchmark JSON results."""

import json
import sys
from pathlib import Path


def calculate_percentile(data, percentile):
    """Calculate percentile from sorted data."""
    if not data:
        return None
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * percentile / 100
    lower = int(index)
    upper = lower + 1
    weight = index - lower

    if upper >= len(sorted_data):
        return sorted_data[lower]

    return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight


def extract_n_from_test_name(test_name):
    """Extract N (number of records) from test name."""
    import re

    # Our parametrized ids use "n{N}" (e.g. "[n1000-postgres-small]")
    match = re.search(r"n(\d+)", test_name)
    if match:
        return int(match.group(1))

    # Backwards-compatible: plain numeric parameter (e.g. "[1000]")
    match = re.search(r"\[(\d+)\]", test_name)
    return int(match.group(1)) if match else None


def extract_db_type_from_test_name(test_name):
    """Extract database type from test name."""
    import re

    # Look for database type in test name (postgres, mysql)
    match = re.search(r"\[(postgres|mysql)[-\]]", test_name)
    if not match:
        match = re.search(r"-(postgres|mysql)[-\]]", test_name)
    if not match:
        match = re.search(r"(postgres|mysql)", test_name)
    return match.group(1) if match else "unknown"


def extract_content_size_from_test_name(test_name):
    """Extract content size from test name."""
    import re

    match = re.search(r"\[small[-\]]", test_name)
    if not match:
        match = re.search(r"-small[-\]]", test_name)
    if not match:
        match = re.search(r"small", test_name)
    return match.group(0) if match else "small"


def extract_benchmark_id_from_test_name(test_name):
    """
    Extract a stable benchmark identifier from pytest-benchmark's name field.
    Examples:
      "test_benchmark_end_to_end_recall[n1000-sqlite-small]" -> "test_benchmark_end_to_end_recall"
      "test_benchmark_query_embedding_short" -> "test_benchmark_query_embedding_short"
    """
    import re

    match = re.match(r"([^\[]+)", test_name)
    return match.group(1) if match else test_name


def generate_percentile_report(json_file_path, max_n=None):
    """Generate p50/p95/p99 report from benchmark JSON.

    Args:
        json_file_path: Path to pytest-benchmark JSON output
        max_n: Optional maximum N value to include (filters out tests with N > max_n)
    """
    with open(json_file_path) as f:
        data = json.load(f)

    benchmarks = {}

    for benchmark in data.get("benchmarks", []):
        test_name = benchmark.get("name", "")
        benchmark_id = extract_benchmark_id_from_test_name(test_name)
        n = extract_n_from_test_name(test_name)

        # Skip if N is None (couldn't extract) or exceeds max_n filter
        if n is None:
            continue
        if max_n is not None and n > max_n:
            continue

        db_type = extract_db_type_from_test_name(test_name)
        content_size = extract_content_size_from_test_name(test_name)
        extra_info = benchmark.get("extra_info", {}) or {}

        stats = benchmark.get("stats", {})
        times = stats.get("data", [])

        if not times:
            continue

        peak_rss_bytes = extra_info.get("peak_rss_bytes")

        p50 = calculate_percentile(times, 50)
        p95 = calculate_percentile(times, 95)
        p99 = calculate_percentile(times, 99)

        # Create composite key. We include benchmark_id so different benchmark types
        # don't overwrite each other (e.g. end-to-end vs db fetch for same N/db/size).
        key = (benchmark_id, n, db_type, content_size)

        benchmarks[key] = {
            "benchmark_id": benchmark_id,
            "n": n,
            "db_type": db_type,
            "content_size": content_size,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "mean": stats.get("mean", 0),
            "min": stats.get("min", 0),
            "max": stats.get("max", 0),
            "peak_rss_bytes": peak_rss_bytes,
        }

    return benchmarks


def generate_report(benchmarks, output_format="table"):
    """Generate percentile report in specified format as string."""
    lines = []

    if output_format == "table":
        lines.append("\n" + "=" * 100)
        lines.append(
            "PERCENTILE REPORT (p50/p95/p99) per N, Database Type, and Content Size"
        )
        lines.append("=" * 100)
        lines.append(
            f"{'Benchmark':<34} {'N':<8} {'DB':<12} {'Size':<8} {'p50 (ms)':<12} {'p95 (ms)':<12} "
            f"{'p99 (ms)':<12} {'Mean (ms)':<12} {'Peak RSS (MB)':<14}"
        )
        lines.append("-" * 100)

        for key in sorted(benchmarks.keys()):
            stats = benchmarks[key]
            peak_rss_mb = (
                (stats["peak_rss_bytes"] / (1024 * 1024))
                if stats.get("peak_rss_bytes") is not None
                else None
            )
            lines.append(
                f"{stats['benchmark_id']:<34} "
                f"{stats['n']:<8} "
                f"{stats['db_type']:<12} "
                f"{stats['content_size']:<8} "
                f"{stats['p50'] * 1000:<12.4f} "
                f"{stats['p95'] * 1000:<12.4f} "
                f"{stats['p99'] * 1000:<12.4f} "
                f"{stats['mean'] * 1000:<12.4f} "
                f"{(f'{peak_rss_mb:.1f}' if peak_rss_mb is not None else ''):<14}"
            )
        lines.append("=" * 100)
        return "\n".join(lines)

    elif output_format == "csv":
        lines.append(
            "benchmark_id,N,db_type,content_size,p50_ms,p95_ms,p99_ms,mean_ms,min_ms,max_ms,peak_rss_mb"
        )
        for key in sorted(benchmarks.keys()):
            stats = benchmarks[key]
            peak_rss_mb = (
                (stats["peak_rss_bytes"] / (1024 * 1024))
                if stats.get("peak_rss_bytes") is not None
                else None
            )
            lines.append(
                f"{stats['benchmark_id']},"
                f"{stats['n']},"
                f"{stats['db_type']},"
                f"{stats['content_size']},"
                f"{stats['p50'] * 1000:.4f},"
                f"{stats['p95'] * 1000:.4f},"
                f"{stats['p99'] * 1000:.4f},"
                f"{stats['mean'] * 1000:.4f},"
                f"{stats['min'] * 1000:.4f},"
                f"{stats['max'] * 1000:.4f},"
                f"{(f'{peak_rss_mb:.4f}' if peak_rss_mb is not None else '')}"
            )
        return "\n".join(lines)

    elif output_format == "json":
        output = {}
        for key in sorted(benchmarks.keys()):
            stats = benchmarks[key]
            output_key = f"{stats['benchmark_id']}_{stats['n']}_{stats['db_type']}_{stats['content_size']}"
            peak_rss_mb = (
                (stats["peak_rss_bytes"] / (1024 * 1024))
                if stats.get("peak_rss_bytes") is not None
                else None
            )
            output[output_key] = {
                "benchmark_id": stats["benchmark_id"],
                "n": stats["n"],
                "db_type": stats["db_type"],
                "content_size": stats["content_size"],
                "p50_ms": stats["p50"] * 1000,
                "p95_ms": stats["p95"] * 1000,
                "p99_ms": stats["p99"] * 1000,
                "mean_ms": stats["mean"] * 1000,
                "min_ms": stats["min"] * 1000,
                "max_ms": stats["max"] * 1000,
                "peak_rss_mb": peak_rss_mb,
            }
        return json.dumps(output, indent=2)

    return ""


def print_report(benchmarks, output_format="table"):
    """Print percentile report to stdout."""
    print(generate_report(benchmarks, output_format))


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python generate_percentile_report.py <benchmark.json> [format] [output_file] [max_n]"
        )
        print("  format: table (default), csv, or json")
        print("  output_file: optional file path to write report (default: stdout)")
        print(
            "  max_n: optional maximum N value to include (filters out tests with N > max_n)"
        )
        sys.exit(1)

    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"Error: File not found: {json_file}")
        sys.exit(1)

    output_format = sys.argv[2] if len(sys.argv) > 2 else "table"

    if output_format not in ["table", "csv", "json"]:
        print(f"Error: Invalid format '{output_format}'. Use: table, csv, or json")
        sys.exit(1)

    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    max_n = int(sys.argv[4]) if len(sys.argv) > 4 else None

    benchmarks = generate_percentile_report(json_file, max_n=max_n)

    if not benchmarks:
        print("No benchmark data found with N values.")
        if max_n:
            print(f"(Filtered to N <= {max_n})")
        sys.exit(1)

    report = generate_report(benchmarks, output_format)

    if output_file:
        output_path = Path(output_file)
        output_path.write_text(report)
        print(f"Report written to: {output_path}")
        if max_n:
            print(f"(Filtered to N <= {max_n})")
    else:
        print(report)


if __name__ == "__main__":
    main()
