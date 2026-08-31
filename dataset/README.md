# Payroll dataset samples

This directory contains small samples of the structured payroll datasets used by the Payroll AI Agent.

The original datasets are published by the City of Houston through its open data portal:

- [City of Houston Payroll](https://data.houstontx.gov/dataset/payroll)

## Available samples

| Sample | Description |
|---|---|
| [`payroll-2023-sample.csv`](payroll-2023-sample.csv) | First 40 records from the 2023 payroll dataset |
| [`payroll-2024-sample.csv`](payroll-2024-sample.csv) | First 40 records from the 2024 payroll dataset |
| [`payroll-2025-sample.csv`](payroll-2025-sample.csv) | First 40 records from the 2025 payroll dataset |
| [`payroll-2026-sample.csv`](payroll-2026-sample.csv) | First 40 records from the 2026 payroll dataset |

These files are included only to demonstrate the CSV schema and example values used by the agent. They are not intended to be representative statistical samples or substitutes for the complete datasets.

The complete CSV files are not stored in this repository. During execution, the agent reads the complete datasets from Azure Blob Storage.