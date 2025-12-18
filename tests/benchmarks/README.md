# AWS EC2 Benchmark Guide

This guide explains how to run Memori benchmarks on an EC2 instance in the same VPC as your AWS database (RDS Postgres or MySQL).

## Setup on EC2

1. **SSH into EC2**:
   ```bash
   ssh ec2-user@your-ec2-ip
   ```

2. **Run Setup**:
   Copy `tests/benchmarks/setup_ec2_benchmarks.sh` to your EC2 or clone the repo and run it:
   ```bash
   chmod +x tests/benchmarks/setup_ec2_benchmarks.sh
   ./tests/benchmarks/setup_ec2_benchmarks.sh
   ```

## Running Benchmarks

The `run_benchmarks_ec2.sh` script is flexible and handles automatic CSV generation.

### Environment Variables

- `DB_TYPE`: `postgres` (default) or `mysql`
- `TEST_TYPE`: `all` (default), `end_to_end`, `db_retrieval`, `semantic_search`, `embedding`
- `BENCHMARK_POSTGRES_URL`: Connection string for Postgres
- `BENCHMARK_MYSQL_URL`: Connection string for MySQL

### Examples

#### Run all Postgres benchmarks
```bash
export BENCHMARK_POSTGRES_URL="CHANGEME"
DB_TYPE=postgres TEST_TYPE=all ./tests/benchmarks/run_benchmarks_ec2.sh
```

#### Run only End-to-End MySQL benchmarks
```bash
export BENCHMARK_MYSQL_URL="CHANGEME"
DB_TYPE=mysql TEST_TYPE=end_to_end ./tests/benchmarks/run_benchmarks_ec2.sh
```

## Results

All results are automatically saved to the `./results` directory with a timestamp to prevent overwriting:
- JSON output: `results_{db}_{type}_{timestamp}.json`
- **CSV Report**: `report_{db}_{type}_{timestamp}.csv`

To download the CSV reports to your local machine:
```bash
scp ec2-user@your-ec2-ip:~/Memori/results/report_*.csv ./local_results/
```

## Database Connection Requirements

Ensure the EC2 Security Group allows outbound traffic to the database on ports 5432 (Postgres) or 3306 (MySQL).
The database must be in the same VPC or accessible via VPC Peering/Transit Gateway.
