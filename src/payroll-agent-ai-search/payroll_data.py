"""Load and cache payroll CSV files from Azure Blob Storage.

This module centralizes payroll-data access for the agent tools. It
validates supported payroll years, authenticates with Azure, downloads
the corresponding CSV file, and returns it as a pandas DataFrame.
"""

import os

from functools import lru_cache
from io import BytesIO

import pandas as pd

from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ResourceNotFoundError,
)
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


# Load local development settings from .env when the file exists.
# In Microsoft Foundry, the hosted environment supplies equivalent
# settings through deployment and platform-managed variables.
load_dotenv()


# Payroll files expected in the configured Blob Storage container.
AVAILABLE_PAYROLL_YEARS = {
    2023,
    2024,
    2025,
    2026,
}


def _get_required_environment_variable(
    variable_name: str,
) -> str:
    """Return a required environment variable."""

    value = os.getenv(variable_name)

    if not value:
        raise RuntimeError(
            f"Environment variable {variable_name} "
            "is not configured."
        )

    return value


# Payroll file loading
@lru_cache(maxsize=1)
def _get_blob_service_client() -> BlobServiceClient:
    """Create and cache the authenticated Blob service client."""

    account_url = _get_required_environment_variable(
        "PAYROLL_STORAGE_ACCOUNT_URL"
    )

    # DefaultAzureCredential uses the developer's Azure credentials
    # locally and the hosted agent's managed identity in Azure.    
    credential = DefaultAzureCredential()

    return BlobServiceClient(
        account_url=account_url,
        credential=credential,
    )


# Cache management
def _get_payroll_blob_name(year: int) -> str:
    """Return the expected blob name for a payroll year."""

    if year not in AVAILABLE_PAYROLL_YEARS:
        available_years = ", ".join(
            str(available_year)
            for available_year in sorted(
                AVAILABLE_PAYROLL_YEARS
            )
        )

        raise ValueError(
            f"Payroll data is not available for year {year}. "
            f"Available years: {available_years}."
        )

    return f"payroll-{year}.csv"


@lru_cache(maxsize=4)
def _load_payroll_dataframe_cached(
    year: int,
) -> pd.DataFrame:
    """Download and cache one payroll CSV as a DataFrame."""

    container_name = _get_required_environment_variable(
        "PAYROLL_STORAGE_CONTAINER"
    )

    blob_name = _get_payroll_blob_name(year)

    blob_client = (
        _get_blob_service_client()
        .get_blob_client(
            container=container_name,
            blob=blob_name,
        )
    )

    try:
        csv_bytes = (
            blob_client
            .download_blob()
            .readall()
        )
    except ResourceNotFoundError as error:
        raise RuntimeError(
            f"Payroll blob was not found: "
            f"{container_name}/{blob_name}."
        ) from error
    except ClientAuthenticationError as error:
        raise RuntimeError(
            "The current identity could not authenticate "
            "with Azure Blob Storage."
        ) from error
    except HttpResponseError as error:
        raise RuntimeError(
            f"Azure Blob Storage could not return "
            f"{container_name}/{blob_name}: {error.message}"
        ) from error

    dataframe = pd.read_csv(
        BytesIO(csv_bytes),
        dtype={
            "Pay Grade": str,
            "Hash1": str,
            "Hash2": str,
        },
    )

    return dataframe




def load_payroll_dataframe(
    year: int,
) -> pd.DataFrame:
    """Return an independent copy of the payroll data for a year.

    Returning a copy prevents individual tools from modifying the
    cached DataFrame shared by subsequent requests.
    """

    dataframe = _load_payroll_dataframe_cached(year)

    return dataframe.copy(deep=True)


def clear_payroll_cache() -> None:
    """Clear cached clients and payroll DataFrames."""

    _load_payroll_dataframe_cached.cache_clear()
    _get_blob_service_client.cache_clear()