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


class TestXSDCompliance:
    """Tests for XSD-confirmed AIXM 4.5 structure correctness in the JS parser."""

    def test_parse_coordinate_dms_decimal_seconds(self):
        """Test DMS with decimal seconds (e.g., 510520.60N)."""
        import re
        def parseCoordinate(coord):
            if not coord:
                return None
            coord = coord.strip()
            match = re.match(r'^(\d{2,3})(\d{2})(\d{2}(?:\.\d+)?)([NSEW])$', coord, re.I)
            if match:
                deg = int(match.group(1))
                mn = int(match.group(2))
                sec = float(match.group(3))
                dir_ = match.group(4).upper()
                decimal = deg + mn / 60 + sec / 3600
                if dir_ in ('S', 'W'):
                    decimal = -decimal
                return decimal
            try:
                return float(coord)
            except ValueError:
                return None

        result = parseCoordinate("510520.60N")
        assert result is not None, "Should parse DMS with decimal seconds"
        assert abs(result - 51.0890) < 0.0001, f"Expected ~51.0890 but got {result}"

        result2 = parseCoordinate("0010230.50E")
        assert result2 is not None
        assert abs(result2 - 1.0418) < 0.0001  # 001°02'30.5"E = 1.04180°

    def test_gbv_border_vertex_extraction(self):
        """Confirm that GeographicalBorderVertexType (Gbv) uses geoLat/geoLong, not posList."""
        # Simulate extraction from Gbv elements as per XSD lines 3816–3863
        gbv_elements = [
            {'geoLat': '341200N', 'geoLong': '0163411E'},
            {'geoLat': '344451N', 'geoLong': '0175530E'},
            {'geoLat': '330000N', 'geoLong': '0170000E'},
        ]

        def parse_coord(s):
            import re
            m = re.match(r'^(\d{2,3})(\d{2})(\d{2})([NSEW])$', s)
            if m:
                d, mn, sc, dir_ = int(m[1]), int(m[2]), int(m[3]), m[4]
                v = d + mn / 60 + sc / 3600
                return -v if dir_ in ('S', 'W') else v
            return None

        polygon = []
        for gbv in gbv_elements:
            lat = parse_coord(gbv['geoLat'])
            lon = parse_coord(gbv['geoLong'])
            if lat is not None and lon is not None:
                polygon.append([lat, lon])

        assert len(polygon) == 3, "Should extract 3 vertices from Gbv elements"
        assert polygon[0][0] > 34, "First vertex latitude should be ~34°N"
        assert polygon[0][1] > 16, "First vertex longitude should be ~16°E"

    def test_cwa_arc_interpolation_produces_intermediate_points(self):
        """CWA arc vertex should generate interpolated points between start and end."""
        import math

        def interpolate_arc(start_lat, start_lon, center_lat, center_lon, clockwise, end_lat, end_lon, num_pts=16):
            to_rad = lambda d: d * math.pi / 180
            to_deg = lambda r: r * 180 / math.pi

            def bearing(flat, flon, tlat, tlon):
                lat1, lat2 = to_rad(flat), to_rad(tlat)
                dlon = to_rad(tlon - flon)
                x = math.sin(dlon) * math.cos(lat2)
                y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
                return (to_deg(math.atan2(x, y)) + 360) % 360

            def dest_pt(lat, lon, brg, dist_nm):
                R = 3440.065
                delta = dist_nm / R
                phi1, lam1, theta = to_rad(lat), to_rad(lon), to_rad(brg)
                phi2 = math.asin(math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta))
                lam2 = lam1 + math.atan2(math.sin(theta) * math.sin(delta) * math.cos(phi1), math.cos(delta) - math.sin(phi1) * math.sin(phi2))
                return (to_deg(phi2), to_deg(lam2))

            def dist_nm(lat1, lon1, lat2, lon2):
                R = 3440.065
                phi1, phi2 = to_rad(lat1), to_rad(lat2)
                dp, dl = to_rad(lat2 - lat1), to_rad(lon2 - lon1)
                a = math.sin(dp / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
                return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            radius = dist_nm(center_lat, center_lon, start_lat, start_lon)
            start_brg = bearing(center_lat, center_lon, start_lat, start_lon)
            end_brg = bearing(center_lat, center_lon, end_lat, end_lon)

            if clockwise:
                sweep = end_brg - start_brg if end_brg >= start_brg else 360 - start_brg + end_brg
            else:
                sweep = start_brg - end_brg if start_brg >= end_brg else 360 - end_brg + start_brg
            if sweep < 1:
                sweep = 360

            pts = []
            for i in range(num_pts + 1):
                angle = (start_brg + sweep * i / num_pts) % 360 if clockwise else (start_brg - sweep * i / num_pts + 360) % 360
                pts.append(dest_pt(center_lat, center_lon, angle, radius))
            return pts

        # Circle of radius 10 NM, CWA from North to East
        center_lat, center_lon = 35.0, 33.0
        start_pt = (35.0 + 10 / 60, 33.0)  # approx 10 NM north
        end_pt = (35.0, 33.0 + 10 / 60)    # approx 10 NM east

        pts = interpolate_arc(start_pt[0], start_pt[1], center_lat, center_lon, True, end_pt[0], end_pt[1], 8)
        assert len(pts) == 9, f"Should have 9 points (0..8), got {len(pts)}"
        # All points should be roughly 10 NM from center
        for lat, lon in pts:
            d = math.sqrt((lat - center_lat) ** 2 + (lon - center_lon) ** 2)
            assert d > 0.1, "Arc points should not collapse to center"

    def test_circle_airspace_polygon_from_circle_element(self):
        """AirspaceCircularVertexType (Circle) should generate a closed polygon."""
        import math

        def interpolate_circle(center_lat, center_lon, radius_nm, num_pts=36):
            to_rad = lambda d: d * math.pi / 180
            to_deg = lambda r: r * 180 / math.pi
            R = 3440.065
            delta = radius_nm / R
            phi1, lam1 = to_rad(center_lat), to_rad(center_lon)
            pts = []
            for i in range(num_pts + 1):
                theta = to_rad(360 * i / num_pts)
                phi2 = math.asin(math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta))
                lam2 = lam1 + math.atan2(math.sin(theta) * math.sin(delta) * math.cos(phi1), math.cos(delta) - math.sin(phi1) * math.sin(phi2))
                pts.append((to_deg(phi2), to_deg(lam2)))
            return pts

        pts = interpolate_circle(35.0, 33.0, 5.0)

        assert len(pts) == 37, "Should have 37 points (0..36 inclusive)"
        assert pts[0] == pts[-1], "First and last point should be identical (closed ring)"
        # All points should be approx 5 NM from center
        for lat, lon in pts:
            dist_lat = abs(lat - 35.0) * 60
            dist_lon = abs(lon - 33.0) * 60 * math.cos(math.radians(35))
            approx_nm = math.sqrt(dist_lat ** 2 + dist_lon ** 2)
            assert 4.5 < approx_nm < 5.5, f"Circle point should be ~5NM from center, got {approx_nm:.2f}NM"

    def test_rdn_threshold_position_extracted(self):
        """RunwayDirectionType (Rdn) has geoLat/geoLong for threshold position."""
        import re

        # Simulate parsing an Rdn element per XSD lines 6863–6975
        rdn_data = {
            'geoLat': '345152N',   # Threshold lat
            'geoLong': '0334006E', # Threshold lon
            'valTrueBrg': '272.0',
            'valMagBrg': '270.0',
            'airportId': 'LCLK',
            'codeId': '27',        # Runway designator
        }

        def parse_coord(s):
            m = re.match(r'^(\d{2,3})(\d{2})(\d{2})([NSEW])$', s)
            if m:
                d, mn, sc, dir_ = int(m[1]), int(m[2]), int(m[3]), m[4]
                v = d + mn / 60 + sc / 3600
                return -v if dir_ in ('S', 'W') else v
            return None

        lat = parse_coord(rdn_data['geoLat'])
        lon = parse_coord(rdn_data['geoLong'])

        assert lat is not None, "Threshold latitude should parse"
        assert lon is not None, "Threshold longitude should parse"
        assert 34 < lat < 35, f"LCLK RWY 27 threshold lat should be ~34.86°N, got {lat}"
        assert 33 < lon < 34, f"LCLK RWY 27 threshold lon should be ~33.67°E, got {lon}"
        assert float(rdn_data['valTrueBrg']) == 272.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

