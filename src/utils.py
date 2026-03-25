"""
Utility functions for AIXM parsing.

Includes coordinate parsing, XML namespace handling, and helper functions.
"""

import re
from typing import Optional, List, Union
import xml.etree.ElementTree as ET


def parse_coordinate(val: str, ref: str) -> float:
    """
    Parse AIXM coordinate strings to decimal degrees.
    
    Handles formats:
    - DDMMSS.ssX (e.g., "355456N", "0353959E")
    - DDMM.mmX (e.g., "3554.5N")
    - DD.ddX (e.g., "35.5N")
    
    Args:
        val: Coordinate string from AIXM
        ref: "lat" for latitude, "lon" for longitude
        
    Returns:
        Decimal degrees (negative for South/West)
    """
    if not val:
        return 0.0
    
    # Clean the input
    s_coord = str(val).strip().replace(" ", "").replace(",", "")
    s_coord = s_coord.replace("°", "").replace("'", "").replace('"', "")
    
    # Extract direction indicator
    s_dir = ""
    if s_coord[-1].upper() in ["N", "S", "E", "W", "O"]:
        s_dir = s_coord[-1].upper()
        s_coord = s_coord[:-1]
    elif s_coord[0].upper() in ["N", "S", "E", "W", "O"]:
        s_dir = s_coord[0].upper()
        s_coord = s_coord[1:]
    
    # Handle "O" for West (sometimes used in European sources)
    if s_dir == "O":
        s_dir = "W"
    
    try:
        # Check for decimal point
        if "." in s_coord:
            parts = s_coord.split(".")
            main = parts[0]
            decimal_part = float("0." + parts[1])
        else:
            main = s_coord
            decimal_part = 0.0
        
        n = len(main)
        
        if ref == "lat":
            # Latitude: DDMMSS or DDMM or DD
            if n <= 2:  # DD.dd
                deg, mnt, sec = float(main), 0.0, 0.0
            elif n <= 4:  # DDMM.mm
                main = main.zfill(4)
                deg = float(main[:2])
                mnt = float(main[2:]) + decimal_part
                sec = 0.0
            else:  # DDMMSS.ss
                main = main.zfill(6)
                deg = float(main[:2])
                mnt = float(main[2:4])
                sec = float(main[4:]) + decimal_part
        else:  # lon
            # Longitude: DDDMMSS or DDDMM or DDD
            if n <= 3:  # DDD.dd
                deg, mnt, sec = float(main), 0.0, 0.0
            elif n <= 5:  # DDDMM.mm
                main = main.zfill(5)
                deg = float(main[:3])
                mnt = float(main[3:]) + decimal_part
                sec = 0.0
            else:  # DDDMMSS.ss
                main = main.zfill(7)
                deg = float(main[:3])
                mnt = float(main[3:5])
                sec = float(main[5:]) + decimal_part
        
        # Calculate decimal degrees
        dd = deg + (mnt / 60.0) + (sec / 3600.0)
        
        # Apply sign based on direction
        if s_dir in ["S", "W"]:
            dd *= -1
            
        return round(dd, 8)
        
    except (ValueError, IndexError) as e:
        return 0.0


def parse_dms(val: str) -> float:
    """
    Alias for parse_coordinate for backward compatibility.
    Defaults to latitude parsing.
    """
    return parse_coordinate(val, "lat")


def find_all_tags(element: ET.Element, tag_name: str) -> List[ET.Element]:
    """
    Find all instances of a tag, ignoring namespaces.
    
    Args:
        element: XML element to search
        tag_name: Tag name to find
        
    Returns:
        List of matching elements
    """
    # Try without namespace first
    results = element.findall(f".//{tag_name}")
    if results:
        return results
    
    # Try with wildcard namespace
    results = element.findall(f".//{{*}}{tag_name}")
    if results:
        return results
    
    return []


def find_tag_text(element: Optional[ET.Element], tag_name: str, default: str = "") -> str:
    """
    Find text of a tag within an element, ignoring namespaces.
    
    Args:
        element: Parent XML element
        tag_name: Tag name to find
        default: Default value if not found
        
    Returns:
        Text content or default value
    """
    if element is None:
        return default
    
    # Try without namespace
    child = element.find(tag_name)
    if child is not None and child.text:
        return child.text.strip()
    
    # Try with wildcard namespace
    child = element.find(f"{{*}}{tag_name}")
    if child is not None and child.text:
        return child.text.strip()
    
    return default


def find_child_element(element: Optional[ET.Element], tag_name: str) -> Optional[ET.Element]:
    """
    Find a child element, ignoring namespaces.
    
    Args:
        element: Parent XML element
        tag_name: Tag name to find
        
    Returns:
        Child element or None
    """
    if element is None:
        return None
    
    # Try without namespace
    child = element.find(tag_name)
    if child is not None:
        return child
    
    # Try with wildcard namespace
    return element.find(f"{{*}}{tag_name}")


def safe_int(value: Optional[str], default: int = 0) -> int:
    """
    Safely convert a string to integer.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value
    """
    if not value:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value: Optional[str], default: float = 0.0) -> float:
    """
    Safely convert a string to float.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value
    """
    if not value:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def infer_parent_fir(code_id: Optional[str]) -> str:
    """
    Infer the parent FIR from an airspace or sector code.
    
    Uses heuristics based on ICAO region codes.
    
    Args:
        code_id: Airspace code identifier
        
    Returns:
        Inferred FIR code or "UNKNOWN"
    """
    if not code_id:
        return "UNKNOWN"
    
    code_id = code_id.upper()
    
    # Known FIR mappings
    if code_id.startswith("LC"):
        return "LCCC"  # Nicosia FIR
    if code_id.startswith("OL"):
        return "OLBB"  # Beirut FIR
    if code_id.startswith("LL"):
        return "LLLL"  # Tel Aviv FIR
    if code_id.startswith("HE"):
        return "HECC"  # Cairo FIR
    if code_id.startswith("LG"):
        return "LGGG"  # Athens FIR
    if code_id.startswith("LT"):
        return "LTAA"  # Ankara FIR
    if code_id.startswith("UB"):
        return "UBBA"  # Baku FIR
    if code_id.startswith("UD"):
        return "UDDD"  # Yerevan FIR
    if code_id.startswith("OI"):
        return "OIIX"  # Tehran FIR
    if code_id.startswith("OK"):
        return "OKAC"  # Kuwait FIR
    if code_id.startswith("OM"):
        return "OMDB"  # Emirates FIR
    if code_id.startswith("OO"):
        return "OOOI"  # Muscat FIR
    if code_id.startswith("OP"):
        return "OPKR"  # Karachi FIR
    if code_id.startswith("OR"):
        return "ORBB"  # Baghdad FIR
    if code_id.startswith("OS"):
        return "OSTT"  # Damascus FIR
    if code_id.startswith("OY"):
        return "OYSC"  # Sanaa FIR
    
    # Generic: first 2-4 characters
    if len(code_id) >= 4:
        return code_id[:4]
    if len(code_id) >= 2:
        return code_id[:2] + "XX"
    
    return "UNKNOWN"


def parse_vertical_limit(val: Optional[str], uom: Optional[str]) -> tuple:
    """
    Parse vertical limit value and unit.
    
    Args:
        val: Value string (e.g., "6500", "FL65")
        uom: Unit of measurement (e.g., "FT", "FL")
        
    Returns:
        Tuple of (limit_value, unit_type) where unit_type is "FL" or "FT" or "M"
    """
    if not val:
        return (None, None)
    
    val_str = val.strip().upper()
    
    # Check if value already includes FL prefix
    if val_str.startswith("FL"):
        try:
            fl_val = int(val_str[2:])
            return (str(fl_val), "FL")
        except ValueError:
            return (None, None)
    
    # Use provided unit
    if uom:
        uom_upper = uom.upper()
        if "FL" in uom_upper:
            return (val_str, "FL")
        elif "FT" in uom_upper or "FEET" in uom_upper:
            return (val_str, "FT")
        elif "M" in uom_upper:
            return (val_str, "M")
    
    # Default to feet
    return (val_str, "FT")


def get_namespace(element: ET.Element) -> str:
    """
    Extract namespace from an XML element tag.
    
    Args:
        element: XML element
        
    Returns:
        Namespace string or empty string
    """
    tag = element.tag
    if tag.startswith("{"):
        return tag.split("}")[0][1:]
    return ""


def strip_namespace(tag: str) -> str:
    """
    Remove namespace from an XML tag.
    
    Args:
        tag: XML tag string
        
    Returns:
        Tag without namespace
    """
    if tag.startswith("{"):
        return tag.split("}")[1]
    return tag
