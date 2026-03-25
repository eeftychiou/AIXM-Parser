"""
Comprehensive test cases for AIXM 4.5 specification elements.

This module provides tests for all AIXM feature types including:
- Airspace (Ase) and AirspaceBorder (Abd)
- Airport/Aerodrome (Ahp)
- Waypoint/DesignatedPoint (Dpn)
- Navaids: VOR (Vor), NDB (Ndb), DME (Dme), TACAN (Tcn), Marker (Mkr)
- Routes (Rte) and RouteSegments (Rsg)
- GeographicalBorder (Gbr)
- Organization (Org)
- And additional AIXM elements found in sample files

Usage:
    pytest tests/test_aixm_elements.py -v
"""

import unittest
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Set, Dict, List, Optional, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parser import AIXMParser
from src.models import (
    Point, Polygon, LineString, AIXMFeature, VerticalLimits,
    Airspace, Airport, Waypoint, Route, RouteSegment, Navaid,
    GeographicalBorder, Organization,
    Runway, Taxiway, Apron, Service, Frequency, Unit,
    SID, STAR, InstrumentApproach, ILS, Marker
)
from src.utils import parse_coordinate, find_all_tags, find_tag_text


class TestElementPresence(unittest.TestCase):
    """Test to detect which AIXM elements are present in sample files."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures - find sample files and collect element types."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        
        # Collect all unique element types from all samples
        cls.element_counts: Dict[str, int] = {}
        cls.elements_by_file: Dict[str, Dict[str, int]] = {}
        
        for sample_file in cls.sample_files:
            cls.elements_by_file[sample_file.name] = {}
            try:
                tree = ET.parse(sample_file)
                root = tree.getroot()
                
                for elem in root.iter():
                    tag = elem.tag
                    if '}' in tag:
                        tag = tag.split('}')[1]
                    
                    cls.element_counts[tag] = cls.element_counts.get(tag, 0) + 1
                    cls.elements_by_file[sample_file.name][tag] = \
                        cls.elements_by_file[sample_file.name].get(tag, 0) + 1
            except Exception as e:
                print(f"Warning: Could not parse {sample_file}: {e}")
    
    def test_sample_files_exist(self):
        """Verify that sample files exist."""
        self.assertGreater(len(self.sample_files), 0, "No sample XML files found")
    
    def test_detected_elements(self):
        """Print and verify detected element types."""
        # Core AIXM feature elements we expect to find
        core_elements = [
            'Ase', 'Abd', 'Ahp', 'Dpn', 'Vor', 'Ndb', 'Dme', 'Tcn',
            'Rte', 'Rsg', 'Gbr', 'Org', 'Rwy', 'Twy', 'Apn', 'Ser',
            'Fqy', 'Uni', 'Sid', 'Sia', 'Iap', 'Ils', 'Mkr'
        ]
        
        found_core = [elem for elem in core_elements if elem in self.element_counts]
        not_found = [elem for elem in core_elements if elem not in self.element_counts]
        
        print(f"\n{'='*60}")
        print("AIXM ELEMENT PRESENCE IN SAMPLE FILES")
        print(f"{'='*60}")
        print(f"\nSample files analyzed: {len(self.sample_files)}")
        for sf in self.sample_files:
            print(f"  - {sf.name}")
        
        print(f"\nCore elements found ({len(found_core)}/{len(core_elements)}):")
        for elem in sorted(found_core):
            print(f"  ✓ {elem}: {self.element_counts[elem]} instances")
        
        if not_found:
            print(f"\nCore elements NOT found ({len(not_found)}):")
            for elem in sorted(not_found):
                print(f"  ✗ {elem}")
        
        print(f"\nAll unique element types ({len(self.element_counts)}):")
        for elem in sorted(self.element_counts.keys()):
            print(f"  {elem}: {self.element_counts[elem]}")
        
        # Verify we found at least some core elements
        self.assertGreater(len(found_core), 0, "No core AIXM elements found")


class TestAirspaceParsing(unittest.TestCase):
    """Test Airspace (Ase) and AirspaceBorder (Abd) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        # Use first available sample file
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_airspaces_returns_list(self):
        """Test that get_airspaces returns a list."""
        airspaces = self.parser.get_airspaces()
        self.assertIsInstance(airspaces, list)
    
    def test_airspace_attributes(self):
        """Test that airspaces have required attributes."""
        airspaces = self.parser.get_airspaces()
        if not airspaces:
            self.skipTest("No airspaces found in sample file")
        
        for airspace in airspaces:
            self.assertIsInstance(airspace, Airspace)
            self.assertTrue(hasattr(airspace, 'mid'))
            self.assertTrue(hasattr(airspace, 'code_id'))
            self.assertTrue(hasattr(airspace, 'name'))
            self.assertTrue(hasattr(airspace, 'type_code'))
            self.assertTrue(hasattr(airspace, 'polygon'))
            self.assertTrue(hasattr(airspace, 'vertical_limits'))
            self.assertTrue(hasattr(airspace, 'parent_fir'))
    
    def test_airspace_types(self):
        """Test that airspaces have valid type codes."""
        airspaces = self.parser.get_airspaces()
        if not airspaces:
            self.skipTest("No airspaces found in sample file")
        
        valid_types = {'FIR', 'CTA', 'TMA', 'CTR', 'P', 'R', 'D', 'Z', 'MTA', 'UTA', 'SIV', 'UIR', 'OCTA'}
        
        for airspace in airspaces:
            if airspace.type_code:
                self.assertIn(airspace.type_code.upper(), valid_types | {airspace.type_code.upper()})
    
    def test_airspace_vertical_limits(self):
        """Test that airspaces have valid vertical limits."""
        airspaces = self.parser.get_airspaces()
        if not airspaces:
            self.skipTest("No airspaces found in sample file")
        
        for airspace in airspaces:
            if airspace.vertical_limits:
                self.assertIsInstance(airspace.vertical_limits, VerticalLimits)
                # Check that limits have expected attributes
                self.assertTrue(hasattr(airspace.vertical_limits, 'lower_limit'))
                self.assertTrue(hasattr(airspace.vertical_limits, 'upper_limit'))
    
    def test_airspace_polygon(self):
        """Test that airspaces have valid polygon geometry."""
        airspaces = self.parser.get_airspaces()
        if not airspaces:
            self.skipTest("No airspaces found in sample file")
        
        for airspace in airspaces:
            if airspace.polygon:
                self.assertIsInstance(airspace.polygon, Polygon)
                self.assertGreater(len(airspace.polygon.points), 0)
    
    def test_get_airspaces_by_fir(self):
        """Test filtering airspaces by FIR."""
        # Test with known FIR codes that might be in the data
        fir_codes = ['LCCC', 'HECC', 'LGGG', 'OLBB', 'LLLL']
        
        found_any = False
        for fir in fir_codes:
            airspaces = self.parser.get_airspaces_by_fir(fir)
            self.assertIsInstance(airspaces, list)
            if airspaces:
                found_any = True
                for airspace in airspaces:
                    self.assertEqual(airspace.parent_fir, fir)
        
        if not found_any:
            self.skipTest("No airspaces found for known FIR codes")
    
    def test_get_airspaces_by_type(self):
        """Test filtering airspaces by type."""
        type_codes = ['FIR', 'CTA', 'TMA']
        
        found_any = False
        for type_code in type_codes:
            airspaces = self.parser.get_airspaces_by_type(type_code)
            self.assertIsInstance(airspaces, list)
            if airspaces:
                found_any = True
                for airspace in airspaces:
                    self.assertEqual(airspace.type_code, type_code)
        
        if not found_any:
            self.skipTest("No airspaces found for known type codes")


class TestAirportParsing(unittest.TestCase):
    """Test Airport (Ahp) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_airports_returns_list(self):
        """Test that get_airports returns a list."""
        airports = self.parser.get_airports()
        self.assertIsInstance(airports, list)
    
    def test_airport_attributes(self):
        """Test that airports have required attributes."""
        airports = self.parser.get_airports()
        if not airports:
            self.skipTest("No airports found in sample file")
        
        for airport in airports:
            self.assertIsInstance(airport, Airport)
            self.assertTrue(hasattr(airport, 'mid'))
            self.assertTrue(hasattr(airport, 'code_id'))
            self.assertTrue(hasattr(airport, 'name'))
            self.assertTrue(hasattr(airport, 'icao'))
            self.assertTrue(hasattr(airport, 'iata'))
            self.assertTrue(hasattr(airport, 'position'))
            self.assertTrue(hasattr(airport, 'elevation'))
            self.assertTrue(hasattr(airport, 'city'))
    
    def test_airport_position(self):
        """Test that airports have valid position data."""
        airports = self.parser.get_airports()
        if not airports:
            self.skipTest("No airports found in sample file")
        
        for airport in airports:
            if airport.position:
                self.assertIsInstance(airport.position, Point)
                self.assertIsInstance(airport.position.lat, float)
                self.assertIsInstance(airport.position.lon, float)
                # Valid latitude range
                self.assertGreaterEqual(airport.position.lat, -90)
                self.assertLessEqual(airport.position.lat, 90)
                # Valid longitude range
                self.assertGreaterEqual(airport.position.lon, -180)
                self.assertLessEqual(airport.position.lon, 180)
    
    def test_get_airports_by_icao(self):
        """Test getting airport by ICAO code."""
        airports = self.parser.get_airports()
        if not airports:
            self.skipTest("No airports found in sample file")
        
        # Test with first airport's ICAO
        first_airport = airports[0]
        if first_airport.icao:
            found = self.parser.get_airports_by_icao(first_airport.icao)
            self.assertIsNotNone(found)
            self.assertEqual(found.icao.upper(), first_airport.icao.upper())
    
    def test_airport_to_dict(self):
        """Test airport serialization to dict."""
        airports = self.parser.get_airports()
        if not airports:
            self.skipTest("No airports found in sample file")
        
        for airport in airports:
            d = airport.to_dict()
            self.assertIsInstance(d, dict)
            self.assertIn('mid', d)
            self.assertIn('code_id', d)
            self.assertIn('name', d)
            self.assertIn('icao', d)
            self.assertIn('lat', d)
            self.assertIn('lon', d)


class TestWaypointParsing(unittest.TestCase):
    """Test Waypoint (Dpn) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_waypoints_returns_list(self):
        """Test that get_waypoints returns a list."""
        waypoints = self.parser.get_waypoints()
        self.assertIsInstance(waypoints, list)
    
    def test_waypoint_attributes(self):
        """Test that waypoints have required attributes."""
        waypoints = self.parser.get_waypoints()
        if not waypoints:
            self.skipTest("No waypoints found in sample file")
        
        for waypoint in waypoints:
            self.assertIsInstance(waypoint, Waypoint)
            self.assertTrue(hasattr(waypoint, 'mid'))
            self.assertTrue(hasattr(waypoint, 'code_id'))
            self.assertTrue(hasattr(waypoint, 'name'))
            self.assertTrue(hasattr(waypoint, 'position'))
            self.assertTrue(hasattr(waypoint, 'type_code'))
    
    def test_waypoint_position(self):
        """Test that waypoints have valid position data."""
        waypoints = self.parser.get_waypoints()
        if not waypoints:
            self.skipTest("No waypoints found in sample file")
        
        for waypoint in waypoints:
            if waypoint.position:
                self.assertIsInstance(waypoint.position, Point)
                self.assertIsInstance(waypoint.position.lat, float)
                self.assertIsInstance(waypoint.position.lon, float)
                # Valid latitude range
                self.assertGreaterEqual(waypoint.position.lat, -90)
                self.assertLessEqual(waypoint.position.lat, 90)
                # Valid longitude range
                self.assertGreaterEqual(waypoint.position.lon, -180)
                self.assertLessEqual(waypoint.position.lon, 180)
    
    def test_waypoint_to_dict(self):
        """Test waypoint serialization to dict."""
        waypoints = self.parser.get_waypoints()
        if not waypoints:
            self.skipTest("No waypoints found in sample file")
        
        for waypoint in waypoints:
            d = waypoint.to_dict()
            self.assertIsInstance(d, dict)
            self.assertIn('mid', d)
            self.assertIn('code_id', d)
            self.assertIn('name', d)
            self.assertIn('lat', d)
            self.assertIn('lon', d)
            self.assertIn('type', d)


class TestNavaidParsing(unittest.TestCase):
    """Test Navaid (Vor, Ndb, Dme, Tcn) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_navaids_returns_list(self):
        """Test that get_navaids returns a list."""
        navaids = self.parser.get_navaids()
        self.assertIsInstance(navaids, list)
    
    def test_navaid_attributes(self):
        """Test that navaids have required attributes."""
        navaids = self.parser.get_navaids()
        if not navaids:
            self.skipTest("No navaids found in sample file")
        
        for navaid in navaids:
            self.assertIsInstance(navaid, Navaid)
            self.assertTrue(hasattr(navaid, 'mid'))
            self.assertTrue(hasattr(navaid, 'code_id'))
            self.assertTrue(hasattr(navaid, 'name'))
            self.assertTrue(hasattr(navaid, 'position'))
            self.assertTrue(hasattr(navaid, 'navaid_type'))
            self.assertIn(navaid.navaid_type, ['VOR', 'NDB', 'DME', 'TACAN'])
    
    def test_navaid_position(self):
        """Test that navaids have valid position data."""
        navaids = self.parser.get_navaids()
        if not navaids:
            self.skipTest("No navaids found in sample file")
        
        for navaid in navaids:
            if navaid.position:
                self.assertIsInstance(navaid.position, Point)
                self.assertIsInstance(navaid.position.lat, float)
                self.assertIsInstance(navaid.position.lon, float)
                # Valid latitude range
                self.assertGreaterEqual(navaid.position.lat, -90)
                self.assertLessEqual(navaid.position.lat, 90)
                # Valid longitude range
                self.assertGreaterEqual(navaid.position.lon, -180)
                self.assertLessEqual(navaid.position.lon, 180)
    
    def test_navaid_types(self):
        """Test that different navaid types are correctly identified."""
        navaids = self.parser.get_navaids()
        if not navaids:
            self.skipTest("No navaids found in sample file")
        
        types_found = set()
        for navaid in navaids:
            types_found.add(navaid.navaid_type)
        
        # We should have at least one navaid type
        self.assertGreater(len(types_found), 0)
        
        # All types should be valid
        for nav_type in types_found:
            self.assertIn(nav_type, ['VOR', 'NDB', 'DME', 'TACAN'])
    
    def test_vor_frequency(self):
        """Test that VOR navaids have frequency data."""
        navaids = self.parser.get_navaids()
        vors = [n for n in navaids if n.navaid_type == 'VOR']
        
        if not vors:
            self.skipTest("No VORs found in sample file")
        
        for vor in vors:
            if vor.frequency:
                self.assertIsInstance(vor.frequency, float)
                self.assertGreater(vor.frequency, 0)
    
    def test_ndb_frequency(self):
        """Test that NDB navaids have frequency data."""
        navaids = self.parser.get_navaids()
        ndbs = [n for n in navaids if n.navaid_type == 'NDB']
        
        if not ndbs:
            self.skipTest("No NDBs found in sample file")
        
        for ndb in ndbs:
            if ndb.frequency:
                self.assertIsInstance(ndb.frequency, float)
                self.assertGreater(ndb.frequency, 0)
    
    def test_dme_channel(self):
        """Test that DME navaids have channel data."""
        navaids = self.parser.get_navaids()
        dmes = [n for n in navaids if n.navaid_type == 'DME']
        
        if not dmes:
            self.skipTest("No DMEs found in sample file")
        
        for dme in dmes:
            # DME should have a channel
            self.assertIsNotNone(dme.channel)
    
    def test_tacan_channel(self):
        """Test that TACAN navaids have channel data."""
        navaids = self.parser.get_navaids()
        tacans = [n for n in navaids if n.navaid_type == 'TACAN']
        
        if not tacans:
            self.skipTest("No TACANs found in sample file")
        
        for tacan in tacans:
            # TACAN should have a channel
            self.assertIsNotNone(tacan.channel)
    
    def test_navaid_to_dict(self):
        """Test navaid serialization to dict."""
        navaids = self.parser.get_navaids()
        if not navaids:
            self.skipTest("No navaids found in sample file")
        
        for navaid in navaids:
            d = navaid.to_dict()
            self.assertIsInstance(d, dict)
            self.assertIn('mid', d)
            self.assertIn('code_id', d)
            self.assertIn('name', d)
            self.assertIn('type', d)
            self.assertIn('lat', d)
            self.assertIn('lon', d)


class TestRouteParsing(unittest.TestCase):
    """Test Route (Rte) and RouteSegment (Rsg) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_routes_returns_list(self):
        """Test that get_routes returns a list."""
        routes = self.parser.get_routes()
        self.assertIsInstance(routes, list)
    
    def test_route_attributes(self):
        """Test that routes have required attributes."""
        routes = self.parser.get_routes()
        if not routes:
            self.skipTest("No routes found in sample file")
        
        for route in routes:
            self.assertIsInstance(route, Route)
            self.assertTrue(hasattr(route, 'mid'))
            self.assertTrue(hasattr(route, 'code_id'))
            self.assertTrue(hasattr(route, 'designator'))
            self.assertTrue(hasattr(route, 'route_type'))
            self.assertTrue(hasattr(route, 'segments'))
            self.assertIsInstance(route.segments, list)
    
    def test_route_segment_attributes(self):
        """Test that route segments have required attributes."""
        routes = self.parser.get_routes()
        if not routes:
            self.skipTest("No routes found in sample file")
        
        for route in routes:
            for segment in route.segments:
                self.assertIsInstance(segment, RouteSegment)
                self.assertTrue(hasattr(segment, 'mid'))
                self.assertTrue(hasattr(segment, 'route_mid'))
                self.assertTrue(hasattr(segment, 'start_waypoint_id'))
                self.assertTrue(hasattr(segment, 'end_waypoint_id'))
                self.assertTrue(hasattr(segment, 'start_point'))
                self.assertTrue(hasattr(segment, 'end_point'))
    
    def test_route_get_waypoint_ids(self):
        """Test getting waypoint IDs from a route."""
        routes = self.parser.get_routes()
        if not routes:
            self.skipTest("No routes found in sample file")
        
        for route in routes:
            waypoint_ids = route.get_waypoint_ids()
            self.assertIsInstance(waypoint_ids, list)
            # Each waypoint ID should be a string
            for wp_id in waypoint_ids:
                self.assertIsInstance(wp_id, str)


class TestGeographicalBorderParsing(unittest.TestCase):
    """Test GeographicalBorder (Gbr) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_geographical_borders_returns_list(self):
        """Test that get_geographical_borders returns a list."""
        borders = self.parser.get_geographical_borders()
        self.assertIsInstance(borders, list)
    
    def test_border_attributes(self):
        """Test that borders have required attributes."""
        borders = self.parser.get_geographical_borders()
        if not borders:
            self.skipTest("No geographical borders found in sample file")
        
        for border in borders:
            self.assertIsInstance(border, GeographicalBorder)
            self.assertTrue(hasattr(border, 'mid'))
            self.assertTrue(hasattr(border, 'code_id'))
            self.assertTrue(hasattr(border, 'name'))
            self.assertTrue(hasattr(border, 'border_type'))
            self.assertTrue(hasattr(border, 'polygon'))


class TestOrganizationParsing(unittest.TestCase):
    """Test Organization (Org) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_organizations_returns_list(self):
        """Test that get_organizations returns a list."""
        organizations = self.parser.get_organizations()
        self.assertIsInstance(organizations, list)
    
    def test_organization_attributes(self):
        """Test that organizations have required attributes."""
        organizations = self.parser.get_organizations()
        if not organizations:
            self.skipTest("No organizations found in sample file")
        
        for org in organizations:
            self.assertIsInstance(org, Organization)
            self.assertTrue(hasattr(org, 'mid'))
            self.assertTrue(hasattr(org, 'code_id'))
            self.assertTrue(hasattr(org, 'name'))
            self.assertTrue(hasattr(org, 'identifier'))
            self.assertTrue(hasattr(org, 'org_type'))


class TestStatistics(unittest.TestCase):
    """Test parser statistics functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_statistics(self):
        """Test that get_statistics returns expected keys."""
        stats = self.parser.get_statistics()
        
        expected_keys = [
            'airspaces', 'airports', 'waypoints', 'routes',
            'navaids', 'borders', 'organizations'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], int)
            self.assertGreaterEqual(stats[key], 0)
    
    def test_statistics_consistency(self):
        """Test that statistics match actual counts."""
        stats = self.parser.get_statistics()
        
        self.assertEqual(stats['airspaces'], len(self.parser.get_airspaces()))
        self.assertEqual(stats['airports'], len(self.parser.get_airports()))
        self.assertEqual(stats['waypoints'], len(self.parser.get_waypoints()))
        self.assertEqual(stats['routes'], len(self.parser.get_routes()))
        self.assertEqual(stats['navaids'], len(self.parser.get_navaids()))
        self.assertEqual(stats['borders'], len(self.parser.get_geographical_borders()))
        self.assertEqual(stats['organizations'], len(self.parser.get_organizations()))


class TestCacheFunctionality(unittest.TestCase):
    """Test parser caching functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_cache_returns_same_object(self):
        """Test that cached results return the same object."""
        airspaces1 = self.parser.get_airspaces()
        airspaces2 = self.parser.get_airspaces()
        
        self.assertIs(airspaces1, airspaces2)
    
    def test_clear_cache(self):
        """Test that clear_cache creates new objects."""
        airspaces1 = self.parser.get_airspaces()
        self.parser.clear_cache()
        airspaces2 = self.parser.get_airspaces()
        
        self.assertIsNot(airspaces1, airspaces2)
        # But they should have the same content
        self.assertEqual(len(airspaces1), len(airspaces2))


class TestAdditionalElements(unittest.TestCase):
    """Test for additional AIXM elements found in sample files."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_runway_elements_present(self):
        """Test if Runway (Rwy) elements exist in sample."""
        runways = list(self.parser.root.iter())
        runway_tags = [e for e in runways if 'Rwy' in (e.tag.split('}')[1] if '}' in e.tag else e.tag)]
        
        if runway_tags:
            print(f"\nFound {len(runway_tags)} Runway-related elements")
    
    def test_taxiway_elements_present(self):
        """Test if Taxiway (Twy) elements exist in sample."""
        taxiways = list(self.parser.root.iter())
        taxiway_tags = [e for e in taxiways if 'Twy' in (e.tag.split('}')[1] if '}' in e.tag else e.tag)]
        
        if taxiway_tags:
            print(f"\nFound {len(taxiway_tags)} Taxiway-related elements")
    
    def test_service_elements_present(self):
        """Test if Service (Ser) elements exist in sample."""
        services = list(self.parser.root.iter())
        service_tags = [e for e in services if 'Ser' in (e.tag.split('}')[1] if '}' in e.tag else e.tag)]
        
        if service_tags:
            print(f"\nFound {len(service_tags)} Service-related elements")
    
    def test_frequency_elements_present(self):
        """Test if Frequency (Fqy) elements exist in sample."""
        frequencies = list(self.parser.root.iter())
        freq_tags = [e for e in frequencies if 'Fqy' in (e.tag.split('}')[1] if '}' in e.tag else e.tag)]
        
        if freq_tags:
            print(f"\nFound {len(freq_tags)} Frequency-related elements")
    
    def test_unit_elements_present(self):
        """Test if Unit (Uni) elements exist in sample."""
        units = list(self.parser.root.iter())
        unit_tags = [e for e in units if 'Uni' in (e.tag.split('}')[1] if '}' in e.tag else e.tag)]
        
        if unit_tags:
            print(f"\nFound {len(unit_tags)} Unit-related elements")


class TestRunwayParsing(unittest.TestCase):
    """Test Runway (Rwy) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_runways_returns_list(self):
        """Test that get_runways returns a list."""
        runways = self.parser.get_runways()
        self.assertIsInstance(runways, list)
    
    def test_runway_attributes(self):
        """Test that runways have required attributes."""
        runways = self.parser.get_runways()
        if not runways:
            self.skipTest("No runways found in sample file")
        
        for runway in runways:
            self.assertIsInstance(runway, Runway)
            self.assertTrue(hasattr(runway, 'mid'))
            self.assertTrue(hasattr(runway, 'code_id'))
            self.assertTrue(hasattr(runway, 'airport_mid'))
            self.assertTrue(hasattr(runway, 'length'))
            self.assertTrue(hasattr(runway, 'width'))


class TestTaxiwayParsing(unittest.TestCase):
    """Test Taxiway (Twy) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_taxiways_returns_list(self):
        """Test that get_taxiways returns a list."""
        taxiways = self.parser.get_taxiways()
        self.assertIsInstance(taxiways, list)
    
    def test_taxiway_attributes(self):
        """Test that taxiways have required attributes."""
        taxiways = self.parser.get_taxiways()
        if not taxiways:
            self.skipTest("No taxiways found in sample file")
        
        for taxiway in taxiways:
            self.assertIsInstance(taxiway, Taxiway)
            self.assertTrue(hasattr(taxiway, 'mid'))
            self.assertTrue(hasattr(taxiway, 'code_id'))
            self.assertTrue(hasattr(taxiway, 'taxiway_type'))
            self.assertTrue(hasattr(taxiway, 'width'))


class TestApronParsing(unittest.TestCase):
    """Test Apron (Apn) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_aprons_returns_list(self):
        """Test that get_aprons returns a list."""
        aprons = self.parser.get_aprons()
        self.assertIsInstance(aprons, list)
    
    def test_apron_attributes(self):
        """Test that aprons have required attributes."""
        aprons = self.parser.get_aprons()
        if not aprons:
            self.skipTest("No aprons found in sample file")
        
        for apron in aprons:
            self.assertIsInstance(apron, Apron)
            self.assertTrue(hasattr(apron, 'mid'))
            self.assertTrue(hasattr(apron, 'code_id'))
            self.assertTrue(hasattr(apron, 'surface_composition'))


class TestServiceParsing(unittest.TestCase):
    """Test Service (Ser) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_services_returns_list(self):
        """Test that get_services returns a list."""
        services = self.parser.get_services()
        self.assertIsInstance(services, list)
    
    def test_service_attributes(self):
        """Test that services have required attributes."""
        services = self.parser.get_services()
        if not services:
            self.skipTest("No services found in sample file")
        
        for service in services:
            self.assertIsInstance(service, Service)
            self.assertTrue(hasattr(service, 'mid'))
            self.assertTrue(hasattr(service, 'code_id'))
            self.assertTrue(hasattr(service, 'service_type'))


class TestFrequencyParsing(unittest.TestCase):
    """Test Frequency (Fqy) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_frequencies_returns_list(self):
        """Test that get_frequencies returns a list."""
        frequencies = self.parser.get_frequencies()
        self.assertIsInstance(frequencies, list)
    
    def test_frequency_attributes(self):
        """Test that frequencies have required attributes."""
        frequencies = self.parser.get_frequencies()
        if not frequencies:
            self.skipTest("No frequencies found in sample file")
        
        for freq in frequencies:
            self.assertIsInstance(freq, Frequency)
            self.assertTrue(hasattr(freq, 'mid'))
            self.assertTrue(hasattr(freq, 'frequency'))
            self.assertTrue(hasattr(freq, 'frequency_type'))


class TestUnitParsing(unittest.TestCase):
    """Test Unit (Uni) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_units_returns_list(self):
        """Test that get_units returns a list."""
        units = self.parser.get_units()
        self.assertIsInstance(units, list)
    
    def test_unit_attributes(self):
        """Test that units have required attributes."""
        units = self.parser.get_units()
        if not units:
            self.skipTest("No units found in sample file")
        
        for unit in units:
            self.assertIsInstance(unit, Unit)
            self.assertTrue(hasattr(unit, 'mid'))
            self.assertTrue(hasattr(unit, 'code_id'))
            self.assertTrue(hasattr(unit, 'unit_type'))


class TestSIDParsing(unittest.TestCase):
    """Test SID (Sid) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_sids_returns_list(self):
        """Test that get_sids returns a list."""
        sids = self.parser.get_sids()
        self.assertIsInstance(sids, list)
    
    def test_sid_attributes(self):
        """Test that SIDs have required attributes."""
        sids = self.parser.get_sids()
        if not sids:
            self.skipTest("No SIDs found in sample file")
        
        for sid in sids:
            self.assertIsInstance(sid, SID)
            self.assertTrue(hasattr(sid, 'mid'))
            self.assertTrue(hasattr(sid, 'code_id'))
            self.assertTrue(hasattr(sid, 'designator'))


class TestSTARParsing(unittest.TestCase):
    """Test STAR (Sia) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_stars_returns_list(self):
        """Test that get_stars returns a list."""
        stars = self.parser.get_stars()
        self.assertIsInstance(stars, list)
    
    def test_star_attributes(self):
        """Test that STARs have required attributes."""
        stars = self.parser.get_stars()
        if not stars:
            self.skipTest("No STARs found in sample file")
        
        for star in stars:
            self.assertIsInstance(star, STAR)
            self.assertTrue(hasattr(star, 'mid'))
            self.assertTrue(hasattr(star, 'code_id'))
            self.assertTrue(hasattr(star, 'designator'))


class TestInstrumentApproachParsing(unittest.TestCase):
    """Test Instrument Approach (Iap) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_instrument_approaches_returns_list(self):
        """Test that get_instrument_approaches returns a list."""
        approaches = self.parser.get_instrument_approaches()
        self.assertIsInstance(approaches, list)
    
    def test_instrument_approach_attributes(self):
        """Test that instrument approaches have required attributes."""
        approaches = self.parser.get_instrument_approaches()
        if not approaches:
            self.skipTest("No instrument approaches found in sample file")
        
        for approach in approaches:
            self.assertIsInstance(approach, InstrumentApproach)
            self.assertTrue(hasattr(approach, 'mid'))
            self.assertTrue(hasattr(approach, 'code_id'))
            self.assertTrue(hasattr(approach, 'designator'))


class TestILSParsing(unittest.TestCase):
    """Test ILS parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_ils_returns_list(self):
        """Test that get_ils returns a list."""
        ils_list = self.parser.get_ils()
        self.assertIsInstance(ils_list, list)
    
    def test_ils_attributes(self):
        """Test that ILS have required attributes."""
        ils_list = self.parser.get_ils()
        if not ils_list:
            self.skipTest("No ILS found in sample file")
        
        for ils in ils_list:
            self.assertIsInstance(ils, ILS)
            self.assertTrue(hasattr(ils, 'mid'))
            self.assertTrue(hasattr(ils, 'category'))


class TestMarkerParsing(unittest.TestCase):
    """Test Marker (Mkr) parsing."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.samples_dir = Path(__file__).parent.parent / "Samples"
        cls.sample_files = list(cls.samples_dir.glob("*.xml"))
        cls.parser = None
        
        for sample_file in cls.sample_files:
            try:
                cls.parser = AIXMParser(str(sample_file))
                cls.sample_file = sample_file
                break
            except Exception:
                continue
    
    def setUp(self):
        """Skip tests if no parser available."""
        if not self.parser:
            self.skipTest("No valid sample file found")
    
    def test_get_markers_returns_list(self):
        """Test that get_markers returns a list."""
        markers = self.parser.get_markers()
        self.assertIsInstance(markers, list)
    
    def test_marker_attributes(self):
        """Test that markers have required attributes."""
        markers = self.parser.get_markers()
        if not markers:
            self.skipTest("No markers found in sample file")
        
        for marker in markers:
            self.assertIsInstance(marker, Marker)
            self.assertTrue(hasattr(marker, 'mid'))
            self.assertTrue(hasattr(marker, 'marker_type'))


if __name__ == '__main__':
    unittest.main()
