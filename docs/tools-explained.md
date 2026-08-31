# Agent tools and capabilities

The Payroll AI Agent combines deterministic payroll-data operations
with regulatory document retrieval. The language model interprets the
user's request and selects the capability whose description and
parameters best match the requested task.

The agent's capabilities are registered in `main.py`, but their
implementations are distributed across three parts of the project:

| Location | Responsibility |
|---|---|
| `agent_tools.py` | Payroll calculations and data-quality checks |
| `workflow.py` | Multi-step comparison of the 2025 and 2026 payroll datasets |
| `azure.yaml` | Configuration of the Azure AI Search tool exposed through Foundry Toolbox |


## Structured payroll tools

The structured-data tools analyse payroll CSV files loaded from Azure
Blob Storage through `payroll_data.py`.

Available payroll years are 2023, 2024, 2025, and 2026.

### `get_salary_statistics`

Calculates Annual Base Salary statistics for a selected payroll year
and Pay Grade.

**Parameters**

| Parameter | Description |
|---|---|
| `year` | Payroll year to analyse |
| `pay_grade` | Pay Grade to use as a filter |

**Returned information**

- Number of matching payroll records.
- Number of valid salary records.
- Number of missing salary values.
- Mean Annual Base Salary.
- Median Annual Base Salary.
- Standard deviation.
- Minimum salary.
- Maximum salary.

Pay Grades are normalized before filtering so that differences in
capitalization or surrounding whitespace do not affect the match.

**Example request**

```text
Calculate the Annual Base Salary statistics for Pay Grade 13 in 2026.
```
