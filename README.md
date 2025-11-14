# LaneViz 🚚

**Freight Lane Visualization Tool** - A public-facing Streamlit application for geocoding and visualizing freight lane networks using yat_geo_db and Kepler.gl.

## Overview

LaneViz allows users to upload CSV files containing freight lane data, automatically geocode all origins and destinations, and visualize the Origin/Destination (O/D) network on an interactive Kepler.gl map.

## Features

- **CSV Upload**: Easy drag-and-drop interface for uploading freight lane data
- **Automatic Validation**: Ensures all required columns are present
- **Geocoding**: Converts city/state/ZIP to latitude/longitude using yat_geo_db
- **Data Processing**: Automatic cleaning, deduplication, and aggregation
- **Interactive Visualization**: Beautiful network maps powered by Kepler.gl
- **Summary Statistics**: View key metrics about your freight network

## CSV Input Specification

Your CSV file must contain the following columns:

| Column Name        | Type    | Description                          |
|--------------------|---------|--------------------------------------|
| `lane_id`          | String  | Unique identifier for the lane       |
| `origin_city`      | String  | Origin city name                     |
| `origin_state`     | String  | Origin state (2-letter code)         |
| `origin_zip`       | String  | Origin ZIP code                      |
| `destination_city` | String  | Destination city name                |
| `destination_state`| String  | Destination state (2-letter code)    |
| `destination_zip`  | String  | Destination ZIP code                 |
| `miles`            | Numeric | Distance in miles                    |
| `equipment_type`   | String  | Type of equipment (e.g., van, reefer)|
| `volume`           | Numeric | Freight volume                       |

### Sample Data Format

```csv
lane_id,origin_city,origin_state,origin_zip,destination_city,destination_state,destination_zip,miles,equipment_type,volume
L001,Chicago,IL,60601,Atlanta,GA,30301,715,Van,1500
L002,Los Angeles,CA,90001,Seattle,WA,98101,1135,Reefer,2300
L003,Dallas,TX,75201,Miami,FL,33101,1300,Flatbed,800
```

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Installation Steps

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/LaneViz.git
cd LaneViz
```

2. **Create and activate a virtual environment**

```bash
# On macOS/Linux
python -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure secrets (optional)**

If you need to configure database credentials or API keys:

```bash
mkdir .streamlit
cp config/secrets.template .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your actual credentials
```

## Running LaneViz

### Local Development

```bash
streamlit run app/main.py
```

The application will open in your default browser at `http://localhost:8501`

### Production Deployment

LaneViz can be deployed to various platforms:

- **Streamlit Cloud**: Push to GitHub and deploy via [streamlit.io/cloud](https://streamlit.io/cloud)
- **Heroku**: Use the included `Procfile` (to be added)
- **Docker**: Use the included `Dockerfile` (to be added)

## Project Structure

```
LaneViz/
├── app/
│   ├── __init__.py
│   └── main.py              # Main Streamlit application
├── utils/
│   ├── __init__.py
│   ├── geocode.py           # Geocoding utilities (yat_geo_db)
│   ├── transform.py         # Data cleaning and transformation
│   └── map_builder.py       # Kepler.gl map configuration
├── data/                    # Temporary uploaded files (git-ignored)
├── config/
│   └── secrets.template     # Template for secrets configuration
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md
```

## High-Level Architecture

```
┌─────────────────┐
│  User uploads   │
│   CSV file      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Validation    │
│  (transform.py) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Geocoding     │
│  (geocode.py)   │
│  yat_geo_db     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Data Prep      │
│  (transform.py) │
│  Aggregation    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Visualization  │
│ (map_builder.py)│
│   Kepler.gl     │
└─────────────────┘
```

## Usage Guide

### Step 1: Upload Data

1. Click the "Browse files" button
2. Select your CSV file containing freight lane data
3. The app will automatically validate the file structure

### Step 2: Geocode Locations

1. Review the data summary statistics
2. Click "Geocode All Locations"
3. Wait for the geocoding process to complete
4. Review the success rate and any failed locations

### Step 3: Visualize Network

1. Configure map options (aggregation, filters, etc.)
2. Click "Generate Map"
3. Explore your freight network on the interactive map
4. Use tooltips to see lane details

## Development

### Current Status

This is the initial boilerplate setup. The following features are currently placeholders:

- ⚠️ **Geocoding**: yat_geo_db integration is stubbed out
- ⚠️ **Map Rendering**: Kepler.gl integration needs Streamlit component
- ⚠️ **Export**: HTML/PDF export functionality

### TODO Items

- [ ] Implement actual yat_geo_db geocoding in `utils/geocode.py`
- [ ] Add Streamlit-Kepler.gl integration for map rendering
- [ ] Create sample CSV download functionality
- [ ] Add data export features (CSV, HTML map export)
- [ ] Implement caching for improved performance
- [ ] Add filters for equipment type, volume thresholds
- [ ] Create unit tests for all utility modules
- [ ] Add comprehensive error handling
- [ ] Implement logging throughout the application
- [ ] Add map customization options (colors, styles, etc.)
- [ ] Create user documentation and tooltips
- [ ] Add support for batch processing multiple files

### Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Include docstrings for all functions and classes
- Keep functions modular and testable
- Add comments for complex logic

## Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest --cov=utils tests/
```

### Writing Tests

Add tests to the `tests/` directory (to be created):

```
tests/
├── test_geocode.py
├── test_transform.py
└── test_map_builder.py
```

## Troubleshooting

### Common Issues

**Issue**: CSV upload fails with encoding error
- **Solution**: Ensure your CSV is UTF-8 encoded

**Issue**: Geocoding returns no results
- **Solution**: Check that city/state/ZIP data is properly formatted

**Issue**: Map doesn't render
- **Solution**: Verify that keplergl is properly installed

## Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [yat_geo_db Documentation](https://github.com/yourusername/yat_geo_db)
- [Kepler.gl Documentation](https://docs.kepler.gl/)
- [Pandas Documentation](https://pandas.pydata.org/docs/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or feature requests:

- Open an issue on GitHub
- Contact the development team
- Check the documentation

## Changelog

### v0.1.0 (Current)

- Initial project setup
- Basic file upload and validation
- Geocoding module structure (placeholder)
- Map builder module structure (placeholder)
- Data transformation utilities
- Streamlit UI framework

---

**Built with** ❤️ **using Streamlit, yat_geo_db, and Kepler.gl**
