"""Validate, compare, and interpret two payroll periods.

The workflow loads structured payroll data from Azure Blob Storage,
validates the required columns, calculates comparable metrics, and
uses a Microsoft Foundry agent to interpret the observed changes.

Adapted from the Microsoft Agent Framework functional workflow sample:
https://github.com/microsoft/agent-framework/blob/main/python/samples/
01-get-started/05_functional_workflow_with_agents.py
"""

# Common libraries
import os
from typing import Any

# Data analysis
import pandas as pd


# Microsoft Agent Framework
from agent_framework import (
    Agent,
    step,
    tool,
    workflow,
)
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential


# Environment variables
from dotenv import load_dotenv


# Payroll data stored in Azure Blob Storage
from payroll_data import (
    AVAILABLE_PAYROLL_YEARS,
    load_payroll_dataframe,
)


load_dotenv()


REQUIRED_COLUMNS = {
    "Department Name",
    "Pay Grade",
    "Annual Base Salary",
    "Gross Pay",
    "Base Pay",
    "Overtime Pay",
}


#=====================================================
# Foundry client for the workflow interpreter agent
#=====================================================

model_name = (
    os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    or os.getenv("FOUNDRY_MODEL_NAME")
)

if not model_name:
    raise RuntimeError(
        "Model deployment name is not configured. Set "
        "AZURE_AI_MODEL_DEPLOYMENT_NAME or "
        "FOUNDRY_MODEL_NAME."
    )


payroll_interpreter_client = FoundryChatClient(
    project_endpoint=os.environ[
        "FOUNDRY_PROJECT_ENDPOINT"
    ],
    model=model_name,
    credential=DefaultAzureCredential(),
)


payroll_interpreter_agent = Agent(
    client=payroll_interpreter_client,
    name="PayrollComparisonInterpreter",
    instructions=(
        "You are a payroll data analyst. "
        "Interpret the comparison between two payroll periods. "
        "Only describe changes supported by the provided statistics. "
        "Never describe the number of rows as employee headcount "
        "unless employee uniqueness has been explicitly verified. "
        "Do not infer causes for the changes. "
        "Distinguish clearly between observed results and "
        "possible explanations. Keep the interpretation brief."
    ),
)


#=====================================================
# Step 1: Validate payroll years
#=====================================================

@step
async def validate_payroll_years(
    years: list[int],
) -> dict[str, Any]:
    """Validate that payroll years exist and contain required columns."""

    errors: list[str] = []

    for year in years:
        if year not in AVAILABLE_PAYROLL_YEARS:
            errors.append(
                f"Payroll data is not available for year {year}."
            )
            continue

        try:
            payroll_data = load_payroll_dataframe(year)
        except Exception as error:
            errors.append(
                f"Could not read payroll-{year}.csv: {error}"
            )
            continue

        missing_columns = (
            REQUIRED_COLUMNS - set(payroll_data.columns)
        )

        if missing_columns:
            errors.append(
                f"payroll-{year}.csv is missing columns: "
                f"{sorted(missing_columns)}"
            )

    return {
        "is_valid": not errors,
        "errors": errors,
        "years": years,
    }


#=====================================================
# Step 2: Summarise payroll years
#=====================================================

@step
async def summarise_payroll_years(
    years: list[int],
) -> list[dict[str, Any]]:
    """Calculate comparable metrics for each payroll year."""

    summaries: list[dict[str, Any]] = []

    for year in years:
        payroll_data = load_payroll_dataframe(year)

        annual_base_salary = pd.to_numeric(
            payroll_data["Annual Base Salary"],
            errors="coerce",
        )

        gross_pay = pd.to_numeric(
            payroll_data["Gross Pay"],
            errors="coerce",
        )

        base_pay = pd.to_numeric(
            payroll_data["Base Pay"],
            errors="coerce",
        )

        overtime_pay = pd.to_numeric(
            payroll_data["Overtime Pay"],
            errors="coerce",
        )

        summaries.append({
            "file_name": f"payroll-{year}.csv",
            "year": year,
            "rows": len(payroll_data),
            "mean_annual_base_salary": (
                annual_base_salary.mean()
            ),
            "total_gross_pay": gross_pay.sum(),
            "total_base_pay": base_pay.sum(),
            "total_overtime_pay": overtime_pay.sum(),
        })

    return summaries


#=====================================================
# Step 3: Compare payroll periods
#=====================================================

@step
async def compare_payroll_periods(
    summaries: list[dict[str, Any]],
) -> str:
    """Compare payroll metrics between two periods."""

    first_period = summaries[0]
    second_period = summaries[1]

    def percentage_change(
        old_value: float,
        new_value: float,
    ) -> float | None:
        """Calculate percentage change between two values."""

        if old_value == 0:
            return None

        return (
            (new_value - old_value)
            / old_value
            * 100
        )

    metrics = {
        "Number of records": "rows",
        "Mean Annual Base Salary": (
            "mean_annual_base_salary"
        ),
        "Total Gross Pay": "total_gross_pay",
        "Total Base Pay": "total_base_pay",
        "Total Overtime Pay": "total_overtime_pay",
    }

    comparison_lines = [
        (
            f"Comparison: {first_period['file_name']} "
            f"vs {second_period['file_name']}"
        )
    ]

    for metric_name, metric_key in metrics.items():
        old_value = first_period[metric_key]
        new_value = second_period[metric_key]

        change = percentage_change(
            old_value,
            new_value,
        )

        change_text = (
            f"{change:+.2f}%"
            if change is not None
            else "not available"
        )

        comparison_lines.append(
            f"{metric_name}: "
            f"{old_value:,.2f} -> "
            f"{new_value:,.2f} "
            f"({change_text})"
        )

    return "\n".join(comparison_lines)


#=====================================================
# Step 4: Interpret comparison with Foundry Agent
#=====================================================

@step
async def interpret_payroll_comparison(
    comparison: str,
) -> str:
    """Use a Foundry agent to interpret the payroll comparison."""

    prompt = (
        "Interpret the following payroll comparison:\n\n"
        f"{comparison}\n\n"
        "Identify the most relevant changes and explain them "
        "in a concise and neutral way."
    )

    response = await payroll_interpreter_agent.run(
        prompt
    )

    return response.text


#=====================================================
# Payroll comparison workflow
#=====================================================

@workflow(
    name="payroll_comparison_workflow",
    description=(
        "Validates and compares two payroll years."
    ),
)
async def payroll_comparison_workflow(
    years: list[int],
) -> str:
    """Validate and compare two payroll periods."""

    if len(years) != 2:
        return (
            "Workflow stopped: exactly two payroll "
            "years are required."
        )

    validation_result = await validate_payroll_years(
        years
    )

    if not validation_result["is_valid"]:
        error_report = "\n".join(
            validation_result["errors"]
        )

        return (
            "Workflow stopped because validation failed:\n"
            f"{error_report}"
        )

    summaries = await summarise_payroll_years(
        validation_result["years"]
    )

    comparison = await compare_payroll_periods(
        summaries
    )

    interpretation = await interpret_payroll_comparison(
        comparison
    )

    return (
        "Validation completed successfully.\n\n"
        f"{comparison}\n\n"
        "AI Agent interpretation:\n"
        f"{interpretation}"
    )


#=====================================================
# Workflow as a tool
#=====================================================

@tool(approval_mode="never_require")
async def run_payroll_comparison_workflow() -> str:
    """
    Compare the 2025 and 2026 payroll files.

    Use this tool when the user asks to compare payroll periods,
    years, salaries, gross pay, base pay, or overtime changes
    between 2025 and 2026.
    """

    payroll_years = [
        2025,
        2026,
    ]

    workflow_instance = (
        payroll_comparison_workflow.build()
    )

    result = await workflow_instance.run(
        payroll_years
    )

    outputs = result.get_outputs()

    if not outputs:
        return (
            "The payroll comparison workflow "
            "produced no output."
        )

    return str(outputs[0])