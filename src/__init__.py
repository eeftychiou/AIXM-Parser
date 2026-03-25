"""
AIXM 4.5 Parser - Aeronautical Information Exchange Model Parser

A Python library for parsing AIXM 4.5 XML files and visualizing aeronautical data.

Usage:
    from aixm_parser import AIXMParser
    
    parser = AIXMParser("path/to/aixm_file.xml")
    airspaces = parser.get_airspaces()
    airports = parser.get_airports()
"""

__version__ = "0.1.0"
__author__ = "AIXM Parser Team"

from .parser import AIXMParser
from .models import (
    AIXMFeature,
    Airspace,
    Airport,
    Waypoint,
    Route,
    RouteSegment,
    Navaid,
    Point,
    Polygon,
    LineString,
)

__all__ = [
    "AIXMParser",
    "AIXMFeature",
    "Airspace",
    "Airport",
    "Waypoint",
    "Route",
    "RouteSegment",
    "Navaid",
    "Point",
    "Polygon",
    "LineString",
]
