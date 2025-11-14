"""
Data transformation and validation utilities for freight lane data.
"""

import pandas as pd
from typing import List, Dict, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Required columns for the input CSV
REQUIRED_COLUMNS = [
    'lane_id',
    'origin_city',
    'origin_state',
    'origin_zip',
    'destination_city',
    'destination_state',
    'destination_zip',
    'miles',
    'equipment_type',
    'volume'
]


def validate_csv(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate that the uploaded CSV contains all required columns.

    Args:
        df: DataFrame to validate

    Returns:
        Tuple of (is_valid, list_of_missing_columns)
    """
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing_columns:
        logger.warning(f"Missing required columns: {missing_columns}")
        return False, missing_columns

    logger.info("CSV validation successful - all required columns present")
    return True, []


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize the freight lane data.

    Args:
        df: Raw DataFrame from CSV upload

    Returns:
        Cleaned DataFrame
    """
    logger.info(f"Cleaning data: {len(df)} rows")

    # Create a copy to avoid modifying the original
    df_clean = df.copy()

    # Standardize column names (strip whitespace, lowercase)
    df_clean.columns = df_clean.columns.str.strip().str.lower()

    # Clean string columns
    string_columns = [
        'lane_id', 'origin_city', 'origin_state', 'destination_city',
        'destination_state', 'equipment_type'
    ]

    for col in string_columns:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.strip()

    # Standardize state codes to uppercase
    if 'origin_state' in df_clean.columns:
        df_clean['origin_state'] = df_clean['origin_state'].str.upper()
    if 'destination_state' in df_clean.columns:
        df_clean['destination_state'] = df_clean['destination_state'].str.upper()

    # Clean ZIP codes (remove non-numeric characters, pad to 5 digits)
    for zip_col in ['origin_zip', 'destination_zip']:
        if zip_col in df_clean.columns:
            df_clean[zip_col] = (
                df_clean[zip_col]
                .astype(str)
                .str.extract(r'(\d{5})', expand=False)
            )

    # Convert numeric columns
    numeric_columns = ['miles', 'volume']
    for col in numeric_columns:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # Remove rows with missing critical data
    initial_count = len(df_clean)
    df_clean = df_clean.dropna(subset=['origin_city', 'destination_city', 'volume'])

    removed_count = initial_count - len(df_clean)
    if removed_count > 0:
        logger.warning(f"Removed {removed_count} rows with missing critical data")

    # Remove rows with zero or negative volume
    df_clean = df_clean[df_clean['volume'] > 0]

    logger.info(f"Data cleaning complete: {len(df_clean)} rows remaining")

    return df_clean


def deduplicate_lanes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate lanes based on origin/destination pairs.

    Args:
        df: DataFrame with lane data

    Returns:
        DataFrame with duplicates removed
    """
    initial_count = len(df)

    # Define columns that identify a unique lane
    lane_key_columns = [
        'origin_city', 'origin_state', 'origin_zip',
        'destination_city', 'destination_state', 'destination_zip',
        'equipment_type'
    ]

    # Keep the first occurrence of each unique lane
    df_dedup = df.drop_duplicates(subset=lane_key_columns, keep='first')

    removed_count = initial_count - len(df_dedup)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate lanes")

    return df_dedup


def aggregate_lanes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate lanes by origin/destination pairs, summing volumes.

    Args:
        df: DataFrame with lane data

    Returns:
        Aggregated DataFrame
    """
    logger.info("Aggregating lanes by origin/destination pairs...")

    # Group by origin/destination and equipment type
    group_columns = [
        'origin_city', 'origin_state', 'origin_zip',
        'destination_city', 'destination_state', 'destination_zip',
        'equipment_type'
    ]

    # Check if geocoded columns exist
    geo_columns = []
    for prefix in ['origin', 'destination']:
        lat_col = f'{prefix}_lat'
        lon_col = f'{prefix}_lon'
        if lat_col in df.columns and lon_col in df.columns:
            geo_columns.extend([lat_col, lon_col])

    # Aggregate
    agg_dict = {
        'volume': 'sum',
        'miles': 'mean',  # Average miles for aggregated lanes
        'lane_id': 'count'  # Count of lanes aggregated
    }

    # Add geocoded columns to aggregation (take first value)
    for col in geo_columns:
        agg_dict[col] = 'first'

    df_agg = df.groupby(group_columns, as_index=False).agg(agg_dict)

    # Rename lane_id count to lane_count
    df_agg = df_agg.rename(columns={'lane_id': 'lane_count'})

    logger.info(f"Aggregated {len(df)} lanes into {len(df_agg)} unique O/D pairs")

    return df_agg


def create_summary_stats(df: pd.DataFrame) -> Dict:
    """
    Generate summary statistics for the lane data.

    Args:
        df: DataFrame with lane data

    Returns:
        Dictionary with summary statistics
    """
    stats = {
        'total_lanes': len(df),
        'total_volume': df['volume'].sum() if 'volume' in df.columns else 0,
        'unique_origins': df[['origin_city', 'origin_state']].drop_duplicates().shape[0]
        if 'origin_city' in df.columns else 0,
        'unique_destinations': df[['destination_city', 'destination_state']].drop_duplicates().shape[0]
        if 'destination_city' in df.columns else 0,
        'equipment_types': df['equipment_type'].nunique() if 'equipment_type' in df.columns else 0,
        'avg_miles': df['miles'].mean() if 'miles' in df.columns else 0,
        'avg_volume': df['volume'].mean() if 'volume' in df.columns else 0,
    }

    return stats
