# AIXM 4.5 Parser

A comprehensive Python library and browser-based tool for parsing AIXM (Aeronautical Information Exchange Model) 4.5 XML files and visualizing aeronautical data on interactive maps.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![AIXM](https://img.shields.io/badge/AIXM-4.5-orange.svg)

## Overview

AIXM (Aeronautical Information Exchange Model) is the global standard for the provision of aeronautical data in XML format. This tool provides:

- **Python Library**: Parse AIXM 4.5 XML files and extract aeronautical features programmatically
- **Visualization Module**: Render aeronautical data as interactive Folium-based maps
- **Browser-based Web App**: Standalone HTML/JavaScript application for parsing and visualizing AIXM files without any server or installation

## Features

### Core Capabilities
- **Parse AIXM 4.5 XML files**: Extract airspaces, airports, waypoints, routes, navaids, and more
- **Robust coordinate parsing**: Handles AIXM coordinate formats (DDMMSS, DDMM, DD, DMS with decimals)
- **Airspace geometry**: Link Airspace (Ase) elements with Border (Abd) polygon data
- **Vertical limits**: Parse and represent airspace altitude restrictions
- **Filtering**: Filter features by type, FIR, or custom criteria

### Supported AIXM Features

| Feature | AIXM Code | Description |
|---------|-----------|-------------|
| Airspace | Ase + Abd | Airspace boundaries with polygon geometry (including arc/circle) |
| Airport | Ahp | Aerodromes and heliports |
| Waypoint | Dpn | Designated points |
| Route | Rte + Rsg | Airways and route segments |
| VOR | Vor | VHF omnidirectional range |
| NDB | Ndb | Non-directional beacon |
| DME | Dme | Distance measuring equipment |
| TACAN | Tcn | Tactical air navigation |
| Runway | Rwy | Runways with dimensions |
| Runway Direction | Rdn | Runway threshold position and bearing |
| Taxiway | Twy | Taxiways |
| Apron | Apn | Aprons/ramps |
| Apron Geometry | Apg | Apron polygon geometry |
| SID | Sid | Standard Instrument Departures |
| STAR | Sia | Standard Terminal Arrival Routes |
| Approach | Iap | Instrument Approach Procedures |
| ILS | Ils | Instrument Landing Systems |
| Marker | Mkr | Marker beacons |
| Border | Gbr | Geographical borders (Gbv vertices) |
| Organization | Org | Aviation authorities |
| Obstacle | Obs | Obstacles (terrain/structures) |
| Holding | Hpe | Holding procedures |
| MSA Group | Mgp | Minimum safe altitude sectors |
| Airspace Assoc | Aas | Airspace parent/child hierarchy |

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/aixm-parser.git
cd aixm-parser

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

**Required:**
- `folium>=0.14.0` - Interactive map generation

**Development:**
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Test coverage
- `black>=23.0.0` - Code formatting
- `mypy>=1.0.0` - Type checking

## Python Library Usage

### Basic Parsing

```python
from src.parser import AIXMParser

# Parse an AIXM file
parser = AIXMParser("path/to/aixm_file.xml")

# Get statistics
stats = parser.get_statistics()
print(f"Airspaces: {stats['airspaces']}")
print(f"Airports: {stats['airports']}")
print(f"Waypoints: {stats['waypoints']}")

# Extract specific features
airspaces = parser.get_airspaces()
airports = parser.get_airports()
waypoints = parser.get_waypoints()
routes = parser.get_routes()
navaids = parser.get_navaids()
```

### Working with Airspaces

```python
# Get all airspaces in a specific FIR
lccc_airspaces = parser.get_airspaces_by_fir("LCCC")

# Get airspaces by type
fir_airspaces = parser.get_airspaces_by_type("FIR")
cta_airspaces = parser.get_airspaces_by_type("CTA")

# Access airspace details
for airspace in airspaces[:5]:
    print(f"Name: {airspace.name}")
    print(f"Code: {airspace.code_id}")
    print(f"Type: {airspace.type_code}")
    print(f"FIR: {airspace.parent_fir}")
    if airspace.vertical_limits:
        print(f"Vertical: {airspace.vertical_limits.lower_limit} - {airspace.vertical_limits.upper_limit}")
    if airspace.polygon:
        print(f"Polygon: {len(airspace.polygon.points)} points")
```

### Working with Airports

```python
# Get airport by ICAO code
airport = parser.get_airports_by_icao("LCLK")
if airport:
    print(f"Name: {airport.name}")
    print(f"ICAO: {airport.icao}")
    print(f"IATA: {airport.iata}")
    print(f"Position: {airport.position.lat}, {airport.position.lon}")
    print(f"Elevation: {airport.elevation} {airport.elevation_unit}")

# Get all airports
airports = parser.get_airports()
for airport in airports[:5]:
    print(f"{airport.icao}: {airport.name}")
```

### Filtering Features

```python
from src.filter import AIXMFilterConfig

# Create filter configuration
filter_config = AIXMFilterConfig(
    include_types=['airspace', 'airport', 'waypoint'],
    include_firs=['LCCC', 'LGGG'],
    exclude_types=['border']
)

# Apply filter to parser
parser.set_filter(filter_config)

# Now only filtered features will be returned
filtered_airspaces = parser.get_airspaces()
```

## Visualization Module

### Creating Interactive Maps

```python
from src.parser import AIXMParser
from src.visualization.map_renderer import MapRenderer

# Parse the file
parser = AIXMParser("path/to/aixm_file.xml")

# Create map renderer
renderer = MapRenderer(parser)

# Render all features
renderer.render_all(
    airspaces=True,
    airports=True,
    waypoints=True,
    routes=True,
    navaids=True,
    borders=False
)

# Save the map
renderer.save_map("aixm_map.html")
```

### Filtered Visualizations

```python
# Render only FIR airspaces
renderer = MapRenderer(parser)
renderer.render_airspaces(filter_type='FIR')
renderer.render_airports()
renderer.save_map("firs_only.html")

# Render airspaces for a specific FIR
renderer2 = MapRenderer(parser)
renderer2.render_airspaces(filter_fir='LCCC')
renderer2.render_airports()
renderer2.save_map("lccc_fir.html")
```

### Map Features

- **Interactive maps**: Pan, zoom, and click features for details
- **Layer control**: Toggle different feature types on/off
- **Popups**: Click features for detailed information
- **Color coding**: Different colors for airspace types (FIR, CTA, TMA, etc.)
- **Multiple tile layers**: CartoDB, OpenStreetMap, Dark Mode
- **Professional symbols**: ICAO-compliant aeronautical symbols for navaids

## Browser-based Web Application

The web application provides a complete, standalone solution for parsing and visualizing AIXM files without requiring Python or any server installation.

### Running the Web App

```bash
# Navigate to the web_ui directory
cd web_ui

# Start a local server
python -m http.server 8000

# Open in browser
# http://localhost:8000
```

Or simply open `web_ui/index.html` directly in a modern web browser.

### Web App Features

1. **File Upload**
   - Drag-and-drop AIXM XML files
   - Click to browse and select files
   - Instant parsing in the browser

2. **Element Filtering**
   - Include/Exclude filter modes
   - Select specific element types (Airspace, Airport, VOR, NDB, etc.)
   - Real-time filter application

3. **Map Visualization**
   - Interactive Leaflet-based map
   - Layer control for different feature types
   - Click features for detailed popups
   - Pan and zoom navigation

4. **Data Views**
   - **Map View**: Interactive visualization
   - **Table View**: Tabular data display
   - **JSON View**: Raw parsed data

5. **Export**
   - Export filtered data as GeoJSON

### Web App Architecture

The web app consists of three main JavaScript modules:

- **`aixm-parser.js`**: Pure JavaScript AIXM parser that runs in the browser
- **`map-renderer.js`**: Leaflet-based map rendering with aeronautical symbology
- **`app.js`**: Main application logic, UI handling, and event management

## Examples

See the `examples/` directory for complete working examples:

### `parse_sample.py`
Demonstrates basic parsing and data extraction:
```bash
python examples/parse_sample.py
```

### `visualize_sample.py`
Creates an interactive map with all features:
```bash
python examples/visualize_sample.py
```

### `filter_demo.py`
Shows advanced filtering capabilities:
```bash
python examples/filter_demo.py
```

## Data Models

### Airspace

```python
@dataclass
class Airspace:
    mid: str              # Unique identifier
    code_id: str          # Airspace code (e.g., "LCCC")
    name: str             # Airspace name
    type_code: str        # Type (FIR, CTA, TMA, SECTOR, etc.)
    local_type: str       # Local type designation
    polygon: Polygon      # Geographic boundary
    vertical_limits: VerticalLimits  # FL lower/upper
    parent_fir: str       # Parent FIR code
```

### Airport

```python
@dataclass
class Airport:
    mid: str
    code_id: str
    name: str
    icao: str             # ICAO code
    iata: str             # IATA code
    position: Point       # Lat/lon
    elevation: float      # Elevation
    elevation_unit: str   # FT or M
    type_code: str        # AD (aerodrome) or HP (heliport)
    city: str             # City name
```

### Waypoint

```python
@dataclass
class Waypoint:
    mid: str
    code_id: str          # Waypoint identifier
    name: str
    position: Point
    type_code: str        # ENRT, TERM, etc.
```

### Navaid

```python
@dataclass
class Navaid:
    mid: str
    code_id: str
    name: str
    position: Point
    frequency: float      # For VOR/NDB
    frequency_unit: str
    channel: str          # For DME/TACAN
    navaid_type: str      # VOR, NDB, DME, TACAN
    magnetic_variation: float
```

## Coordinate Formats

The parser handles all AIXM coordinate formats:

| Format | Example | Description |
|--------|---------|-------------|
| DDMMSS.ssX | `355456.50N` | Degrees, minutes, seconds with decimals |
| DDMMSSX | `355456N` | Degrees, minutes, seconds |
| DDMM.mmX | `3554.50N` | Degrees, decimal minutes |
| DD.ddX | `35.5N` | Decimal degrees |

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src

# Run specific test file
pytest tests/test_parser.py -v
pytest tests/test_visualization.py -v
pytest tests/test_web_ui.py -v
```

## Project Structure

```
AixmParser/
├── src/                          # Python library
│   ├── __init__.py
│   ├── parser.py                 # Main AIXM parser
│   ├── models.py                 # Data models
│   ├── utils.py                  # Utility functions
│   ├── filter.py                 # Filtering logic
│   └── visualization/            # Visualization module
│       ├── __init__.py
│       ├── map_renderer.py       # Folium map renderer
│       └── symbol_loader.py      # Aeronautical symbols
├── web_ui/                       # Browser-based app
│   ├── index.html                # Main HTML page
│   └── js/                       # JavaScript modules
│       ├── aixm-parser.js        # Browser parser
│       ├── map-renderer.js       # Leaflet renderer
│       └── app.js                # Application logic
├── examples/                     # Example scripts
│   ├── parse_sample.py
│   ├── visualize_sample.py
│   └── filter_demo.py
├── tests/                        # Test suite
│   ├── test_parser.py
│   ├── test_visualization.py
│   ├── test_web_ui.py
│   └── test_aixm_elements.py
├── Samples/                      # Sample AIXM files
├── Docs/                         # Documentation
├── Specifications/               # AIXM specifications
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- AIXM is a trademark of the FAA and Eurocontrol
- Aeronautical symbols based on ICAO standards
- Built with [Folium](https://python-visualization.github.io/folium/) and [Leaflet](https://leafletjs.com/)

## Support

For issues, questions, or feature requests, please open an issue on GitHub.
