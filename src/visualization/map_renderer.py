"""
Map rendering module for AIXM data visualization with ICAO charting symbols.

Uses Folium to create interactive maps with ICAO-standard aeronautical symbols
for airspaces, airports, waypoints, routes, and navaids.

ICAO Charting Symbols Reference (Annex 4):
- VOR: Compass rose with hexagonal center
- VOR-DME: VOR symbol with DME rectangle
- NDB: Beacon symbol with dot pattern
- DME: Small rectangle
- TACAN: Similar to VOR-DME
- Airports: Blue (towered) or magenta (non-towered) circles
- Waypoints: Four-pointed star or triangle
"""

import folium
from folium import GeoJson, LayerControl, Marker, PolyLine, CircleMarker, DivIcon
from folium.plugins import MarkerCluster, MiniMap, Fullscreen
from typing import List, Optional, Tuple, Dict, Any
import json
import colorsys

from ..models import (
    Airspace, Airport, Waypoint, Route, Navaid, 
    GeographicalBorder, Point, Polygon
)
from ..parser import AIXMParser
from .symbol_loader import AeronauticalSymbolLoader


class MapRenderer:
    """
    Renders AIXM data on interactive Folium maps using ICAO charting symbols.
    
    This class provides methods to visualize various AIXM features
    using standardized ICAO aeronautical chart symbols.
    
    Usage:
        parser = AIXMParser("aixm_file.xml")
        renderer = MapRenderer(parser)
        renderer.render_airspaces()
        renderer.render_airports()
        renderer.save_map("output.html")
    
    Attributes:
        parser: AIXMParser instance
        map: Folium Map instance
        layers: Dictionary of layer groups for each feature type
    """
    
    # ICAO Chart Colors (standard aeronautical chart colors)
    ICAO_COLORS = {
        'airspace_fir': '#FF0000',      # Red for FIR boundaries
        'airspace_cta': '#FF6600',      # Orange for CTA
        'airspace_tma': '#FFCC00',      # Yellow for TMA
        'airspace_sector': '#00AA00',   # Green for sectors
        'airspace_default': '#666666',  # Gray for others
        'airport_towered': '#0066CC',   # Blue for towered airports
        'airport_non_towered': '#CC00CC',  # Magenta for non-towered
        'airport_military': '#CC0000',  # Red for military
        'waypoint': '#663399',          # Purple for waypoints
        'waypoint_flyover': '#663399',  # Purple for fly-over waypoints
        'route': '#666666',             # Gray for routes
        'vor': '#0066CC',               # Blue for VOR
        'ndb': '#CC6633',               # Brown for NDB
        'dme': '#CC00CC',               # Magenta for DME
        'tacan': '#0066CC',             # Blue for TACAN
        'border': '#444444',            # Dark gray for borders
    }
    
    def __init__(self, parser: AIXMParser, center: Optional[Tuple[float, float]] = None, 
                 zoom_start: int = 6, use_icao_symbols: bool = True):
        """
        Initialize the map renderer.
        
        Args:
            parser: AIXMParser instance with parsed data
            center: Initial map center (lat, lon). Auto-calculated if None.
            zoom_start: Initial zoom level
            use_icao_symbols: Use ICAO charting symbols (True) or simple markers (False)
        """
        self.parser = parser
        self.use_icao_symbols = use_icao_symbols
        
        # Initialize symbol loader for professional aeronautical symbols
        self.symbol_loader = AeronauticalSymbolLoader()
        
        # Calculate center if not provided
        if center is None:
            center = self._calculate_center()
        
        # Create the base map
        self.map = folium.Map(
            location=center,
            zoom_start=zoom_start,
            tiles='CartoDB positron',
            control_scale=True
        )
        
        # Add additional tile layers
        folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(self.map)
        folium.TileLayer('CartoDB dark_matter', name='Dark Mode').add_to(self.map)
        
        # Initialize layer groups
        self.layers: Dict[str, folium.FeatureGroup] = {}
        self._init_layers()
        
        # Add plugins
        self._add_plugins()
    
    def _calculate_center(self) -> Tuple[float, float]:
        """Calculate map center from airspace bounds."""
        airspaces = self.parser.get_airspaces()
        
        if not airspaces:
            # Default to Europe/Middle East
            return (35.0, 33.0)
        
        # Collect all bounds
        all_lats = []
        all_lons = []
        
        for airspace in airspaces:
            if airspace.polygon:
                bounds = airspace.polygon.bounds()
                if bounds:
                    min_lat, min_lon, max_lat, max_lon = bounds
                    all_lats.extend([min_lat, max_lat])
                    all_lons.extend([min_lon, max_lon])
        
        if all_lats and all_lons:
            return (sum(all_lats) / len(all_lats), sum(all_lons) / len(all_lons))
        
        return (35.0, 33.0)
    
    def _init_layers(self):
        """Initialize layer groups for different feature types."""
        self.layers['airspaces'] = folium.FeatureGroup(name='Airspaces', show=True)
        self.layers['airports'] = folium.FeatureGroup(name='Airports', show=True)
        self.layers['waypoints'] = folium.FeatureGroup(name='Waypoints', show=False)
        self.layers['routes'] = folium.FeatureGroup(name='Routes', show=False)
        self.layers['navaids'] = folium.FeatureGroup(name='Navaids', show=False)
        self.layers['borders'] = folium.FeatureGroup(name='Borders', show=False)
    
    def _add_plugins(self):
        """Add Folium plugins."""
        # Mini map
        MiniMap().add_to(self.map)
        
        # Fullscreen control
        Fullscreen().add_to(self.map)
    
    def _get_airspace_color(self, airspace: Airspace) -> str:
        """Get ICAO color for an airspace based on its type."""
        type_code = (airspace.type_code or '').upper()
        
        if type_code == 'FIR':
            return self.ICAO_COLORS['airspace_fir']
        elif type_code == 'CTA':
            return self.ICAO_COLORS['airspace_cta']
        elif type_code == 'TMA':
            return self.ICAO_COLORS['airspace_tma']
        elif type_code in ['SECTOR', 'SECTOR_C', 'SECTOR_A', 'SECTOR_D']:
            return self.ICAO_COLORS['airspace_sector']
        
        return self.ICAO_COLORS['airspace_default']
    
    def _polygon_to_geojson(self, polygon: Polygon, properties: Dict[str, Any]) -> Dict:
        """Convert a Polygon to GeoJSON format."""
        return {
            'type': 'Feature',
            'properties': properties,
            'geometry': {
                'type': 'Polygon',
                'coordinates': [polygon.to_geojson()]
            }
        }
    
    # ==================== ICAO SYMBOL GENERATORS ====================
    
    def _get_vor_icon(self, navaid: Navaid) -> DivIcon:
        """
        Create VOR symbol using professional aeronautical charting SVG.
        """
        if self.symbol_loader:
            try:
                svg = self.symbol_loader.get_vor_icon()
                return DivIcon(
                    html=svg,
                    icon_size=(32, 32),
                    icon_anchor=(16, 16),
                    popup_anchor=(0, -16)
                )
            except (FileNotFoundError, ValueError):
                pass
        
        # Fallback to simple icon
        return self._get_fallback_vor_icon(navaid)

    def _get_fallback_vor_icon(self, navaid: Navaid) -> DivIcon:
        """
        Create improved ICAO VOR symbol.
        
        Professional styling with gradient fill and clean lines.
        """
        color = self.ICAO_COLORS['vor']
        
        # Improved SVG for VOR symbol
        svg = f'''
        <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="vorGrad" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" style="stop-color:#E3F2FD;stop-opacity:0.8" />
                    <stop offset="100%" style="stop-color:#BBDEFB;stop-opacity:0.4" />
                </radialGradient>
            </defs>
            <!-- Outer glow -->
            <circle cx="14" cy="14" r="12" fill="url(#vorGrad)" stroke="none"/>
            <!-- Compass rose circle -->
            <circle cx="14" cy="14" r="11" fill="none" stroke="{color}" stroke-width="2"/>
            <!-- Hexagon center -->
            <polygon points="14,5 20,8 20,16 14,20 8,16 8,8" 
                     fill="white" stroke="{color}" stroke-width="2"/>
            <!-- Center dot -->
            <circle cx="14" cy="13" r="2.5" fill="{color}"/>
            <!-- N indicator -->
            <text x="14" y="4" text-anchor="middle" font-size="6" fill="{color}" font-family="Arial" font-weight="bold">N</text>
        </svg>
        '''
        
        return DivIcon(
            html=svg,
            icon_size=(28, 28),
            icon_anchor=(14, 14),
            popup_anchor=(0, -14)
        )
    
    def _get_vor_dme_icon(self, navaid: Navaid) -> DivIcon:
        """
        Create ICAO VOR-DME symbol (VOR with DME rectangle).
        
        ICAO Standard: VOR symbol with rectangular DME indicator
        """
        color = self.ICAO_COLORS['vor']
        dme_color = self.ICAO_COLORS['dme']
        
        svg = f'''
        <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
            <!-- DME rectangle -->
            <rect x="18" y="4" width="8" height="8" fill="none" stroke="{dme_color}" stroke-width="1.5"/>
            <!-- Compass rose circle -->
            <circle cx="12" cy="16" r="8" fill="none" stroke="{color}" stroke-width="1.5"/>
            <!-- Hexagon center -->
            <polygon points="12,9 16,12 16,17 12,20 8,17 8,12" 
                     fill="none" stroke="{color}" stroke-width="1.5"/>
            <!-- Center dot -->
            <circle cx="12" cy="16" r="1.5" fill="{color}"/>
        </svg>
        '''
        
        return DivIcon(
            html=svg,
            icon_size=(28, 28),
            icon_anchor=(14, 14),
            popup_anchor=(0, -14)
        )
    
    def _get_ndb_icon(self, navaid: Navaid) -> DivIcon:
        """
        Create NDB symbol using professional aeronautical charting SVG.
        """
        if self.symbol_loader:
            try:
                svg = self.symbol_loader.get_ndb_icon()
                return DivIcon(
                    html=svg,
                    icon_size=(32, 32),
                    icon_anchor=(16, 16),
                    popup_anchor=(0, -16)
                )
            except (FileNotFoundError, ValueError):
                pass
        
        # Fallback to simple icon
        return self._get_fallback_ndb_icon(navaid)

    def _get_fallback_ndb_icon(self, navaid: Navaid) -> DivIcon:
        """
        Create improved NDB symbol.
        
        Professional beacon symbol with warm colors and clean design.
        """
        color = self.ICAO_COLORS['ndb']
        
        svg = f'''
        <svg width="26" height="26" viewBox="0 0 26 26" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="ndbGrad" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" style="stop-color:#FFF3E0;stop-opacity:0.6" />
                    <stop offset="100%" style="stop-color:#FFE0B2;stop-opacity:0.3" />
                </radialGradient>
            </defs>
            <!-- Outer glow -->
            <circle cx="13" cy="13" r="11" fill="url(#ndbGrad)" stroke="none"/>
            <!-- Outer circle -->
            <circle cx="13" cy="13" r="10" fill="none" stroke="{color}" stroke-width="2.5"/>
            <!-- Middle circle -->
            <circle cx="13" cy="13" r="6" fill="none" stroke="{color}" stroke-width="1.5"/>
            <!-- Center dot -->
            <circle cx="13" cy="13" r="3" fill="{color}"/>
            <!-- Signal waves -->
            <path d="M 13 2 Q 15 5 13 8" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.7"/>
            <path d="M 13 18 Q 15 21 13 24" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.7"/>
            <path d="M 2 13 Q 5 15 8 13" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.7"/>
            <path d="M 18 13 Q 21 15 24 13" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.7"/>
        </svg>
        ''',
        
        return DivIcon(
            html=svg,
            icon_size=(26, 26),
            icon_anchor=(13, 13),
            popup_anchor=(0, -13)
        )
    
    def _get_dme_icon(self, navaid: Navaid) -> DivIcon:
        """
        Create improved DME symbol.
        
        Clean square design with magenta coloring.
        """
        color = self.ICAO_COLORS['dme']
        
        svg = f'''
        <svg width="22" height="22" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="dmeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#F3E5F5;stop-opacity:0.8" />
                    <stop offset="100%" style="stop-color:#E1BEE7;stop-opacity:0.4" />
                </linearGradient>
            </defs>
            <!-- Background -->
            <rect x="2" y="2" width="18" height="18" rx="2" fill="url(#dmeGrad)" stroke="none"/>
            <!-- Outer square -->
            <rect x="3" y="3" width="16" height="16" rx="1" fill="none" stroke="{color}" stroke-width="2.5"/>
            <!-- Inner square -->
            <rect x="7" y="7" width="8" height="8" fill="none" stroke="{color}" stroke-width="1.5"/>
            <!-- Center dot -->
            <circle cx="11" cy="11" r="2" fill="{color}"/>
        </svg>
        '''
        
        return DivIcon(
            html=svg,
            icon_size=(22, 22),
            icon_anchor=(11, 11),
            popup_anchor=(0, -11)
        )
    
    def _get_tacan_icon(self, navaid: Navaid) -> DivIcon:
        """
        Create improved TACAN symbol.
        
        Professional design with T indicator and clean styling.
        """
        color = self.ICAO_COLORS['tacan']
        
        svg = f'''
        <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <radialGradient id="tacanGrad" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" style="stop-color:#E0F7FA;stop-opacity:0.8" />
                    <stop offset="100%" style="stop-color:#B2EBF2;stop-opacity:0.4" />
                </radialGradient>
            </defs>
            <!-- Outer glow -->
            <circle cx="14" cy="14" r="12" fill="url(#tacanGrad)" stroke="none"/>
            <!-- Outer circle -->
            <circle cx="14" cy="14" r="11" fill="none" stroke="{color}" stroke-width="2"/>
            <!-- Hexagon -->
            <polygon points="14,5 20,8 20,16 14,20 8,16 8,8" 
                     fill="white" stroke="{color}" stroke-width="2"/>
            <!-- Center dot -->
            <circle cx="14" cy="13" r="2.5" fill="{color}"/>
            <!-- T label -->
            <rect x="10" y="22" width="8" height="5" rx="1" fill="{color}"/>
            <text x="14" y="26" text-anchor="middle" font-size="4" fill="white" font-family="Arial" font-weight="bold">T</text>
        </svg>
        ''',
        
        return DivIcon(
            html=svg,
            icon_size=(28, 28),
            icon_anchor=(14, 14),
            popup_anchor=(0, -14)
        )
    
    def _get_airport_icon(self, airport: Airport) -> DivIcon:
        """
        Create improved airport symbol.
        
        Professional runway symbol with appropriate colors for airport type.
        """
        # Determine airport type and color
        if airport.type_code and 'MIL' in airport.type_code.upper():
            color = self.ICAO_COLORS['airport_military']
            bg_color = '#FFEBEE'
        elif airport.icao:
            color = self.ICAO_COLORS['airport_towered']
            bg_color = '#E3F2FD'
        else:
            color = self.ICAO_COLORS['airport_non_towered']
            bg_color = '#F3E5F5'
        
        svg = f'''
        <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
            <!-- Background -->
            <circle cx="14" cy="14" r="12" fill="{bg_color}" stroke="none" opacity="0.6"/>
            <!-- Outer circle -->
            <circle cx="14" cy="14" r="11" fill="none" stroke="{color}" stroke-width="2.5"/>
            <!-- Main runway (vertical) -->
            <rect x="12" y="5" width="4" height="18" fill="none" stroke="{color}" stroke-width="1.5"/>
            <!-- Cross runway (horizontal) -->
            <rect x="5" y="12" width="18" height="4" fill="none" stroke="{color}" stroke-width="1.5"/>
            <!-- Center point -->
            <circle cx="14" cy="14" r="2" fill="{color}"/>
        </svg>
        ''',
        
        return DivIcon(
            html=svg,
            icon_size=(28, 28),
            icon_anchor=(14, 14),
            popup_anchor=(0, -14)
        )
    
    def _get_waypoint_icon(self, waypoint: Waypoint, flyover: bool = False) -> DivIcon:
        """
        Create improved waypoint symbol.
        
        Elegant star or triangle design with purple coloring.
        """
        color = self.ICAO_COLORS['waypoint']
        
        if flyover:
            # Fly-over waypoint: triangle with circle
            svg = f'''
            <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <!-- Outer circle -->
                <circle cx="12" cy="12" r="10" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.5"/>
                <!-- Triangle -->
                <polygon points="12,4 20,18 4,18" fill="none" stroke="{color}" stroke-width="2"/>
                <!-- Center dot -->
                <circle cx="12" cy="13" r="2" fill="{color}"/>
            </svg>
            '''
        else:
            # Standard waypoint: elegant four-pointed star
            svg = f'''
            <svg width="22" height="22" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg">
                <!-- Background glow -->
                <circle cx="11" cy="11" r="9" fill="#F3E5F5" opacity="0.5" stroke="none"/>
                <!-- Four-pointed star -->
                <polygon points="11,2 12.5,9 20,11 12.5,13 11,20 9.5,13 2,11 9.5,9" 
                         fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>
                <!-- Center -->
                <circle cx="11" cy="11" r="2" fill="{color}"/>
            </svg>
            '''
        
        return DivIcon(
            html=svg,
            icon_size=(22, 22),
            icon_anchor=(11, 11),
            popup_anchor=(0, -11)
        )
    
    # ==================== RENDER METHODS ====================
    
    def render_airspaces(self, filter_type: Optional[str] = None, 
                         filter_fir: Optional[str] = None):
        """
        Render airspaces on the map with ICAO boundary styling.
        
        Args:
            filter_type: Only render airspaces of this type (e.g., 'FIR', 'CTA')
            filter_fir: Only render airspaces belonging to this FIR
        """
        airspaces = self.parser.get_airspaces()
        
        for airspace in airspaces:
            # Apply filters
            if filter_type and airspace.type_code != filter_type.upper():
                continue
            if filter_fir and airspace.parent_fir != filter_fir.upper():
                continue
            
            if not airspace.polygon:
                continue
            
            # Get color based on type
            color = self._get_airspace_color(airspace)
            
            # Build popup content
            popup_html = self._build_airspace_popup(airspace)
            
            # Create GeoJSON for the polygon
            properties = {
                'name': airspace.name or airspace.code_id,
                'type': airspace.type_code,
                'style': {
                    'fillColor': color,
                    'color': color,
                    'weight': 2,
                    'fillOpacity': 0.15
                }
            }
            
            geojson = self._polygon_to_geojson(airspace.polygon, properties)
            
            # Add to map with ICAO-style dashed boundary for FIRs
            dash_array = '5, 5' if airspace.type_code == 'FIR' else None
            
            GeoJson(
                geojson,
                style_function=lambda x, color=color, dash=dash_array: {
                    'fillColor': color,
                    'color': color,
                    'weight': 2,
                    'fillOpacity': 0.15,
                    'dashArray': dash
                },
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(self.layers['airspaces'])
    
    def _build_airspace_popup(self, airspace: Airspace) -> str:
        """Build HTML popup content for an airspace."""
        html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
            <h4 style="margin: 0 0 10px 0; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px;">
                {airspace.name or airspace.code_id}
            </h4>
            <table style="font-size: 12px; width: 100%;">
                <tr><td><b>Type:</b></td><td>{airspace.type_code or 'N/A'}</td></tr>
                <tr><td><b>Code:</b></td><td>{airspace.code_id or 'N/A'}</td></tr>
                <tr><td><b>FIR:</b></td><td>{airspace.parent_fir or 'N/A'}</td></tr>
        """
        
        if airspace.vertical_limits:
            limits = airspace.vertical_limits
            lower = f"{limits.lower_limit} {limits.lower_unit}" if limits.lower_limit else "N/A"
            upper = f"{limits.upper_limit} {limits.upper_unit}" if limits.upper_limit else "N/A"
            html += f"<tr><td><b>Lower:</b></td><td>{lower}</td></tr>"
            html += f"<tr><td><b>Upper:</b></td><td>{upper}</td></tr>"
        
        html += "</table></div>"
        return html
    
    def render_airports(self, min_zoom: int = 8):
        """
        Render airports on the map with ICAO symbols.
        
        Args:
            min_zoom: Minimum zoom level to show airports
        """
        airports = self.parser.get_airports()
        
        for airport in airports:
            if not airport.position:
                continue
            
            # Build popup content
            popup_html = self._build_airport_popup(airport)
            
            if self.use_icao_symbols:
                # Use ICAO airport symbol
                icon = self._get_airport_icon(airport)
                marker = Marker(
                    location=airport.position.to_tuple(),
                    icon=icon,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=airport.name or airport.code_id
                )
            else:
                # Use simple circle marker
                color = self.ICAO_COLORS['airport_towered'] if airport.icao else self.ICAO_COLORS['airport_non_towered']
                marker = CircleMarker(
                    location=airport.position.to_tuple(),
                    radius=6,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.8,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=airport.name or airport.code_id
                )
            
            marker.add_to(self.layers['airports'])
    
    def _build_airport_popup(self, airport: Airport) -> str:
        """Build HTML popup content for an airport."""
        # Determine airport type label
        if airport.type_code and 'MIL' in airport.type_code.upper():
            type_label = "Military"
        elif airport.icao:
            type_label = "Towered (Controlled)"
        else:
            type_label = "Non-Towered"
        
        html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
            <h4 style="margin: 0 0 10px 0; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px;">
                {airport.name or airport.code_id}
            </h4>
            <table style="font-size: 12px; width: 100%;">
        """
        
        if airport.icao:
            html += f"<tr><td><b>ICAO:</b></td><td>{airport.icao}</td></tr>"
        if airport.iata:
            html += f"<tr><td><b>IATA:</b></td><td>{airport.iata}</td></tr>"
        if airport.code_id and not airport.icao:
            html += f"<tr><td><b>Code:</b></td><td>{airport.code_id}</td></tr>"
        if airport.city:
            html += f"<tr><td><b>City:</b></td><td>{airport.city}</td></tr>"
        if airport.elevation:
            html += f"<tr><td><b>Elevation:</b></td><td>{airport.elevation} {airport.elevation_unit}</td></tr>"
        
        html += f"<tr><td><b>Type:</b></td><td>{type_label}</td></tr>"
        html += "</table></div>"
        return html
    
    def render_waypoints(self):
        """Render waypoints on the map with ICAO symbols."""
        waypoints = self.parser.get_waypoints()
        
        for waypoint in waypoints:
            if not waypoint.position:
                continue
            
            popup_html = self._build_waypoint_popup(waypoint)
            
            if self.use_icao_symbols:
                # Use ICAO waypoint symbol (four-pointed star)
                icon = self._get_waypoint_icon(waypoint, flyover=False)
                marker = Marker(
                    location=waypoint.position.to_tuple(),
                    icon=icon,
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=waypoint.code_id
                )
            else:
                # Use simple circle marker
                marker = CircleMarker(
                    location=waypoint.position.to_tuple(),
                    radius=4,
                    color=self.ICAO_COLORS['waypoint'],
                    fill=True,
                    fillColor=self.ICAO_COLORS['waypoint'],
                    fillOpacity=0.7,
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=waypoint.code_id
                )
            
            marker.add_to(self.layers['waypoints'])
    
    def _build_waypoint_popup(self, waypoint: Waypoint) -> str:
        """Build HTML popup content for a waypoint."""
        html = f"""
        <div style="font-family: Arial, sans-serif;">
            <h4 style="margin: 0 0 10px 0; color: #333;">{waypoint.code_id}</h4>
            <p style="margin: 5px 0; font-size: 12px;">
                <b>Type:</b> {waypoint.type_code or 'N/A'}<br>
                <b>Lat:</b> {waypoint.position.lat:.4f}<br>
                <b>Lon:</b> {waypoint.position.lon:.4f}
            </p>
        </div>
        """
        return html
    
    def render_routes(self):
        """Render routes on the map."""
        routes = self.parser.get_routes()
        
        for route in routes:
            for segment in route.segments:
                line = segment.to_line()
                if not line:
                    continue
                
                popup_html = f"""
                <div style="font-family: Arial, sans-serif;">
                    <h4 style="margin: 0 0 10px 0; color: #333;">{route.designator or route.code_id}</h4>
                    <p style="margin: 5px 0; font-size: 12px;">
                        <b>From:</b> {segment.start_waypoint_id or 'N/A'}<br>
                        <b>To:</b> {segment.end_waypoint_id or 'N/A'}<br>
                        <b>Type:</b> {segment.path_type or 'N/A'}
                    </p>
                </div>
                """
                
                PolyLine(
                    locations=line.to_tuples(),
                    color=self.ICAO_COLORS['route'],
                    weight=1,
                    opacity=0.6,
                    popup=folium.Popup(popup_html, max_width=200)
                ).add_to(self.layers['routes'])
    
    def render_navaids(self):
        """Render navigation aids on the map with ICAO symbols."""
        navaids = self.parser.get_navaids()
        
        for navaid in navaids:
            if not navaid.position:
                continue
            
            popup_html = self._build_navaid_popup(navaid)
            
            if self.use_icao_symbols:
                # Select ICAO symbol based on navaid type
                navaid_type = (navaid.navaid_type or '').upper()
                
                if navaid_type == 'VOR':
                    icon = self._get_vor_icon(navaid)
                elif navaid_type == 'NDB':
                    icon = self._get_ndb_icon(navaid)
                elif navaid_type == 'DME':
                    icon = self._get_dme_icon(navaid)
                elif navaid_type == 'TACAN':
                    icon = self._get_tacan_icon(navaid)
                else:
                    # Default to VOR symbol
                    icon = self._get_vor_icon(navaid)
                
                marker = Marker(
                    location=navaid.position.to_tuple(),
                    icon=icon,
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=f"{navaid.code_id} ({navaid.navaid_type})"
                )
            else:
                # Use simple circle marker
                navaid_type = (navaid.navaid_type or '').lower()
                color = self.ICAO_COLORS.get(navaid_type, self.ICAO_COLORS['vor'])
                
                marker = CircleMarker(
                    location=navaid.position.to_tuple(),
                    radius=5,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.8,
                    popup=folium.Popup(popup_html, max_width=200),
                    tooltip=f"{navaid.code_id} ({navaid.navaid_type})"
                )
            
            marker.add_to(self.layers['navaids'])
    
    def _build_navaid_popup(self, navaid: Navaid) -> str:
        """Build HTML popup content for a navaid."""
        html = f"""
        <div style="font-family: Arial, sans-serif; min-width: 180px;">
            <h4 style="margin: 0 0 10px 0; color: #333; border-bottom: 1px solid #ddd; padding-bottom: 5px;">
                {navaid.code_id} ({navaid.navaid_type})
            </h4>
            <table style="font-size: 12px; width: 100%;">
        """
        
        if navaid.name:
            html += f"<tr><td><b>Name:</b></td><td>{navaid.name}</td></tr>"
        if navaid.frequency:
            html += f"<tr><td><b>Freq:</b></td><td>{navaid.frequency} {navaid.frequency_unit or ''}</td></tr>"
        if navaid.channel:
            html += f"<tr><td><b>Channel:</b></td><td>{navaid.channel}</td></tr>"
        
        html += "</table></div>"
        return html
    
    def render_borders(self):
        """Render geographical borders on the map."""
        borders = self.parser.get_geographical_borders()
        
        for border in borders:
            if not border.polygon:
                continue
            
            properties = {
                'name': border.name,
                'type': border.border_type,
                'style': {
                    'fillColor': self.ICAO_COLORS['border'],
                    'color': self.ICAO_COLORS['border'],
                    'weight': 1,
                    'fillOpacity': 0.1
                }
            }
            
            geojson = self._polygon_to_geojson(border.polygon, properties)
            
            popup_html = f"""
            <div style="font-family: Arial, sans-serif;">
                <h4 style="margin: 0 0 10px 0; color: #333;">{border.name}</h4>
                <p style="margin: 5px 0; font-size: 12px;">
                    <b>Type:</b> {border.border_type or 'N/A'}
                </p>
            </div>
            """
            
            GeoJson(
                geojson,
                style_function=lambda x: {
                    'fillColor': self.ICAO_COLORS['border'],
                    'color': self.ICAO_COLORS['border'],
                    'weight': 1,
                    'fillOpacity': 0.1
                },
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(self.layers['borders'])
    
    def render_all(self, airspaces: bool = True, airports: bool = True, 
                   waypoints: bool = False, routes: bool = False,
                   navaids: bool = False, borders: bool = False):
        """
        Render all selected feature types.
        
        Args:
            airspaces: Render airspaces
            airports: Render airports
            waypoints: Render waypoints
            routes: Render routes
            navaids: Render navaids
            borders: Render borders
        """
        if airspaces:
            self.render_airspaces()
        if airports:
            self.render_airports()
        if waypoints:
            self.render_waypoints()
        if routes:
            self.render_routes()
        if navaids:
            self.render_navaids()
        if borders:
            self.render_borders()
    
    def finalize(self):
        """Add all layers to the map and add layer control."""
        # Add all layer groups to map
        for layer in self.layers.values():
            layer.add_to(self.map)
        
        # Add layer control
        LayerControl().add_to(self.map)
    
    def save_map(self, filepath: str):
        """
        Save the map to an HTML file.
        
        Args:
            filepath: Output file path
        """
        self.finalize()
        self.map.save(filepath)
        print(f"Map saved to: {filepath}")
    
    def get_map(self) -> folium.Map:
        """Get the Folium map object."""
        self.finalize()
        return self.map
