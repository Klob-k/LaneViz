"""
Kepler.gl map building and configuration utilities for freight lane visualization.
"""

import pandas as pd
from typing import Dict, Optional
import logging

try:
    from keplergl import KeplerGl
except ImportError:
    KeplerGl = None
    logging.warning("keplergl not installed - map functionality will be limited")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def prepare_kepler_data(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Prepare data for Kepler.gl visualization.
    Creates separate datasets for origin points, destination points, and arc layers.

    Args:
        df: DataFrame with geocoded lane data

    Returns:
        Dictionary of datasets for Kepler.gl
    """
    logger.info("Preparing data for Kepler.gl visualization...")

    # Validate required columns
    required_cols = [
        'origin_lat', 'origin_lon', 'destination_lat', 'destination_lon'
    ]

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Missing required columns for visualization: {missing_cols}")
        raise ValueError(f"Missing columns: {missing_cols}")

    # Filter out rows with missing coordinates
    df_valid = df.dropna(subset=required_cols)
    logger.info(f"{len(df_valid)}/{len(df)} lanes have valid coordinates")

    # Create arc layer data (for lane connections)
    arc_data = df_valid.copy()

    # Create origin points dataset
    origin_data = df_valid[[
        'origin_city', 'origin_state', 'origin_zip',
        'origin_lat', 'origin_lon', 'volume'
    ]].copy()

    origin_data = origin_data.groupby(
        ['origin_city', 'origin_state', 'origin_zip', 'origin_lat', 'origin_lon'],
        as_index=False
    ).agg({'volume': 'sum'})

    origin_data.rename(columns={
        'origin_lat': 'lat',
        'origin_lon': 'lon',
        'origin_city': 'city',
        'origin_state': 'state',
        'origin_zip': 'zip'
    }, inplace=True)

    # Create destination points dataset
    dest_data = df_valid[[
        'destination_city', 'destination_state', 'destination_zip',
        'destination_lat', 'destination_lon', 'volume'
    ]].copy()

    dest_data = dest_data.groupby(
        ['destination_city', 'destination_state', 'destination_zip',
         'destination_lat', 'destination_lon'],
        as_index=False
    ).agg({'volume': 'sum'})

    dest_data.rename(columns={
        'destination_lat': 'lat',
        'destination_lon': 'lon',
        'destination_city': 'city',
        'destination_state': 'state',
        'destination_zip': 'zip'
    }, inplace=True)

    logger.info(
        f"Prepared {len(arc_data)} lanes, {len(origin_data)} origins, "
        f"{len(dest_data)} destinations"
    )

    return {
        'lanes': arc_data,
        'origins': origin_data,
        'destinations': dest_data
    }


def get_kepler_config() -> Dict:
    """
    Get default Kepler.gl map configuration.

    Returns:
        Configuration dictionary for Kepler.gl
    """
    # TODO: Customize this configuration based on specific visualization needs
    config = {
        'version': 'v1',
        'config': {
            'visState': {
                'filters': [],
                'layers': [
                    {
                        'type': 'arc',
                        'config': {
                            'dataId': 'lanes',
                            'label': 'Freight Lanes',
                            'color': [18, 147, 154],
                            'columns': {
                                'lat0': 'origin_lat',
                                'lng0': 'origin_lon',
                                'lat1': 'destination_lat',
                                'lng1': 'destination_lon'
                            },
                            'isVisible': True,
                            'visConfig': {
                                'opacity': 0.8,
                                'thickness': 2,
                                'colorRange': {
                                    'name': 'Global Warming',
                                    'type': 'sequential',
                                    'category': 'Uber',
                                    'colors': [
                                        '#5A1846', '#900C3F', '#C70039',
                                        '#E3611C', '#F1920E', '#FFC300'
                                    ]
                                },
                                'sizeRange': [0, 10],
                                'targetColor': None
                            }
                        }
                    }
                ],
                'interactionConfig': {
                    'tooltip': {
                        'fieldsToShow': {
                            'lanes': [
                                'origin_city', 'origin_state',
                                'destination_city', 'destination_state',
                                'volume', 'miles', 'equipment_type'
                            ]
                        },
                        'enabled': True
                    },
                    'brush': {'size': 0.5, 'enabled': False}
                }
            },
            'mapState': {
                'bearing': 0,
                'dragRotate': False,
                'latitude': 39.8283,  # Center of US
                'longitude': -98.5795,
                'pitch': 0,
                'zoom': 4,
                'isSplit': False
            },
            'mapStyle': {
                'styleType': 'dark',
                'topLayerGroups': {},
                'visibleLayerGroups': {
                    'label': True,
                    'road': True,
                    'border': False,
                    'building': True,
                    'water': True,
                    'land': True,
                    '3d building': False
                }
            }
        }
    }

    return config


def create_kepler_map(
    data: Dict[str, pd.DataFrame],
    config: Optional[Dict] = None,
    height: int = 600
) -> Optional[KeplerGl]:
    """
    Create a Kepler.gl map with the provided data and configuration.

    Args:
        data: Dictionary of datasets (from prepare_kepler_data)
        config: Optional Kepler.gl configuration (uses default if None)
        height: Map height in pixels

    Returns:
        KeplerGl map instance or None if keplergl is not available
    """
    if KeplerGl is None:
        logger.error("keplergl is not installed - cannot create map")
        return None

    logger.info("Creating Kepler.gl map...")

    # Use default config if none provided
    if config is None:
        config = get_kepler_config()

    # Create map instance
    map_instance = KeplerGl(height=height, config=config)

    # Add datasets
    for dataset_name, dataset_df in data.items():
        map_instance.add_data(data=dataset_df, name=dataset_name)
        logger.info(f"Added dataset '{dataset_name}' with {len(dataset_df)} rows")

    logger.info("Kepler.gl map created successfully")

    return map_instance


def export_map_html(
    map_instance: KeplerGl,
    file_path: str
) -> bool:
    """
    Export Kepler.gl map to HTML file.

    Args:
        map_instance: KeplerGl map instance
        file_path: Path to save HTML file

    Returns:
        True if successful, False otherwise
    """
    try:
        map_instance.save_to_html(file_name=file_path)
        logger.info(f"Map exported to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export map: {e}")
        return False
