/**
 * Map Renderer - Leaflet-based visualization for AIXM data
 * 
 * Renders aeronautical features on an interactive map using Leaflet.js
 */

class MapRenderer {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.layers = {};
        this.markers = [];
        this.init();
    }

    /**
     * Initialize the map
     */
    init() {
        // Create map centered on Europe/Middle East
        this.map = L.map(this.containerId).setView([35.0, 33.0], 6);

        // Add tile layers
        const baseLayers = {
            'OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }),
            'CartoDB Positron': L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
                attribution: '© CartoDB'
            }),
            'CartoDB Dark': L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '© CartoDB'
            })
        };

        // Add default layer
        baseLayers['CartoDB Positron'].addTo(this.map);

        // Add layer control
        L.control.layers(baseLayers).addTo(this.map);

        // Initialize feature groups
        this.layers = {
            airspace: L.featureGroup().addTo(this.map),
            airport: L.featureGroup().addTo(this.map),
            waypoint: L.featureGroup().addTo(this.map),
            vor: L.featureGroup().addTo(this.map),
            ndb: L.featureGroup().addTo(this.map),
            dme: L.featureGroup().addTo(this.map),
            tacan: L.featureGroup().addTo(this.map),
            route: L.featureGroup().addTo(this.map),
            border: L.featureGroup().addTo(this.map),
            runway: L.featureGroup().addTo(this.map),
            taxiway: L.featureGroup().addTo(this.map),
            apron: L.featureGroup().addTo(this.map),
            service: L.featureGroup().addTo(this.map),
            frequency: L.featureGroup().addTo(this.map),
            unit: L.featureGroup().addTo(this.map),
            sid: L.featureGroup().addTo(this.map),
            star: L.featureGroup().addTo(this.map),
            approach: L.featureGroup().addTo(this.map),
            ils: L.featureGroup().addTo(this.map),
            marker: L.featureGroup().addTo(this.map)
        };

        // Add scale control
        L.control.scale().addTo(this.map);
    }

    /**
     * Clear all layers
     */
    clear() {
        for (let key in this.layers) {
            this.layers[key].clearLayers();
        }
        this.markers = [];
    }

    /**
     * Render features on the map
     */
    renderFeatures(features) {
        this.clear();
        
        // Store all features for route rendering (waypoint lookup)
        this.allFeatures = features;

        for (let feature of features) {
            this.renderFeature(feature);
        }

        // Fit bounds if we have features
        const allLayers = Object.values(this.layers);
        const visibleLayers = allLayers.filter(l => l.getLayers().length > 0);
        
        if (visibleLayers.length > 0) {
            const group = L.featureGroup(visibleLayers);
            const bounds = group.getBounds();
            // Check if bounds are valid (not empty or a single point)
            if (bounds.isValid() && !bounds.isEmpty()) {
                this.map.fitBounds(bounds.pad(0.1));
            } else {
                // If bounds are invalid or empty, reset to a default view or current view
                // This prevents issues with fitBounds on a single point or no features
                this.map.setView([35.0, 33.0], 6); // Default view
            }
        }
    }

    /**
     * Render a single feature
     */
    renderFeature(feature) {
        switch (feature.type) {
            case 'airspace':
                return this.renderAirspace(feature);
            case 'airport':
                return this.renderAirport(feature);
            case 'waypoint':
                return this.renderWaypoint(feature);
            case 'vor':
            case 'ndb':
            case 'dme':
            case 'tacan':
                return this.renderNavaid(feature);
            case 'route':
                return this.renderRoute(feature);
            case 'border':
                return this.renderBorder(feature);
            case 'marker':
                return this.renderMarker(feature);
            default:
                // For other types, try to render as point if position exists
                if (feature.position) {
                    return this.renderGenericPoint(feature);
                }
                return false;
        }
    }

    /**
     * Render airspace polygon
     */
    renderAirspace(feature) {
        if (!feature.polygon || feature.polygon.length === 0) return false;

        const color = this.getAirspaceColor(feature.codeType);
        
        const polygon = L.polygon(feature.polygon, {
            color: color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.15,
            dashArray: feature.codeType === 'FIR' ? '5, 5' : null
        });

        const popup = this.createPopup(feature, `
            <b>${feature.txtName || feature.codeId || 'Airspace'}</b><br>
            Type: ${feature.codeType || 'N/A'}<br>
            Code: ${feature.codeId || 'N/A'}
        `);

        polygon.bindPopup(popup);
        polygon.addTo(this.layers.airspace);
        return true;
    }

    /**
     * Render airport
     */
    renderAirport(feature) {
        if (!feature.position) return false;

        const icon = this.createAirportIcon(feature);
        
        const marker = L.marker([feature.position.lat, feature.position.lon], { icon });
        
        const popup = this.createPopup(feature, `
            <b>${feature.name || feature.icao || 'Airport'}</b><br>
            ICAO: ${feature.icao || 'N/A'}<br>
            IATA: ${feature.iata || 'N/A'}<br>
            City: ${feature.city || 'N/A'}<br>
            Elevation: ${feature.elevation || 'N/A'}
        `);

        marker.bindPopup(popup);
        marker.addTo(this.layers.airport);
        return true;
    }

    /**
     * Render waypoint
     */
    renderWaypoint(feature) {
        if (!feature.position) return false;

        const icon = this.createWaypointIcon();
        
        const marker = L.marker([feature.position.lat, feature.position.lon], { icon });
        
        const popup = this.createPopup(feature, `
            <b>${feature.codeId || 'Waypoint'}</b><br>
            Type: ${feature.codeType || 'N/A'}<br>
            Lat: ${feature.position.lat.toFixed(4)}<br>
            Lon: ${feature.position.lon.toFixed(4)}
        `);

        marker.bindPopup(popup);
        marker.addTo(this.layers.waypoint);
        return true;
    }

    /**
     * Render navaid
     */
    renderNavaid(feature) {
        if (!feature.position) return false;

        const icon = this.createNavaidIcon(feature.type);
        
        const marker = L.marker([feature.position.lat, feature.position.lon], { icon });
        
        const popup = this.createPopup(feature, `
            <b>${feature.codeId} (${feature.type.toUpperCase()})</b><br>
            Name: ${feature.name || 'N/A'}<br>
            Freq: ${feature.frequency || 'N/A'}<br>
            Channel: ${feature.channel || 'N/A'}
        `);

        marker.bindPopup(popup);
        marker.addTo(this.layers[feature.type]);
        return true;
    }

    /**
     * Render route as polylines connecting waypoints
     */
    renderRoute(feature) {
        if (!feature.segments || feature.segments.length === 0) return false;

        // Get all waypoints from the map renderer's current features
        // We need to look up waypoint positions from the parsed features
        const waypoints = {};
        const vors = {};
        
        // Build lookup maps from all features
        // Note: This assumes renderFeatures has been called with all features
        // We'll use the features that were passed to renderFeatures
        if (this.allFeatures) {
            for (let f of this.allFeatures) {
                if (f.type === 'waypoint' && f.codeId && f.position) {
                    waypoints[f.codeId] = f.position;
                } else if (f.type === 'vor' && f.codeId && f.position) {
                    vors[f.codeId] = f.position;
                }
            }
        }

        let renderedCount = 0;

        for (let segment of feature.segments) {
            // Get start position
            let startPos = null;
            if (segment.startPointType === 'waypoint' && segment.startPointId) {
                startPos = waypoints[segment.startPointId];
            } else if (segment.startPointType === 'vor' && segment.startPointId) {
                startPos = vors[segment.startPointId];
            }

            // Get end position
            let endPos = null;
            if (segment.endPointType === 'waypoint' && segment.endPointId) {
                endPos = waypoints[segment.endPointId];
            } else if (segment.endPointType === 'vor' && segment.endPointId) {
                endPos = vors[segment.endPointId];
            }

            // Skip if we don't have both positions
            if (!startPos || !endPos) continue;

            // Draw the route segment as a polyline
            const polyline = L.polyline([
                [startPos.lat, startPos.lon],
                [endPos.lat, endPos.lon]
            ], {
                color: '#666666',
                weight: 1.5,
                opacity: 0.7,
                dashArray: null
            });

            const popup = this.createPopup(feature, `
                <b>${feature.designator || feature.codeId || 'Route'}</b><br>
                From: ${segment.startPointId || 'N/A'}<br>
                To: ${segment.endPointId || 'N/A'}<br>
                Type: ${segment.pathType || 'N/A'}<br>
                Length: ${segment.length || 'N/A'} ${segment.lengthUnit || ''}
            `);

            polyline.bindPopup(popup);
            polyline.addTo(this.layers.route);
            renderedCount++;
        }

        return renderedCount > 0;
    }

    /**
     * Render border
     */
    renderBorder(feature) {
        if (!feature.polygon || feature.polygon.length === 0) return false;

        const polygon = L.polygon(feature.polygon, {
            color: '#444444',
            weight: 1,
            fillColor: '#444444',
            fillOpacity: 0.1
        });

        const popup = this.createPopup(feature, `
            <b>${feature.name || 'Border'}</b><br>
            Type: ${feature.borderType || 'N/A'}
        `);

        polygon.bindPopup(popup);
        polygon.addTo(this.layers.border);
        return true;
    }

    /**
     * Render marker beacon
     */
    renderMarker(feature) {
        if (!feature.position) return false;

        const icon = this.createMarkerIcon(feature.markerType);
        
        const marker = L.marker([feature.position.lat, feature.position.lon], { icon });
        
        const popup = this.createPopup(feature, `
            <b>${feature.codeId || 'Marker'}</b><br>
            Type: ${feature.markerType || 'N/A'}
        `);

        marker.bindPopup(popup);
        marker.addTo(this.layers.marker);
        return true;
    }

    /**
     * Render generic point feature
     */
    renderGenericPoint(feature) {
        // Assuming feature.position exists as checked by renderFeature before calling this.
        const marker = L.circleMarker([feature.position.lat, feature.position.lon], {
            radius: 5,
            color: '#666',
            fillColor: '#999',
            fillOpacity: 0.7
        });

        const popup = this.createPopup(feature, `
            <b>${feature.codeId || feature.name || 'Feature'}</b><br>
            Type: ${feature.type}<br>
            MID: ${feature.mid || 'N/A'}
        `);

        marker.bindPopup(popup);
        
        const layer = this.layers[feature.type];
        if (layer) {
            marker.addTo(layer);
        }
        return true;
    }

    /**
     * Create popup content
     */
    createPopup(feature, content) {
        return L.popup().setContent(`
            <div style="font-family: Arial, sans-serif; min-width: 200px;">
                ${content}
            </div>
        `);
    }

    /**
     * Get color for airspace type
     */
    getAirspaceColor(type) {
        const colors = {
            'FIR': '#FF0000',
            'CTA': '#FF6600',
            'TMA': '#FFCC00',
            'CTR': '#00AA00',
            'SECTOR': '#00AA00',
            'default': '#666666'
        };
        return colors[type] || colors.default;
    }

    /**
     * Create airport icon
     */
    createAirportIcon(feature) {
        const color = feature.icao ? '#0066CC' : '#CC00CC';
        
        return L.divIcon({
            className: 'custom-airport-icon',
            html: `
                <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="14" cy="14" r="11" fill="none" stroke="${color}" stroke-width="2.5"/>
                    <rect x="12" y="5" width="4" height="18" fill="none" stroke="${color}" stroke-width="1.5"/>
                    <rect x="5" y="12" width="18" height="4" fill="none" stroke="${color}" stroke-width="1.5"/>
                    <circle cx="14" cy="14" r="2" fill="${color}"/>
                </svg>
            `,
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });
    }

    /**
     * Create waypoint icon
     */
    createWaypointIcon() {
        return L.divIcon({
            className: 'custom-waypoint-icon',
            html: `
                <svg width="22" height="22" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg">
                    <polygon points="11,2 12.5,9 20,11 12.5,13 11,20 9.5,13 2,11 9.5,9" 
                             fill="none" stroke="#663399" stroke-width="2" stroke-linejoin="round"/>
                    <circle cx="11" cy="11" r="2" fill="#663399"/>
                </svg>
            `,
            iconSize: [22, 22],
            iconAnchor: [11, 11]
        });
    }

    /**
     * Create navaid icon
     */
    createNavaidIcon(type) {
        const colors = {
            vor: '#0066CC',
            ndb: '#CC6633',
            dme: '#CC00CC',
            tacan: '#0066CC'
        };
        const color = colors[type] || '#666';

        let svg = '';
        if (type === 'vor') {
            svg = `
                <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="14" cy="14" r="11" fill="none" stroke="${color}" stroke-width="2"/>
                    <polygon points="14,5 20,8 20,16 14,20 8,16 8,8" 
                             fill="white" stroke="${color}" stroke-width="2"/>
                    <circle cx="14" cy="13" r="2.5" fill="${color}"/>
                </svg>
            `;
        } else if (type === 'ndb') {
            svg = `
                <svg width="26" height="26" viewBox="0 0 26 26" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="13" cy="13" r="10" fill="none" stroke="${color}" stroke-width="2.5"/>
                    <circle cx="13" cy="13" r="6" fill="none" stroke="${color}" stroke-width="1.5"/>
                    <circle cx="13" cy="13" r="3" fill="${color}"/>
                </svg>
            `;
        } else {
            svg = `
                <svg width="22" height="22" viewBox="0 0 22 22" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="3" width="16" height="16" rx="1" fill="none" stroke="${color}" stroke-width="2.5"/>
                    <rect x="7" y="7" width="8" height="8" fill="none" stroke="${color}" stroke-width="1.5"/>
                    <circle cx="11" cy="11" r="2" fill="${color}"/>
                </svg>
            `;
        }

        return L.divIcon({
            className: `custom-navaid-icon ${type}`,
            html: svg,
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });
    }

    /**
     * Create marker beacon icon
     */
    createMarkerIcon(markerType) {
        const colors = {
            'OUTER': '#CC0000',
            'MIDDLE': '#FFCC00',
            'INNER': '#00CC00'
        };
        const color = colors[markerType] || '#666';

        return L.divIcon({
            className: 'custom-marker-icon',
            html: `
                <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <ellipse cx="10" cy="10" rx="8" ry="5" fill="${color}" stroke="white" stroke-width="1"/>
                </svg>
            `,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
    }

    /**
     * Toggle layer visibility
     */
    toggleLayer(type, visible) {
        if (this.layers[type]) {
            if (visible) {
                this.map.addLayer(this.layers[type]);
            } else {
                this.map.removeLayer(this.layers[type]);
            }
        }
    }

    /**
     * Show all layers
     */
    showAllLayers() {
        for (let key in this.layers) {
            this.map.addLayer(this.layers[key]);
        }
    }

    /**
     * Hide all layers
     */
    hideAllLayers() {
        for (let key in this.layers) {
            this.map.removeLayer(this.layers[key]);
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MapRenderer;
}
