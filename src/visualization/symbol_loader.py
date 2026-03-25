"""
SVG Symbol Loader for Aeronautical Charting

Loads and customizes professional SVG symbols from the aeronautical_charting repository.
https://github.com/antoniolocandro/aeronautical_charting

These are ICAO-compliant symbols designed for professional aeronautical charts.
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional


class AeronauticalSymbolLoader:
    """
    Loads and customizes professional aeronautical SVG symbols.
    
    This class loads SVG files from the aeronautical_charting repository
    and customizes them with appropriate colors for use in Folium maps.
    """
    
    # Mapping of symbol names to SVG filenames
    SYMBOL_FILES = {
        'vor': '101_Navaid_VOR.svg',
        'ndb': '100_Navaid_NDB.svg',
        'dme': '102_Navaid_DME.svg',
        'vor_dme': '103_Navaid_VOR_DME.svg',
        'tacan': '106_Navaid_TACAN.svg',
        'vortac': '107_Navaid_VORTAC.svg',
        'airport_civil': '084_AD_CivilLand.svg',
        'airport_military': '086_AD_MilitaryLand.svg',
        'airport_heliport': '094_AD_Heliport.svg',
        'airport_emergency': '090_AD_Emergency_No_Facility.svg',
        'waypoint_compulsory': '121_Compulsory_Fly_By_Waypoint.svg',
        'waypoint_on_request': '121_On_Request_Fly_By_Waypoint.svg',
        'waypoint_flyover': '121_On_Request_Fly_Over_Waypoint.svg',
        'ats_met_compulsory': '123_ATS_MET_compulsory.svg',
        'ats_met_non_compulsory': '123_ATS_MET_non_compulsory.svg',
        'faf': '124_FAF.svg',
        'rvr_site': '153_AD_RVR_site.svg',
        'windsock': '996_Windsock.svg',
        'vdp': '997_VDP.svg',
        'mapt': '998_MAPt.svg',
        'obstacle': '130_obstacle.svg',
        'obstacle_lighted': '131_lighted_obstacle.svg',
        'obstacle_grouped': '132_grouped_obstacle.svg',
        'obstacle_grouped_lighted': '133_grouped_lighted_obstacle.svg',
        'windfarm': '140_single_windfarm_no_light.svg',
        'tree': 'tree.svg',
    }
    
    # ICAO standard colors for aeronautical charts
    COLORS = {
        'vor': '#000080',           # Navy blue for VOR
        'ndb': '#8B4513',           # Brown for NDB
        'dme': '#000080',           # Navy blue for DME
        'tacan': '#000080',         # Navy blue for TACAN
        'airport_civil': '#000080', # Navy blue for civil airports
        'airport_military': '#CC0000',  # Red for military
        'waypoint': '#000080',      # Navy blue for waypoints
        'obstacle': '#000000',      # Black for obstacles
    }
    
    def __init__(self, symbols_dir: Optional[str] = None):
        """
        Initialize the symbol loader.
        
        Args:
            symbols_dir: Path to the SVG symbols directory. 
                        If None, looks for 'charting_symbols/svg_icons/qgis_parametrized'
                        relative to the current file.
        """
        if symbols_dir is None:
            # Default path relative to this file
            current_dir = Path(__file__).parent.parent.parent
            symbols_dir = current_dir / 'charting_symbols' / 'svg_icons' / 'qgis_parametrized'
        
        self.symbols_dir = Path(symbols_dir)
        self._cache: Dict[str, str] = {}
    
    def _load_svg(self, filename: str) -> str:
        """Load an SVG file and return its contents."""
        filepath = self.symbols_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Symbol file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _customize_svg(self, svg_content: str, color: str) -> str:
        """
        Customize SVG with the given color.
        
        Replaces QGIS param(fill) placeholders with actual color values.
        """
        # Replace param(fill)#000000 pattern
        svg_content = re.sub(
            r'param\(fill\)#([0-9A-Fa-f]{6})',
            color,
            svg_content
        )
        
        # Replace param(fill) pattern
        svg_content = re.sub(
            r'param\(fill\)',
            color,
            svg_content
        )
        
        # Replace param(stroke) pattern
        svg_content = re.sub(
            r'param\(stroke\)',
            color,
            svg_content
        )
        
        return svg_content
    
    def _extract_svg_content(self, svg_content: str) -> str:
        """
        Extract just the SVG content between svg tags.
        
        Removes XML declaration, metadata, and namespace prefixes to get clean SVG for embedding.
        """
        # Find the svg tag
        svg_match = re.search(r'(<svg[^>]*>.*?</svg>)', svg_content, re.DOTALL)
        if svg_match:
            svg_content = svg_match.group(1)
        
        # Remove XML declarations
        svg_content = re.sub(r'<\?xml[^?]*\?>', '', svg_content)
        
        # Remove DOCTYPE declarations
        svg_content = re.sub(r'<!DOCTYPE[^>]*>', '', svg_content, flags=re.DOTALL)
        
        # Remove metadata sections
        svg_content = re.sub(r'<metadata>.*?</metadata>', '', svg_content, flags=re.DOTALL)
        
        # Remove sodipodi and inkscape namespace elements and attributes
        svg_content = re.sub(r'<sodipodi:[^>]*>', '', svg_content)
        svg_content = re.sub(r'</sodipodi:[^>]*>', '', svg_content)
        svg_content = re.sub(r'<inkscape:[^>]*>', '', svg_content)
        svg_content = re.sub(r'</inkscape:[^>]*>', '', svg_content)
        
        # Remove sodipodi and inkscape attributes
        svg_content = re.sub(r'\s+inkscape:[^=]*="[^"]*"', '', svg_content)
        svg_content = re.sub(r'\s+sodipodi:[^=]*="[^"]*"', '', svg_content)
        
        # Remove xmlns:sodipodi and xmlns:inkscape declarations
        svg_content = re.sub(r'\s+xmlns:sodipodi="[^"]*"', '', svg_content)
        svg_content = re.sub(r'\s+xmlns:inkscape="[^"]*"', '', svg_content)
        
        # Remove other namespace declarations (dc, cc, rdf, svg)
        svg_content = re.sub(r'\s+xmlns:dc="[^"]*"', '', svg_content)
        svg_content = re.sub(r'\s+xmlns:cc="[^"]*"', '', svg_content)
        svg_content = re.sub(r'\s+xmlns:rdf="[^"]*"', '', svg_content)
        svg_content = re.sub(r'\s+xmlns:svg="[^"]*"', '', svg_content)
        
        # Remove rdf:RDF sections
        svg_content = re.sub(r'<rdf:RDF>.*?</rdf:RDF>', '', svg_content, flags=re.DOTALL)
        
        # Remove cc:Work and dc elements
        svg_content = re.sub(r'<cc:Work[^>]*>.*?</cc:Work>', '', svg_content, flags=re.DOTALL)
        svg_content = re.sub(r'<dc:[^>]*>[^<]*</dc:[^>]*>', '', svg_content)
        
        # Normalize whitespace - replace multiple newlines/spaces with single space
        svg_content = re.sub(r'\s+', ' ', svg_content)
        
        # Remove spaces between tags
        svg_content = re.sub(r'>\s+<', '><', svg_content)
        
        # Convert double quotes to single quotes for JavaScript embedding
        svg_content = svg_content.replace('"', "'")
        
        return svg_content.strip()
    
    def get_symbol(self, symbol_name: str, color: Optional[str] = None) -> str:
        """
        Get a customized SVG symbol.
        
        Args:
            symbol_name: Name of the symbol (e.g., 'vor', 'ndb', 'airport_civil')
            color: Custom color (hex). If None, uses default color.
        
        Returns:
            SVG content as string
        """
        # Check cache first
        cache_key = f"{symbol_name}_{color}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Get filename
        filename = self.SYMBOL_FILES.get(symbol_name)
        if not filename:
            raise ValueError(f"Unknown symbol: {symbol_name}")
        
        # Load and customize
        svg_content = self._load_svg(filename)
        
        # Use default color if not specified
        if color is None:
            color = self.COLORS.get(symbol_name, '#000000')
        
        # Customize with color
        svg_content = self._customize_svg(svg_content, color)
        
        # Extract clean SVG
        svg_content = self._extract_svg_content(svg_content)
        
        # Cache result
        self._cache[cache_key] = svg_content
        
        return svg_content
    
    def get_vor_icon(self) -> str:
        """Get VOR symbol."""
        return self.get_symbol('vor')
    
    def get_ndb_icon(self) -> str:
        """Get NDB symbol."""
        return self.get_symbol('ndb')
    
    def get_dme_icon(self) -> str:
        """Get DME symbol."""
        return self.get_symbol('dme')
    
    def get_vor_dme_icon(self) -> str:
        """Get VOR-DME symbol."""
        return self.get_symbol('vor_dme')
    
    def get_tacan_icon(self) -> str:
        """Get TACAN symbol."""
        return self.get_symbol('tacan')
    
    def get_airport_icon(self, airport_type: str = 'civil') -> str:
        """
        Get airport symbol.
        
        Args:
            airport_type: 'civil', 'military', 'heliport', or 'emergency'
        """
        symbol_map = {
            'civil': 'airport_civil',
            'military': 'airport_military',
            'heliport': 'airport_heliport',
            'emergency': 'airport_emergency',
        }
        symbol_name = symbol_map.get(airport_type, 'airport_civil')
        return self.get_symbol(symbol_name)
    
    def get_waypoint_icon(self, waypoint_type: str = 'compulsory') -> str:
        """
        Get waypoint symbol.
        
        Args:
            waypoint_type: 'compulsory', 'on_request', or 'flyover'
        """
        symbol_map = {
            'compulsory': 'waypoint_compulsory',
            'on_request': 'waypoint_on_request',
            'flyover': 'waypoint_flyover',
        }
        symbol_name = symbol_map.get(waypoint_type, 'waypoint_compulsory')
        return self.get_symbol(symbol_name)
    
    def list_available_symbols(self) -> list:
        """List all available symbol names."""
        return list(self.SYMBOL_FILES.keys())
