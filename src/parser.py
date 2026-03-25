"""
Main AIXM 4.5 Parser class.

This module provides the AIXMParser class for parsing AIXM XML files
and extracting aeronautical features.
"""

import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from .models import (
    AIXMFeature, Airspace, Airport, Waypoint, Route, RouteSegment,
    Navaid, GeographicalBorder, Organization, Point, Polygon,
    VerticalLimits, LineString,
    Runway, Taxiway, Apron, Service, Frequency, Unit,
    ProcedureLeg, SID, STAR, InstrumentApproach, ILS, Marker
)
from .utils import (
    parse_coordinate, find_all_tags, find_tag_text, find_child_element,
    safe_int, safe_float, infer_parent_fir, parse_vertical_limit
)
from .filter import AIXMFilterConfig, AIXMFilter


class AIXMParser:
    """
    Parser for AIXM 4.5 XML files.
    
    This class parses AIXM-Snapshot files and extracts aeronautical features
    including airspaces, airports, waypoints, routes, and navaids.
    
    Usage:
        parser = AIXMParser("path/to/aixm_file.xml")
        airspaces = parser.get_airspaces()
        airports = parser.get_airports()
    
    Attributes:
        file_path: Path to the AIXM XML file
        root: Root XML element
        tree: ElementTree instance
        _cache: Internal cache for parsed features
    """
    
    def __init__(self, file_path: str, filter_config: Optional[AIXMFilterConfig] = None):
        """
        Initialize the parser with an AIXM XML file.
        
        Args:
            file_path: Path to the AIXM XML file
            filter_config: Optional filter configuration to apply
        
        Raises:
            FileNotFoundError: If the file doesn't exist
            ET.ParseError: If the XML is malformed
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"AIXM file not found: {file_path}")
        
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        
        # Internal cache for parsed features
        self._cache: Dict[str, Any] = {}
        
        # Filter configuration
        self._filter_config = filter_config
        self._filter = AIXMFilter(filter_config) if filter_config else None
        
        # Index for quick MID lookup
        self._mid_index: Dict[str, ET.Element] = {}
        self._build_mid_index()
    
    def set_filter(self, filter_config: AIXMFilterConfig):
        """
        Set or update the filter configuration.
        
        Args:
            filter_config: New filter configuration
        """
        self._filter_config = filter_config
        self._filter = AIXMFilter(filter_config)
        self.clear_cache()
    
    def clear_filter(self):
        """Clear all filters."""
        self._filter_config = None
        self._filter = None
        self.clear_cache()
    
    def get_filter_config(self) -> Optional[AIXMFilterConfig]:
        """Get the current filter configuration."""
        return self._filter_config
    
    def _should_parse_type(self, element_type: str) -> bool:
        """Check if an element type should be parsed based on filters."""
        if not self._filter_config:
            return True
        return self._filter_config.should_include_type(element_type)
    
    def _build_mid_index(self):
        """Build an index of elements by their MID attribute."""
        for elem in self.root.iter():
            mid = elem.get('mid')
            if mid:
                self._mid_index[mid] = elem
    
    def _get_element_by_mid(self, mid: str) -> Optional[ET.Element]:
        """Get an element by its MID attribute."""
        return self._mid_index.get(mid)
    
    def _parse_point(self, element: ET.Element) -> Optional[Point]:
        """Parse a Point from geoLat/geoLong elements."""
        lat_str = find_tag_text(element, 'geoLat')
        lon_str = find_tag_text(element, 'geoLong')
        
        if lat_str and lon_str:
            lat = parse_coordinate(lat_str, 'lat')
            lon = parse_coordinate(lon_str, 'lon')
            return Point(lat, lon)
        return None
    
    def _parse_polygon_from_abd(self, abd_element: ET.Element) -> Optional[Polygon]:
        """Parse a Polygon from an Abd (Airspace Border) element."""
        points = []
        
        for avx in find_all_tags(abd_element, 'Avx'):
            lat_str = find_tag_text(avx, 'geoLat')
            lon_str = find_tag_text(avx, 'geoLong')
            
            if lat_str and lon_str:
                lat = parse_coordinate(lat_str, 'lat')
                lon = parse_coordinate(lon_str, 'lon')
                
                # Avoid duplicate consecutive points
                if not points or (lat != points[-1].lat or lon != points[-1].lon):
                    points.append(Point(lat, lon))
        
        if points:
            return Polygon(points)
        return None
    
    def _parse_vertical_limits(self, element: ET.Element) -> VerticalLimits:
        """Parse vertical limits from an airspace element."""
        limits = VerticalLimits()
        
        # Lower limit
        lower_val = find_tag_text(element, 'valDistVerLower')
        lower_uom = find_tag_text(element, 'uomDistVerLower')
        lower_code = find_tag_text(element, 'codeDistVerLower')
        
        if lower_val:
            limits.lower_limit, limits.lower_unit = parse_vertical_limit(lower_val, lower_uom or lower_code)
        
        # Upper limit
        upper_val = find_tag_text(element, 'valDistVerUpper')
        upper_uom = find_tag_text(element, 'uomDistVerUpper')
        upper_code = find_tag_text(element, 'codeDistVerUpper')
        
        if upper_val:
            limits.upper_limit, limits.upper_unit = parse_vertical_limit(upper_val, upper_uom or upper_code)
        
        return limits
    
    def get_airspaces(self) -> List[Airspace]:
        """
        Extract all airspaces from the AIXM file.
        
        Returns:
            List of Airspace objects with polygons and vertical limits
        """
        if 'airspaces' in self._cache:
            return self._cache['airspaces']
        
        airspaces = []
        
        # First pass: collect all Ase (Airspace) elements
        ase_by_mid: Dict[str, Dict] = {}
        
        for ase in find_all_tags(self.root, 'Ase'):
            uid = find_child_element(ase, 'AseUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            code_type = find_tag_text(uid, 'codeType')
            name = find_tag_text(ase, 'txtName')
            local_type = find_tag_text(ase, 'txtLocalType')
            
            # Parse vertical limits
            limits = self._parse_vertical_limits(ase)
            
            airspace_data = {
                'mid': mid,
                'code_id': code_id,
                'name': name or code_id,
                'type_code': code_type,
                'local_type': local_type,
                'vertical_limits': limits,
                'parent_fir': infer_parent_fir(code_id),
            }
            
            if mid:
                ase_by_mid[mid] = airspace_data
        
        # Second pass: match with Abd (Airspace Border) elements
        for abd in find_all_tags(self.root, 'Abd'):
            uid = find_child_element(abd, 'AbdUid')
            if uid is None:
                continue
            
            ase_uid = find_child_element(uid, 'AseUid')
            if ase_uid is None:
                continue
            
            target_mid = ase_uid.get('mid')
            target_code = find_tag_text(ase_uid, 'codeId')
            
            # Find matching airspace
            airspace_data = None
            if target_mid and target_mid in ase_by_mid:
                airspace_data = ase_by_mid[target_mid]
            elif target_code:
                # Try to find by code_id
                for data in ase_by_mid.values():
                    if data['code_id'] == target_code:
                        airspace_data = data
                        break
            
            if airspace_data:
                polygon = self._parse_polygon_from_abd(abd)
                if polygon:
                    airspace_data['polygon'] = polygon
        
        # Create Airspace objects
        for data in ase_by_mid.values():
            airspace = Airspace(
                mid=data.get('mid'),
                code_id=data.get('code_id'),
                name=data.get('name'),
                type_code=data.get('type_code'),
                local_type=data.get('local_type'),
                polygon=data.get('polygon'),
                vertical_limits=data.get('vertical_limits'),
                parent_fir=data.get('parent_fir'),
            )
            airspaces.append(airspace)
        
        self._cache['airspaces'] = airspaces
        return airspaces
    
    def get_airports(self) -> List[Airport]:
        """
        Extract all airports/aerodromes from the AIXM file.
        
        Returns:
            List of Airport objects
        """
        if 'airports' in self._cache:
            return self._cache['airports']
        
        airports = []
        
        for ahp in find_all_tags(self.root, 'Ahp'):
            uid = find_child_element(ahp, 'AhpUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            position = self._parse_point(ahp)
            
            airport = Airport(
                mid=mid,
                code_id=code_id,
                name=find_tag_text(ahp, 'txtName'),
                icao=find_tag_text(ahp, 'codeIcao'),
                iata=find_tag_text(ahp, 'codeIata'),
                position=position,
                elevation=safe_float(find_tag_text(ahp, 'valElev')),
                elevation_unit=find_tag_text(ahp, 'uomDistVer') or 'FT',
                type_code=find_tag_text(ahp, 'codeType'),
                city=find_tag_text(ahp, 'txtNameCitySer'),
            )
            airports.append(airport)
        
        self._cache['airports'] = airports
        return airports
    
    def get_waypoints(self) -> List[Waypoint]:
        """
        Extract all waypoints/designated points from the AIXM file.
        
        Returns:
            List of Waypoint objects
        """
        if 'waypoints' in self._cache:
            return self._cache['waypoints']
        
        waypoints = []
        
        for dpn in find_all_tags(self.root, 'Dpn'):
            uid = find_child_element(dpn, 'DpnUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            # Try to get coordinates from uid first, then from parent
            lat_str = find_tag_text(uid, 'geoLat') or find_tag_text(dpn, 'geoLat')
            lon_str = find_tag_text(uid, 'geoLong') or find_tag_text(dpn, 'geoLong')
            
            position = None
            if lat_str and lon_str:
                lat = parse_coordinate(lat_str, 'lat')
                lon = parse_coordinate(lon_str, 'lon')
                position = Point(lat, lon)
            
            waypoint = Waypoint(
                mid=mid,
                code_id=code_id,
                name=find_tag_text(dpn, 'txtName'),
                position=position,
                type_code=find_tag_text(dpn, 'codeType'),
            )
            waypoints.append(waypoint)
        
        self._cache['waypoints'] = waypoints
        return waypoints
    
    def get_navaids(self) -> List[Navaid]:
        """
        Extract all navigation aids from the AIXM file.
        
        Returns:
            List of Navaid objects (VOR, NDB, DME, TACAN)
        """
        if 'navaids' in self._cache:
            return self._cache['navaids']
        
        navaids = []
        
        # Parse VORs
        for vor in find_all_tags(self.root, 'Vor'):
            uid = find_child_element(vor, 'VorUid')
            if uid is None:
                continue
            
            # Try to get position from VorUid first, then from Vor
            position = self._parse_point(uid)
            if position is None:
                position = self._parse_point(vor)
            
            navaid = Navaid(
                mid=uid.get('mid'),
                code_id=find_tag_text(uid, 'codeId'),
                name=find_tag_text(vor, 'txtName'),
                position=position,
                frequency=safe_float(find_tag_text(vor, 'valFreq')),
                frequency_unit=find_tag_text(vor, 'uomFreq'),
                navaid_type='VOR',
                magnetic_variation=safe_float(find_tag_text(vor, 'valMagVar')),
            )
            navaids.append(navaid)
        
        # Parse NDBs
        for ndb in find_all_tags(self.root, 'Ndb'):
            uid = find_child_element(ndb, 'NdbUid')
            if uid is None:
                continue
            
            # Try to get position from NdbUid first, then from Ndb
            position = self._parse_point(uid)
            if position is None:
                position = self._parse_point(ndb)
            
            navaid = Navaid(
                mid=uid.get('mid'),
                code_id=find_tag_text(uid, 'codeId'),
                name=find_tag_text(ndb, 'txtName'),
                position=position,
                frequency=safe_float(find_tag_text(ndb, 'valFreq')),
                frequency_unit=find_tag_text(ndb, 'uomFreq'),
                navaid_type='NDB',
                magnetic_variation=safe_float(find_tag_text(ndb, 'valMagVar')),
            )
            navaids.append(navaid)
        
        # Parse DMEs
        for dme in find_all_tags(self.root, 'Dme'):
            uid = find_child_element(dme, 'DmeUid')
            if uid is None:
                continue
            
            # Try to get position from DmeUid first, then from Dme
            position = self._parse_point(uid)
            if position is None:
                position = self._parse_point(dme)
            
            navaid = Navaid(
                mid=uid.get('mid'),
                code_id=find_tag_text(uid, 'codeId'),
                name=find_tag_text(dme, 'txtName'),
                position=position,
                channel=find_tag_text(dme, 'codeChannel'),
                navaid_type='DME',
                magnetic_variation=safe_float(find_tag_text(dme, 'valMagVar')),
            )
            navaids.append(navaid)
        
        # Parse TACANs
        for tcn in find_all_tags(self.root, 'Tcn'):
            uid = find_child_element(tcn, 'TcnUid')
            if uid is None:
                continue
            
            # Try to get position from TcnUid first, then from Tcn
            position = self._parse_point(uid)
            if position is None:
                position = self._parse_point(tcn)
            
            navaid = Navaid(
                mid=uid.get('mid'),
                code_id=find_tag_text(uid, 'codeId'),
                name=find_tag_text(tcn, 'txtName'),
                position=position,
                channel=find_tag_text(tcn, 'codeChannel'),
                navaid_type='TACAN',
                magnetic_variation=safe_float(find_tag_text(tcn, 'valMagVar')),
            )
            navaids.append(navaid)
        
        self._cache['navaids'] = navaids
        return navaids
    
    def get_routes(self) -> List[Route]:
        """
        Extract all routes and their segments from the AIXM file.
        
        Returns:
            List of Route objects with segments
        """
        if 'routes' in self._cache:
            return self._cache['routes']
        
        routes = []
        
        # First, cache waypoints by codeId for quick lookup
        waypoint_cache: Dict[str, Point] = {}
        for wp in self.get_waypoints():
            if wp.code_id and wp.position:
                waypoint_cache[wp.code_id] = wp.position
        
        # Parse route definitions (Rte)
        route_info: Dict[str, Dict] = {}
        for rte in find_all_tags(self.root, 'Rte'):
            uid = find_child_element(rte, 'RteUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            designator = find_tag_text(uid, 'txtDesig')
            
            if mid:
                route_info[mid] = {
                    'mid': mid,
                    'designator': designator,
                    'route_type': find_tag_text(rte, 'codeType'),
                    'segments': [],
                }
        
        # Parse route segments (Rsg)
        for rsg in find_all_tags(self.root, 'Rsg'):
            uid = find_child_element(rsg, 'RsgUid')
            if uid is None:
                continue
            
            # Get route reference
            rte_uid = find_child_element(uid, 'RteUid')
            route_mid = rte_uid.get('mid') if rte_uid else None
            
            # Get start and end waypoints
            sta_uid = find_child_element(uid, 'DpnUidSta')
            end_uid = find_child_element(uid, 'DpnUidEnd')
            
            sta_code = find_tag_text(sta_uid, 'codeId') if sta_uid else None
            end_code = find_tag_text(end_uid, 'codeId') if end_uid else None
            
            # Get coordinates
            sta_point = None
            end_point = None
            
            if sta_code and sta_code in waypoint_cache:
                sta_point = waypoint_cache[sta_code]
            elif sta_uid:
                sta_point = self._parse_point(sta_uid)
            
            if end_code and end_code in waypoint_cache:
                end_point = waypoint_cache[end_code]
            elif end_uid:
                end_point = self._parse_point(end_uid)
            
            segment = RouteSegment(
                mid=rsg.get('mid'),
                route_mid=route_mid,
                start_waypoint_id=sta_code,
                end_waypoint_id=end_code,
                start_point=sta_point,
                end_point=end_point,
                rnp=find_tag_text(rsg, 'codeRnp'),
                path_type=find_tag_text(rsg, 'codeTypePath'),
            )
            
            # Add segment to route
            if route_mid and route_mid in route_info:
                route_info[route_mid]['segments'].append(segment)
        
        # Create Route objects
        for info in route_info.values():
            route = Route(
                mid=info['mid'],
                code_id=info['designator'],
                name=info['designator'],
                designator=info['designator'],
                route_type=info['route_type'],
                segments=info['segments'],
            )
            routes.append(route)
        
        self._cache['routes'] = routes
        return routes
    
    def get_geographical_borders(self) -> List[GeographicalBorder]:
        """
        Extract all geographical borders from the AIXM file.
        
        Returns:
            List of GeographicalBorder objects
        """
        if 'borders' in self._cache:
            return self._cache['borders']
        
        borders = []
        
        for gbr in find_all_tags(self.root, 'Gbr'):
            uid = find_child_element(gbr, 'GbrUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            name = find_tag_text(uid, 'txtName')
            
            # Parse border vertices
            points = []
            for gbv in find_all_tags(gbr, 'Gbv'):
                lat_str = find_tag_text(gbv, 'geoLat')
                lon_str = find_tag_text(gbv, 'geoLong')
                
                if lat_str and lon_str:
                    lat = parse_coordinate(lat_str, 'lat')
                    lon = parse_coordinate(lon_str, 'lon')
                    points.append(Point(lat, lon))
            
            polygon = Polygon(points) if points else None
            
            border = GeographicalBorder(
                mid=mid,
                code_id=name,
                name=name,
                border_type=find_tag_text(gbr, 'codeType'),
                polygon=polygon,
            )
            borders.append(border)
        
        self._cache['borders'] = borders
        return borders
    
    def get_organizations(self) -> List[Organization]:
        """
        Extract all organizations from the AIXM file.
        
        Returns:
            List of Organization objects
        """
        if 'organizations' in self._cache:
            return self._cache['organizations']
        
        organizations = []
        
        for org in find_all_tags(self.root, 'Org'):
            uid = find_child_element(org, 'OrgUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            name = find_tag_text(uid, 'txtName')
            
            organization = Organization(
                mid=mid,
                code_id=find_tag_text(org, 'codeId'),
                name=name,
                identifier=find_tag_text(org, 'codeId'),
                org_type=find_tag_text(org, 'codeType'),
            )
            organizations.append(organization)
        
        self._cache['organizations'] = organizations
        return organizations
    
    def get_airspaces_by_fir(self, fir_code: str) -> List[Airspace]:
        """
        Get all airspaces belonging to a specific FIR.
        
        Args:
            fir_code: FIR code (e.g., "LCCC", "HECC")
            
        Returns:
            List of Airspace objects in the FIR
        """
        all_airspaces = self.get_airspaces()
        return [a for a in all_airspaces if a.parent_fir == fir_code.upper()]
    
    def get_airspaces_by_type(self, type_code: str) -> List[Airspace]:
        """
        Get all airspaces of a specific type.
        
        Args:
            type_code: Airspace type (e.g., "CTA", "TMA", "FIR")
            
        Returns:
            List of Airspace objects of the specified type
        """
        all_airspaces = self.get_airspaces()
        return [a for a in all_airspaces if a.type_code == type_code.upper()]
    
    def get_airports_by_icao(self, icao_code: str) -> Optional[Airport]:
        """
        Get an airport by its ICAO code.
        
        Args:
            icao_code: ICAO airport code (e.g., "LCLK")
            
        Returns:
            Airport object or None
        """
        all_airports = self.get_airports()
        for airport in all_airports:
            if airport.icao and airport.icao.upper() == icao_code.upper():
                return airport
        return None
    
    def get_runways(self) -> List[Runway]:
        """
        Extract all runways from the AIXM file.
        
        Returns:
            List of Runway objects
        """
        if 'runways' in self._cache:
            return self._cache['runways']
        
        runways = []
        
        for rwy in find_all_tags(self.root, 'Rwy'):
            uid = find_child_element(rwy, 'RwyUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            # Get airport reference
            ahp_uid = find_child_element(uid, 'AhpUid')
            airport_mid = ahp_uid.get('mid') if ahp_uid else None
            
            # Get dimensions
            length = safe_float(find_tag_text(rwy, 'valLen'))
            width = safe_float(find_tag_text(rwy, 'valWid'))
            dim_unit = find_tag_text(rwy, 'uomDimRwy')
            
            # Get PCN data
            pcn_class = find_tag_text(rwy, 'valPcnClass')
            pcn_pavement_type = find_tag_text(rwy, 'codePcnPavementType')
            pcn_subgrade = find_tag_text(rwy, 'codePcnPavementSubgrade')
            pcn_tire_pressure = find_tag_text(rwy, 'codePcnMaxTirePressure')
            pcn_eval_method = find_tag_text(rwy, 'codePcnEvalMethod')
            
            # Get strip dimensions
            strip_length = safe_float(find_tag_text(rwy, 'valLenStrip'))
            strip_width = safe_float(find_tag_text(rwy, 'valWidStrip'))
            strip_unit = find_tag_text(rwy, 'uomDimStrip')
            
            runway = Runway(
                mid=mid,
                code_id=code_id,
                airport_mid=airport_mid,
                length=length,
                width=width,
                length_unit=dim_unit,
                width_unit=dim_unit,
                pcn_class=pcn_class,
                pcn_pavement_type=pcn_pavement_type,
                pcn_subgrade=pcn_subgrade,
                pcn_tire_pressure=pcn_tire_pressure,
                pcn_eval_method=pcn_eval_method,
                strip_length=strip_length,
                strip_width=strip_width,
                strip_unit=strip_unit,
                surface_composition=find_tag_text(rwy, 'codeComposition'),
                profile=find_tag_text(rwy, 'txtProfile'),
                marking=find_tag_text(rwy, 'txtMarking'),
            )
            runways.append(runway)
        
        self._cache['runways'] = runways
        return runways
    
    def get_taxiways(self) -> List[Taxiway]:
        """
        Extract all taxiways from the AIXM file.
        
        Returns:
            List of Taxiway objects
        """
        if 'taxiways' in self._cache:
            return self._cache['taxiways']
        
        taxiways = []
        
        for twy in find_all_tags(self.root, 'Twy'):
            uid = find_child_element(twy, 'TwyUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            # Get airport reference
            ahp_uid = find_child_element(uid, 'AhpUid')
            airport_mid = ahp_uid.get('mid') if ahp_uid else None
            
            # Get width
            width = safe_float(find_tag_text(twy, 'valWid'))
            width_unit = find_tag_text(twy, 'uomWid')
            
            taxiway = Taxiway(
                mid=mid,
                code_id=code_id,
                airport_mid=airport_mid,
                taxiway_type=find_tag_text(twy, 'codeType'),
                width=width,
                width_unit=width_unit,
                pcn_class=find_tag_text(twy, 'valPcnClass'),
                pcn_pavement_type=find_tag_text(twy, 'codePcnPavementType'),
                pcn_subgrade=find_tag_text(twy, 'codePcnPavementSubgrade'),
                pcn_tire_pressure=find_tag_text(twy, 'codePcnMaxTirePressure'),
                pcn_eval_method=find_tag_text(twy, 'codePcnEvalMethod'),
                surface_composition=find_tag_text(twy, 'codeComposition'),
                marking=find_tag_text(twy, 'txtMarking'),
            )
            taxiways.append(taxiway)
        
        self._cache['taxiways'] = taxiways
        return taxiways
    
    def get_aprons(self) -> List[Apron]:
        """
        Extract all aprons from the AIXM file.
        
        Returns:
            List of Apron objects
        """
        if 'aprons' in self._cache:
            return self._cache['aprons']
        
        aprons = []
        
        for apn in find_all_tags(self.root, 'Apn'):
            uid = find_child_element(apn, 'ApnUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            # Get airport reference
            ahp_uid = find_child_element(uid, 'AhpUid')
            airport_mid = ahp_uid.get('mid') if ahp_uid else None
            
            apron = Apron(
                mid=mid,
                code_id=code_id,
                airport_mid=airport_mid,
                surface_composition=find_tag_text(apn, 'codeComposition'),
                pcn_class=find_tag_text(apn, 'valPcnClass'),
                pcn_pavement_type=find_tag_text(apn, 'codePcnPavementType'),
                pcn_subgrade=find_tag_text(apn, 'codePcnPavementSubgrade'),
                pcn_tire_pressure=find_tag_text(apn, 'codePcnMaxTirePressure'),
                pcn_eval_method=find_tag_text(apn, 'codePcnEvalMethod'),
            )
            aprons.append(apron)
        
        self._cache['aprons'] = aprons
        return aprons
    
    def get_services(self) -> List[Service]:
        """
        Extract all services from the AIXM file.
        
        Returns:
            List of Service objects
        """
        if 'services' in self._cache:
            return self._cache['services']
        
        services = []
        
        for ser in find_all_tags(self.root, 'Ser'):
            uid = find_child_element(ser, 'SerUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            # Parse position
            position = self._parse_point(ser)
            
            service = Service(
                mid=mid,
                code_id=code_id,
                service_type=find_tag_text(ser, 'codeType'),
                source=find_tag_text(ser, 'codeSource'),
                position=position,
                datum=find_tag_text(ser, 'codeDatum'),
                crc=find_tag_text(ser, 'valCrc'),
            )
            services.append(service)
        
        self._cache['services'] = services
        return services
    
    def get_frequencies(self) -> List[Frequency]:
        """
        Extract all frequencies from the AIXM file.
        
        Returns:
            List of Frequency objects
        """
        if 'frequencies' in self._cache:
            return self._cache['frequencies']
        
        frequencies = []
        
        for fqy in find_all_tags(self.root, 'Fqy'):
            uid = find_child_element(fqy, 'FqyUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            frequency = Frequency(
                mid=mid,
                code_id=code_id,
                frequency=safe_float(find_tag_text(fqy, 'valFreqRec')),
                frequency_unit=find_tag_text(fqy, 'uomFreq'),
                frequency_type=find_tag_text(fqy, 'codeType'),
                emission_type=find_tag_text(fqy, 'codeEm'),
            )
            frequencies.append(frequency)
        
        self._cache['frequencies'] = frequencies
        return frequencies
    
    def get_units(self) -> List[Unit]:
        """
        Extract all units (ATC units) from the AIXM file.
        
        Returns:
            List of Unit objects
        """
        if 'units' in self._cache:
            return self._cache['units']
        
        units = []
        
        for uni in find_all_tags(self.root, 'Uni'):
            uid = find_child_element(uni, 'UniUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            # Get organization reference
            org_uid = find_child_element(uni, 'OrgUid')
            organization_mid = org_uid.get('mid') if org_uid else None
            
            # Get airport reference
            ahp_uid = find_child_element(uni, 'AhpUid')
            airport_mid = ahp_uid.get('mid') if ahp_uid else None
            
            # Parse position
            position = self._parse_point(uni)
            
            unit = Unit(
                mid=mid,
                code_id=code_id,
                organization_mid=organization_mid,
                airport_mid=airport_mid,
                unit_type=find_tag_text(uni, 'codeType'),
                unit_class=find_tag_text(uni, 'codeClass'),
                position=position,
                datum=find_tag_text(uni, 'codeDatum'),
            )
            units.append(unit)
        
        self._cache['units'] = units
        return units
    
    def get_sids(self) -> List[SID]:
        """
        Extract all SIDs (Standard Instrument Departures) from the AIXM file.
        
        Returns:
            List of SID objects
        """
        if 'sids' in self._cache:
            return self._cache['sids']
        
        sids = []
        
        for sid in find_all_tags(self.root, 'Sid'):
            uid = find_child_element(sid, 'SidUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            designator = find_tag_text(uid, 'txtDesig')
            
            # Get runway direction reference
            rdn_uid = find_child_element(sid, 'RdnUid')
            runway_direction_mid = rdn_uid.get('mid') if rdn_uid else None
            
            # Get MSA group reference
            mgp_uid = find_child_element(sid, 'MgpUid')
            msa_group_mid = mgp_uid.get('mid') if mgp_uid else None
            
            sid_obj = SID(
                mid=mid,
                code_id=code_id,
                designator=designator,
                runway_direction_mid=runway_direction_mid,
                msa_group_mid=msa_group_mid,
                route_type=find_tag_text(sid, 'codeTypeRte'),
                description=find_tag_text(sid, 'txtDescr'),
                com_failure=find_tag_text(sid, 'txtDescrComFail'),
            )
            sids.append(sid_obj)
        
        self._cache['sids'] = sids
        return sids
    
    def get_stars(self) -> List[STAR]:
        """
        Extract all STARs (Standard Terminal Arrival Routes) from the AIXM file.
        
        Returns:
            List of STAR objects
        """
        if 'stars' in self._cache:
            return self._cache['stars']
        
        stars = []
        
        for star in find_all_tags(self.root, 'Sia'):
            uid = find_child_element(star, 'SiaUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            designator = find_tag_text(uid, 'txtDesig')
            
            # Get MSA group reference
            mgp_uid = find_child_element(star, 'MgpUid')
            msa_group_mid = mgp_uid.get('mid') if mgp_uid else None
            
            star_obj = STAR(
                mid=mid,
                code_id=code_id,
                designator=designator,
                msa_group_mid=msa_group_mid,
                route_type=find_tag_text(star, 'codeTypeRte'),
                description=find_tag_text(star, 'txtDescr'),
                com_failure=find_tag_text(star, 'txtDescrComFail'),
            )
            stars.append(star_obj)
        
        self._cache['stars'] = stars
        return stars
    
    def get_instrument_approaches(self) -> List[InstrumentApproach]:
        """
        Extract all instrument approaches from the AIXM file.
        
        Returns:
            List of InstrumentApproach objects
        """
        if 'approaches' in self._cache:
            return self._cache['approaches']
        
        approaches = []
        
        for iap in find_all_tags(self.root, 'Iap'):
            uid = find_child_element(iap, 'IapUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            designator = find_tag_text(uid, 'txtDesig')
            
            # Get runway direction reference
            rdn_uid = find_child_element(iap, 'RdnUid')
            runway_direction_mid = rdn_uid.get('mid') if rdn_uid else None
            
            # Get MSA group reference
            mgp_uid = find_child_element(iap, 'MgpUid')
            msa_group_mid = mgp_uid.get('mid') if mgp_uid else None
            
            approach = InstrumentApproach(
                mid=mid,
                code_id=code_id,
                designator=designator,
                runway_direction_mid=runway_direction_mid,
                msa_group_mid=msa_group_mid,
                approach_type=find_tag_text(iap, 'codeTypeRte'),
                description=find_tag_text(iap, 'txtDescr'),
                missed_approach=find_tag_text(iap, 'txtDescrMiss'),
            )
            approaches.append(approach)
        
        self._cache['approaches'] = approaches
        return approaches
    
    def get_ils(self) -> List[ILS]:
        """
        Extract all ILS (Instrument Landing Systems) from the AIXM file.
        
        Returns:
            List of ILS objects
        """
        if 'ils' in self._cache:
            return self._cache['ils']
        
        ils_list = []
        
        for ils in find_all_tags(self.root, 'Ils'):
            uid = find_child_element(ils, 'IlsUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            
            # Get runway direction reference
            rdn_uid = find_child_element(uid, 'RdnUid')
            runway_direction_mid = rdn_uid.get('mid') if rdn_uid else None
            
            # Get DME reference
            dme_uid = find_child_element(ils, 'DmeUid')
            dme_mid = dme_uid.get('mid') if dme_uid else None
            
            ils_obj = ILS(
                mid=mid,
                code_id=None,  # ILS uses runway direction for identification
                runway_direction_mid=runway_direction_mid,
                category=find_tag_text(ils, 'codeCat'),
                channel=find_tag_text(ils, 'codeChannel'),
                dme_mid=dme_mid,
            )
            ils_list.append(ils_obj)
        
        self._cache['ils'] = ils_list
        return ils_list
    
    def get_markers(self) -> List[Marker]:
        """
        Extract all marker beacons from the AIXM file.
        
        Returns:
            List of Marker objects
        """
        if 'markers' in self._cache:
            return self._cache['markers']
        
        markers = []
        
        for mkr in find_all_tags(self.root, 'Mkr'):
            uid = find_child_element(mkr, 'MkrUid')
            if uid is None:
                continue
            
            mid = uid.get('mid')
            code_id = find_tag_text(uid, 'codeId')
            
            # Get airport reference
            ahp_uid = find_child_element(uid, 'AhpUid')
            airport_mid = ahp_uid.get('mid') if ahp_uid else None
            
            # Parse position
            position = self._parse_point(uid)
            if position is None:
                position = self._parse_point(mkr)
            
            marker = Marker(
                mid=mid,
                code_id=code_id,
                position=position,
                marker_type=find_tag_text(mkr, 'codeType'),
                frequency=safe_float(find_tag_text(mkr, 'valFreq')),
                bearing=safe_float(find_tag_text(mkr, 'valMagBrg')),
                airport_mid=airport_mid,
            )
            markers.append(marker)
        
        self._cache['markers'] = markers
        return markers
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get statistics about the parsed AIXM file.
        
        Returns:
            Dictionary with feature counts
        """
        return {
            'airspaces': len(self.get_airspaces()),
            'airports': len(self.get_airports()),
            'waypoints': len(self.get_waypoints()),
            'routes': len(self.get_routes()),
            'navaids': len(self.get_navaids()),
            'borders': len(self.get_geographical_borders()),
            'organizations': len(self.get_organizations()),
            'runways': len(self.get_runways()),
            'taxiways': len(self.get_taxiways()),
            'aprons': len(self.get_aprons()),
            'services': len(self.get_services()),
            'frequencies': len(self.get_frequencies()),
            'units': len(self.get_units()),
            'sids': len(self.get_sids()),
            'stars': len(self.get_stars()),
            'instrument_approaches': len(self.get_instrument_approaches()),
            'ils': len(self.get_ils()),
            'markers': len(self.get_markers()),
        }
    
    def clear_cache(self):
        """Clear the internal feature cache."""
        self._cache.clear()
