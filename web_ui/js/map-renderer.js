/**
 * AIXM Map Renderer — Leaflet-based renderer for AIXM 4.5 features.
 *
 * Supports: airspace, airport, waypoint, vor, ndb, dme, tacan, route,
 *           border, organization, runway, runway_direction, taxiway, apron,
 *           service, frequency, unit, sid, star, approach, ils, marker,
 *           obstacle, holding, msa_group, airspace_assoc, apron_geometry
 */

class MapRenderer {
    constructor(mapElementId) {
        this.map = L.map(mapElementId, {
            center: [40, 25],
            zoom: 5,
            zoomControl: true,
        });

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19,
        }).addTo(this.map);

        // Feature layer groups — keyed by feature.type
        this.layerGroups = {
            airspace:         L.featureGroup(),
            airport:          L.featureGroup(),
            waypoint:         L.featureGroup(),
            vor:              L.featureGroup(),
            ndb:              L.featureGroup(),
            dme:              L.featureGroup(),
            tacan:            L.featureGroup(),
            route:            L.featureGroup(),
            border:           L.featureGroup(),
            organization:     L.featureGroup(),
            runway:           L.featureGroup(),
            runway_direction: L.featureGroup(),
            taxiway:          L.featureGroup(),
            apron:            L.featureGroup(),
            apron_geometry:   L.featureGroup(),
            service:          L.featureGroup(),
            frequency:        L.featureGroup(),
            unit:             L.featureGroup(),
            sid:              L.featureGroup(),
            star:             L.featureGroup(),
            approach:         L.featureGroup(),
            ils:              L.featureGroup(),
            marker:           L.featureGroup(),
            obstacle:         L.featureGroup(),
            holding:          L.featureGroup(),
            msa_group:        L.featureGroup(),
            airspace_assoc:   L.featureGroup(),
        };

        // Add all groups to map
        for (const group of Object.values(this.layerGroups)) {
            group.addTo(this.map);
        }

        this.allFeatures = [];
    }

    // ─────────────────────────── Public API ───────────────────────────────

    renderFeatures(features) {
        this.clear();
        this.allFeatures = features;

        // Build lookup tables for routes before rendering
        this._waypointsById = {};
        this._navaidsById = {};
        for (const f of features) {
            if (f.type === 'waypoint' && f.codeId && f.position) {
                this._waypointsById[f.codeId] = f.position;
            }
            if (['vor', 'ndb', 'dme', 'tacan'].includes(f.type) && f.codeId && f.position) {
                this._navaidsById[f.codeId] = f.position;
            }
        }

        let rendered = 0;
        for (const feature of features) {
            if (this.renderFeature(feature)) rendered++;
        }

        // Fit map bounds if we rendered anything
        if (rendered > 0) {
            const allLayers = Object.values(this.layerGroups).filter(g => g.getLayers().length > 0);
            if (allLayers.length > 0) {
                try {
                    const group = L.featureGroup(allLayers.flatMap(g => g.getLayers()));
                    const bounds = group.getBounds();
                    if (bounds.isValid()) {
                        this.map.fitBounds(bounds, { padding: [20, 20], maxZoom: 10 });
                    }
                } catch (e) { /* ignore invalid bounds */ }
            }
        }
        return rendered;
    }

    clear() {
        for (const group of Object.values(this.layerGroups)) {
            group.clearLayers();
        }
        this.allFeatures = [];
        this._waypointsById = {};
        this._navaidsById = {};
    }

    // ─────────────────────────── Feature router ───────────────────────────

    renderFeature(feature) {
        switch (feature.type) {
            case 'airspace':         return this.renderAirspace(feature);
            case 'airport':          return this.renderAirport(feature);
            case 'waypoint':         return this.renderWaypoint(feature);
            case 'vor':              return this.renderNavaid(feature, '#0066cc', 'VOR');
            case 'ndb':              return this.renderNavaid(feature, '#cc6600', 'NDB');
            case 'dme':              return this.renderNavaid(feature, '#006666', 'DME');
            case 'tacan':            return this.renderNavaid(feature, '#660066', 'TCN');
            case 'route':            return this.renderRoute(feature);
            case 'border':           return this.renderBorder(feature);
            case 'runway':           return this.renderRunway(feature);
            case 'runway_direction': return this.renderRunwayDirection(feature);
            case 'obstacle':         return this.renderObstacle(feature);
            case 'holding':          return this.renderHolding(feature);
            case 'msa_group':        return this.renderMSAGroup(feature);
            case 'ils':              return this.renderILS(feature);
            case 'marker':           return this.renderMarker(feature);
            case 'sid':
            case 'star':
            case 'approach':         return this.renderProcedure(feature);
            case 'apron_geometry':   return this.renderApronGeometry(feature);
            // Types with no geometry to display
            case 'organization':
            case 'service':
            case 'frequency':
            case 'unit':
            case 'taxiway':
            case 'apron':
            case 'airspace_assoc':   return false;
            default:                 return false;
        }
    }

    // ─────────────────────────── Airspace ────────────────────────────────

    renderAirspace(feature) {
        if (!feature.polygon || feature.polygon.length < 3) return false;

        const { color, fillColor, fillOpacity, dashArray } = this.getAirspaceStyle(feature.codeType);

        // Polygon stored as [[lat,lon], ...] which is exactly what Leaflet needs
        const layer = L.polygon(feature.polygon, {
            color,
            fillColor,
            fillOpacity,
            weight: 1.5,
            dashArray,
        });

        layer.bindPopup(this.buildAirspacePopup(feature));
        this.layerGroups.airspace.addLayer(layer);
        return true;
    }

    buildAirspacePopup(f) {
        const lower = f.valDistVerLower
            ? `${f.valDistVerLower} ${f.uomDistVerLower} ${f.codeDistVerLower}`
            : '—';
        const upper = f.valDistVerUpper
            ? `${f.valDistVerUpper} ${f.uomDistVerUpper} ${f.codeDistVerUpper}`
            : '—';
        return `
            <b>${f.txtName || f.codeId}</b><br>
            <small>Type: ${f.codeType || '—'} | ID: ${f.codeId || '—'}</small><br>
            <small>Lower: ${lower}</small><br>
            <small>Upper: ${upper}</small>
        `;
    }

    getAirspaceStyle(codeType) {
        const ct = (codeType || '').toUpperCase();
        const styles = {
            FIR: { color: '#cc0000', fillColor: '#cc0000', fillOpacity: 0.04, dashArray: '8 4' },
            UIR: { color: '#990000', fillColor: '#990000', fillOpacity: 0.04, dashArray: '8 4' },
            CTA: { color: '#0044cc', fillColor: '#0044cc', fillOpacity: 0.07 },
            TMA: { color: '#0066ff', fillColor: '#0066ff', fillOpacity: 0.08 },
            CTR: { color: '#0099ff', fillColor: '#0099ff', fillOpacity: 0.10 },
            ATZ: { color: '#44aaff', fillColor: '#44aaff', fillOpacity: 0.10 },
            TRA: { color: '#ff6600', fillColor: '#ff6600', fillOpacity: 0.10 },
            TSA: { color: '#ff4400', fillColor: '#ff4400', fillOpacity: 0.10 },
            D:   { color: '#cc0000', fillColor: '#ff0000', fillOpacity: 0.12 },
            R:   { color: '#cc0000', fillColor: '#ff0000', fillOpacity: 0.12 },
            P:   { color: '#880000', fillColor: '#cc0000', fillOpacity: 0.15 },
            SECTOR: { color: '#009900', fillColor: '#00cc00', fillOpacity: 0.06, dashArray: '4 4' },
            AWY: { color: '#888800', fillColor: '#aaaa00', fillOpacity: 0.05 },
        };
        return styles[ct] || { color: '#555555', fillColor: '#888888', fillOpacity: 0.06 };
    }

    // ─────────────────────────── Airlines / Airports ──────────────────────

    renderAirport(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const icon = L.divIcon({
            className: '',
            html: `<div style="background:#1a56db;color:#fff;border-radius:3px;padding:1px 3px;font-size:9px;font-weight:bold;white-space:nowrap;border:1px solid #fff;">✈ ${feature.icao || feature.codeId || ''}</div>`,
            iconAnchor: [0, 8],
        });

        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`
            <b>${feature.txtName || feature.codeId}</b><br>
            ICAO: ${feature.icao || '—'} | IATA: ${feature.iata || '—'}<br>
            Type: ${feature.codeType || '—'}<br>
            ${feature.city ? 'City: ' + feature.city + '<br>' : ''}
            ${feature.valElev ? 'Elev: ' + feature.valElev + ' ' + (feature.uomDistVer || '') + '<br>' : ''}
        `);
        this.layerGroups.airport.addLayer(marker);
        return true;
    }

    // ─────────────────────────── Waypoints ───────────────────────────────

    renderWaypoint(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const icon = L.divIcon({
            className: '',
            html: '<div style="width:5px;height:5px;background:#555;border-radius:50%;border:1px solid #fff;"></div>',
            iconAnchor: [3, 3],
        });
        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`<b>${feature.codeId}</b><br>Type: ${feature.codeType || '—'}<br>${feature.txtName || ''}`);
        this.layerGroups.waypoint.addLayer(marker);
        return true;
    }

    // ─────────────────────────── Navaids ─────────────────────────────────

    renderNavaid(feature, color, label) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const icon = L.divIcon({
            className: '',
            html: `<div style="border:2px solid ${color};color:${color};border-radius:2px;padding:1px 2px;font-size:8px;font-weight:bold;background:rgba(255,255,255,0.85);">${label}</div>`,
            iconAnchor: [0, 8],
        });
        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`
            <b>${feature.codeId}</b> (${label})<br>
            ${feature.txtName ? feature.txtName + '<br>' : ''}
            ${feature.valFreq ? 'Freq: ' + feature.valFreq + ' ' + (feature.uomFreq || '') + '<br>' : ''}
        `);
        this.layerGroups[feature.type].addLayer(marker);
        return true;
    }

    // ─────────────────────────── Routes ──────────────────────────────────

    renderRoute(feature) {
        if (!feature.segments || feature.segments.length === 0) return false;

        let renderedCount = 0;

        for (const segment of feature.segments) {
            // Resolve start position: prefer pre-resolved segment.startPosition,
            // then fall back to the renderer's position lookup tables.
            const startPos = segment.startPosition
                || this._waypointsById[segment.startPointId]
                || this._navaidsById[segment.startPointId]
                || null;

            const endPos = segment.endPosition
                || this._waypointsById[segment.endPointId]
                || this._navaidsById[segment.endPointId]
                || null;

            if (!startPos || !endPos) continue;

            const line = L.polyline(
                [[startPos.lat, startPos.lon], [endPos.lat, endPos.lon]],
                { color: '#e65c00', weight: 1.5, opacity: 0.7 }
            );
            line.bindPopup(`
                <b>${feature.txtDesig || feature.codeId}</b><br>
                Type: ${feature.codeType || '—'}<br>
                ${segment.startPointId} → ${segment.endPointId}<br>
                ${segment.valLen ? 'Length: ' + segment.valLen + ' ' + (segment.uomLen || '') : ''}
            `);
            this.layerGroups.route.addLayer(line);
            renderedCount++;
        }

        return renderedCount > 0;
    }

    // ─────────────────────────── Borders ─────────────────────────────────

    renderBorder(feature) {
        if (!feature.polygon || feature.polygon.length < 2) return false;

        // Borders may be open polylines or closed polygons
        const layer = feature.polygon.length >= 3
            ? L.polygon(feature.polygon, { color: '#666633', fillColor: '#aaaa33', fillOpacity: 0.04, weight: 1.5, dashArray: '6 3' })
            : L.polyline(feature.polygon, { color: '#666633', weight: 1.5, dashArray: '6 3' });

        layer.bindPopup(`<b>${feature.txtName || feature.codeId}</b><br>Type: ${feature.codeType || '—'}`);
        this.layerGroups.border.addLayer(layer);
        return true;
    }

    // ─────────────────────────── Runways ─────────────────────────────────

    renderRunway(feature) {
        // Runway has no position directly — it is rendered via runway_direction thresholds
        // We skip rendering here; runway_direction handles it
        return false;
    }

    renderRunwayDirection(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const bearing = feature.valTrueBrg ? parseFloat(feature.valTrueBrg) : null;
        const brgStr = bearing !== null ? bearing.toFixed(1) + '°' : '—';

        const icon = L.divIcon({
            className: '',
            html: `<div style="background:#333;color:#fff;border-radius:2px;padding:1px 3px;font-size:8px;font-weight:bold;transform:rotate(${bearing || 0}deg)">▶ ${feature.codeId || ''}</div>`,
            iconAnchor: [10, 6],
        });

        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`
            <b>Runway ${feature.codeId}</b><br>
            Airport: ${feature.airportId || '—'}<br>
            True Bearing: ${brgStr}<br>
            Mag Bearing: ${feature.valMagBrg ? feature.valMagBrg + '°' : '—'}<br>
            TDZ Elev: ${feature.valElevTdz || '—'}
        `);
        this.layerGroups.runway_direction.addLayer(marker);
        return true;
    }

    // ─────────────────────────── Obstacles (NEW) ─────────────────────────

    renderObstacle(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const icon = L.divIcon({
            className: '',
            html: '<div style="font-size:10px;color:#cc0000;">⚠</div>',
            iconAnchor: [5, 5],
        });
        const marker = L.marker([lat, lon], { icon });
        const hgt = feature.valHgt ? feature.valHgt + ' ' + (feature.uomDistVer || '') : '—';
        marker.bindPopup(`
            <b>Obstacle: ${feature.codeType || feature.codeId}</b><br>
            Height: ${hgt}<br>
            Elevation: ${feature.valElev || '—'}
        `);
        this.layerGroups.obstacle.addLayer(marker);
        return true;
    }

    // ─────────────────────────── Holdings (NEW) ──────────────────────────

    renderHolding(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const icon = L.divIcon({
            className: '',
            html: '<div style="font-size:11px;color:#9900cc;">⬡</div>',
            iconAnchor: [5, 5],
        });
        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`
            <b>Holding: ${feature.txtName || feature.codeId}</b><br>
            Inbound Course: ${feature.valInboundCourse || '—'}°<br>
            Status: ${feature.codeStatus || '—'}
        `);
        this.layerGroups.holding.addLayer(marker);
        return true;
    }

    // ─────────────────────────── MSA Groups (NEW) ────────────────────────

    renderMSAGroup(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const icon = L.divIcon({
            className: '',
            html: `<div style="border:1px solid #0066cc;border-radius:50%;width:14px;height:14px;text-align:center;font-size:8px;color:#0066cc;line-height:14px;background:rgba(255,255,255,0.7);">M</div>`,
            iconAnchor: [7, 7],
        });
        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`<b>${feature.txtName}</b>`);
        this.layerGroups.msa_group.addLayer(marker);
        return true;
    }

    // ─────────────────────────── ILS / Markers ───────────────────────────

    renderILS(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const icon = L.divIcon({
            className: '',
            html: '<div style="border-left:2px solid #cc00cc;border-right:2px solid #cc00cc;border-bottom:2px solid #cc00cc;width:8px;height:6px;background:rgba(204,0,204,0.2);"></div>',
            iconAnchor: [4, 6],
        });
        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`<b>ILS: ${feature.codeId}</b><br>Type: ${feature.codeType}<br>Freq: ${feature.valFreq || '—'}`);
        this.layerGroups.ils.addLayer(marker);
        return true;
    }

    renderMarker(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const colorMap = { OM: '#00aa00', MM: '#aaaa00', IM: '#aa0000' };
        const color = colorMap[feature.codeType] || '#555555';

        const icon = L.divIcon({
            className: '',
            html: `<div style="background:${color};color:#fff;font-size:8px;padding:1px 2px;border-radius:2px;">${feature.codeType || 'MKR'}</div>`,
            iconAnchor: [10, 6],
        });
        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`<b>Marker: ${feature.codeId}</b><br>Type: ${feature.codeType || '—'}`);
        this.layerGroups.marker.addLayer(marker);
        return true;
    }

    // ─────────────────────────── Procedures ──────────────────────────────

    renderProcedure(feature) {
        if (!feature.position) return false;
        const { lat, lon } = feature.position;

        const styleMap = {
            sid:      { color: '#006600', label: '↗' },
            star:     { color: '#006600', label: '↙' },
            approach: { color: '#0066cc', label: '⤵' },
        };
        const s = styleMap[feature.type] || { color: '#333', label: '✈' };

        const icon = L.divIcon({
            className: '',
            html: `<div style="color:${s.color};font-size:10px;font-weight:bold;">${s.label}</div>`,
            iconAnchor: [5, 5],
        });
        const marker = L.marker([lat, lon], { icon });
        marker.bindPopup(`<b>${feature.type.toUpperCase()}: ${feature.txtName || feature.codeId}</b><br>Airport: ${feature.airportId || '—'}`);
        this.layerGroups[feature.type] && this.layerGroups[feature.type].addLayer(marker);
        return true;
    }

    // ─────────────────────────── Apron Geometry (NEW) ────────────────────

    renderApronGeometry(feature) {
        if (!feature.polygon || feature.polygon.length < 3) return false;

        const layer = L.polygon(feature.polygon, {
            color: '#996600',
            fillColor: '#ccaa44',
            fillOpacity: 0.15,
            weight: 1,
        });
        layer.bindPopup(`<b>${feature.txtName || 'Apron'}</b><br>Airport: ${feature.airportId || '—'}`);
        this.layerGroups.apron_geometry.addLayer(layer);
        return true;
    }
}
