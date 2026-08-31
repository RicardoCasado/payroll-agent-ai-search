"""Provide payroll analysis and data-quality tools for the agent.

The tools in this module analyse payroll CSV files retrieved from
Azure Blob Storage through payroll_data.py. Calculation helpers are
kept separate from Agent Framework tool wrappers when reuse or direct
testing is useful.
"""

from typing import Annotated, Any

import pandas as pd

from agent_framework import tool
from pydantic import Field

from payroll_data import (
    AVAILABLE_PAYROLL_YEARS,
    load_payroll_dataframe,
)



#================================
# 1 Payroll column validation
#===============================
@tool(approval_mode="never_require")
def validate_payroll_values(
    year: Annotated[
        int,
        Field(
            description=(
                "Payroll year to validate. Available years are "
                "2023, 2024, 2025, and 2026."
            )
        ),
    ],
    column_name: Annotated[
        str,
        Field(
            description=(
                "Payroll column to validate. Allowed values are "
                "'Annual Base Salary', 'Gross Pay', 'Base Pay', "
                "'Overtime Pay', and 'Other Pay'."
            )
        ),
    ],
) -> str:
    """
    Find missing and negative values in a payroll column.
    """

    # Restrict validation to numeric payroll fields for which missing
    # and negative values have a meaningful interpretation.
    allowed_columns = {
        "Annual Base Salary",
        "Gross Pay",
        "Base Pay",
        "Overtime Pay",
        "Other Pay",
    }

    if column_name not in allowed_columns:
        return (
            f"Invalid column: {column_name}. "
            f"Allowed columns: {sorted(allowed_columns)}"
        )

    df = load_payroll_dataframe(year)

    missing_rows = df.loc[
        df[column_name].isna(),
        [
            "Hash2",
            "Pay Grade",
            "Department Name",
            column_name,
        ],
    ]

    negative_rows = df.loc[
        df[column_name] < 0,
        [
            "Hash2",
            "Pay Grade",
            "Department Name",
            column_name,
        ],
    ]

    missing_sample = (
        missing_rows
        .head(10)
        .to_dict(orient="records")
    )

    negative_sample = (
        negative_rows
        .head(10)
        .to_dict(orient="records")
    )

    return (
        f"Year: {year}\n"
        f"Column: {column_name}\n"
        f"Missing values: {len(missing_rows)}\n"
        f"Negative values: {len(negative_rows)}\n"
        f"Missing value sample: {missing_sample}\n"
        f"Negative value sample: {negative_sample}"
    )




#================================
# 2 Annual Base Salary statistics
#===============================
def calculate_salary_statistics(
    year: int,
    pay_grade: str,
) -> dict[str, Any]:
    """Calculate Annual Base Salary statistics for a year and Pay Grade.

    This helper contains the deterministic calculation logic independently
    of the Agent Framework tool wrapper so that it can be reused and tested
    without invoking the agent.
    """

    # Normalize user-provided Pay Grades so matching is case-insensitive
    # and unaffected by surrounding whitespace.
    normalized_pay_grade = pay_grade.strip().upper()

    if not normalized_pay_grade:
        return {
            "success": False,
            "error": "Pay Grade cannot be empty.",
        }

    try:
        dataframe = load_payroll_dataframe(year)
    except (RuntimeError, ValueError) as error:
        return {
            "success": False,
            "error": str(error),
            "available_years": sorted(
                AVAILABLE_PAYROLL_YEARS
            ),
        }

    required_columns = {
        "Pay Grade",
        "Annual Base Salary",
    }

    missing_columns = (
        required_columns - set(dataframe.columns)
    )

    if missing_columns:
        return {
            "success": False,
            "error": "Required columns are missing.",
            "missing_columns": sorted(missing_columns),
        }

    pay_grades = (
        dataframe["Pay Grade"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    matching_rows = dataframe.loc[
        pay_grades.eq(normalized_pay_grade)
    ].copy()

    if matching_rows.empty:
        return {
            "success": False,
            "error": (
                "No records were found for "
                f"Pay Grade {normalized_pay_grade} "
                f"in {year}."
            ),
            "year": year,
            "pay_grade": normalized_pay_grade,
        }

    # Convert malformed salary values to missing values so they are
    # excluded from the statistics and counted separately.
    salaries = pd.to_numeric(
        matching_rows["Annual Base Salary"],
        errors="coerce",
    )

    valid_salaries = salaries.dropna()

    if valid_salaries.empty:
        return {
            "success": False,
            "error": (
                "Matching records were found, but none "
                "contained a valid Annual Base Salary."
            ),
            "year": year,
            "pay_grade": normalized_pay_grade,
            "matching_records": len(matching_rows),
        }

    return {
        "success": True,
        "year": year,
        "pay_grade": normalized_pay_grade,
        "matching_records": len(matching_rows),
        "valid_salary_records": len(valid_salaries),
        "missing_salary_records": int(
            salaries.isna().sum()
        ),
        "mean_annual_base_salary": round(
            float(valid_salaries.mean()),
            2,
        ),
        "median_annual_base_salary": round(
            float(valid_salaries.median()),
            2,
        ),
        "standard_deviation": round(
            float(valid_salaries.std()),
            2,
        ),
        "minimum_annual_base_salary": round(
            float(valid_salaries.min()),
            2,
        ),
        "maximum_annual_base_salary": round(
            float(valid_salaries.max()),
            2,
        ),
        "important_note": (
            "The number of payroll records is not necessarily "
            "the number of unique employees."
        ),
    }


@tool(approval_mode="never_require")
def get_salary_statistics(
    year: Annotated[
        int,
        Field(
            description=(
                "Payroll year to analyse. "
                "Available years are 2023, 2024, 2025, and 2026."
            )
        ),
    ],
    pay_grade: Annotated[
        str,
        Field(
            description=(
                "Pay Grade whose Annual Base Salary statistics "
                "should be calculated, for example PA01, "
                "FD03-03, FF05-17, or 13."
            )
        ),
    ],
) -> dict[str, Any]:
    """
    Calculate Annual Base Salary statistics for a year and Pay Grade.

    Use this tool for requests involving the mean, median,
    standard deviation, minimum, or maximum Annual Base Salary
    associated with a Pay Grade.
    """

    return calculate_salary_statistics(
        year=year,
        pay_grade=pay_grade,
    )




#=====================================================
# 3  General payroll data-quality validation
#=====================================================

@tool(approval_mode="never_require")
def validate_payroll_data(
    year: Annotated[
        int,
        Field(
            description=(
                "Payroll year to validate. Available years are "
                "2023, 2024, 2025, and 2026."
            )
        ),
    ],
) -> str:
    """Run general payroll data-quality checks.

    Checks missing Pay Grades, Birth Years outside the accepted range,
    and position end dates earlier than their corresponding start dates.
    """

    df = load_payroll_dataframe(year)

    # Invalid or malformed date values become missing timestamps and are
    # excluded from the date-order comparison.
    start_dates = pd.to_datetime(
        df["Date Position Began"],
        errors="coerce",
    )

    end_dates = pd.to_datetime(
        df["Date Position Ended"],
        errors="coerce",
    )

    missing_pay_grades = (
        df["Pay Grade"]
        .isna()
        .sum()
    )

    impossible_birth_years = (
        (df["Birth Year"] < 1900)
        | (df["Birth Year"] > df["Year"])
    ).sum()

    inconsistent_dates = (
        start_dates.notna()
        & end_dates.notna()
        & (end_dates < start_dates)
    ).sum()

    return (
        "General payroll validation results:\n"
        f"Year: {year}\n"
        f"Rows analysed: {len(df)}\n"
        f"Missing Pay Grades: {missing_pay_grades}\n"
        f"Impossible Birth Years: {impossible_birth_years}\n"
        f"End Dates earlier than Start Dates: "
        f"{inconsistent_dates}"
    )






#=====================================================
# 5 Exempt-record overtime review
#=====================================================

@tool(approval_mode="never_require")
def find_exempt_employees_with_overtime(
    year: Annotated[
        int,
        Field(
            description=(
                "Payroll year to analyse. Available years are "
                "2023, 2024, 2025, and 2026."
            )
        ),
    ],
) -> dict[str, Any]:
    """Find exempt payroll records containing positive Overtime Pay.

    The returned records are candidates for review. This tool does not
    determine whether an overtime payment is incorrect or unlawful.
    """

    if year not in AVAILABLE_PAYROLL_YEARS:
        return {
            "success": False,
            "error": (
                f"Payroll data is not available for year {year}."
            ),
            "available_years": sorted(
                AVAILABLE_PAYROLL_YEARS
            ),
        }

    df = load_payroll_dataframe(year)

    required_columns = {
        "Hash1",
        "Department Name",
        "Pay Grade",
        "FLSA Status",
        "Base Pay",
        "Overtime Pay",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        return {
            "success": False,
            "error": "Required columns are missing.",
            "missing_columns": sorted(missing_columns),
        }

    exempt_with_overtime = df.loc[
        df["FLSA Status"].eq("Exempt")
        & df["Overtime Pay"].gt(0),
        [
            "Hash1",
            "Department Name",
            "Pay Grade",
            "Base Pay",
            "Overtime Pay",
        ],
    ].copy()

    exempt_with_overtime = exempt_with_overtime.sort_values(
        by="Overtime Pay",
        ascending=False,
    )

    return {
        "success": True,
        "year": year,
        "review_reason": (
            "Employee is classified as Exempt "
            "and received overtime pay."
        ),
        "number_of_records": len(exempt_with_overtime),
        "total_overtime_pay": round(
            exempt_with_overtime["Overtime Pay"].sum(),
            2,
        ),
        "records": exempt_with_overtime.head(20).to_dict(
            orient="records"
        ),
        "important_note": (
            "These records require review. The tool does not "
            "determine that the payments are incorrect."
        ),
    }