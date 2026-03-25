"""
Example script demonstrating AIXM visualization.

This script creates an interactive map with all AIXM features.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import AIXMParser
from src.visualization.map_renderer import MapRenderer


def main():
    # Path to your AIXM file
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    # Alternative: use a file from ddfn_v2
    # aixm_file = Path(r"C:\Users\eftyc\Antigravity\ddfn_v2\AIXM\BD_2025-09-30_400005921419525.xml")
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        print("Please update the path to point to your AIXM file.")
        return
    
    print(f"Parsing AIXM file: {aixm_file}")
    
    # Parse the file
    parser = AIXMParser(str(aixm_file))
    
    # Get statistics
    stats = parser.get_statistics()
    print("\nAIXM File Statistics:")
    for feature_type, count in stats.items():
        print(f"  {feature_type.capitalize()}: {count}")
    
    # Create the map renderer
    print("\nCreating interactive map...")
    renderer = MapRenderer(parser)
    
    # Render all features
    print("  - Rendering airspaces...")
    renderer.render_airspaces()
    
    print("  - Rendering airports...")
    renderer.render_airports()
    
    print("  - Rendering waypoints...")
    renderer.render_waypoints()
    
    print("  - Rendering routes...")
    renderer.render_routes()
    
    print("  - Rendering navaids...")
    renderer.render_navaids()
    
    print("  - Rendering borders...")
    renderer.render_borders()
    
    # Save the map
    output_file = Path(__file__).parent.parent / "aixm_visualization.html"
    renderer.save_map(str(output_file))
    
    print(f"\n{'='*60}")
    print(f"Visualization complete!")
    print(f"Map saved to: {output_file}")
    print(f"\nOpen this file in a web browser to view the interactive map.")
    print(f"\nFeatures included:")
    print(f"  - Airspaces (FIRs, CTAs, TMAs, Sectors)")
    print(f"  - Airports")
    print(f"  - Waypoints")
    print(f"  - Routes")
    print(f"  - Navaids (VOR, NDB, DME, TACAN)")
    print(f"  - Geographical Borders")
    print(f"\nControls:")
    print(f"  - Use the layer control (top-right) to toggle features")
    print(f"  - Click on features for detailed information")
    print(f"  - Use mouse wheel to zoom")
    print(f"  - Drag to pan")
    print(f"{'='*60}")


def demo_filtered_view():
    """
    Demonstrate filtering features by type or FIR.
    """
    print("\n" + "="*60)
    print("DEMO: Filtered View")
    print("="*60)
    
    aixm_file = Path(__file__).parent.parent / "Samples" / "BD_2025-09-30_400005921419525.xml"
    
    if not aixm_file.exists():
        print(f"AIXM file not found: {aixm_file}")
        return
    
    parser = AIXMParser(str(aixm_file))
    
    # Create a map showing only FIR airspaces
    print("\nCreating FIR-only map...")
    renderer = MapRenderer(parser)
    renderer.render_airspaces(filter_type='FIR')
    renderer.render_airports()
    
    output_file = Path(__file__).parent.parent / "aixm_firs_only.html"
    renderer.save_map(str(output_file))
    print(f"FIR-only map saved to: {output_file}")
    
    # Create a map for a specific FIR
    print("\nCreating LCCC FIR map...")
    renderer2 = MapRenderer(parser)
    renderer2.render_airspaces(filter_fir='LCCC')
    renderer2.render_airports()
    
    output_file2 = Path(__file__).parent.parent / "aixm_lccc_fir.html"
    renderer2.save_map(str(output_file2))
    print(f"LCCC FIR map saved to: {output_file2}")


if __name__ == "__main__":
    # Run the main visualization
    main()
    
    # Optionally run the filtered view demo
    # demo_filtered_view()
