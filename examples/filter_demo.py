"""
Demo script for AIXM filtering capabilities.

This script demonstrates how to use the filtering system to:
1. Inspect AIXM files to discover element types
2. Filter by element type (include/exclude)
3. Filter by geographic bounds
4. Filter by FIR code
5. Export filtered data

Usage:
    python examples/filter_demo.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import AIXMParser
from src.filter import (
    AIXMInspector, AIXMFilterConfig,
    print_available_element_types, get_available_element_types
)
from src.visualization.map_renderer import MapRenderer


def demo_inspector():
    """Demo: Inspect AIXM file to discover element types."""
    print("\n" + "="*60)
    print("DEMO 1: Inspecting AIXM File")
    print("="*60)
    
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        return
    
    # Create inspector
    inspector = AIXMInspector(str(aixm_file))
    
    # Print full summary
    inspector.print_summary()
    
    # Get specific information
    print("\n--- Element Types Present ---")
    element_types = inspector.get_present_element_types()
    print(f"Found {len(element_types)} element types:")
    for elem_type in element_types:
        print(f"  - {elem_type}")
    
    # Check for specific types
    print("\n--- Checking for Specific Types ---")
    print(f"Has airspace: {inspector.has_element_type('airspace')}")
    print(f"Has runway: {inspector.has_element_type('runway')}")
    print(f"Has marker: {inspector.has_element_type('marker')}")


def demo_element_type_filtering():
    """Demo: Filter by element type."""
    print("\n" + "="*60)
    print("DEMO 2: Element Type Filtering")
    print("="*60)
    
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        return
    
    # Show available element types
    print_available_element_types()
    
    # Example 1: Include only specific types
    print("\n--- Example 1: Include Only Airspace, Airport, Waypoint ---")
    config = AIXMFilterConfig(include=['airspace', 'airport', 'waypoint'])
    parser = AIXMParser(str(aixm_file), filter_config=config)
    
    stats = parser.get_statistics()
    print("Statistics with include filter:")
    for key, value in stats.items():
        if value > 0:
            print(f"  {key}: {value}")
    
    # Example 2: Exclude procedures
    print("\n--- Example 2: Exclude Procedures (SID, STAR, Approach) ---")
    config2 = AIXMFilterConfig(exclude=['sid', 'star', 'approach'])
    parser2 = AIXMParser(str(aixm_file), filter_config=config2)
    
    stats2 = parser2.get_statistics()
    print("Statistics with exclude filter:")
    print(f"  SIDs: {stats2.get('sids', 0)}")
    print(f"  STARs: {stats2.get('stars', 0)}")
    print(f"  Approaches: {stats2.get('instrument_approaches', 0)}")
    print(f"  Airspaces: {stats2.get('airspaces', 0)}")


def demo_geographic_filtering():
    """Demo: Filter by geographic bounds."""
    print("\n" + "="*60)
    print("DEMO 3: Geographic Filtering")
    print("="*60)
    
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        return
    
    # Filter by bounds (Cyprus area)
    print("\n--- Filtering by Geographic Bounds (Cyprus area) ---")
    config = AIXMFilterConfig(bounds=(34.0, 32.0, 36.0, 34.5))
    parser = AIXMParser(str(aixm_file), filter_config=config)
    
    print(f"Bounds: (34.0, 32.0, 36.0, 34.5)")
    print(f"Filter config: {parser.get_filter_config()}")
    
    # Note: Geographic filtering is applied when accessing elements
    # that have position data (airports, waypoints, navaids)
    airports = parser.get_airports()
    print(f"\nTotal airports in file: {len(airports)}")
    
    # Filtered airports would be accessed through the filter
    from src.filter import AIXMFilter
    filter_obj = AIXMFilter(config)
    filtered_airports = filter_obj.filter_by_bounds(
        airports, lambda a: a.position
    )
    print(f"Airports in bounds: {len(filtered_airports)}")


def demo_fir_filtering():
    """Demo: Filter by FIR code."""
    print("\n" + "="*60)
    print("DEMO 4: FIR Code Filtering")
    print("="*60)
    
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        return
    
    # Filter by FIR code
    print("\n--- Filtering by FIR Code (LCCC) ---")
    config = AIXMFilterConfig(fir_code='LCCC')
    parser = AIXMParser(str(aixm_file), filter_config=config)
    
    # Get airspaces in LCCC FIR
    airspaces = parser.get_airspaces_by_fir('LCCC')
    print(f"Airspaces in LCCC FIR: {len(airspaces)}")
    
    for airspace in airspaces[:5]:  # Show first 5
        print(f"  - {airspace.name or airspace.code_id} ({airspace.type_code})")


def demo_visualization_with_filtering():
    """Demo: Create filtered visualization."""
    print("\n" + "="*60)
    print("DEMO 5: Filtered Visualization")
    print("="*60)
    
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        return
    
    # Create a map with only airspace and airports
    print("\n--- Creating Airspace + Airport Only Map ---")
    config = AIXMFilterConfig(include=['airspace', 'airport'])
    parser = AIXMParser(str(aixm_file), filter_config=config)
    
    renderer = MapRenderer(parser)
    renderer.render_airspaces()
    renderer.render_airports()
    
    output_file = Path(__file__).parent.parent / "filtered_airspace_airport.html"
    renderer.save_map(str(output_file))
    print(f"Filtered map saved to: {output_file}")
    
    # Create a map for LCCC FIR only
    print("\n--- Creating LCCC FIR Map ---")
    parser2 = AIXMParser(str(aixm_file))
    renderer2 = MapRenderer(parser2)
    renderer2.render_airspaces(filter_fir='LCCC')
    renderer2.render_airports()
    
    output_file2 = Path(__file__).parent.parent / "filtered_lccc_fir.html"
    renderer2.save_map(str(output_file2))
    print(f"LCCC FIR map saved to: {output_file2}")


def demo_dynamic_filtering():
    """Demo: Change filters dynamically."""
    print("\n" + "="*60)
    print("DEMO 6: Dynamic Filter Changes")
    print("="*60)
    
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        return
    
    # Start with no filter
    parser = AIXMParser(str(aixm_file))
    print(f"No filter - Total airspaces: {len(parser.get_airspaces())}")
    
    # Apply include filter
    config1 = AIXMFilterConfig(include=['airspace'])
    parser.set_filter(config1)
    print(f"With include filter - Total airspaces: {len(parser.get_airspaces())}")
    
    # Change to exclude filter
    config2 = AIXMFilterConfig(exclude=['runway', 'taxiway', 'apron'])
    parser.set_filter(config2)
    print(f"With exclude filter - Total airspaces: {len(parser.get_airspaces())}")
    print(f"With exclude filter - Total runways: {len(parser.get_runways())}")
    
    # Clear filter
    parser.clear_filter()
    print(f"After clearing filter - Total airspaces: {len(parser.get_airspaces())}")
    print(f"After clearing filter - Total runways: {len(parser.get_runways())}")


def main():
    """Run all demos."""
    print("\n" + "="*60)
    print("AIXM FILTERING SYSTEM DEMONSTRATION")
    print("="*60)
    
    # Run demos
    demo_inspector()
    demo_element_type_filtering()
    demo_geographic_filtering()
    demo_fir_filtering()
    demo_dynamic_filtering()
    
    # Skip visualization demo if running in non-interactive mode
    # demo_visualization_with_filtering()
    
    print("\n" + "="*60)
    print("DEMONSTRATION COMPLETE")
    print("="*60)
    print("\nKey Takeaways:")
    print("  1. Use AIXMInspector to discover what's in AIXM files")
    print("  2. Use AIXMFilterConfig to define filtering criteria")
    print("  3. Pass filter_config to AIXMParser constructor")
    print("  4. Use set_filter() to change filters dynamically")
    print("  5. Use clear_filter() to remove all filters")
    print("\nFor more details, see the implementation_plan.md")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
