"""
Tests for the AIXM visualization module.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import AIXMParser
from src.visualization.map_renderer import MapRenderer
from src.models import Point, Polygon, Airspace


class TestMapRenderer(unittest.TestCase):
    """Test MapRenderer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_file = Path(__file__).parent.parent / "Samples" / "BD_2026-03-24_400006091018854.xml"
        
        if not self.sample_file.exists():
            self.sample_file = Path(r"C:\Users\eftyc\Antigravity\ddfn_v2\AIXM\BD_2025-09-30_400005921419525.xml")
        
        self.parser = None
        self.renderer = None
        
        if self.sample_file.exists():
            self.parser = AIXMParser(str(self.sample_file))
            self.renderer = MapRenderer(self.parser)
    
    def test_renderer_initialization(self):
        """Test renderer initialization."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        self.assertIsNotNone(self.renderer.map)
        self.assertIsNotNone(self.renderer.parser)
        self.assertIsInstance(self.renderer.layers, dict)
    
    def test_render_airspaces(self):
        """Test rendering airspaces."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        # Should not raise any exceptions
        self.renderer.render_airspaces()
    
    def test_render_airports(self):
        """Test rendering airports."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        self.renderer.render_airports()
    
    def test_render_waypoints(self):
        """Test rendering waypoints."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        self.renderer.render_waypoints()
    
    def test_render_routes(self):
        """Test rendering routes."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        self.renderer.render_routes()
    
    def test_render_navaids(self):
        """Test rendering navaids."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        self.renderer.render_navaids()
    
    def test_render_borders(self):
        """Test rendering borders."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        self.renderer.render_borders()
    
    def test_render_all(self):
        """Test rendering all features."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        self.renderer.render_all(
            airspaces=True,
            airports=True,
            waypoints=True,
            routes=True,
            navaids=True,
            borders=True
        )
    
    def test_get_map(self):
        """Test getting the map object."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        map_obj = self.renderer.get_map()
        self.assertIsNotNone(map_obj)
    
    def test_save_map(self):
        """Test saving the map."""
        if not self.renderer:
            self.skipTest("No sample AIXM file found")
        
        import tempfile
        import os
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            temp_path = f.name
        
        try:
            self.renderer.render_airspaces()
            self.renderer.save_map(temp_path)
            
            # Check file was created
            self.assertTrue(Path(temp_path).exists())
            
            # Check file is not empty
            self.assertGreater(Path(temp_path).stat().st_size, 0)
        finally:
            # Clean up
            if Path(temp_path).exists():
                os.unlink(temp_path)


class TestAirspaceColor(unittest.TestCase):
    """Test airspace color selection."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock parser with minimal data
        self.parser = None
        
    def test_get_airspace_color(self):
        """Test color selection based on airspace type."""
        from src.visualization.map_renderer import MapRenderer
        
        # We can't test without a real parser, but we can test the color constants
        self.assertIn('airspace_fir', MapRenderer.ICAO_COLORS)
        self.assertIn('airspace_cta', MapRenderer.ICAO_COLORS)
        self.assertIn('airspace_tma', MapRenderer.ICAO_COLORS)
        self.assertIn('airspace_sector', MapRenderer.ICAO_COLORS)


if __name__ == '__main__':
    unittest.main()
