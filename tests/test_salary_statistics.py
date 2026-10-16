from unittest.mock import Mock

import pandas as pd
import pytest

import agent_tools


# ============================================================
#  Test for calculate_salary_statistics
# ============================================================

@pytest.fixture
def payroll_loader(monkeypatch):
    """Replace Azure data loading with controlled test data."""
    loader = Mock(
        return_value=pd.DataFrame({
            "Pay Grade": [" A1 ", "a1", "A1", "A1", "B2"],
            "Annual Base Salary": [
                10000, 20000, 30000, "invalid", 999999,
            ],
        })
    )

    # Replace the real Azure loader with a mock during the test.
    monkeypatch.setattr(
        agent_tools, "load_payroll_dataframe", loader
    )
    return loader


def test_statistics_filter_and_normalize_pay_grade(payroll_loader):
    result = agent_tools.calculate_salary_statistics(2026, " a1 ")

    assert result["success"] is True
    assert result["year"] == 2026
    assert result["pay_grade"] == "A1"
    assert result["matching_records"] == 4
    assert result["valid_salary_records"] == 3
    assert result["missing_salary_records"] == 1
    assert result["mean_annual_base_salary"] == pytest.approx(20000)
    assert result["median_annual_base_salary"] == pytest.approx(20000)
    assert result["standard_deviation"] == pytest.approx(10000)
    payroll_loader.assert_called_once_with(2026)


def test_empty_pay_grade_does_not_load_data(payroll_loader):
    result = agent_tools.calculate_salary_statistics(2026, "   ")

    assert result["success"] is False
    assert result["error"] == "Pay Grade cannot be empty."
    payroll_loader.assert_not_called()


def test_unknown_pay_grade(payroll_loader):
    result = agent_tools.calculate_salary_statistics(2026, "ZZ")

    assert result["success"] is False
    assert result["pay_grade"] == "ZZ"
    assert "No records were found" in result["error"]


def test_missing_required_column(payroll_loader):
    payroll_loader.return_value = pd.DataFrame({
        "Pay Grade": ["A1"],
    })

    result = agent_tools.calculate_salary_statistics(2026, "A1")

    assert result["success"] is False
    assert result["missing_columns"] == ["Annual Base Salary"]


def test_no_valid_salaries(payroll_loader):
    payroll_loader.return_value = pd.DataFrame({
        "Pay Grade": ["A1", "A1"],
        "Annual Base Salary": [None, "invalid"],
    })

    result = agent_tools.calculate_salary_statistics(2026, "A1")

    assert result["success"] is False
    assert result["matching_records"] == 2
    assert "none contained a valid" in result["error"]


@pytest.mark.parametrize("error_type", [RuntimeError, ValueError])
def test_data_loading_error(payroll_loader, error_type):
    payroll_loader.side_effect = error_type("Test loading failure")

    result = agent_tools.calculate_salary_statistics(2026, "A1")

    assert result["success"] is False
    assert result["error"] == "Test loading failure"
    assert result["available_years"] == sorted(
        agent_tools.AVAILABLE_PAYROLL_YEARS
    )





# ============================================================
#  Test for validate_payroll_values
# ============================================================

@pytest.fixture
def payroll_validation_loader(monkeypatch):
    """Simulate payroll data without connecting to Azure."""
    loader = Mock(
        return_value=pd.DataFrame({
            "Hash2": ["E001", "E002", "E003"],
            "Pay Grade": ["A1", "A1", "B2"],
            "Department Name": ["IT", "Finance", "HR"],
            "Annual Base Salary": [30000, -5000, None],
        })
    )

    monkeypatch.setattr(
        agent_tools, "load_payroll_dataframe", loader
    )

    return loader


def test_missing_and_negative_salaries(payroll_validation_loader):
    result = agent_tools.validate_payroll_values.func(
        2026, "Annual Base Salary"
    )

    assert "Missing values: 1" in result
    assert "Negative values: 1" in result

    payroll_validation_loader.assert_called_once_with(2026)
