# LaneViz Technical Research: yat_geo_db & Kepler.gl

## Research Summary

This document provides comprehensive research findings on `yat_geo_db` and `Kepler.gl` to guide the implementation of geocoding and visualization features in LaneViz.

---

## Part 1: yat_geo_db Library

### Overview
- **Package**: `yat-geo-db` (PyPI: https://pypi.org/project/yat-geo-db/)
- **Repository**: https://github.com/yat-co/yat_geo_db
- **Description**: A Python wrapper around the YAT Open Geo Database for US, Canada, and Mexico
- **Python Version**: Requires Python 3.7+

### Core Functionality

#### 1. Data Loading
```python
from yat_geo_db import GeoManager

# Initialize and load data
geo_manager = GeoManager()
geo_manager.load_data(
    force_db_fetch=False,  # True to force download latest
    cache_local=True,      # Cache files locally
    compressed=True        # Use compressed files
)
```

**Key Points**:
- Uses flat file architecture (not a traditional database)
- Downloads geo DB files from https://yat-geo-db.sfo3.digitaloceanspaces.com/
- Supports versioning and local caching
- Initial download required, subsequent loads use cache

#### 2. Available Methods

**Fuzzy Search** (Auto-complete style search):
```python
results = geo_manager.fuzzy_search(
    search_param="Nashville",
    num_results=10,
    filters={
        "ref_data.state_prov": "TN",
        "ref_data.country": "US"
    }
)
# Returns: [{'value': 'Nashville, TN', 'id': 'us__tn__nashville'}, ...]
```

**Get Shape by Reference Code**:
```python
shape = geo_manager.get_shape_by_ref_code('us__tn__nashville')
# Returns complete location data (see Data Structure below)
```

**Radius Search**:
```python
nearby = geo_manager.radius_search(
    reference_code='us__tn__nashville',
    radius=10,  # miles
    country_exact=True,  # Respect country boundaries
    full_results=False   # True to return full shape objects
)
# Returns: List of shape IDs or full location objects
```

#### 3. Data Structure

The Shape object returns comprehensive location data:

```python
{
    # Geographic coordinates
    'latitude': 36.1627,
    'longitude': -86.7816,
    'bbox': [minLng, minLat, maxLng, maxLat],
    'area': float,  # square miles
    'geo_type': 'City',  # or 'ZipCode', etc.

    # Reference data
    'ref_data': {
        'city': 'Nashville',
        'state_prov': 'TN',
        'country': 'US',
        'zip_code': '37201'  # if applicable
    },

    # Display names
    'short_display': 'Nashville, TN',
    'long_display': 'Nashville, Tennessee, United States',

    # Additional metadata
    'population': int,
    'is_zip_code': bool,
    'is_aggregate': bool,
    'primary_timezone': 'America/Chicago',
    'reference_code': 'us__tn__nashville',
    'related_shape_id': str
}
```

#### 4. Reference Code Format

Format: `<country>__<state>__<name_with_underscores>`

Examples:
- `us__tn__nashville`
- `us__ca__los_angeles`
- `ca__on__toronto` (Canada)
- `mx__df__mexico_city` (Mexico)

### Search Strategies for LaneViz

#### Strategy 1: City + State Search
```python
# Best for most US freight lanes
results = geo_manager.fuzzy_search(
    search_param=f"{city}",
    filters={
        "ref_data.state_prov": state_code,
        "ref_data.country": "US"
    }
)
```

#### Strategy 2: ZIP Code Search
```python
# More precise, but may have coverage issues
results = geo_manager.fuzzy_search(
    search_param=zip_code,
    filters={
        "geo_type": "ZipCode",
        "ref_data.country": "US"
    }
)
```

#### Strategy 3: Hybrid Approach (RECOMMENDED)
```python
def geocode_location(city, state, zip_code, country="US"):
    """
    Multi-tiered geocoding approach:
    1. Try ZIP code first (most accurate)
    2. Fall back to City + State
    3. Fall back to fuzzy search on city name only
    """
    # Try ZIP code
    if zip_code:
        results = geo_manager.fuzzy_search(
            search_param=zip_code,
            filters={"ref_data.country": country}
        )
        if results:
            shape = geo_manager.get_shape_by_ref_code(results[0]['id'])
            return (shape['latitude'], shape['longitude'])

    # Try City + State
    results = geo_manager.fuzzy_search(
        search_param=city,
        filters={
            "ref_data.state_prov": state,
            "ref_data.country": country
        }
    )
    if results:
        shape = geo_manager.get_shape_by_ref_code(results[0]['id'])
        return (shape['latitude'], shape['longitude'])

    # Final fallback: City only (less accurate)
    results = geo_manager.fuzzy_search(
        search_param=city,
        num_results=1
    )
    if results:
        shape = geo_manager.get_shape_by_ref_code(results[0]['id'])
        return (shape['latitude'], shape['longitude'])

    return (None, None)
```

### Known Limitations & Considerations

#### Canadian Postal Codes
- **Issue**: Canadian postal codes use alphanumeric format (e.g., "M5H 2N2") vs US numeric ZIP codes
- **Coverage**: While yat_geo_db supports Canada, postal code granularity may vary
- **Recommendation**:
  - Validate Canadian postal code format before search
  - Use City + Province as primary search, postal code as secondary
  - Consider FSA (Forward Sortation Area - first 3 characters) for broader matching

#### Mexican ZIP Codes (Códigos Postales)
- **Issue**: Mexican ZIP codes are 5-digit numeric like US, but data coverage may differ
- **Coverage**: Database includes Mexico, but granularity may be lower than US
- **Recommendation**:
  - Test coverage with sample Mexican locations
  - Use City + State as fallback
  - Be prepared for lower success rates

#### General Limitations
- **Data Freshness**: Dependent on YAT database updates
- **Coverage Gaps**: Smaller cities/rural areas may have limited data
- **Accuracy**: City-level coordinates may be centroid, not specific address
- **Performance**: Initial load requires download (mitigated by caching)

### Performance Best Practices

1. **Caching Strategy**:
   ```python
   # Application-level cache for lookups
   from functools import lru_cache

   @lru_cache(maxsize=10000)
   def cached_geocode(city, state, zip_code, country):
       return geocode_location(city, state, zip_code, country)
   ```

2. **Batch Processing**:
   - Deduplicate locations before geocoding
   - Process unique origin/destination pairs only
   - Cache results in session state

3. **Load Data Once**:
   ```python
   # In Streamlit, use session state
   if 'geo_manager' not in st.session_state:
       st.session_state.geo_manager = GeoManager()
       st.session_state.geo_manager.load_data(cache_local=True)
   ```

---

## Part 2: Kepler.gl with Streamlit

### Overview
- **Base Package**: `keplergl` (Python bindings for Kepler.gl)
- **Streamlit Component**: `streamlit-keplergl`
- **Repository**: https://github.com/chrieke/streamlit-keplergl
- **Docs**: https://docs.kepler.gl/

### Installation
```bash
pip install keplergl
pip install streamlit-keplergl
```

### Basic Usage in Streamlit

```python
import streamlit as st
from streamlit_keplergl import keplergl_static
from keplergl import KeplerGl
import pandas as pd

# Create map instance
map_1 = KeplerGl(height=600)

# Add data
map_1.add_data(data=df, name='freight_lanes')

# Display in Streamlit
keplergl_static(map_1, center_map=True)
```

### Data Format Support

Kepler.gl accepts multiple formats:

1. **Pandas DataFrame** (RECOMMENDED for LaneViz):
   ```python
   df = pd.DataFrame({
       'lane_id': ['L001', 'L002'],
       'origin_lat': [41.85, 34.05],
       'origin_lon': [-87.65, -118.24],
       'destination_lat': [33.75, 47.60],
       'destination_lon': [-84.39, -122.33],
       'volume': [1500, 2300],
       'equipment_type': ['Van', 'Reefer']
   })
   ```

2. **CSV** (string):
   ```python
   with open('lanes.csv', 'r') as f:
       csv_data = f.read()
   map_1.add_data(data=csv_data, name='lanes')
   ```

3. **GeoJSON** (dict or string)
4. **GeoDataFrame** (automatically handles geometry)

### Arc Layer Configuration for Freight Lanes

Arc layers are perfect for visualizing origin-destination pairs:

```python
config = {
    'version': 'v1',
    'config': {
        'visState': {
            'filters': [],
            'layers': [
                {
                    'id': 'freight_lanes',
                    'type': 'arc',
                    'config': {
                        'dataId': 'freight_lanes',  # Must match name in add_data()
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
                                    '#5A1846',
                                    '#900C3F',
                                    '#C70039',
                                    '#E3611C',
                                    '#F1920E',
                                    '#FFC300'
                                ]
                            },
                            'sizeRange': [0, 10],
                            'targetColor': None
                        },
                        'textLabel': [
                            {
                                'field': None,
                                'color': [255, 255, 255],
                                'size': 18,
                                'offset': [0, 0],
                                'anchor': 'start',
                                'alignment': 'center'
                            }
                        ]
                    },
                    'visualChannels': {
                        'colorField': {
                            'name': 'volume',
                            'type': 'integer'
                        },
                        'colorScale': 'quantile',
                        'sizeField': {
                            'name': 'volume',
                            'type': 'integer'
                        },
                        'sizeScale': 'sqrt'
                    }
                }
            ],
            'interactionConfig': {
                'tooltip': {
                    'fieldsToShow': {
                        'freight_lanes': [
                            {'name': 'lane_id', 'format': None},
                            {'name': 'origin_city', 'format': None},
                            {'name': 'destination_city', 'format': None},
                            {'name': 'volume', 'format': None},
                            {'name': 'miles', 'format': None},
                            {'name': 'equipment_type', 'format': None}
                        ]
                    },
                    'compareMode': False,
                    'compareType': 'absolute',
                    'enabled': True
                },
                'brush': {'size': 0.5, 'enabled': False},
                'geocoder': {'enabled': False},
                'coordinate': {'enabled': False}
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
            },
            'themeType': 'dark',
            'mapStyles': {}
        }
    }
}

# Apply config
map_1 = KeplerGl(height=600, config=config)
map_1.add_data(data=df, name='freight_lanes')
```

### Solving the San Francisco Default Zoom Issue

**Problem**: Kepler.gl often defaults to San Francisco (37.77, -122.42) instead of fitting to data.

**Solutions**:

#### Solution 1: Use `center_map=True` (RECOMMENDED)
```python
keplergl_static(map_1, center_map=True)
```

This automatically calculates bounds from your data and centers the map.

#### Solution 2: Calculate Custom Viewport
```python
def calculate_viewport(df):
    """
    Calculate center and zoom level from dataframe containing lanes.
    """
    # Get all latitudes and longitudes
    lats = pd.concat([df['origin_lat'], df['destination_lat']])
    lons = pd.concat([df['origin_lon'], df['destination_lon']])

    # Remove NaN values
    lats = lats.dropna()
    lons = lons.dropna()

    if len(lats) == 0:
        # Default to US center
        return {
            'latitude': 39.8283,
            'longitude': -98.5795,
            'zoom': 4
        }

    # Calculate bounds
    lat_min, lat_max = lats.min(), lats.max()
    lon_min, lon_max = lons.min(), lons.max()

    # Calculate center
    center_lat = (lat_min + lat_max) / 2
    center_lon = (lon_min + lon_max) / 2

    # Calculate zoom level based on bounds
    # Approximate zoom calculation
    lat_diff = lat_max - lat_min
    lon_diff = lon_max - lon_min
    max_diff = max(lat_diff, lon_diff)

    if max_diff < 0.01:
        zoom = 13
    elif max_diff < 0.1:
        zoom = 10
    elif max_diff < 1:
        zoom = 8
    elif max_diff < 5:
        zoom = 6
    elif max_diff < 20:
        zoom = 5
    else:
        zoom = 4

    return {
        'latitude': center_lat,
        'longitude': center_lon,
        'zoom': zoom
    }

# Use in config
viewport = calculate_viewport(df)
config['config']['mapState'].update(viewport)
```

#### Solution 3: Pre-calculate Bounds
```python
def get_bounds(df):
    """Get bounding box [minLng, minLat, maxLng, maxLat]"""
    lats = pd.concat([df['origin_lat'], df['destination_lat']])
    lons = pd.concat([df['origin_lon'], df['destination_lon']])

    return [
        lons.min(),  # minLng
        lats.min(),  # minLat
        lons.max(),  # maxLng
        lats.max()   # maxLat
    ]

# Then use fitBounds in JavaScript if using custom component
bounds = get_bounds(df)
```

### Tooltip Configuration

```python
'interactionConfig': {
    'tooltip': {
        'fieldsToShow': {
            'freight_lanes': [  # Must match dataset name
                {'name': 'lane_id', 'format': None},
                {'name': 'origin_city', 'format': None},
                {'name': 'origin_state', 'format': None},
                {'name': 'destination_city', 'format': None},
                {'name': 'destination_state', 'format': None},
                {'name': 'volume', 'format': None},
                {'name': 'miles', 'format': None},
                {'name': 'equipment_type', 'format': None}
            ]
        },
        'compareMode': False,
        'enabled': True
    }
}
```

### Data-Driven Styling

#### Color by Volume
```python
'visualChannels': {
    'colorField': {
        'name': 'volume',
        'type': 'integer'
    },
    'colorScale': 'quantile',  # or 'quantize', 'ordinal'
}
```

#### Thickness by Volume
```python
'visualChannels': {
    'sizeField': {
        'name': 'volume',
        'type': 'integer'
    },
    'sizeScale': 'sqrt',  # or 'linear', 'log'
}
```

### Color Palettes

Available color ranges:
- `'Global Warming'` - Yellow to Red (good for volume/intensity)
- `'Uber Viz Qualitative'` - Multi-color qualitative
- `'ColorBrewer YlOrRd'` - Yellow-Orange-Red
- `'Viridis'` - Perceptually uniform

### Performance Considerations

1. **Data Volume**:
   - Kepler.gl can handle 1M+ points efficiently
   - For arc layers, expect good performance up to 50k arcs
   - Consider aggregating lanes if >100k

2. **Optimization Strategies**:
   ```python
   # Aggregate by O/D pair before visualization
   df_agg = df.groupby([
       'origin_lat', 'origin_lon',
       'destination_lat', 'destination_lon',
       'origin_city', 'origin_state',
       'destination_city', 'destination_state'
   ]).agg({
       'volume': 'sum',
       'miles': 'mean'
   }).reset_index()
   ```

3. **Use Arrow for Large Datasets**:
   ```python
   map_1.add_data(data=df, name='lanes', use_arrow=True)
   ```

### streamlit-keplergl Parameters

```python
keplergl_static(
    fig,              # KeplerGl instance (required)
    height=600,       # Height in pixels (optional)
    width=None,       # Width in pixels (optional, defaults to container width)
    center_map=True,  # Auto-center on data (RECOMMENDED)
    read_only=False   # Hide customization sidebar
)
```

### Saving and Loading Configurations

#### Export Config from Interactive Map
```python
# In Jupyter or during development
map_1 = KeplerGl(height=600)
map_1.add_data(data=df, name='lanes')
# Customize in the UI, then export:
config = map_1.config
print(config)
```

#### Save Config to File
```python
import json

with open('kepler_config.json', 'w') as f:
    json.dump(map_1.config, f, indent=2)
```

#### Load Config from File
```python
with open('kepler_config.json', 'r') as f:
    config = json.load(f)

map_1 = KeplerGl(height=600, config=config)
```

### Known Limitations

1. **Static Component**: `streamlit-keplergl` is read-only - user interactions don't return to Python
2. **No Real-time Updates**: Must re-render entire map for updates
3. **Memory**: Large datasets may impact browser performance
4. **Export**: No built-in export to image in Streamlit (can use HTML export)

---

## Part 3: Implementation Recommendations for LaneViz

### Recommended Architecture

```python
# 1. Initialize GeoManager once per session
@st.cache_resource
def get_geo_manager():
    geo_manager = GeoManager()
    geo_manager.load_data(cache_local=True, compressed=True)
    return geo_manager

# 2. Geocoding with caching
@st.cache_data
def geocode_lanes_batch(df):
    """Geocode all unique locations in dataframe"""
    geo_manager = get_geo_manager()

    # Get unique origins and destinations
    unique_origins = df[['origin_city', 'origin_state', 'origin_zip']].drop_duplicates()
    unique_dests = df[['destination_city', 'destination_state', 'destination_zip']].drop_duplicates()

    # Geocode (implementation details in utils/geocode.py)
    # ... geocoding logic ...

    return df_with_coords

# 3. Create Kepler map with auto-centering
def create_lane_map(df):
    """Create Kepler.gl map with freight lanes"""
    # Calculate viewport
    viewport = calculate_viewport(df)

    # Load config
    config = get_kepler_config()
    config['config']['mapState'].update(viewport)

    # Create map
    map_1 = KeplerGl(height=600, config=config)
    map_1.add_data(data=df, name='freight_lanes')

    # Display with auto-centering
    keplergl_static(map_1, center_map=True, read_only=False)
```

### Error Handling Strategy

```python
def geocode_with_fallback(city, state, zip_code, country="US"):
    """Geocode with comprehensive error handling"""
    try:
        # Try hybrid approach
        coords = hybrid_geocode(city, state, zip_code, country)
        if coords != (None, None):
            return coords, 'success'

        # Log failure
        logger.warning(f"Geocoding failed: {city}, {state} {zip_code}")
        return (None, None), 'not_found'

    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return (None, None), 'error'

# Track success rates
def geocode_dataframe_with_stats(df):
    """Geocode and return statistics"""
    results = []
    stats = {'success': 0, 'not_found': 0, 'error': 0}

    for _, row in df.iterrows():
        coords, status = geocode_with_fallback(
            row['origin_city'],
            row['origin_state'],
            row['origin_zip']
        )
        results.append(coords)
        stats[status] += 1

    return results, stats
```

### User Experience Recommendations

1. **Progress Indicators**:
   ```python
   progress_bar = st.progress(0)
   status_text = st.empty()

   for i, row in enumerate(df.iterrows()):
       # Geocode
       progress_bar.progress((i + 1) / len(df))
       status_text.text(f"Geocoding {i+1}/{len(df)}...")
   ```

2. **Error Reporting**:
   ```python
   if failed_locations:
       with st.expander("⚠️ Failed Geocoding"):
           st.write(f"{len(failed_locations)} locations could not be geocoded:")
           st.dataframe(failed_locations)
   ```

3. **Interactive Options**:
   ```python
   col1, col2 = st.columns(2)
   with col1:
       aggregate = st.checkbox("Aggregate lanes", value=True)
   with col2:
       color_by = st.selectbox("Color by", ['volume', 'equipment_type', 'miles'])
   ```

### Configuration Management

Store multiple configs for different views:

```python
# config/kepler_configs.py
CONFIGS = {
    'default': {...},
    'volume_heatmap': {...},
    'equipment_breakdown': {...},
    'regional_view': {...}
}
```

---

## Part 4: Testing Recommendations

### Test Cases for yat_geo_db

1. **US ZIP Code Coverage**:
   - Test major metros (NYC, LA, Chicago)
   - Test rural areas
   - Test invalid ZIP codes

2. **Canadian Postal Codes**:
   - Test FSA format (e.g., "M5H")
   - Test full postal codes (e.g., "M5H 2N2")
   - Test major cities (Toronto, Vancouver, Montreal)

3. **Mexican ZIP Codes**:
   - Test major cities (Mexico City, Guadalajara)
   - Measure success rate vs US

4. **Edge Cases**:
   - Empty strings
   - Malformed data
   - Special characters
   - Very long city names

### Test Cases for Kepler.gl

1. **Viewport Centering**:
   - Single lane (should not zoom to SF)
   - US-only lanes
   - Cross-border lanes (US-Canada, US-Mexico)
   - Very dense regional network

2. **Performance**:
   - 100 lanes
   - 1,000 lanes
   - 10,000 lanes
   - 50,000 lanes

3. **Visual Quality**:
   - Overlapping lanes
   - Very long lanes
   - Very short lanes
   - Color scaling with different volume ranges

---

## Part 5: Future Enhancements

1. **Geocoding Improvements**:
   - Add alternative geocoding service as fallback (Google, Mapbox)
   - Implement user corrections/overrides
   - Store failed lookups for review

2. **Visualization Enhancements**:
   - Add point layers for origin/destination hubs
   - Implement filters by equipment type, volume, region
   - Add time-based animations if date data available
   - Export maps as images/PDFs

3. **Performance Optimization**:
   - Implement data sampling for preview
   - Add progressive loading
   - Use WebGL optimizations

4. **Analytics**:
   - Calculate network metrics (hub detection, density)
   - Generate summary reports
   - Identify lane imbalances

---

## References

### yat_geo_db
- PyPI: https://pypi.org/project/yat-geo-db/
- GitHub: https://github.com/yat-co/yat_geo_db
- Data Files: https://yat-geo-db.sfo3.digitaloceanspaces.com/

### Kepler.gl
- Official Docs: https://docs.kepler.gl/
- Python Docs: https://docs.kepler.gl/docs/keplergl-jupyter
- streamlit-keplergl: https://github.com/chrieke/streamlit-keplergl
- Examples: https://github.com/uber-web/kepler.gl-data

### Streamlit
- Docs: https://docs.streamlit.io/
- Component API: https://docs.streamlit.io/library/components

---

**Document Version**: 1.0
**Last Updated**: 2025-11-13
**Author**: LaneViz Development Team
