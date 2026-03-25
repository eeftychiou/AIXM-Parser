"""
Example script demonstrating basic AIXM parsing.

This script shows how to parse an AIXM file and extract various features.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import AIXMParser


def main():
    # Path to your AIXM file
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2026-03-24_400006091018854.xml"
    
    # Alternative: use a file from ddfn_v2
    # aixm_file = Path(r"C:\Users\eftyc\Antigravity\ddfn_v2\AIXM\BD_2025-09-30_400005921419525.xml")
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        print("Please update the path to point to your AIXM file.")
        return
    
    print(f"Parsing AIXM file: {aixm_file}")
    print("-" * 60)
    
    # Parse the file
    parser = AIXMParser(str(aixm_file))
    
    # Get statistics
    stats = parser.get_statistics()
    print("\n=== AIXM File Statistics ===")
    for feature_type, count in stats.items():
        print(f"  {feature_type.capitalize()}: {count}")
    
    # Extract and display airspaces
    print("\n=== Airspaces ===")
    airspaces = parser.get_airspaces()
    for i, airspace in enumerate(airspaces[:10]):  # Show first 10
        print(f"\n{i+1}. {airspace.name}")
        print(f"   Code: {airspace.code_id}")
        print(f"   Type: {airspace.type_code}")
        print(f"   FIR: {airspace.parent_fir}")
        if airspace.vertical_limits:
            lower = airspace.vertical_limits.lower_limit or "N/A"
            upper = airspace.vertical_limits.upper_limit or "N/A"
            print(f"   Vertical: {lower} - {upper}")
        if airspace.polygon:
            print(f"   Has polygon: Yes ({len(airspace.polygon.points)} points)")
    
    if len(airspaces) > 10:
        print(f"\n   ... and {len(airspaces) - 10} more airspaces")
    
    # Extract and display airports
    print("\n=== Airports ===")
    airports = parser.get_airports()
    for i, airport in enumerate(airports[:5]):  # Show first 5
        print(f"\n{i+1}. {airport.name}")
        print(f"   ICAO: {airport.icao}")
        print(f"   IATA: {airport.iata}")
        if airport.position:
            print(f"   Position: {airport.position.lat:.4f}, {airport.position.lon:.4f}")
        if airport.elevation:
            print(f"   Elevation: {airport.elevation} {airport.elevation_unit}")
    
    if len(airports) > 5:
        print(f"\n   ... and {len(airports) - 5} more airports")
    
    # Extract and display waypoints
    print("\n=== Waypoints (first 5) ===")
    waypoints = parser.get_waypoints()
    for i, waypoint in enumerate(waypoints[:5]):
        print(f"\n{i+1}. {waypoint.code_id}")
        print(f"   Name: {waypoint.name}")
        print(f"   Type: {waypoint.type_code}")
        if waypoint.position:
            print(f"   Position: {waypoint.position.lat:.4f}, {waypoint.position.lon:.4f}")
    
    if len(waypoints) > 5:
        print(f"\n   ... and {len(waypoints) - 5} more waypoints")
    
    # Extract and display routes
    print("\n=== Routes ===")
    routes = parser.get_routes()
    for i, route in enumerate(routes[:5]):
        print(f"\n{i+1}. {route.designator}")
        print(f"   Type: {route.route_type}")
        print(f"   Segments: {len(route.segments)}")
        print(f"   Waypoints: {', '.join(route.get_waypoint_ids()[:5])}")
    
    if len(routes) > 5:
        print(f"\n   ... and {len(routes) - 5} more routes")
    
    # Extract and display navaids
    print("\n=== Navaids ===")
    navaids = parser.get_navaids()
    vor_count = sum(1 for n in navaids if n.navaid_type == 'VOR')
    ndb_count = sum(1 for n in navaids if n.navaid_type == 'NDB')
    dme_count = sum(1 for n in navaids if n.navaid_type == 'DME')
    tacan_count = sum(1 for n in navaids if n.navaid_type == 'TACAN')
    
    print(f"  Total: {len(navaids)}")
    print(f"  VOR: {vor_count}")
    print(f"  NDB: {ndb_count}")
    print(f"  DME: {dme_count}")
    print(f"  TACAN: {tacan_count}")
    
    print("\n" + "=" * 60)
    print("Parsing complete!")
    print("\nNext steps:")
    print("  - Run visualize_sample.py to create an interactive map")
    print("  - Use the parser in your own applications")


if __name__ == "__main__":
    main()
