"""
Generic filtering system for AIXM 4.5 parser.

This module provides flexible filtering capabilities for AIXM data:
- Filter by element type (include/exclude)
- Filter by geographic bounds (bounding box)
- Filter by FIR code, ICAO code
- Inspect AIXM files to discover element types
- Export filtered subsets to new XML files

Usage:
    from src.filter import AIXMFilterConfig, AIXMInspector
    
    # Filter by element type
    config = AIXMFilterConfig(include=['airspace', 'airport'])
    
    # Inspect file
    inspector = AIXMInspector("file.xml")
    elements = inspector.get_present_element_types()
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Set
from pathlib import Path
import xml.etree.ElementTree as ET
from datetime import datetime


# AIXM Element Type Registry - Maps friendly names to XML tags
AIXM_ELEMENT_TYPES = {
    # Core elements
    'airspace': ['Ase', 'Abd'],
    'airport': ['Ahp'],
    'waypoint': ['Dpn'],
    'route': ['Rte', 'Rsg'],
    'border': ['Gbr'],
    'organization': ['Org'],
    
    # Navaids
    'vor': ['Vor'],
    'ndb': ['Ndb'],
    'dme': ['Dme'],
    'tacan': ['Tcn'],
    
    # Airport infrastructure
    'runway': ['Rwy'],
    'taxiway': ['Twy'],
    'apron': ['Apn'],
    'service': ['Ser'],
    
    # Communication
    'frequency': ['Fqy'],
    'unit': ['Uni'],
    
    # Procedures
    'sid': ['Sid'],
    'star': ['Sia'],
    'approach': ['Iap'],
    
    # Landing systems
    'ils': ['Ils'],
    'marker': ['Mkr'],
}

# Reverse mapping from XML tag to friendly name
XML_TAG_TO_TYPE = {}
for friendly_name, xml_tags in AIXM_ELEMENT_TYPES.items():
    for tag in xml_tags:
        XML_TAG_TO_TYPE[tag] = friendly_name


@dataclass
class AIXMFilterConfig:
    """
    Configuration for filtering AIXM data.
    
    Attributes:
        include: List of element types to include (if None, include all)
        exclude: List of element types to exclude (if None, exclude none)
        bounds: Geographic bounding box (min_lat, min_lon, max_lat, max_lon)
        fir_code: FIR code to filter by
        icao_code: Airport ICAO code to filter by
    """
    include: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    bounds: Optional[Tuple[float, float, float, float]] = None
    fir_code: Optional[str] = None
    icao_code: Optional[str] = None
    
    def __post_init__(self):
        """Validate filter configuration."""
        if self.include and self.exclude:
            raise ValueError("Cannot specify both 'include' and 'exclude'")
        
        # Normalize element type names
        if self.include:
            self.include = [self._normalize_type(t) for t in self.include]
        if self.exclude:
            self.exclude = [self._normalize_type(t) for t in self.exclude]
    
    def _normalize_type(self, element_type: str) -> str:
        """Normalize element type name to standard form."""
        element_type = element_type.lower().strip()
        if element_type not in AIXM_ELEMENT_TYPES:
            raise ValueError(f"Unknown element type: {element_type}")
        return element_type
    
    def should_include_type(self, element_type: str) -> bool:
        """Check if an element type should be included based on filters."""
        element_type = element_type.lower().strip()
        
        if self.exclude and element_type in self.exclude:
            return False
        
        if self.include and element_type not in self.include:
            return False
        
        return True
    
    def get_xml_tags_to_include(self) -> Set[str]:
        """Get the set of XML tags that should be included."""
        tags = set()
        
        for friendly_name, xml_tags in AIXM_ELEMENT_TYPES.items():
            if self.should_include_type(friendly_name):
                tags.update(xml_tags)
        
        return tags


class AIXMInspector:
    """
    Inspector for AIXM files to discover element types and structure.
    
    This class provides methods to analyze AIXM files without fully parsing them,
    useful for understanding what data is available before processing.
    
    Usage:
        inspector = AIXMInspector("file.xml")
        
        # Get all element types with counts
        counts = inspector.get_element_types()
        
        # Get just the list of element types present
        types = inspector.get_present_element_types()
        
        # Check if specific type exists
        has_airspace = inspector.has_element_type('airspace')
    """
    
    def __init__(self, file_path: str):
        """
        Initialize the inspector.
        
        Args:
            file_path: Path to the AIXM XML file
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"AIXM file not found: {file_path}")
        
        self._element_counts: Optional[Dict[str, int]] = None
        self._xml_tag_counts: Optional[Dict[str, int]] = None
    
    def _analyze(self):
        """Analyze the file and count elements."""
        if self._element_counts is not None:
            return
        
        self._xml_tag_counts = {}
        
        # Parse the XML file
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
            
            # Count all XML tags
            for elem in root.iter():
                tag = elem.tag
                if '}' in tag:
                    tag = tag.split('}')[1]
                
                self._xml_tag_counts[tag] = self._xml_tag_counts.get(tag, 0) + 1
            
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse AIXM file: {e}")
        
        # Map XML tags to friendly names
        self._element_counts = {}
        for xml_tag, count in self._xml_tag_counts.items():
            friendly_name = XML_TAG_TO_TYPE.get(xml_tag)
            if friendly_name:
                self._element_counts[friendly_name] = self._element_counts.get(friendly_name, 0) + count
    
    def get_element_types(self) -> Dict[str, int]:
        """
        Get all AIXM element types present in the file with their counts.
        
        Returns:
            Dictionary mapping element type names to occurrence counts
        """
        self._analyze()
        return dict(self._element_counts)
    
    def get_present_element_types(self) -> List[str]:
        """
        Get a list of AIXM element types present in the file.
        
        Returns:
            List of element type names (e.g., ['airspace', 'airport', 'waypoint'])
        """
        self._analyze()
        return sorted(self._element_counts.keys())
    
    def get_xml_tag_counts(self) -> Dict[str, int]:
        """
        Get raw XML tag counts.
        
        Returns:
            Dictionary mapping XML tag names to occurrence counts
        """
        self._analyze()
        return dict(self._xml_tag_counts)
    
    def has_element_type(self, element_type: str) -> bool:
        """
        Check if a specific element type is present in the file.
        
        Args:
            element_type: Element type name (e.g., 'airspace', 'airport')
            
        Returns:
            True if the element type is present, False otherwise
        """
        self._analyze()
        return element_type.lower() in self._element_counts
    
    def get_element_summary(self) -> Dict[str, Any]:
        """
        Get a detailed summary of the AIXM file contents.
        
        Returns:
            Dictionary with file information and element counts
        """
        self._analyze()
        
        # Get file info
        stat = self.file_path.stat()
        
        return {
            'file_path': str(self.file_path),
            'file_size': stat.st_size,
            'file_size_human': self._format_file_size(stat.st_size),
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'element_counts': self._element_counts,
            'total_element_types': len(self._element_counts),
            'total_xml_tags': len(self._xml_tag_counts),
        }
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable form."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def print_summary(self):
        """Print a formatted summary of the AIXM file."""
        summary = self.get_element_summary()
        
        print(f"\n{'='*60}")
        print("AIXM File Summary")
        print(f"{'='*60}")
        print(f"File: {summary['file_path']}")
        print(f"Size: {summary['file_size_human']}")
        print(f"Modified: {summary['last_modified']}")
        print(f"\nElement Types Found: {summary['total_element_types']}")
        print(f"Total XML Tags: {summary['total_xml_tags']}")
        print(f"\nElement Counts:")
        print(f"{'-'*40}")
        
        for element_type, count in sorted(summary['element_counts'].items()):
            print(f"  {element_type:20s}: {count:6d}")
        
        print(f"{'='*60}\n")


class AIXMFilter:
    """
    Filter for AIXM data based on various criteria.
    
    This class provides methods to filter parsed AIXM data according to
    the configuration specified in AIXMFilterConfig.
    
    Usage:
        config = AIXMFilterConfig(include=['airspace', 'airport'])
        filter = AIXMFilter(config)
        
        # Filter parsed data
        filtered_airspaces = filter.filter_elements(parser.get_airspaces())
    """
    
    def __init__(self, config: AIXMFilterConfig):
        """
        Initialize the filter with configuration.
        
        Args:
            config: AIXMFilterConfig instance
        """
        self.config = config
    
    def filter_by_bounds(self, elements: List[Any], 
                         get_position_fn) -> List[Any]:
        """
        Filter elements by geographic bounds.
        
        Args:
            elements: List of elements to filter
            get_position_fn: Function to extract position from element
            
        Returns:
            Filtered list of elements within bounds
        """
        if not self.config.bounds:
            return elements
        
        min_lat, min_lon, max_lat, max_lon = self.config.bounds
        
        filtered = []
        for elem in elements:
            pos = get_position_fn(elem)
            if pos and self._position_in_bounds(pos, min_lat, min_lon, max_lat, max_lon):
                filtered.append(elem)
        
        return filtered
    
    def _position_in_bounds(self, pos, min_lat: float, min_lon: float,
                           max_lat: float, max_lon: float) -> bool:
        """Check if a position is within geographic bounds."""
        # Handle both Point objects and (lat, lon) tuples
        if hasattr(pos, 'lat') and hasattr(pos, 'lon'):
            lat, lon = pos.lat, pos.lon
        elif isinstance(pos, (tuple, list)) and len(pos) >= 2:
            lat, lon = pos[0], pos[1]
        else:
            return False
        
        return (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon)
    
    def filter_by_fir(self, elements: List[Any], 
                      get_fir_fn) -> List[Any]:
        """
        Filter elements by FIR code.
        
        Args:
            elements: List of elements to filter
            get_fir_fn: Function to extract FIR code from element
            
        Returns:
            Filtered list of elements in the specified FIR
        """
        if not self.config.fir_code:
            return elements
        
        target_fir = self.config.fir_code.upper()
        
        return [elem for elem in elements 
                if get_fir_fn(elem) and get_fir_fn(elem).upper() == target_fir]
    
    def filter_by_icao(self, elements: List[Any],
                       get_icao_fn) -> List[Any]:
        """
        Filter elements by ICAO code.
        
        Args:
            elements: List of elements to filter
            get_icao_fn: Function to extract ICAO code from element
            
        Returns:
            Filtered list of elements matching the ICAO code
        """
        if not self.config.icao_code:
            return elements
        
        target_icao = self.config.icao_code.upper()
        
        return [elem for elem in elements
                if get_icao_fn(elem) and get_icao_fn(elem).upper() == target_icao]


def get_available_element_types() -> Dict[str, List[str]]:
    """
    Get a dictionary of all available AIXM element types.
    
    Returns:
        Dictionary mapping category names to lists of element types
    """
    return {
        'Core': ['airspace', 'airport', 'waypoint', 'route', 'border', 'organization'],
        'Navaids': ['vor', 'ndb', 'dme', 'tacan'],
        'Airport Infrastructure': ['runway', 'taxiway', 'apron', 'service'],
        'Communication': ['frequency', 'unit'],
        'Procedures': ['sid', 'star', 'approach'],
        'Landing Systems': ['ils', 'marker'],
    }


def print_available_element_types():
    """Print a formatted list of available element types."""
    types = get_available_element_types()
    
    print(f"\n{'='*60}")
    print("Available AIXM Element Types for Filtering")
    print(f"{'='*60}")
    
    for category, elements in types.items():
        print(f"\n{category}:")
        print(f"{'-'*40}")
        for elem in elements:
            xml_tags = AIXM_ELEMENT_TYPES.get(elem, [])
            print(f"  {elem:20s} ({', '.join(xml_tags)})")
    
    print(f"\n{'='*60}\n")
