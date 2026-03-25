/**
 * AIXM Parser - Browser-based XML Parser
 * 
 * Parses AIXM 4.5 XML files and extracts aeronautical features.
 * Runs entirely in the browser using native DOMParser.
 */

class AIXMParser {
    constructor() {
        this.xmlDoc = null;
        this.features = [];
        this.namespaces = {};
        this.elementCounts = {};
        this.airspaceBorders = {}; // Map of border key -> polygon points
        this.routeSegments = {}; // Map of route segment key -> segment data
    }

    /**
     * Parse an AIXM XML file
     * @param {File} file - XML file to parse
     * @returns {Promise} - Resolves with parsed data
     */
    async parseFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = (e) => {
                try {
                    const xmlText = e.target.result;
                    this.parseXML(xmlText);
                    resolve(this.getSummary());
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    /**
     * Parse XML text
     * @param {string} xmlText - XML content
     */
    parseXML(xmlText) {
        const parser = new DOMParser();
        this.xmlDoc = parser.parseFromString(xmlText, 'text/xml');
        
        // Check for parsing errors
        const parseError = this.xmlDoc.querySelector('parsererror');
        if (parseError) {
            throw new Error('Invalid XML file');
        }
        
        this.extractNamespaces();
        this.countElements();
        this.extractFeatures();
    }

    /**
     * Extract namespace prefixes
     */
    extractNamespaces() {
        const root = this.xmlDoc.documentElement;
        const attributes = root.attributes;
        
        for (let i = 0; i < attributes.length; i++) {
            const attr = attributes[i];
            if (attr.name.startsWith('xmlns:')) {
                const prefix = attr.name.replace('xmlns:', '');
                this.namespaces[prefix] = attr.value;
            }
        }
    }

    /**
     * Count all AIXM element types
     */
    countElements() {
        this.elementCounts = {};
        
        const allElements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of allElements) {
            const tagName = this.getLocalTagName(elem);
            const friendlyName = this.getFriendlyElementName(tagName);
            
            if (friendlyName) {
                this.elementCounts[friendlyName] = (this.elementCounts[friendlyName] || 0) + 1;
            }
        }
    }

    /**
     * Extract all AIXM features
     */
    extractFeatures() {
        this.features = [];
        this.airspaceBorders = {};
        this.routeSegments = {};
        this.waypointPositions = {};

        // First extract airspace borders (polygons) - needed for airspaces
        this.extractAirspaceBorders();
        
        // Extract each feature type
        this.extractAirspaces();
        this.extractAirports();
        // Extract waypoints first to build position lookup for routes
        this.extractWaypoints();
        this.extractNavaids();
        // Extract route segments first (needed for routes)
        this.extractRouteSegments();
        this.extractRoutes();
        this.extractBorders();
        this.extractOrganizations();
        this.extractRunways();
        this.extractTaxiways();
        this.extractAprons();
        this.extractServices();
        this.extractFrequencies();
        this.extractUnits();
        this.extractSIDs();
        this.extractSTARs();
        this.extractApproaches();
        this.extractILS();
        this.extractMarkers();
    }

    /**
     * Get local tag name without namespace
     */
    getLocalTagName(element) {
        const tagName = element.tagName;
        return tagName.includes(':') ? tagName.split(':')[1] : tagName;
    }

    /**
     * Get friendly element name from XML tag
     */
    getFriendlyElementName(tagName) {
        const mapping = {
            'Ase': 'airspace', 'Abd': 'airspace',
            'Ahp': 'airport',
            'Dpn': 'waypoint',
            'Vor': 'vor', 'Ndb': 'ndb', 'Dme': 'dme', 'Tcn': 'tacan',
            'Rte': 'route', 'Rsg': 'route',
            'Gbr': 'border',
            'Org': 'organization',
            'Rwy': 'runway', 'Twy': 'taxiway', 'Apn': 'apron',
            'Ser': 'service', 'Fqy': 'frequency', 'Uni': 'unit',
            'Sid': 'sid', 'Sia': 'star', 'Iap': 'approach',
            'Ils': 'ils', 'Mkr': 'marker'
        };
        return mapping[tagName] || null;
    }

    /**
     * Get XML tag from friendly name
     */
    getXmlTag(friendlyName) {
        const mapping = {
            'airspace': ['Ase', 'Abd'],
            'airport': ['Ahp'],
            'waypoint': ['Dpn'],
            'vor': ['Vor'], 'ndb': ['Ndb'], 'dme': ['Dme'], 'tacan': ['Tcn'],
            'route': ['Rte', 'Rsg'],
            'border': ['Gbr'],
            'organization': ['Org'],
            'runway': ['Rwy'], 'taxiway': ['Twy'], 'apron': ['Apn'],
            'service': ['Ser'], 'frequency': ['Fqy'], 'unit': ['Uni'],
            'sid': ['Sid'], 'star': ['Sia'], 'approach': ['Iap'],
            'ils': ['Ils'], 'marker': ['Mkr']
        };
        return mapping[friendlyName] || [];
    }

    /**
     * Extract text content from child element
     */
    getChildText(parent, tagName) {
        const children = parent.getElementsByTagName('*');
        for (let child of children) {
            if (this.getLocalTagName(child) === tagName) {
                return child.textContent.trim();
            }
        }
        return null;
    }

    /**
     * Get child element by tag name
     */
    getChildElement(parent, tagName) {
        const children = parent.getElementsByTagName('*');
        for (let child of children) {
            if (this.getLocalTagName(child) === tagName) {
                return child;
            }
        }
        return null;
    }

    /**
     * Get attribute value
     */
    getAttribute(element, attrName) {
        return element.getAttribute(attrName);
    }

    /**
     * Extract position from geoLat/geoLong
     */
    extractPosition(element) {
        const geoLat = this.getChildText(element, 'geoLat');
        const geoLong = this.getChildText(element, 'geoLong');
        
        if (geoLat && geoLong) {
            return {
                lat: this.parseCoordinate(geoLat),
                lon: this.parseCoordinate(geoLong)
            };
        }
        return null;
    }

    /**
     * Parse coordinate string (e.g., "341200N" or "32.4567" or "43.784009N")
     */
    parseCoordinate(coord) {
        if (!coord) return null;
        
        coord = coord.trim();
        
        // Handle decimal format with direction suffix like "43.784009N" or "007.529827E"
        // Must have a decimal point to distinguish from DMS format
        const decimalDirMatch = coord.match(/^(\d+\.\d+)([NSWE])$/);
        if (decimalDirMatch) {
            let decimal = parseFloat(decimalDirMatch[1]);
            const direction = decimalDirMatch[2];
            if (!isNaN(decimal)) {
                if (direction === 'S' || direction === 'W') {
                    decimal = -decimal;
                }
                return decimal;
            }
        }
        
        // Handle DMS format like "341200N" or "0163411E" (3-digit degrees for longitude)
        // Pattern: 2-3 digits degrees, 2 digits minutes, 2 digits seconds, 1 letter direction
        const match = coord.match(/^(\d{2,3})(\d{2})(\d{2})([NSWE])$/);
        if (match) {
            const degrees = parseInt(match[1]);
            const minutes = parseInt(match[2]);
            const seconds = parseInt(match[3]);
            const direction = match[4];
            
            let decimal = degrees + minutes / 60 + seconds / 3600;
            if (direction === 'S' || direction === 'W') {
                decimal = -decimal;
            }
            return decimal;
        }
        
        // Handle DMS format with decimal seconds like "510520.60N"
        const dmsDecimalMatch = coord.match(/^(\d{2,3})(\d{2})(\d{2}\.\d+)([NSWE])$/);
        if (dmsDecimalMatch) {
            const degrees = parseInt(dmsDecimalMatch[1]);
            const minutes = parseInt(dmsDecimalMatch[2]);
            const seconds = parseFloat(dmsDecimalMatch[3]);
            const direction = dmsDecimalMatch[4];
            
            let decimal = degrees + minutes / 60 + seconds / 3600;
            if (direction === 'S' || direction === 'W') {
                decimal = -decimal;
            }
            return decimal;
        }
        
        // Handle pure decimal format
        const decimalValue = parseFloat(coord);
        if (!isNaN(decimalValue)) {
            return decimalValue;
        }
        
        return null;
    }

    /**
     * Extract polygon coordinates from posList
     */
    extractPolygon(element) {
        const posList = this.getChildText(element, 'posList');
        if (posList) {
            return this.parsePosList(posList);
        }
        return null;
    }

    /**
     * Parse posList string into array of coordinates
     */
    parsePosList(posList) {
        const coords = posList.trim().split(/\s+/);
        const points = [];
        
        for (let i = 0; i < coords.length; i += 2) {
            if (i + 1 < coords.length) {
                const lat = parseFloat(coords[i]);
                const lon = parseFloat(coords[i + 1]);
                if (!isNaN(lat) && !isNaN(lon)) {
                    points.push([lat, lon]);
                }
            }
        }
        
        return points;
    }

    // ============ Feature Extraction Methods ============

    /**
     * Extract airspace borders (Abd elements) with their polygons
     * Returns a map of border key (codeId|codeType or mid) -> polygon points
     */
    extractAirspaceBorders() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Abd') {
                // Get the AbdUid to build a lookup key
                const abdUid = this.getChildElement(elem, 'AbdUid');
                if (abdUid) {
                    const aseUid = this.getChildElement(abdUid, 'AseUid');
                    if (aseUid) {
                        // Try to get mid attribute first (for linking)
                        const mid = aseUid.getAttribute('mid');
                        const codeId = this.getChildText(aseUid, 'codeId');
                        const codeType = this.getChildText(aseUid, 'codeType');
                        
                        // Extract polygon from Avx elements
                        const polygon = this.extractAbdPolygon(elem);
                        if (polygon && polygon.length > 0) {
                            // Store by mid if available (primary key for linking)
                            if (mid) {
                                this.airspaceBorders[mid] = polygon;
                            }
                            // Also store by codeId|codeType if available (fallback)
                            if (codeId) {
                                const key = codeType ? `${codeId}|${codeType}` : codeId;
                                this.airspaceBorders[key] = polygon;
                            }
                        }
                    }
                }
            }
        }
    }

    /**
     * Extract polygon from Abd element using Avx children
     */
    extractAbdPolygon(abdElement) {
        const points = [];
        
        // Iterate over direct children of Abd element
        for (let child of abdElement.children) {
            if (this.getLocalTagName(child) === 'Avx') {
                const geoLat = this.getChildText(child, 'geoLat');
                const geoLong = this.getChildText(child, 'geoLong');
                
                if (geoLat && geoLong) {
                    const lat = this.parseCoordinate(geoLat);
                    const lon = this.parseCoordinate(geoLong);
                    if (lat !== null && lon !== null) {
                        points.push([lat, lon]);
                    }
                }
            }
        }
        
        return points;
    }

    extractAirspaces() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Ase') {
                // Get the AseUid to build lookup key
                let polygon = null;
                const aseUid = this.getChildElement(elem, 'AseUid');
                if (aseUid) {
                    // Try to get mid attribute first (primary linking key)
                    const mid = aseUid.getAttribute('mid');
                    const codeId = this.getChildText(aseUid, 'codeId');
                    const codeType = this.getChildText(aseUid, 'codeType');
                    
                    // Look up by mid first, then by codeId|codeType
                    if (mid && this.airspaceBorders[mid]) {
                        polygon = this.airspaceBorders[mid];
                    } else if (codeId) {
                        const key = codeType ? `${codeId}|${codeType}` : codeId;
                        if (this.airspaceBorders[key]) {
                            polygon = this.airspaceBorders[key];
                        }
                    }
                }
                
                // Fallback: try to extract polygon directly from element
                if (!polygon) {
                    polygon = this.extractPolygon(elem);
                }
                
                const feature = {
                    type: 'airspace',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(aseUid, 'codeId'),
                    codeType: this.getChildText(aseUid, 'codeType'),
                    txtName: this.getChildText(elem, 'txtName'),
                    txtRmk: this.getChildText(elem, 'txtRmk'),
                    polygon: polygon
                };
                this.features.push(feature);
            }
        }
    }

    extractAirports() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Ahp') {
                const feature = {
                    type: 'airport',
                    mid: this.getAttribute(elem, 'mid'),
                    icao: this.getChildText(elem, 'codeId'),
                    iata: this.getChildText(elem, 'codeIata'),
                    name: this.getChildText(elem, 'txtName'),
                    city: this.getChildText(elem, 'txtNameCity'),
                    position: this.extractPosition(elem),
                    elevation: this.getChildText(elem, 'valElev')
                };
                this.features.push(feature);
            }
        }
    }

    extractWaypoints() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Dpn') {
                const codeId = this.getChildText(elem, 'codeId');
                const position = this.extractPosition(elem);
                
                const feature = {
                    type: 'waypoint',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: codeId,
                    codeType: this.getChildText(elem, 'codeType'),
                    position: position
                };
                this.features.push(feature);
                
                // Store waypoint position for route rendering
                if (codeId && position) {
                    this.waypointPositions[codeId] = position;
                }
            }
        }
    }

    extractNavaids() {
        const types = ['Vor', 'Ndb', 'Dme', 'Tcn'];
        const elements = this.xmlDoc.getElementsByTagName('*');
        
        for (let elem of elements) {
            const tagName = this.getLocalTagName(elem);
            if (types.includes(tagName)) {
                const codeId = this.getChildText(elem, 'codeId');
                const position = this.extractPosition(elem);
                
                const feature = {
                    type: tagName.toLowerCase(),
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: codeId,
                    name: this.getChildText(elem, 'txtName'),
                    frequency: this.getChildText(elem, 'valFreq'),
                    channel: this.getChildText(elem, 'codeChannel'),
                    position: position
                };
                this.features.push(feature);
                
                // Store VOR position for route rendering
                if (tagName === 'Vor' && codeId && position) {
                    this.waypointPositions[codeId] = position;
                }
            }
        }
    }

    /**
     * Extract route segments (Rsg elements) and store them indexed by route key
     */
    extractRouteSegments() {
        const elements = this.xmlDoc.getElementsByTagName('*');

        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Rsg') {
                // Get the RsgUid to find the parent route
                const rsgUid = this.getChildElement(elem, 'RsgUid');
                if (!rsgUid) continue;

                // Get parent route reference
                const rteUid = this.getChildElement(rsgUid, 'RteUid');
                if (!rteUid) continue;

                const routeCodeId = this.getChildText(rteUid, 'codeId');
                const routeCodeType = this.getChildText(rteUid, 'codeType');
                if (!routeCodeId) continue;

                // Build route key
                const routeKey = routeCodeType ? `${routeCodeId}|${routeCodeType}` : routeCodeId;

                // Get start waypoint reference
                let startPointId = null;
                let startPointType = null;
                const dpnUidStart = this.getChildElement(rsgUid, 'DpnUidSta') || this.getChildElement(rsgUid, 'DpnUidStart');
                if (dpnUidStart) {
                    startPointId = this.getChildText(dpnUidStart, 'codeId');
                    startPointType = 'waypoint';
                }
                // Fallback to VorUidEnd for start
                if (!startPointId) {
                    const vorUidStart = this.getChildElement(rsgUid, 'VorUidSta') || this.getChildElement(rsgUid, 'VorUidStart');
                    if (vorUidStart) {
                        startPointId = this.getChildText(vorUidStart, 'codeId');
                        startPointType = 'vor';
                    }
                }

                // Get end waypoint reference
                let endPointId = null;
                let endPointType = null;
                const dpnUidEnd = this.getChildElement(rsgUid, 'DpnUidEnd');
                if (dpnUidEnd) {
                    endPointId = this.getChildText(dpnUidEnd, 'codeId');
                    endPointType = 'waypoint';
                }
                // Fallback to VorUidEnd
                if (!endPointId) {
                    const vorUidEnd = this.getChildElement(rsgUid, 'VorUidEnd');
                    if (vorUidEnd) {
                        endPointId = this.getChildText(vorUidEnd, 'codeId');
                        endPointType = 'vor';
                    }
                }

                // Create segment object
                const segment = {
                    startPointId: startPointId,
                    startPointType: startPointType,
                    endPointId: endPointId,
                    endPointType: endPointType,
                    pathType: this.getChildText(elem, 'codeType'),
                    length: this.getChildText(elem, 'valLen'),
                    lengthUnit: this.getChildText(elem, 'uomDist')
                };

                // Add to route segments map
                if (!this.routeSegments[routeKey]) {
                    this.routeSegments[routeKey] = [];
                }
                this.routeSegments[routeKey].push(segment);
            }
        }
    }

    extractRoutes() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Rte') {
                // Get route identifier
                const rteUid = this.getChildElement(elem, 'RteUid');
                const codeId = rteUid ? this.getChildText(rteUid, 'codeId') : null;
                const codeType = rteUid ? this.getChildText(rteUid, 'codeType') : null;

                // Build route key to find associated segments
                const routeKey = codeId ? (codeType ? `${codeId}|${codeType}` : codeId) : null;
                const segments = routeKey && this.routeSegments[routeKey] ? this.routeSegments[routeKey] : [];

                const feature = {
                    type: 'route',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: codeId,
                    codeType: codeType,
                    designator: this.getChildText(elem, 'txtDesig'),
                    routeType: this.getChildText(elem, 'codeType'),
                    segments: segments
                };
                this.features.push(feature);
            }
        }
    }

    extractBorders() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Gbr') {
                const feature = {
                    type: 'border',
                    mid: this.getAttribute(elem, 'mid'),
                    name: this.getChildText(elem, 'txtName'),
                    borderType: this.getChildText(elem, 'codeType'),
                    polygon: this.extractPolygon(elem)
                };
                this.features.push(feature);
            }
        }
    }

    extractOrganizations() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Org') {
                const feature = {
                    type: 'organization',
                    mid: this.getAttribute(elem, 'mid'),
                    name: this.getChildText(elem, 'txtName'),
                    icao: this.getChildText(elem, 'codeId')
                };
                this.features.push(feature);
            }
        }
    }

    extractRunways() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Rwy') {
                const feature = {
                    type: 'runway',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    length: this.getChildText(elem, 'valLen'),
                    width: this.getChildText(elem, 'valWid')
                };
                this.features.push(feature);
            }
        }
    }

    extractTaxiways() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Twy') {
                const feature = {
                    type: 'taxiway',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    width: this.getChildText(elem, 'valWid')
                };
                this.features.push(feature);
            }
        }
    }

    extractAprons() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Apn') {
                const feature = {
                    type: 'apron',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId')
                };
                this.features.push(feature);
            }
        }
    }

    extractServices() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Ser') {
                const feature = {
                    type: 'service',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    serviceType: this.getChildText(elem, 'codeType')
                };
                this.features.push(feature);
            }
        }
    }

    extractFrequencies() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Fqy') {
                const feature = {
                    type: 'frequency',
                    mid: this.getAttribute(elem, 'mid'),
                    frequency: this.getChildText(elem, 'valFreqTrans'),
                    freqType: this.getChildText(elem, 'codeType')
                };
                this.features.push(feature);
            }
        }
    }

    extractUnits() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Uni') {
                const feature = {
                    type: 'unit',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    name: this.getChildText(elem, 'txtName'),
                    unitType: this.getChildText(elem, 'codeType')
                };
                this.features.push(feature);
            }
        }
    }

    extractSIDs() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Sid') {
                const feature = {
                    type: 'sid',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    designator: this.getChildText(elem, 'txtDesig')
                };
                this.features.push(feature);
            }
        }
    }

    extractSTARs() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Sia') {
                const feature = {
                    type: 'star',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    designator: this.getChildText(elem, 'txtDesig')
                };
                this.features.push(feature);
            }
        }
    }

    extractApproaches() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Iap') {
                const feature = {
                    type: 'approach',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    designator: this.getChildText(elem, 'txtDesig')
                };
                this.features.push(feature);
            }
        }
    }

    extractILS() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Ils') {
                const feature = {
                    type: 'ils',
                    mid: this.getAttribute(elem, 'mid'),
                    category: this.getChildText(elem, 'codeCatIls')
                };
                this.features.push(feature);
            }
        }
    }

    extractMarkers() {
        const elements = this.xmlDoc.getElementsByTagName('*');
        for (let elem of elements) {
            if (this.getLocalTagName(elem) === 'Mkr') {
                const feature = {
                    type: 'marker',
                    mid: this.getAttribute(elem, 'mid'),
                    codeId: this.getChildText(elem, 'codeId'),
                    markerType: this.getChildText(elem, 'codeTypeMkr'),
                    position: this.extractPosition(elem)
                };
                this.features.push(feature);
            }
        }
    }

    /**
     * Get summary of parsed data
     */
    getSummary() {
        return {
            totalFeatures: this.features.length,
            elementCounts: this.elementCounts,
            features: this.features
        };
    }

    /**
     * Get features by type
     */
    getFeaturesByType(type) {
        return this.features.filter(f => f.type === type);
    }

    /**
     * Get all element types present
     */
    getElementTypes() {
        return Object.keys(this.elementCounts);
    }

    /**
     * Filter features by element types
     */
    filterByTypes(types, mode = 'include') {
        if (mode === 'include') {
            return this.features.filter(f => types.includes(f.type));
        } else {
            return this.features.filter(f => !types.includes(f.type));
        }
    }

    /**
     * Export features to GeoJSON
     */
    toGeoJSON(features = null) {
        const data = features || this.features;
        
        const geojson = {
            type: 'FeatureCollection',
            features: []
        };

        for (let feature of data) {
            const geoFeature = this.featureToGeoJSON(feature);
            if (geoFeature) {
                geojson.features.push(geoFeature);
            }
        }

        return geojson;
    }

    /**
     * Convert single feature to GeoJSON
     */
    featureToGeoJSON(feature) {
        let geometry = null;

        if (feature.position) {
            geometry = {
                type: 'Point',
                coordinates: [feature.position.lon, feature.position.lat]
            };
        } else if (feature.polygon && feature.polygon.length > 0) {
            const coords = feature.polygon.map(p => [p[1], p[0]]); // [lon, lat]
            if (coords.length > 2) {
                geometry = {
                    type: 'Polygon',
                    coordinates: [coords]
                };
            }
        }

        if (!geometry) return null;

        return {
            type: 'Feature',
            properties: { ...feature },
            geometry: geometry
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIXMParser;
}
