/**
 * AIXM Parser - Browser-based AIXM 4.5 Parser
 *
 * Parses AIXM 4.5-r2 XML snapshots in the browser using DOMParser.
 * Supports all 23 original element types plus Rdn, Aas, Obs, Hpe, Mgp, Apg.
 * Correctly handles arc (CWA/CCA) and circular airspace geometry.
 */

class AIXMParser {
    constructor() {
        this.features = [];
        this.airspaceBorders = {};   // mid or 'codeId|codeType' -> [[lat,lon], ...]
        this.waypointPositions = {}; // codeId -> {lat, lon}
        this.navaidPositions = {};   // codeId -> {lat, lon}
        this.stats = {};
        this._xmlDoc = null;
    }

    // ─────────────────────────── XML helpers ──────────────────────────────

    /**
     * Get the first DIRECT child element with the given tag name.
     * Avoids getElementsByTagName which searches all descendants.
     */
    getChildElement(parent, tagName) {
        if (!parent) return null;
        for (const child of parent.children) {
            if (child.tagName === tagName) return child;
        }
        return null;
    }

    /** Get text content of a direct child element, or fallback. */
    getChildText(parent, tagName, fallback = '') {
        const el = this.getChildElement(parent, tagName);
        return el ? (el.textContent || '').trim() : fallback;
    }

    /**
     * Recursive descendant search — use sparingly and only when the target
     * element is guaranteed unique within the subtree.
     */
    findDescendantText(parent, tagName, fallback = '') {
        if (!parent) return fallback;
        const els = parent.getElementsByTagName(tagName);
        return els.length > 0 ? (els[0].textContent || '').trim() : fallback;
    }

    findDescendantElement(parent, tagName) {
        if (!parent) return null;
        const els = parent.getElementsByTagName(tagName);
        return els.length > 0 ? els[0] : null;
    }

    // ─────────────────────────── Coordinate parsing ────────────────────────

    /**
     * Parse an AIXM coordinate string to decimal degrees.
     * Handles:
     *   - DDMMSS[.ss]N/S/E/W  (e.g. "340600N", "0163411E", "510520.60N")
     *   - DDMM[.mm]N/S/E/W    (e.g. "3406N")
     *   - Decimal degrees      (e.g. "34.1", "-120.5")
     */
    parseCoordinate(coord) {
        if (!coord) return null;
        coord = coord.trim();
        if (!coord) return null;

        // Try DMS/DM with compass direction: optional decimal seconds
        const dmsMatch = coord.match(/^(\d{2,3})(\d{2})(\d{2}(?:\.\d+)?)([NSEW])$/i);
        if (dmsMatch) {
            const deg = parseInt(dmsMatch[1], 10);
            const min = parseInt(dmsMatch[2], 10);
            const sec = parseFloat(dmsMatch[3]);
            const dir = dmsMatch[4].toUpperCase();
            let decimal = deg + min / 60 + sec / 3600;
            if (dir === 'S' || dir === 'W') decimal = -decimal;
            return decimal;
        }

        // Try DM only (no seconds)
        const dmMatch = coord.match(/^(\d{2,3})(\d{2}(?:\.\d+)?)([NSEW])$/i);
        if (dmMatch) {
            const deg = parseInt(dmMatch[1], 10);
            const min = parseFloat(dmMatch[2]);
            const dir = dmMatch[3].toUpperCase();
            let decimal = deg + min / 60;
            if (dir === 'S' || dir === 'W') decimal = -decimal;
            return decimal;
        }

        // Try plain decimal
        const val = parseFloat(coord);
        if (!isNaN(val)) return val;
        return null;
    }

    parseLatLon(latStr, lonStr) {
        const lat = this.parseCoordinate(latStr);
        const lon = this.parseCoordinate(lonStr);
        if (lat === null || lon === null) return null;
        if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
        return { lat, lon };
    }

    // ─────────────────────────── Geometry helpers ─────────────────────────

    /** Convert nautical miles to approximate decimal degrees (any direction). */
    nmToMeters(nm) { return nm * 1852; }

    /**
     * Interpolate points along an arc on the earth's surface.
     * @param {number} startLat - arc start latitude (deg)
     * @param {number} startLon - arc start longitude (deg)
     * @param {number} centerLat - arc center latitude (deg)
     * @param {number} centerLon - arc center longitude (deg)
     * @param {boolean} clockwise - CWA = true, CCA = false
     * @param {number} endLat - arc end latitude (deg)
     * @param {number} endLon - arc end longitude (deg)
     * @param {number} numPts - number of interpolation steps
     * @returns {Array<[number,number]>} interpolated points [lat, lon]
     */
    interpolateArc(startLat, startLon, centerLat, centerLon, clockwise, endLat, endLon, numPts = 32) {
        const toRad = d => d * Math.PI / 180;
        const toDeg = r => r * 180 / Math.PI;

        const bearing = (fromLat, fromLon, toLat, toLon) => {
            const lat1 = toRad(fromLat), lat2 = toRad(toLat);
            const dLon = toRad(toLon - fromLon);
            const x = Math.sin(dLon) * Math.cos(lat2);
            const y = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
            return (toDeg(Math.atan2(x, y)) + 360) % 360;
        };

        const destinationPoint = (lat, lon, brg, distNM) => {
            const R = 3440.065; // Earth radius in NM
            const δ = distNM / R;
            const φ1 = toRad(lat), λ1 = toRad(lon), θ = toRad(brg);
            const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
            const λ2 = λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2));
            return [toDeg(φ2), toDeg(λ2)];
        };

        const distNM = (lat1, lon1, lat2, lon2) => {
            const R = 3440.065;
            const φ1 = toRad(lat1), φ2 = toRad(lat2);
            const Δφ = toRad(lat2 - lat1), Δλ = toRad(lon2 - lon1);
            const a = Math.sin(Δφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        };

        const radius = distNM(centerLat, centerLon, startLat, startLon);
        let startBrg = bearing(centerLat, centerLon, startLat, startLon);
        let endBrg = bearing(centerLat, centerLon, endLat, endLon);

        let sweep;
        if (clockwise) {
            sweep = endBrg >= startBrg ? endBrg - startBrg : 360 - startBrg + endBrg;
        } else {
            sweep = startBrg >= endBrg ? startBrg - endBrg : 360 - endBrg + startBrg;
        }
        if (sweep < 1) sweep = 360; // full circle fallback

        const pts = [];
        for (let i = 0; i <= numPts; i++) {
            const angle = clockwise
                ? (startBrg + (sweep * i / numPts)) % 360
                : (startBrg - (sweep * i / numPts) + 360) % 360;
            pts.push(destinationPoint(centerLat, centerLon, angle, radius));
        }
        return pts;
    }

    /**
     * Interpolate points forming a full circle.
     * @param {number} centerLat
     * @param {number} centerLon
     * @param {number} radiusNM
     * @param {number} numPts
     * @returns {Array<[number,number]>}
     */
    interpolateCircle(centerLat, centerLon, radiusNM, numPts = 72) {
        const toRad = d => d * Math.PI / 180;
        const toDeg = r => r * 180 / Math.PI;
        const R = 3440.065;
        const δ = radiusNM / R;
        const φ1 = toRad(centerLat);
        const λ1 = toRad(centerLon);
        const pts = [];
        for (let i = 0; i <= numPts; i++) {
            const θ = toRad((360 * i) / numPts);
            const φ2 = Math.asin(Math.sin(φ1) * Math.cos(δ) + Math.cos(φ1) * Math.sin(δ) * Math.cos(θ));
            const λ2 = λ1 + Math.atan2(Math.sin(θ) * Math.sin(δ) * Math.cos(φ1), Math.cos(δ) - Math.sin(φ1) * Math.sin(φ2));
            pts.push([toDeg(φ2), toDeg(λ2)]);
        }
        return pts;
    }

    // ─────────────────────────── File loading ──────────────────────────────

    async parseFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const xmlText = e.target.result;
                    this.parseXML(xmlText);
                    resolve(this.features);
                } catch (err) {
                    reject(err);
                }
            };
            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsText(file);
        });
    }

    parseXML(xmlText) {
        const parser = new DOMParser();
        this._xmlDoc = parser.parseFromString(xmlText, 'text/xml');

        const parseError = this._xmlDoc.querySelector('parsererror');
        if (parseError) throw new Error('XML parse error: ' + parseError.textContent);

        this.features = [];
        this.airspaceBorders = {};
        this.waypointPositions = {};
        this.navaidPositions = {};
        this.stats = {};

        this.extractFeatures();
        this.buildStats();
    }

    // ─────────────────────────── Element extraction ────────────────────────

    extractFeatures() {
        // Pass 1: index borders and positions before linking
        this.extractAirspaceBorders();
        this.extractWaypointPositions();
        this.extractNavaidPositions();

        // Pass 2: main feature extraction
        this.extractAirspaces();
        this.extractAirports();
        this.extractWaypoints();
        this.extractVORs();
        this.extractNDBs();
        this.extractDMEs();
        this.extractTACANs();
        this.extractRoutes();
        this.extractBorders();
        this.extractOrganizations();
        this.extractRunways();
        this.extractRunwayDirections();
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
        this.extractObstacles();
        this.extractHoldings();
        this.extractMSAGroups();
        this.extractAirspaceAssociations();
        this.extractApronGeometries();
    }

    // ─── Pass-1 indexers ──────────────────────────────────────────────────

    /**
     * Build waypointPositions index from all Dpn elements.
     */
    extractWaypointPositions() {
        const elems = this._xmlDoc.getElementsByTagName('Dpn');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'DpnUid');
            if (!uid) continue;
            const codeId = this.getChildText(uid, 'codeId');
            const lat = this.getChildText(elem, 'geoLat');
            const lon = this.getChildText(elem, 'geoLong');
            const pos = this.parseLatLon(lat, lon);
            if (codeId && pos) this.waypointPositions[codeId] = pos;
        }
    }

    /**
     * Build navaidPositions index from VOR, NDB, DME, TACAN.
     */
    extractNavaidPositions() {
        const types = [
            { tag: 'Vor', uidTag: 'VorUid' },
            { tag: 'Ndb', uidTag: 'NdbUid' },
            { tag: 'Dme', uidTag: 'DmeUid' },
            { tag: 'Tcn', uidTag: 'TcnUid' },
        ];
        for (const { tag, uidTag } of types) {
            const elems = this._xmlDoc.getElementsByTagName(tag);
            for (const elem of elems) {
                const uid = this.getChildElement(elem, uidTag);
                if (!uid) continue;
                const codeId = this.getChildText(uid, 'codeId');
                const lat = this.getChildText(elem, 'geoLat');
                const lon = this.getChildText(elem, 'geoLong');
                const pos = this.parseLatLon(lat, lon);
                if (codeId && pos) this.navaidPositions[codeId] = pos;
            }
        }
    }

    /**
     * Extract all Abd (AirspaceBorder) elements and build the border lookup.
     * Indexed by: mid attribute AND 'codeId|codeType' of the referenced AseUid.
     */
    extractAirspaceBorders() {
        const elems = this._xmlDoc.getElementsByTagName('Abd');
        for (const elem of elems) {
            const abdUid = this.getChildElement(elem, 'AbdUid');
            if (!abdUid) continue;
            const mid = elem.getAttribute('mid') || abdUid.getAttribute('mid') || '';
            const aseUid = this.getChildElement(abdUid, 'AseUid');

            let codeIdKey = '';
            let codeTypeKey = '';
            if (aseUid) {
                codeIdKey = this.getChildText(aseUid, 'codeId');
                codeTypeKey = this.getChildText(aseUid, 'codeType');
            }
            const aseMid = aseUid ? (aseUid.getAttribute('mid') || '') : '';

            // Try Circle first
            const circleEl = this.getChildElement(elem, 'Circle');
            let polygon = null;
            if (circleEl) {
                polygon = this.extractCirclePolygon(circleEl);
            } else {
                polygon = this.extractAbdPolygon(elem);
            }

            if (!polygon || polygon.length < 3) continue;

            // Store under multiple keys for fallback lookup
            if (mid) this.airspaceBorders[mid] = polygon;
            if (aseMid) this.airspaceBorders[aseMid] = polygon;
            if (codeIdKey && codeTypeKey) {
                this.airspaceBorders[`${codeIdKey}|${codeTypeKey}`] = polygon;
            }
            if (codeIdKey) this.airspaceBorders[codeIdKey] = polygon;
        }
    }

    /**
     * Extract polygon from an Abd element using Avx children.
     * Handles GRC, RHL (straight lines) and CWA, CCA (arcs).
     */
    extractAbdPolygon(abdElem) {
        const avxList = abdElem.getElementsByTagName('Avx');
        if (!avxList.length) return null;

        const polygon = [];
        let prevLat = null, prevLon = null;

        for (const avx of avxList) {
            const codeType = this.getChildText(avx, 'codeType');
            const lat = this.parseCoordinate(this.getChildText(avx, 'geoLat'));
            const lon = this.parseCoordinate(this.getChildText(avx, 'geoLong'));

            if (lat === null || lon === null) continue;

            if ((codeType === 'CWA' || codeType === 'CCA') && prevLat !== null) {
                // Arc vertex — interpolate arc from previous point to this one
                const arcLatStr = this.getChildText(avx, 'geoLatArc');
                const arcLonStr = this.getChildText(avx, 'geoLongArc');
                const arcLat = this.parseCoordinate(arcLatStr);
                const arcLon = this.parseCoordinate(arcLonStr);

                if (arcLat !== null && arcLon !== null) {
                    const arcPts = this.interpolateArc(
                        prevLat, prevLon,
                        arcLat, arcLon,
                        codeType === 'CWA',
                        lat, lon
                    );
                    // Skip first point (already in polygon from previous iteration)
                    for (let i = 1; i < arcPts.length; i++) polygon.push(arcPts[i]);
                } else {
                    // No center available — add endpoint as straight-line fallback
                    polygon.push([lat, lon]);
                }
            } else if (codeType === 'END') {
                // Close the polygon — push the endpoint but stop
                polygon.push([lat, lon]);
                break;
            } else {
                // GRC / RHL / FNT — straight line to this vertex
                polygon.push([lat, lon]);
            }

            prevLat = lat;
            prevLon = lon;
        }

        return polygon.length >= 3 ? polygon : null;
    }

    /**
     * Extract circular airspace polygon from an Abd's Circle child.
     * AirspaceCircularVertexType: geoLat, geoLong, valRadius, uomRadius
     */
    extractCirclePolygon(circleElem) {
        const centerLat = this.parseCoordinate(this.getChildText(circleElem, 'geoLat'));
        const centerLon = this.parseCoordinate(this.getChildText(circleElem, 'geoLong'));
        const radiusStr = this.getChildText(circleElem, 'valRadius');
        const uom = this.getChildText(circleElem, 'uomRadius').toUpperCase();

        if (centerLat === null || centerLon === null || !radiusStr) return null;

        let radiusNM = parseFloat(radiusStr);
        if (isNaN(radiusNM)) return null;

        // Convert to NM if needed
        if (uom === 'KM') radiusNM = radiusNM / 1.852;
        else if (uom === 'M') radiusNM = radiusNM / 1852;
        // uom === 'NM' is already correct

        return this.interpolateCircle(centerLat, centerLon, radiusNM);
    }

    // ─── Airspaces ────────────────────────────────────────────────────────

    extractAirspaces() {
        const elems = this._xmlDoc.getElementsByTagName('Ase');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'AseUid');
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const codeId = this.getChildText(uid, 'codeId');
            const codeType = this.getChildText(uid, 'codeType');

            // Find border by multiple keys
            const keys = [mid, `${codeId}|${codeType}`, codeId];
            let polygon = null;
            for (const k of keys) {
                if (k && this.airspaceBorders[k]) { polygon = this.airspaceBorders[k]; break; }
            }

            const feature = {
                type: 'airspace',
                mid,
                codeId,
                codeType,
                txtName: this.getChildText(elem, 'txtName'),
                txtLocalType: this.getChildText(elem, 'txtLocalType'),
                codeMil: this.getChildText(elem, 'codeMil'),
                // Vertical limits
                valDistVerLower: this.getChildText(elem, 'valDistVerLower'),
                uomDistVerLower: this.getChildText(elem, 'uomDistVerLower'),
                codeDistVerLower: this.getChildText(elem, 'codeDistVerLower'),
                valDistVerUpper: this.getChildText(elem, 'valDistVerUpper'),
                uomDistVerUpper: this.getChildText(elem, 'uomDistVerUpper'),
                codeDistVerUpper: this.getChildText(elem, 'codeDistVerUpper'),
                polygon,
            };
            this.features.push(feature);
        }
    }

    // ─── Airports ─────────────────────────────────────────────────────────

    extractAirports() {
        const elems = this._xmlDoc.getElementsByTagName('Ahp');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'AhpUid');
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const codeId = this.getChildText(uid, 'codeId'); // Location designator (UID key)
            const lat = this.getChildText(elem, 'geoLat');
            const lon = this.getChildText(elem, 'geoLong');
            const position = this.parseLatLon(lat, lon);

            this.features.push({
                type: 'airport',
                mid,
                codeId,
                icao: this.getChildText(elem, 'codeIcao') || codeId,
                iata: this.getChildText(elem, 'codeIata'),
                codeType: this.getChildText(elem, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
                city: this.getChildText(elem, 'txtNameCitySer'),
                valElev: this.getChildText(elem, 'valElev'),
                uomDistVer: this.getChildText(elem, 'uomDistVer'),
                valMagVar: this.getChildText(elem, 'valMagVar'),
                position,
            });
        }
    }

    // ─── Waypoints ────────────────────────────────────────────────────────

    extractWaypoints() {
        const elems = this._xmlDoc.getElementsByTagName('Dpn');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'DpnUid');
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const codeId = this.getChildText(uid, 'codeId');
            const lat = this.getChildText(elem, 'geoLat');
            const lon = this.getChildText(elem, 'geoLong');
            const position = this.parseLatLon(lat, lon);

            this.features.push({
                type: 'waypoint',
                mid,
                codeId,
                codeType: this.getChildText(uid, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
                position,
            });
        }
    }

    // ─── Navaids ─────────────────────────────────────────────────────────

    extractNavaidGeneric(tag, uidTag, typeName, extraFields = []) {
        const elems = this._xmlDoc.getElementsByTagName(tag);
        for (const elem of elems) {
            const uid = this.getChildElement(elem, uidTag);
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const codeId = this.getChildText(uid, 'codeId');
            const lat = this.getChildText(elem, 'geoLat');
            const lon = this.getChildText(elem, 'geoLong');
            const position = this.parseLatLon(lat, lon);

            const feature = {
                type: typeName,
                mid,
                codeId,
                codeType: this.getChildText(uid, 'codeType') || this.getChildText(elem, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
                valFreq: this.getChildText(elem, 'valFreq'),
                uomFreq: this.getChildText(elem, 'uomFreq'),
                valMagVar: this.getChildText(elem, 'valMagVar'),
                position,
            };
            for (const f of extraFields) {
                feature[f] = this.getChildText(elem, f);
            }
            this.features.push(feature);
        }
    }

    extractVORs()   { this.extractNavaidGeneric('Vor', 'VorUid', 'vor', ['codeType', 'valDeclination']); }
    extractNDBs()   { this.extractNavaidGeneric('Ndb', 'NdbUid', 'ndb'); }
    extractDMEs()   { this.extractNavaidGeneric('Dme', 'DmeUid', 'dme', ['codeChannel']); }
    extractTACANs() { this.extractNavaidGeneric('Tcn', 'TcnUid', 'tacan', ['codeChannel', 'valDeclination']); }

    // ─── Routes ───────────────────────────────────────────────────────────

    extractRoutes() {
        // Build segment index keyed by 'codeId|codeType'
        const segIndex = this.buildRouteSegmentIndex();

        const elems = this._xmlDoc.getElementsByTagName('Rte');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'RteUid');
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const codeId = this.getChildText(uid, 'codeId');
            const codeType = this.getChildText(uid, 'codeType');
            const key = `${codeId}|${codeType}`;
            const segments = segIndex[key] || segIndex[codeId] || [];

            this.features.push({
                type: 'route',
                mid,
                codeId,
                codeType,
                txtDesig: this.getChildText(elem, 'txtDesig') || codeId,
                txtName: this.getChildText(elem, 'txtName'),
                segments,
                // Resolve positions for renderer
                waypointPositions: this.waypointPositions,
                navaidPositions: this.navaidPositions,
            });
        }
    }

    buildRouteSegmentIndex() {
        const index = {};
        const segs = this._xmlDoc.getElementsByTagName('Rsg');
        for (const seg of segs) {
            const segUid = this.getChildElement(seg, 'RsgUid');
            if (!segUid) continue;

            const rteUid = this.getChildElement(segUid, 'RteUid');
            if (!rteUid) continue;
            const rteCid = this.getChildText(rteUid, 'codeId');
            const rteCtype = this.getChildText(rteUid, 'codeType');
            const key = `${rteCid}|${rteCtype}`;

            // Start point
            const startPos = this.extractSegmentPoint(segUid, 'start');
            const endPos = this.extractSegmentPoint(segUid, 'end');

            const segment = {
                startPointId: startPos.codeId,
                startPosition: startPos.position,
                endPointId: endPos.codeId,
                endPosition: endPos.position,
                codeTypePath: this.getChildText(seg, 'codeTypePath'),
                valLen: this.getChildText(seg, 'valLen'),
                uomLen: this.getChildText(seg, 'uomLen'),
            };

            if (!index[key]) index[key] = [];
            index[key].push(segment);
            if (!index[rteCid]) index[rteCid] = [];
            index[rteCid].push(segment);
        }
        return index;
    }

    /**
     * Extract start or end point from RsgUid.
     * SignificantPointGroupStart/End has: DpnUidSta, VorUidSta, NdbUidSta, DpnUidEnd, VorUidEnd, etc.
     */
    extractSegmentPoint(rsgUid, which) {
        const suffix = which === 'start' ? 'Sta' : 'End';
        const tags = ['Dpn', 'Vor', 'Ndb', 'Dme', 'Tcn'];
        let codeId = '';
        let position = null;

        for (const tag of tags) {
            const uidElem = this.getChildElement(rsgUid, `${tag}Uid${suffix}`);
            if (uidElem) {
                codeId = this.getChildText(uidElem, 'codeId');
                const inlineLat = this.getChildText(uidElem, 'geoLat');
                const inlineLon = this.getChildText(uidElem, 'geoLong');
                position = this.parseLatLon(inlineLat, inlineLon);
                if (!position) {
                    // Fall back to pre-built position indexes
                    position = this.waypointPositions[codeId] || this.navaidPositions[codeId] || null;
                }
                break;
            }
        }
        return { codeId, position };
    }

    // ─── Geographic Borders ───────────────────────────────────────────────

    extractBorders() {
        const elems = this._xmlDoc.getElementsByTagName('Gbr');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'GbrUid');
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const codeId = this.getChildText(uid, 'codeId');
            const polygon = this.extractGbvPolygon(elem);

            this.features.push({
                type: 'border',
                mid,
                codeId,
                txtName: this.getChildText(elem, 'txtName'),
                codeType: this.getChildText(elem, 'codeType'),
                polygon,
            });
        }
    }

    /**
     * Extract polygon from a Gbr element using its Gbv children.
     * GeographicalBorderVertexType: codeType, geoLat, geoLong
     */
    extractGbvPolygon(gbrElem) {
        const gbvList = gbrElem.getElementsByTagName('Gbv');
        if (!gbvList.length) return null;

        const polygon = [];
        for (const gbv of gbvList) {
            const lat = this.parseCoordinate(this.getChildText(gbv, 'geoLat'));
            const lon = this.parseCoordinate(this.getChildText(gbv, 'geoLong'));
            if (lat !== null && lon !== null) polygon.push([lat, lon]);
        }
        return polygon.length >= 2 ? polygon : null;
    }

    // ─── Organizations ────────────────────────────────────────────────────

    extractOrganizations() {
        const elems = this._xmlDoc.getElementsByTagName('Org');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'OrgUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            this.features.push({
                type: 'organization',
                mid,
                codeId: this.getChildText(uid, 'codeId'),
                codeType: this.getChildText(uid, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
            });
        }
    }

    // ─── Runways ──────────────────────────────────────────────────────────

    extractRunways() {
        const elems = this._xmlDoc.getElementsByTagName('Rwy');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'RwyUid');
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const ahpUid = this.getChildElement(uid, 'AhpUid');
            const airportId = ahpUid ? this.getChildText(ahpUid, 'codeId') : '';
            // Correct: designator is RwyUid/codeId, not txtDesig
            const codeId = this.getChildText(uid, 'codeId');

            this.features.push({
                type: 'runway',
                mid,
                codeId,
                airportId,
                txtName: codeId,
                valLen: this.getChildText(elem, 'valLen'),
                valWid: this.getChildText(elem, 'valWid'),
                uomDistHorz: this.getChildText(elem, 'uomDistHorz'),
                codeComposition: this.getChildText(elem, 'codeComposition'),
            });
        }
    }

    // ─── Runway Directions (NEW) ──────────────────────────────────────────

    extractRunwayDirections() {
        const elems = this._xmlDoc.getElementsByTagName('Rdn');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'RdnUid');
            if (!uid) continue;

            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const rwyUid = this.getChildElement(uid, 'RwyUid');
            const ahpUid = rwyUid ? this.getChildElement(rwyUid, 'AhpUid') : null;
            const airportId = ahpUid ? this.getChildText(ahpUid, 'codeId') : '';
            const rwyDesig = rwyUid ? this.getChildText(rwyUid, 'codeId') : '';
            const codeId = this.getChildText(uid, 'txtDesig') || rwyDesig;

            // Threshold position
            const thresholdLat = this.getChildText(elem, 'geoLat');
            const thresholdLon = this.getChildText(elem, 'geoLong');
            const position = this.parseLatLon(thresholdLat, thresholdLon);

            this.features.push({
                type: 'runway_direction',
                mid,
                codeId,
                airportId,
                txtName: codeId,
                valTrueBrg: this.getChildText(elem, 'valTrueBrg'),
                valMagBrg: this.getChildText(elem, 'valMagBrg'),
                valElevTdz: this.getChildText(elem, 'valElevTdz'),
                position,
            });

            // Also update airport position if airport has no ref point
            if (airportId && position) {
                this.waypointPositions['RWY:' + airportId] = position;
            }
        }
    }

    // ─── Taxiways / Aprons ────────────────────────────────────────────────

    extractGenericInfra(tag, uidTag, typeName) {
        const elems = this._xmlDoc.getElementsByTagName(tag);
        for (const elem of elems) {
            const uid = this.getChildElement(elem, uidTag);
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const ahpUid = this.getChildElement(uid, 'AhpUid');
            const airportId = ahpUid ? this.getChildText(ahpUid, 'codeId') : '';
            this.features.push({
                type: typeName,
                mid,
                codeId: this.getChildText(uid, 'codeId') || this.getChildText(uid, 'txtDesig'),
                airportId,
                txtName: this.getChildText(elem, 'txtName'),
                valLen: this.getChildText(elem, 'valLen'),
                valWid: this.getChildText(elem, 'valWid'),
            });
        }
    }

    extractTaxiways() { this.extractGenericInfra('Twy', 'TwyUid', 'taxiway'); }
    extractAprons()   { this.extractGenericInfra('Apn', 'ApnUid', 'apron'); }

    // ─── Apron Geometries (NEW) ───────────────────────────────────────────

    extractApronGeometries() {
        const elems = this._xmlDoc.getElementsByTagName('Apg');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'ApgUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const apnUid = this.getChildElement(uid, 'ApnUid');
            const ahpUid = apnUid ? this.getChildElement(apnUid, 'AhpUid') : null;
            const airportId = ahpUid ? this.getChildText(ahpUid, 'codeId') : '';

            // Apron geometry may use Avx or a polygon list
            const polygon = this.extractAbdPolygon(elem);

            this.features.push({
                type: 'apron_geometry',
                mid,
                airportId,
                txtName: airportId + ' Apron',
                polygon,
            });
        }
    }

    // ─── Services / Freqs / Units ─────────────────────────────────────────

    extractServices() {
        const elems = this._xmlDoc.getElementsByTagName('Ser');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'SerUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            this.features.push({
                type: 'service',
                mid,
                codeId: this.getChildText(uid, 'codeId'),
                codeType: this.getChildText(uid, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
            });
        }
    }

    extractFrequencies() {
        const elems = this._xmlDoc.getElementsByTagName('Fqy');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'FqyUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            this.features.push({
                type: 'frequency',
                mid,
                codeId: this.getChildText(uid, 'codeId') || this.getChildText(uid, 'noSeq'),
                valFreq: this.getChildText(elem, 'valFreqTrans') || this.getChildText(elem, 'valFreqRec'),
                uomFreq: this.getChildText(elem, 'uomFreq'),
                txtName: this.getChildText(elem, 'txtName'),
            });
        }
    }

    extractUnits() {
        const elems = this._xmlDoc.getElementsByTagName('Uni');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'UniUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            this.features.push({
                type: 'unit',
                mid,
                codeId: this.getChildText(uid, 'codeId'),
                codeType: this.getChildText(uid, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
            });
        }
    }

    // ─── Procedures ───────────────────────────────────────────────────────

    extractProcedureGeneric(tag, uidTag, typeName) {
        const elems = this._xmlDoc.getElementsByTagName(tag);
        for (const elem of elems) {
            const uid = this.getChildElement(elem, uidTag);
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const ahpUid = this.getChildElement(uid, 'AhpUid');
            const airportId = ahpUid ? this.getChildText(ahpUid, 'codeId') : '';
            // Try to get airport position for map placement
            const pos = this.lookupAirportPosition(airportId);
            this.features.push({
                type: typeName,
                mid,
                codeId: this.getChildText(uid, 'codeId'),
                airportId,
                txtName: this.getChildText(elem, 'txtName') || this.getChildText(uid, 'codeId'),
                txtDesig: this.getChildText(uid, 'txtDesig'),
                codeType: this.getChildText(uid, 'codeType'),
                position: pos,
            });
        }
    }

    lookupAirportPosition(airportId) {
        if (!airportId) return null;
        // Find airport feature
        for (const f of this.features) {
            if (f.type === 'airport' && (f.codeId === airportId || f.icao === airportId)) {
                return f.position;
            }
        }
        return null;
    }

    extractSIDs()       { this.extractProcedureGeneric('Sid', 'SidUid', 'sid'); }
    extractSTARs()      { this.extractProcedureGeneric('Sia', 'SiaUid', 'star'); }
    extractApproaches() { this.extractProcedureGeneric('Iap', 'IapUid', 'approach'); }

    // ─── ILS / Markers ────────────────────────────────────────────────────

    extractILS() {
        const elems = this._xmlDoc.getElementsByTagName('Ils');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'IlsUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const lat = this.getChildText(elem, 'geoLat');
            const lon = this.getChildText(elem, 'geoLong');
            const position = this.parseLatLon(lat, lon);
            this.features.push({
                type: 'ils',
                mid,
                codeId: this.getChildText(uid, 'codeId'),
                codeType: this.getChildText(uid, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
                valFreq: this.getChildText(elem, 'valFreq'),
                position,
            });
        }
    }

    extractMarkers() {
        const elems = this._xmlDoc.getElementsByTagName('Mkr');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'MkrUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const lat = this.getChildText(elem, 'geoLat');
            const lon = this.getChildText(elem, 'geoLong');
            const position = this.parseLatLon(lat, lon);
            this.features.push({
                type: 'marker',
                mid,
                codeId: this.getChildText(uid, 'codeId'),
                codeType: this.getChildText(uid, 'codeType'),
                txtName: this.getChildText(elem, 'txtName'),
                position,
            });
        }
    }

    // ─── Obstacles (NEW) ──────────────────────────────────────────────────

    extractObstacles() {
        const elems = this._xmlDoc.getElementsByTagName('Obs');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'ObsUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const lat = this.getChildText(uid, 'geoLat');
            const lon = this.getChildText(uid, 'geoLong');
            const position = this.parseLatLon(lat, lon);
            this.features.push({
                type: 'obstacle',
                mid,
                codeId: this.getChildText(uid, 'codeId') || mid,
                txtName: this.getChildText(elem, 'txtName'),
                codeType: this.getChildText(elem, 'codeType'),
                valElev: this.getChildText(elem, 'valElev'),
                valHgt: this.getChildText(elem, 'valHgt'),
                uomDistVer: this.getChildText(elem, 'uomDistVer'),
                position,
            });
        }
    }

    // ─── Holdings (NEW) ───────────────────────────────────────────────────

    extractHoldings() {
        const elems = this._xmlDoc.getElementsByTagName('Hpe');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'HpeUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';

            // Holding fix may be a Dpn, Vor, or Ndb
            let codeId = '', position = null;
            for (const tag of ['DpnUid', 'VorUid', 'NdbUid']) {
                const fixUid = this.getChildElement(uid, tag);
                if (fixUid) {
                    codeId = this.getChildText(fixUid, 'codeId');
                    position = this.waypointPositions[codeId] || this.navaidPositions[codeId] || null;
                    break;
                }
            }

            this.features.push({
                type: 'holding',
                mid,
                codeId,
                txtName: this.getChildText(elem, 'txtDesig') || codeId,
                valInboundCourse: this.getChildText(elem, 'valInboundCourse'),
                codeStatus: this.getChildText(elem, 'codeStatus'),
                position,
            });
        }
    }

    // ─── MSA Groups (NEW) ─────────────────────────────────────────────────

    extractMSAGroups() {
        const elems = this._xmlDoc.getElementsByTagName('Mgp');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'MgpUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';

            // Center fix (significant point)
            let codeId = '', position = null;
            for (const tag of ['DpnUid', 'VorUid', 'NdbUid']) {
                const fixUid = this.findDescendantElement(uid, tag);
                if (fixUid) {
                    codeId = this.getChildText(fixUid, 'codeId');
                    position = this.waypointPositions[codeId] || this.navaidPositions[codeId] || null;
                    break;
                }
            }

            this.features.push({
                type: 'msa_group',
                mid,
                codeId,
                txtName: 'MSA ' + (codeId || mid),
                position,
            });
        }
    }

    // ─── Airspace Associations (NEW) ─────────────────────────────────────

    extractAirspaceAssociations() {
        const elems = this._xmlDoc.getElementsByTagName('Aas');
        for (const elem of elems) {
            const uid = this.getChildElement(elem, 'AasUid');
            if (!uid) continue;
            const mid = elem.getAttribute('mid') || uid.getAttribute('mid') || '';
            const childUid = this.getChildElement(uid, 'AseUidChi');
            const parentUid = this.getChildElement(uid, 'AseUidPar');
            this.features.push({
                type: 'airspace_assoc',
                mid,
                childId: childUid ? this.getChildText(childUid, 'codeId') : '',
                parentId: parentUid ? this.getChildText(parentUid, 'codeId') : '',
                txtName: 'Airspace Association',
            });
        }
    }

    // ─────────────────────────── Stats / Filtering ──────────────────────────

    buildStats() {
        this.stats = {};
        for (const f of this.features) {
            this.stats[f.type] = (this.stats[f.type] || 0) + 1;
        }
    }

    getSummary() {
        return {
            totalFeatures: this.features.length,
            elementCounts: this.stats,
        };
    }

    filterByTypes(types, mode = 'include') {
        if (mode === 'include') {
            return this.features.filter(f => types.includes(f.type));
        } else {
            return this.features.filter(f => !types.includes(f.type));
        }
    }

    // ─────────────────────────── GeoJSON export ───────────────────────────

    toGeoJSON(features) {
        const geojsonFeatures = [];
        for (const f of features) {
            let geom = null;
            if (f.polygon && f.polygon.length >= 3) {
                // Close the ring if needed
                const ring = [...f.polygon];
                if (ring[0][0] !== ring[ring.length - 1][0] || ring[0][1] !== ring[ring.length - 1][1]) {
                    ring.push(ring[0]);
                }
                geom = { type: 'Polygon', coordinates: [ring.map(p => [p[1], p[0]])] };
            } else if (f.position) {
                geom = { type: 'Point', coordinates: [f.position.lon, f.position.lat] };
            } else if (f.segments && f.segments.length > 0) {
                const coords = [];
                for (const seg of f.segments) {
                    const s = seg.startPosition;
                    const e = seg.endPosition;
                    if (s) coords.push([s.lon, s.lat]);
                    if (e) coords.push([e.lon, e.lat]);
                }
                if (coords.length >= 2) geom = { type: 'LineString', coordinates: coords };
            }
            if (!geom) continue;
            geojsonFeatures.push({
                type: 'Feature',
                properties: { ...f, polygon: undefined, segments: undefined, waypointPositions: undefined, navaidPositions: undefined },
                geometry: geom,
            });
        }
        return { type: 'FeatureCollection', features: geojsonFeatures };
    }
}
