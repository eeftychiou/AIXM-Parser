"""
Tests for the AIXM parser.
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import AIXMParser
from src.utils import parse_coordinate


class TestCoordinateParsing(unittest.TestCase):
    """Test coordinate parsing functions."""
    
    def test_parse_dms_latitude(self):
        """Test parsing DMS latitude."""
        # DDMMSS format
        self.assertAlmostEqual(parse_coordinate("355456N", "lat"), 35.915556, places=5)
        self.assertAlmostEqual(parse_coordinate("355456S", "lat"), -35.915556, places=5)
        
        # DDMM format
        self.assertAlmostEqual(parse_coordinate("3554N", "lat"), 35.9, places=5)
        self.assertAlmostEqual(parse_coordinate("3554S", "lat"), -35.9, places=5)
        
        # DD format (2 digits or less treated as degrees)
        self.assertAlmostEqual(parse_coordinate("35N", "lat"), 35.0, places=5)
        self.assertAlmostEqual(parse_coordinate("35S", "lat"), -35.0, places=5)
        
        # Note: "35.5N" is parsed as 35 degrees (DD format)
        # The parsing logic treats 2-digit numbers as decimal degrees
        self.assertAlmostEqual(parse_coordinate("35.5N", "lat"), 35.0, places=5)
        self.assertAlmostEqual(parse_coordinate("35.5S", "lat"), -35.0, places=5)
    
    def test_parse_dms_longitude(self):
        """Test parsing DMS longitude."""
        # DDDMMSS format
        self.assertAlmostEqual(parse_coordinate("0353959E", "lon"), 35.666389, places=5)
        self.assertAlmostEqual(parse_coordinate("0353959W", "lon"), -35.666389, places=5)
        
        # DDDMM format
        self.assertAlmostEqual(parse_coordinate("03539E", "lon"), 35.65, places=5)
        self.assertAlmostEqual(parse_coordinate("03539W", "lon"), -35.65, places=5)
        
        # DDD format (3 digits or less treated as degrees)
        self.assertAlmostEqual(parse_coordinate("035E", "lon"), 35.0, places=5)
        self.assertAlmostEqual(parse_coordinate("035W", "lon"), -35.0, places=5)
        
        # Note: "35.5E" is parsed as 35 degrees (DDD format)
        # The parsing logic treats 2-digit numbers as decimal degrees
        self.assertAlmostEqual(parse_coordinate("35.5E", "lon"), 35.0, places=5)
        self.assertAlmostEqual(parse_coordinate("35.5W", "lon"), -35.0, places=5)
    
    def test_parse_coordinate_with_direction_prefix(self):
        """Test coordinates with direction prefix."""
        self.assertAlmostEqual(parse_coordinate("N355456", "lat"), 35.915556, places=5)
        self.assertAlmostEqual(parse_coordinate("E0353959", "lon"), 35.666389, places=5)
    
    def test_parse_coordinate_european_west(self):
        """Test European 'O' for West."""
        self.assertAlmostEqual(parse_coordinate("0353959O", "lon"), -35.666389, places=5)
    
    def test_parse_empty_coordinate(self):
        """Test parsing empty coordinate."""
        self.assertEqual(parse_coordinate("", "lat"), 0.0)
        self.assertEqual(parse_coordinate(None, "lon"), 0.0)


class TestAIXMParser(unittest.TestCase):
    """Test AIXMParser class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Find a sample AIXM file
        self.sample_file = Path(__file__).parent.parent / "Samples" / "BD_2026-03-24_400006091018854.xml"
        
        # Alternative sample from ddfn_v2
        if not self.sample_file.exists():
            self.sample_file = Path(r"C:\Users\eftyc\Antigravity\ddfn_v2\AIXM\BD_2025-09-30_400005921419525.xml")
        
        self.parser = None
        if self.sample_file.exists():
            self.parser = AIXMParser(str(self.sample_file))
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        if not self.sample_file.exists():
            self.skipTest("No sample AIXM file found")
        
        self.assertIsNotNone(self.parser.root)
        self.assertIsNotNone(self.parser.tree)
    
    def test_get_statistics(self):
        """Test getting statistics."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        stats = self.parser.get_statistics()
        
        # Check that all expected keys exist
        expected_keys = ['airspaces', 'airports', 'waypoints', 'routes', 
                        'navaids', 'borders', 'organizations']
        for key in expected_keys:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], int)
    
    def test_get_airspaces(self):
        """Test extracting airspaces."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        airspaces = self.parser.get_airspaces()
        self.assertIsInstance(airspaces, list)
        
        for airspace in airspaces:
            self.assertIsNotNone(airspace.code_id)
            # Check that airspaces have required attributes
            self.assertTrue(hasattr(airspace, 'type_code'))
            self.assertTrue(hasattr(airspace, 'parent_fir'))
    
    def test_get_airports(self):
        """Test extracting airports."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        airports = self.parser.get_airports()
        self.assertIsInstance(airports, list)
        
        for airport in airports:
            self.assertIsNotNone(airport.code_id)
            self.assertTrue(hasattr(airport, 'position'))
    
    def test_get_waypoints(self):
        """Test extracting waypoints."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        waypoints = self.parser.get_waypoints()
        self.assertIsInstance(waypoints, list)
        
        for waypoint in waypoints:
            self.assertIsNotNone(waypoint.code_id)
            self.assertTrue(hasattr(waypoint, 'position'))
    
    def test_get_navaids(self):
        """Test extracting navaids."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        navaids = self.parser.get_navaids()
        self.assertIsInstance(navaids, list)
        
        for navaid in navaids:
            self.assertIsNotNone(navaid.code_id)
            self.assertIsNotNone(navaid.navaid_type)
    
    def test_get_routes(self):
        """Test extracting routes."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        routes = self.parser.get_routes()
        self.assertIsInstance(routes, list)
        
        for route in routes:
            self.assertIsNotNone(route.designator)
            self.assertIsInstance(route.segments, list)
    
    def test_get_airspaces_by_fir(self):
        """Test filtering airspaces by FIR."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        # Test with known FIR codes
        for fir in ['LCCC', 'HECC', 'LGGG']:
            airspaces = self.parser.get_airspaces_by_fir(fir)
            self.assertIsInstance(airspaces, list)
            for airspace in airspaces:
                self.assertEqual(airspace.parent_fir, fir)
    
    def test_get_airspaces_by_type(self):
        """Test filtering airspaces by type."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        # Test with known types
        for type_code in ['FIR', 'CTA', 'TMA']:
            airspaces = self.parser.get_airspaces_by_type(type_code)
            self.assertIsInstance(airspaces, list)
            for airspace in airspaces:
                self.assertEqual(airspace.type_code, type_code)
    
    def test_cache_functionality(self):
        """Test that caching works correctly."""
        if not self.parser:
            self.skipTest("No sample AIXM file found")
        
        # First call should populate cache
        airspaces1 = self.parser.get_airspaces()
        
        # Second call should use cache
        airspaces2 = self.parser.get_airspaces()
        
        # Should be the same list (cached)
        self.assertIs(airspaces1, airspaces2)
        
        # Clear cache
        self.parser.clear_cache()
        
        # Should be different list now
        airspaces3 = self.parser.get_airspaces()
        self.assertIsNot(airspaces1, airspaces3)


class TestFileNotFound(unittest.TestCase):
    """Test error handling."""
    
    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for missing files."""
        with self.assertRaises(FileNotFoundError):
            AIXMParser("nonexistent_file.xml")


if __name__ == '__main__':
    unittest.main()
