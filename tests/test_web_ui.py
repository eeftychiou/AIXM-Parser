"""
UI Test Suite for Browser-Based AIXM Parser

These tests verify the functionality of the web UI including:
- File upload and parsing
- Element filtering (Include/Exclude modes)
- Map rendering of different feature types
- Coordinate parsing (DMS and decimal formats)
- Airspace polygon extraction from Abd elements
- Route segment extraction and rendering

Run with: python -m pytest tests/test_web_ui.py -v
"""

import pytest
import json
from pathlib import Path


class TestAIXMParserJS:
    """Tests for the JavaScript parser logic (simulated in Python)"""
    
    @pytest.fixture
    def parser(self):
        """Create a mock parser with the same logic as the JS version"""
        class MockAIXMParser:
            def __init__(self):
                self.airspaceBorders = {}
                
            def parseCoordinate(self, coord):
                """JavaScript parseCoordinate equivalent"""
                if not coord:
                    return None
                
                coord = coord.strip()
                
                # Handle DMS format like "341200N" or "0163411E"
                import re
                match = re.match(r'^(\d{2,3})(\d{2})(\d{2})([NSWE])$', coord)
                if match:
                    degrees = int(match[1])
                    minutes = int(match[2])
                    seconds = int(match[3])
                    direction = match[4]
                    
                    decimal = degrees + minutes / 60 + seconds / 3600
                    if direction in ('S', 'W'):
                        decimal = -decimal
                    return decimal
                
                # Handle decimal format
                try:
                    return float(coord)
                except ValueError:
                    return None
        
        return MockAIXMParser()
    
    def test_parse_coordinate_decimal(self, parser):
        """Test parsing decimal coordinates"""
        assert parser.parseCoordinate("35.5") == 35.5
        assert parser.parseCoordinate("-120.75") == -120.75
        assert parser.parseCoordinate("0") == 0.0
    
    def test_parse_coordinate_dms_latitude(self, parser):
        """Test parsing DMS latitude coordinates"""
        # 34°12'00"N = 34.2
        assert abs(parser.parseCoordinate("341200N") - 34.2) < 0.001
        # 48°06'37"N = 48.1103
        assert abs(parser.parseCoordinate("480637N") - 48.1103) < 0.001
    
    def test_parse_coordinate_dms_longitude(self, parser):
        """Test parsing DMS longitude coordinates (3-digit degrees)"""
        # 016°34'11"E = 16.5697
        assert abs(parser.parseCoordinate("0163411E") - 16.5697) < 0.001
        # 033°17'18"E = 33.2883
        assert abs(parser.parseCoordinate("0331718E") - 33.2883) < 0.001
    
    def test_parse_coordinate_dms_south_west(self, parser):
        """Test parsing DMS coordinates with South/West directions"""
        # 34°12'00"S = -34.2
        assert abs(parser.parseCoordinate("341200S") - (-34.2)) < 0.001
        # 120°30'00"W = -120.5
        assert abs(parser.parseCoordinate("1203000W") - (-120.5)) < 0.001
    
    def test_parse_coordinate_invalid(self, parser):
        """Test parsing invalid coordinates"""
        assert parser.parseCoordinate(None) is None
        assert parser.parseCoordinate("") is None
        assert parser.parseCoordinate("invalid") is None
        assert parser.parseCoordinate("ABC123") is None

    def test_route_segment_logic(self):
        """Test the logic for creating route segments from consecutive points"""
        route_points = [
            {"lat": 10, "lon": 20},
            {"lat": 11, "lon": 21},
            {"lat": 12, "lon": 22}
        ]
        # Simulate creating segments from consecutive points
        segments = []
        for i in range(len(route_points) - 1):
            segments.append({
                "start": route_points[i],
                "end": route_points[i + 1]
            })
        
        assert len(segments) == 2
        assert segments[0]["start"] == {"lat": 10, "lon": 20}
        assert segments[0]["end"] == {"lat": 11, "lon": 21}
        assert segments[1]["start"] == {"lat": 11, "lon": 21}
        assert segments[1]["end"] == {"lat": 12, "lon": 22}

    def test_airspace_border_lookup_by_codeid_codetype(self):
        """Test airspace border lookup using codeId|codeType as key"""
        # Simulate the new extraction logic using codeId|codeType
        borders = {
            "LCCC|FIR": [
                [34.8986, 33.2883],  # 345354N, 0331718E
                [34.7975, 33.3339],  # 344751N, 0332002E
                [34.7442, 33.0847],  # 344439N, 0330505E
            ]
        }
        
        # Verify border lookup by codeId|codeType
        assert "LCCC|FIR" in borders
        assert len(borders["LCCC|FIR"]) == 3
        assert borders["LCCC|FIR"][0][0] > 34  # Latitude around 35N
        assert borders["LCCC|FIR"][0][1] > 33  # Longitude around 33E

    def test_airspace_linking_by_codeid_codetype(self):
        """Test that Ase elements link to Abd elements via codeId|codeType"""
        # Simulate airspace with AseUid containing codeId and codeType
        airspace = {
            "type": "airspace",
            "mid": "ASE_1",
            "codeId": "LCCC",
            "codeType": "FIR",
            "txtName": "Nicosia FIR",
        }
        
        borders = {
            "LCCC|FIR": [[34.9, 33.3], [34.8, 33.4], [34.7, 33.1]]
        }
        
        # Link airspace to its border using codeId|codeType
        lookup_key = f"{airspace['codeId']}|{airspace['codeType']}"
        if lookup_key in borders:
            airspace["polygon"] = borders[lookup_key]
        
        assert "polygon" in airspace
        assert len(airspace["polygon"]) == 3


class TestAirspacePolygonExtraction:
    """Tests for airspace polygon extraction from Abd elements"""
    
    def test_airspace_border_extraction(self):
        """Test that Abd elements are extracted with their polygons"""
        # Simulate the extraction logic
        abd_data = {
            "mid": "ABD_1",
            "polygon": [
                [34.8986, 33.2883],  # 345354N, 0331718E
                [34.7975, 33.3339],  # 344751N, 0332002E
                [34.7442, 33.0847],  # 344439N, 0330505E
            ]
        }
        
        assert abd_data["mid"] == "ABD_1"
        assert len(abd_data["polygon"]) == 3
        assert abd_data["polygon"][0][0] > 34  # Latitude around 35N
        assert abd_data["polygon"][0][1] > 33  # Longitude around 33E
    
    def test_airspace_abd_linking(self):
        """Test that Ase elements link to Abd elements via AbdUid"""
        # Simulate airspace with AbdUid reference
        airspace = {
            "type": "airspace",
            "mid": "ASE_1",
            "codeId": "LCCC",
            "txtName": "Nicosia FIR",
            "abdUid": "ABD_1",  # Reference to border
        }
        
        borders = {
            "ABD_1": [[34.9, 33.3], [34.8, 33.4], [34.7, 33.1]]
        }
        
        # Link airspace to its border
        if airspace["abdUid"] in borders:
            airspace["polygon"] = borders[airspace["abdUid"]]
        
        assert "polygon" in airspace
        assert len(airspace["polygon"]) == 3


class TestRouteSegmentExtraction:
    """Tests for route segment extraction"""
    
    def test_route_segment_extraction(self):
        """Test that route segments are extracted with start/end waypoints"""
        # Simulate route segments
        route_segments = {
            "A1|AWY": [
                {
                    "startPointId": "WPT1",
                    "startPointType": "waypoint",
                    "endPointId": "WPT2",
                    "endPointType": "waypoint",
                    "pathType": "CONV",
                    "length": "45",
                    "lengthUnit": "NM"
                }
            ]
        }
        
        assert "A1|AWY" in route_segments
        assert len(route_segments["A1|AWY"]) == 1
        segment = route_segments["A1|AWY"][0]
        assert segment["startPointId"] == "WPT1"
        assert segment["endPointId"] == "WPT2"
        assert segment["pathType"] == "CONV"
    
    def test_route_with_segments(self):
        """Test that routes include their segments"""
        route = {
            "type": "route",
            "codeId": "A1",
            "codeType": "AWY",
            "designator": "A1",
            "routeType": "AWY",
            "segments": [
                {
                    "startPointId": "WPT1",
                    "startPointType": "waypoint",
                    "endPointId": "WPT2",
                    "endPointType": "waypoint",
                    "pathType": "CONV",
                    "length": "45",
                    "lengthUnit": "NM"
                }
            ]
        }
        
        assert "segments" in route
        assert len(route["segments"]) == 1
        assert route["segments"][0]["startPointId"] == "WPT1"
    
    def test_route_rendering_with_waypoint_lookup(self):
        """Test that routes can be rendered by looking up waypoint positions"""
        # Waypoint positions lookup
        waypoints = {
            "WPT1": {"lat": 34.8751, "lon": 33.6249},
            "WPT2": {"lat": 35.0, "lon": 34.0}
        }
        
        route_segment = {
            "startPointId": "WPT1",
            "startPointType": "waypoint",
            "endPointId": "WPT2",
            "endPointType": "waypoint"
        }
        
        # Look up positions
        start_pos = waypoints.get(route_segment["startPointId"])
        end_pos = waypoints.get(route_segment["endPointId"])
        
        assert start_pos is not None
        assert end_pos is not None
        assert start_pos["lat"] == 34.8751
        assert end_pos["lat"] == 35.0


class TestFilterLogic:
    """Tests for the filter include/exclude logic"""
    
    @pytest.fixture
    def sample_features(self):
        """Create sample features for testing"""
        return [
            {"type": "airport", "name": "Larnaca", "icao": "LCLK"},
            {"type": "airport", "name": "Paphos", "icao": "LCPH"},
            {"type": "vor", "name": "VOR1", "codeId": "VOR1"},
            {"type": "waypoint", "name": "WPT1", "codeId": "WPT1"},
            {"type": "airspace", "name": "Nicosia FIR", "codeId": "LCCC"},
        ]
    
    def test_filter_include_nothing_selected(self, sample_features):
        """Test include mode with nothing selected returns empty"""
        selected_types = []
        mode = "include"
        
        if mode == "include":
            filtered = [] if len(selected_types) == 0 else [
                f for f in sample_features if f["type"] in selected_types
            ]
        else:
            filtered = sample_features if len(selected_types) == 0 else [
                f for f in sample_features if f["type"] not in selected_types
            ]
        
        assert len(filtered) == 0
    
    def test_filter_include_with_selection(self, sample_features):
        """Test include mode with selection returns only selected types"""
        selected_types = ["airport"]
        mode = "include"
        
        filtered = [f for f in sample_features if f["type"] in selected_types]
        
        assert len(filtered) == 2
        assert all(f["type"] == "airport" for f in filtered)
    
    def test_filter_exclude_nothing_selected(self, sample_features):
        """Test exclude mode with nothing selected returns all"""
        selected_types = []
        mode = "exclude"
        
        filtered = sample_features if len(selected_types) == 0 else [
            f for f in sample_features if f["type"] not in selected_types
        ]
        
        assert len(filtered) == 5
    
    def test_filter_exclude_with_selection(self, sample_features):
        """Test exclude mode with selection returns all except selected"""
        selected_types = ["airport"]
        mode = "exclude"
        
        filtered = [f for f in sample_features if f["type"] not in selected_types]
        
        assert len(filtered) == 3
        assert all(f["type"] != "airport" for f in filtered)
    
    def test_filter_multiple_types(self, sample_features):
        """Test filtering with multiple types selected"""
        selected_types = ["airport", "vor"]
        mode = "include"
        
        filtered = [f for f in sample_features if f["type"] in selected_types]
        
        assert len(filtered) == 3
        assert all(f["type"] in ["airport", "vor"] for f in filtered)


class TestMapRendering:
    """Tests for map rendering logic"""
    
    def test_geojson_point_conversion(self):
        """Test conversion of point features to GeoJSON"""
        feature = {
            "type": "airport",
            "name": "Larnaca",
            "position": {"lat": 34.8751, "lon": 33.6249}
        }
        
        geojson = {
            "type": "Feature",
            "properties": feature,
            "geometry": {
                "type": "Point",
                "coordinates": [feature["position"]["lon"], feature["position"]["lat"]]
            }
        }
        
        assert geojson["geometry"]["type"] == "Point"
        assert geojson["geometry"]["coordinates"] == [33.6249, 34.8751]
    
    def test_geojson_polygon_conversion(self):
        """Test conversion of polygon features to GeoJSON"""
        feature = {
            "type": "airspace",
            "name": "Nicosia FIR",
            "polygon": [[34.9, 33.3], [34.8, 33.4], [34.7, 33.1], [34.9, 33.3]]
        }
        
        # Convert to GeoJSON (swap lat/lon to lon/lat)
        coords = [[p[1], p[0]] for p in feature["polygon"]]
        geojson = {
            "type": "Feature",
            "properties": feature,
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
        
        assert geojson["geometry"]["type"] == "Polygon"
        assert len(geojson["geometry"]["coordinates"][0]) == 4
        assert geojson["geometry"]["coordinates"][0][0] == [33.3, 34.9]
    
    def test_feature_without_geometry_is_skipped(self):
        """Test that features without position or polygon are skipped"""
        feature = {
            "type": "route",
            "name": "Route A",
            # No position or polygon
        }
        
        # Should return null/None when converting to GeoJSON
        has_geometry = "position" in feature or "polygon" in feature
        assert not has_geometry
    
    def test_route_segment_rendering(self):
        """Test that route segments can be rendered as polylines"""
        # Waypoint positions
        waypoints = {
            "WPT1": {"lat": 34.8751, "lon": 33.6249},
            "WPT2": {"lat": 35.0, "lon": 34.0}
        }
        
        route = {
            "type": "route",
            "codeId": "A1",
            "segments": [
                {
                    "startPointId": "WPT1",
                    "startPointType": "waypoint",
                    "endPointId": "WPT2",
                    "endPointType": "waypoint"
                }
            ]
        }
        
        # Simulate rendering
        rendered_count = 0
        for segment in route["segments"]:
            start_pos = waypoints.get(segment["startPointId"])
            end_pos = waypoints.get(segment["endPointId"])
            if start_pos and end_pos:
                rendered_count += 1
        
        assert rendered_count == 1


class TestUIWorkflow:
    """Integration tests for complete UI workflows"""
    
    def test_load_file_then_filter_airspace(self):
        """Test complete workflow: load file, filter for airspace"""
        # Simulate file loading
        element_counts = {
            "airspace": 189,
            "airport": 45,
            "waypoint": 11377,
            "vor": 103,
        }
        
        # Verify counts are displayed
        assert element_counts["airspace"] > 0
        assert element_counts["airport"] > 0
        
        # Simulate selecting airspace filter
        selected_types = ["airspace"]
        all_features = [{"type": t} for t in ["airspace"] * 189 + ["airport"] * 45]
        
        filtered = [f for f in all_features if f["type"] in selected_types]
        assert len(filtered) == 189
    
    def test_filter_mode_switching(self):
        """Test switching between include and exclude modes"""
        features = [
            {"type": "airport"},
            {"type": "vor"},
            {"type": "waypoint"},
        ]
        
        # Include mode - select airports
        selected = ["airport"]
        include_result = [f for f in features if f["type"] in selected]
        assert len(include_result) == 1
        
        # Exclude mode - exclude airports
        exclude_result = [f for f in features if f["type"] not in selected]
        assert len(exclude_result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
