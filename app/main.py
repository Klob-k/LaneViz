"""
LaneViz - Freight Lane Visualization Tool

A Streamlit application for geocoding and visualizing freight lane networks
using yat_geo_db and Kepler.gl.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path to import utils
sys.path.append(str(Path(__file__).parent.parent))

from utils.geocode import YatGeocodeLookup
from utils.transform import (
    validate_csv,
    clean_data,
    aggregate_lanes,
    create_summary_stats,
    REQUIRED_COLUMNS
)
from utils.map_builder import (
    prepare_kepler_data,
    create_kepler_map,
    get_kepler_config
)


# Page configuration
st.set_page_config(
    page_title="LaneViz - Freight Lane Visualization",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'data' not in st.session_state:
        st.session_state.data = None
    if 'geocoded_data' not in st.session_state:
        st.session_state.geocoded_data = None
    if 'geocoder' not in st.session_state:
        st.session_state.geocoder = YatGeocodeLookup()


def display_header():
    """Display the application header."""
    st.title("🚚 LaneViz")
    st.markdown(
        "**Freight Lane Visualization Tool** - "
        "Upload your freight lane data to geocode and visualize O/D networks"
    )
    st.divider()


def display_sidebar():
    """Display the sidebar with instructions and controls."""
    with st.sidebar:
        st.header("📋 Instructions")

        st.markdown("""
        ### How to use LaneViz

        1. **Upload CSV**: Upload your freight lane data
        2. **Validate**: Ensure all required columns are present
        3. **Geocode**: Convert locations to coordinates
        4. **Visualize**: View your network on an interactive map

        ### Required CSV Columns
        """)

        # Display required columns in a nice format
        for col in REQUIRED_COLUMNS:
            st.markdown(f"- `{col}`")

        st.divider()

        st.markdown("""
        ### Sample Data Format

        | lane_id | origin_city | origin_state | ... |
        |---------|-------------|--------------|-----|
        | L001    | Chicago     | IL           | ... |
        | L002    | Atlanta     | GA           | ... |
        """)

        st.divider()

        # TODO: Add download sample CSV functionality
        st.markdown("### 📥 Download")
        st.info("Sample CSV download coming soon!")


def upload_and_validate():
    """Handle file upload and validation."""
    st.header("1. Upload Freight Lane Data")

    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload a CSV file containing your freight lane data"
    )

    if uploaded_file is not None:
        try:
            # Read CSV
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ File uploaded successfully! {len(df)} rows loaded.")

            # Display preview
            with st.expander("📊 Preview uploaded data (first 10 rows)"):
                st.dataframe(df.head(10))

            # Validate columns
            is_valid, missing_columns = validate_csv(df)

            if not is_valid:
                st.error(
                    f"❌ Missing required columns: {', '.join(missing_columns)}"
                )
                st.info(
                    "Please ensure your CSV contains all required columns. "
                    "See the sidebar for the complete list."
                )
                return None

            st.success("✅ All required columns present!")

            # Clean data
            df_clean = clean_data(df)

            # Display data quality info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Original Rows", len(df))
            with col2:
                st.metric("Cleaned Rows", len(df_clean))
            with col3:
                removed = len(df) - len(df_clean)
                st.metric("Rows Removed", removed)

            return df_clean

        except Exception as e:
            st.error(f"❌ Error reading file: {str(e)}")
            return None

    return None


def geocode_data(df):
    """Geocode origin and destination locations."""
    st.header("2. Geocode Locations")

    if df is None:
        st.info("👆 Please upload and validate a CSV file first.")
        return None

    st.markdown(
        "Convert city/state/ZIP information to geographic coordinates "
        "using yat_geo_db."
    )

    # Display summary stats before geocoding
    stats = create_summary_stats(df)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Lanes", stats['total_lanes'])
    with col2:
        st.metric("Unique Origins", stats['unique_origins'])
    with col3:
        st.metric("Unique Destinations", stats['unique_destinations'])
    with col4:
        st.metric("Equipment Types", stats['equipment_types'])

    # Geocode button
    if st.button("🌍 Geocode All Locations", type="primary"):
        with st.spinner("Geocoding origins..."):
            # TODO: Implement actual geocoding once yat_geo_db is set up
            st.warning(
                "⚠️ Geocoding not yet implemented. "
                "This is a placeholder for yat_geo_db integration."
            )

            # Placeholder: Add dummy coordinates for demonstration
            df_geocoded = df.copy()
            # df_geocoded = st.session_state.geocoder.geocode_dataframe(
            #     df_geocoded, 'origin'
            # )

        with st.spinner("Geocoding destinations..."):
            # df_geocoded = st.session_state.geocoder.geocode_dataframe(
            #     df_geocoded, 'destination'
            # )
            pass

        # TODO: Replace with actual geocoding results
        st.info(
            "📍 When geocoding is implemented, coordinates will appear here. "
            "You'll see success rates and any locations that couldn't be geocoded."
        )

        return df_geocoded

    return None


def visualize_map(df_geocoded):
    """Create and display the Kepler.gl map."""
    st.header("3. Visualize Network")

    if df_geocoded is None:
        st.info("👆 Please geocode your data first.")
        return

    st.markdown("Interactive freight lane network visualization")

    # TODO: Check if data has valid coordinates
    has_coords = all(
        col in df_geocoded.columns
        for col in ['origin_lat', 'origin_lon', 'destination_lat', 'destination_lon']
    )

    if not has_coords:
        st.warning(
            "⚠️ Geocoded coordinates not found. "
            "Complete the geocoding step first to enable visualization."
        )
        return

    # Aggregation options
    with st.expander("⚙️ Map Options"):
        aggregate = st.checkbox(
            "Aggregate lanes by O/D pair",
            value=True,
            help="Combine multiple lanes between the same origin and destination"
        )

        if aggregate:
            df_viz = aggregate_lanes(df_geocoded)
            st.info(f"Aggregated to {len(df_viz)} unique O/D pairs")
        else:
            df_viz = df_geocoded

    # Create map button
    if st.button("🗺️ Generate Map", type="primary"):
        with st.spinner("Preparing data for visualization..."):
            try:
                # Prepare data for Kepler.gl
                kepler_data = prepare_kepler_data(df_viz)

                # Create map
                kepler_map = create_kepler_map(
                    kepler_data,
                    config=get_kepler_config(),
                    height=600
                )

                if kepler_map is not None:
                    # Display map in Streamlit
                    st.write("### 🗺️ Interactive Freight Lane Network")

                    # TODO: Integrate Kepler.gl with Streamlit
                    # This requires keplergl's Streamlit integration
                    st.info(
                        "📍 Kepler.gl map will be displayed here once "
                        "the integration is complete."
                    )

                    # Placeholder for map
                    # from streamlit_keplergl import keplergl_static
                    # keplergl_static(kepler_map)

                else:
                    st.error("Failed to create map. Check that keplergl is installed.")

            except Exception as e:
                st.error(f"Error creating map: {str(e)}")


def main():
    """Main application entry point."""
    # Initialize session state
    init_session_state()

    # Display header
    display_header()

    # Display sidebar
    display_sidebar()

    # Step 1: Upload and validate
    df_clean = upload_and_validate()
    if df_clean is not None:
        st.session_state.data = df_clean

    # Step 2: Geocode
    df_geocoded = geocode_data(st.session_state.data)
    if df_geocoded is not None:
        st.session_state.geocoded_data = df_geocoded

    # Step 3: Visualize
    visualize_map(st.session_state.geocoded_data)

    # Footer
    st.divider()
    st.markdown(
        "<p style='text-align: center; color: gray;'>"
        "LaneViz v0.1.0 - Freight Lane Visualization Tool"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
