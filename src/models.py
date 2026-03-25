"""
Data models for AIXM 4.5 features.

This module defines dataclasses for all AIXM feature types including
airspaces, airports, waypoints, routes, and navaids.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


@dataclass
class Point:
    """Geographic point with latitude and longitude."""
    lat: float
    lon: float
    
    def to_tuple(self) -> Tuple[float, float]:
        """Return as (lat, lon) tuple."""
        return (self.lat, self.lon)
    
    def to_geojson(self) -> List[float]:
        """Return as GeoJSON [lon, lat] coordinate."""
        return [self.lon, self.lat]


@dataclass
class Polygon:
    """Polygon geometry for airspace boundaries."""
    points: List[Point] = field(default_factory=list)
    
    def to_tuples(self) -> List[Tuple[float, float]]:
        """Return as list of (lat, lon) tuples."""
        return [p.to_tuple() for p in self.points]
    
    def to_geojson(self) -> List[List[float]]:
        """Return as GeoJSON coordinate array."""
        return [p.to_geojson() for p in self.points]
    
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Return (min_lat, min_lon, max_lat, max_lon) or None if empty."""
        if not self.points:
            return None
        lats = [p.lat for p in self.points]
        lons = [p.lon for p in self.points]
        return (min(lats), min(lons), max(lats), max(lons))


@dataclass
class LineString:
    """Line geometry for routes and paths."""
    points: List[Point] = field(default_factory=list)
    
    def to_tuples(self) -> List[Tuple[float, float]]:
        """Return as list of (lat, lon) tuples."""
        return [p.to_tuple() for p in self.points]
    
    def to_geojson(self) -> List[List[float]]:
        """Return as GeoJSON coordinate array."""
        return [p.to_geojson() for p in self.points]


@dataclass
class AIXMFeature:
    """Base class for all AIXM features."""
    mid: Optional[str] = None
    code_id: Optional[str] = None
    name: Optional[str] = None
    effective_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default name if not provided."""
        if self.name is None and self.code_id is not None:
            self.name = self.code_id


@dataclass
class VerticalLimits:
    """Vertical limits for airspaces."""
    lower_limit: Optional[str] = None  # e.g., "FL65", "0", "SFC"
    lower_unit: Optional[str] = None   # "FL" or "FT" or "M"
    upper_limit: Optional[str] = None  # e.g., "FL660", "UNLIMITED"
    upper_unit: Optional[str] = None   # "FL" or "FT" or "M"
    
    def lower_fl(self) -> Optional[int]:
        """Return lower limit as flight level if applicable."""
        if self.lower_unit == "FL" and self.lower_limit:
            try:
                return int(self.lower_limit)
            except ValueError:
                return None
        return None
    
    def upper_fl(self) -> Optional[int]:
        """Return upper limit as flight level if applicable."""
        if self.upper_unit == "FL" and self.upper_limit:
            try:
                return int(self.upper_limit)
            except ValueError:
                return None
        return None


@dataclass
class Airspace(AIXMFeature):
    """Airspace feature (Ase + Abd)."""
    type_code: Optional[str] = None           # codeType: CTA, TMA, FIR, etc.
    local_type: Optional[str] = None          # txtLocalType
    polygon: Optional[Polygon] = None
    vertical_limits: Optional[VerticalLimits] = None
    parent_fir: Optional[str] = None          # Inferred parent FIR
    
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Return bounding box of airspace polygon."""
        if self.polygon:
            return self.polygon.bounds()
        return None
    
    def center(self) -> Optional[Point]:
        """Return approximate center point of airspace."""
        bounds = self.bounds()
        if bounds:
            min_lat, min_lon, max_lat, max_lon = bounds
            return Point((min_lat + max_lat) / 2, (min_lon + max_lon) / 2)
        return None


@dataclass
class Airport(AIXMFeature):
    """Aerodrome/Heliport feature (Ahp)."""
    icao: Optional[str] = None
    iata: Optional[str] = None
    position: Optional[Point] = None
    elevation: Optional[float] = None
    elevation_unit: Optional[str] = "FT"
    type_code: Optional[str] = None           # AD (aerodrome) or HP (heliport)
    city: Optional[str] = None
    organization: Optional[str] = None        # OrgUid reference
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "name": self.name,
            "icao": self.icao,
            "iata": self.iata,
            "lat": self.position.lat if self.position else None,
            "lon": self.position.lon if self.position else None,
            "elevation": self.elevation,
            "type": self.type_code,
        }


@dataclass
class Waypoint(AIXMFeature):
    """Designated Point feature (Dpn)."""
    position: Optional[Point] = None
    type_code: Optional[str] = None           # ENRT, TERM, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "name": self.name,
            "lat": self.position.lat if self.position else None,
            "lon": self.position.lon if self.position else None,
            "type": self.type_code,
        }


@dataclass
class RouteSegment:
    """Route segment connecting two waypoints (Rsg)."""
    mid: Optional[str] = None
    route_mid: Optional[str] = None           # Reference to parent route
    start_waypoint_id: Optional[str] = None   # DpnUidSta codeId
    end_waypoint_id: Optional[str] = None     # DpnUidEnd codeId
    start_point: Optional[Point] = None
    end_point: Optional[Point] = None
    rnp: Optional[str] = None                 # Required Navigation Performance
    path_type: Optional[str] = None           # codeTypePath: GREAT_CIRCLE, etc.
    
    def to_line(self) -> Optional[LineString]:
        """Return as LineString geometry."""
        if self.start_point and self.end_point:
            return LineString([self.start_point, self.end_point])
        return None


@dataclass
class Route(AIXMFeature):
    """Enroute Route feature (Rte)."""
    designator: Optional[str] = None          # txtDesig: e.g., "L888", "B9"
    route_type: Optional[str] = None          # codeType: AWY (airway), etc.
    segments: List[RouteSegment] = field(default_factory=list)
    
    def get_waypoint_ids(self) -> List[str]:
        """Get all unique waypoint IDs in this route."""
        ids = set()
        for seg in self.segments:
            if seg.start_waypoint_id:
                ids.add(seg.start_waypoint_id)
            if seg.end_waypoint_id:
                ids.add(seg.end_waypoint_id)
        return sorted(list(ids))


@dataclass
class Navaid(AIXMFeature):
    """Navigation aid base class (Vor, Ndb, Dme, Tcn)."""
    position: Optional[Point] = None
    frequency: Optional[float] = None
    frequency_unit: Optional[str] = None      # KHZ, MHZ
    channel: Optional[str] = None             # For DME/TACAN
    navaid_type: Optional[str] = None         # VOR, NDB, DME, TACAN
    magnetic_variation: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "name": self.name,
            "type": self.navaid_type,
            "lat": self.position.lat if self.position else None,
            "lon": self.position.lon if self.position else None,
            "frequency": self.frequency,
            "unit": self.frequency_unit,
            "channel": self.channel,
        }


@dataclass
class GeographicalBorder(AIXMFeature):
    """Geographical Border feature (Gbr)."""
    border_type: Optional[str] = None         # codeType: ST (state border), etc.
    polygon: Optional[Polygon] = None
    
    def bounds(self) -> Optional[Tuple[float, float, float, float]]:
        """Return bounding box of border polygon."""
        if self.polygon:
            return self.polygon.bounds()
        return None


@dataclass
class Organization(AIXMFeature):
    """Organization/Authority feature (Org)."""
    org_type: Optional[str] = None            # codeType: S (state), A (authority), etc.
    identifier: Optional[str] = None          # codeId


@dataclass
class Runway(AIXMFeature):
    """Runway feature (Rwy)."""
    airport_mid: Optional[str] = None         # Reference to Ahp
    length: Optional[float] = None            # valLen
    width: Optional[float] = None             # valWid
    length_unit: Optional[str] = None         # uomDimRwy
    width_unit: Optional[str] = None          # uomDimRwy
    pcn_class: Optional[str] = None           # valPcnClass
    pcn_pavement_type: Optional[str] = None   # codePcnPavementType
    pcn_subgrade: Optional[str] = None        # codePcnPavementSubgrade
    pcn_tire_pressure: Optional[str] = None   # codePcnMaxTirePressure
    pcn_eval_method: Optional[str] = None     # codePcnEvalMethod
    strip_length: Optional[float] = None      # valLenStrip
    strip_width: Optional[float] = None       # valWidStrip
    strip_unit: Optional[str] = None          # uomDimStrip
    surface_composition: Optional[str] = None # codeComposition
    profile: Optional[str] = None             # txtProfile
    marking: Optional[str] = None             # txtMarking

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "airport_mid": self.airport_mid,
            "length": self.length,
            "width": self.width,
            "length_unit": self.length_unit,
            "width_unit": self.width_unit,
            "pcn_class": self.pcn_class,
            "surface_composition": self.surface_composition,
        }


@dataclass
class Taxiway(AIXMFeature):
    """Taxiway feature (Twy)."""
    airport_mid: Optional[str] = None         # Reference to Ahp
    taxiway_type: Optional[str] = None        # codeType
    width: Optional[float] = None             # valWid
    width_unit: Optional[str] = None          # uomWid
    pcn_class: Optional[str] = None           # valPcnClass
    pcn_pavement_type: Optional[str] = None   # codePcnPavementType
    pcn_subgrade: Optional[str] = None        # codePcnPavementSubgrade
    pcn_tire_pressure: Optional[str] = None   # codePcnMaxTirePressure
    pcn_eval_method: Optional[str] = None     # codePcnEvalMethod
    surface_composition: Optional[str] = None # codeComposition
    marking: Optional[str] = None             # txtMarking

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "airport_mid": self.airport_mid,
            "taxiway_type": self.taxiway_type,
            "width": self.width,
            "width_unit": self.width_unit,
            "pcn_class": self.pcn_class,
        }


@dataclass
class Apron(AIXMFeature):
    """Apron feature (Apn)."""
    airport_mid: Optional[str] = None         # Reference to Ahp
    surface_composition: Optional[str] = None # codeComposition
    pcn_class: Optional[str] = None           # valPcnClass
    pcn_pavement_type: Optional[str] = None   # codePcnPavementType
    pcn_subgrade: Optional[str] = None        # codePcnPavementSubgrade
    pcn_tire_pressure: Optional[str] = None   # codePcnMaxTirePressure
    pcn_eval_method: Optional[str] = None     # codePcnEvalMethod

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "airport_mid": self.airport_mid,
            "surface_composition": self.surface_composition,
            "pcn_class": self.pcn_class,
        }


@dataclass
class Service(AIXMFeature):
    """Service feature (Ser)."""
    service_type: Optional[str] = None        # codeType
    source: Optional[str] = None              # codeSource
    position: Optional[Point] = None          # geoLat/geoLong
    datum: Optional[str] = None               # codeDatum
    crc: Optional[str] = None                 # valCrc

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "service_type": self.service_type,
            "source": self.source,
            "lat": self.position.lat if self.position else None,
            "lon": self.position.lon if self.position else None,
        }


@dataclass
class Frequency(AIXMFeature):
    """Frequency feature (Fqy)."""
    frequency: Optional[float] = None         # valFreqRec
    frequency_unit: Optional[str] = None      # uomFreq
    frequency_type: Optional[str] = None      # codeType
    emission_type: Optional[str] = None       # codeEm

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "frequency": self.frequency,
            "frequency_unit": self.frequency_unit,
            "frequency_type": self.frequency_type,
            "emission_type": self.emission_type,
        }


@dataclass
class Unit(AIXMFeature):
    """Unit feature (Uni) - ATC Unit."""
    organization_mid: Optional[str] = None    # OrgUid reference
    airport_mid: Optional[str] = None         # AhpUid reference
    unit_type: Optional[str] = None           # codeType
    unit_class: Optional[str] = None          # codeClass
    position: Optional[Point] = None          # geoLat/geoLong
    datum: Optional[str] = None               # codeDatum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "name": self.name,
            "unit_type": self.unit_type,
            "unit_class": self.unit_class,
            "lat": self.position.lat if self.position else None,
            "lon": self.position.lon if self.position else None,
        }


@dataclass
class ProcedureLeg:
    """Procedure leg for SID/STAR/Approach."""
    mid: Optional[str] = None
    leg_type: Optional[str] = None            # codeType
    phase: Optional[str] = None               # codePhase
    course: Optional[float] = None            # valCourse
    course_type: Optional[str] = None         # codeTypeCourse
    turn_direction: Optional[str] = None      # codeDirTurn
    fly_by: Optional[bool] = None             # codeTurnValid
    upper_limit: Optional[str] = None         # valDistVerUpper
    upper_unit: Optional[str] = None          # uomDistVerUpper
    lower_limit: Optional[str] = None         # valDistVerLower
    lower_unit: Optional[str] = None          # uomDistVerLower
    speed_limit: Optional[float] = None       # valSpeedLimit
    speed_unit: Optional[str] = None          # uomSpeed
    distance: Optional[float] = None          # valDist
    duration: Optional[float] = None          # valDur
    theta: Optional[float] = None             # valTheta
    rho: Optional[float] = None               # valRho


@dataclass
class SID(AIXMFeature):
    """Standard Instrument Departure (Sid)."""
    designator: Optional[str] = None          # txtDesig
    airport_mid: Optional[str] = None         # Via RdnUid -> Rwy -> Ahp
    runway_direction_mid: Optional[str] = None # RdnUid
    msa_group_mid: Optional[str] = None       # MgpUid
    route_type: Optional[str] = None          # codeTypeRte
    description: Optional[str] = None         # txtDescr
    com_failure: Optional[str] = None         # txtDescrComFail
    procedure_legs: List[ProcedureLeg] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "designator": self.designator,
            "airport_mid": self.airport_mid,
            "route_type": self.route_type,
            "description": self.description,
            "legs_count": len(self.procedure_legs),
        }


@dataclass
class STAR(AIXMFeature):
    """Standard Terminal Arrival Route (Sia)."""
    designator: Optional[str] = None          # txtDesig
    airport_mid: Optional[str] = None         # Via RdnUid -> Rwy -> Ahp
    msa_group_mid: Optional[str] = None       # MgpUid
    route_type: Optional[str] = None          # codeTypeRte
    description: Optional[str] = None         # txtDescr
    com_failure: Optional[str] = None         # txtDescrComFail
    procedure_legs: List[ProcedureLeg] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "designator": self.designator,
            "airport_mid": self.airport_mid,
            "route_type": self.route_type,
            "description": self.description,
            "legs_count": len(self.procedure_legs),
        }


@dataclass
class InstrumentApproach(AIXMFeature):
    """Instrument Approach Procedure (Iap)."""
    designator: Optional[str] = None          # txtDesig
    airport_mid: Optional[str] = None         # Via RdnUid -> Rwy -> Ahp
    runway_direction_mid: Optional[str] = None # RdnUid
    msa_group_mid: Optional[str] = None       # MgpUid
    approach_type: Optional[str] = None       # codeTypeRte
    description: Optional[str] = None         # txtDescr
    missed_approach: Optional[str] = None     # txtDescrMiss
    procedure_legs: List[ProcedureLeg] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "designator": self.designator,
            "airport_mid": self.airport_mid,
            "approach_type": self.approach_type,
            "description": self.description,
            "legs_count": len(self.procedure_legs),
        }


@dataclass
class ILS(AIXMFeature):
    """Instrument Landing System (Ils)."""
    runway_direction_mid: Optional[str] = None # RdnUid
    category: Optional[str] = None            # codeCat
    channel: Optional[str] = None             # codeChannel
    localizer_freq: Optional[float] = None    # From Ilz
    glidepath_angle: Optional[float] = None   # From Igp
    dme_mid: Optional[str] = None             # DmeUid reference

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "category": self.category,
            "channel": self.channel,
            "localizer_freq": self.localizer_freq,
            "glidepath_angle": self.glidepath_angle,
        }


@dataclass
class Marker(AIXMFeature):
    """Marker Beacon (Mkr)."""
    position: Optional[Point] = None          # geoLat/geoLong
    marker_type: Optional[str] = None         # codeType
    frequency: Optional[float] = None         # valFreq
    bearing: Optional[float] = None           # valMagBrg
    airport_mid: Optional[str] = None         # AhpUid reference

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "mid": self.mid,
            "code_id": self.code_id,
            "name": self.name,
            "marker_type": self.marker_type,
            "lat": self.position.lat if self.position else None,
            "lon": self.position.lon if self.position else None,
            "frequency": self.frequency,
        }
