#!/bin/bash
# Shared benchmark execution functions for AWS EC2 environment

set -e

# Get script location to handle relative paths correctly
BENCHMARK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$BENCHMARK_DIR/../.." && pwd)"

# Default settings
DB_TYPE=${DB_TYPE:-"postgres"}
TEST_TYPE=${TEST_TYPE:-"all"} # options: all, end_to_end, db_retrieval, semantic_search, embedding
OUTPUT_DIR=${OUTPUT_DIR:-"$REPO_ROOT/results"}

mkdir -p "$OUTPUT_DIR"

run_benchmarks() {
    local db=$1
    local type=$2
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local output_json="$OUTPUT_DIR/results_${db}_${type}_${timestamp}.json"
    local output_csv="$OUTPUT_DIR/report_${db}_${type}_${timestamp}.csv"

    echo "===================================================="
    echo "Running benchmarks for: DB=$db, Type=$type"
    echo "Output JSON: $output_json"
    echo "Output CSV:  $output_csv"
    echo "===================================================="

    # Determine pytest filter (-k) based on test type
    local filter=""
    case $type in
        "end_to_end") filter="TestEndToEndRecallBenchmarks" ;;
        "db_retrieval") filter="DatabaseEmbeddingRetrievalBenchmarks or DatabaseFactContentRetrievalBenchmarks" ;;
        "semantic_search") filter="TestSemanticSearchBenchmarks" ;;
        "embedding") filter="TestQueryEmbeddingBenchmarks" ;;
        "all") filter="" ;;
        *) echo "Unknown test type: $type"; exit 1 ;;
    esac

    # Add database filter
    if [[ -n "$filter" ]]; then
        filter="($filter) and $db"
    else
        filter="$db"
    fi

    # Run benchmarks from repo root
    (
        cd "$REPO_ROOT"
        uv run pytest -m benchmark \
            --benchmark-only \
            tests/benchmarks/test_recall_benchmarks.py \
            -k "$filter" \
            -v \
            --benchmark-json="$output_json"

        # Automatically convert to CSV
        if [[ -f "$output_json" ]]; then
            echo "Converting results to CSV..."
            uv run python tests/benchmarks/generate_percentile_report.py \
                "$output_json" \
                csv \
                "$output_csv"
            echo "CSV Report generated: $output_csv"
        else
            echo "Warning: JSON results file not found, skipping CSV generation."
        fi
    )
}

# If script is executed directly (not sourced), run based on env vars
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Print usage info if help requested
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        echo "Usage: DB_TYPE=[postgres|mysql] TEST_TYPE=[all|end_to_end|db_retrieval|semantic_search|embedding] $0"
        exit 0
    fi

    run_benchmarks "$DB_TYPE" "$TEST_TYPE"

    echo "===================================================="
    echo "Benchmark Run Complete"
    echo "===================================================="
fi
