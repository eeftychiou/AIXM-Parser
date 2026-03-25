/**
 * AIXM Parser Web UI - Main Application
 * 
 * Self-contained browser-based AIXM parser with:
 * - File upload and drag-drop
 * - Element filtering
 * - Map visualization
 * - Data table view
 * - JSON export
 */

class AIXMApp {
    constructor() {
        this.parser = new AIXMParser();
        this.mapRenderer = null;
        this.currentFile = null;
        this.filterMode = 'include';
        this.selectedElements = new Set();
        
        this.init();
    }

    init() {
        this.initMap();
        this.initEventListeners();
        this.initElementTypes();
    }

    initMap() {
        this.mapRenderer = new MapRenderer('map');
    }

    initEventListeners() {
        // File upload
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');

        uploadZone.addEventListener('click', () => fileInput.click());
        
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });

        // Filter tabs
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.filterMode = tab.dataset.mode;
            });
        });

        // View tabs
        document.querySelectorAll('.view-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
                document.getElementById(tab.dataset.view + 'View').classList.add('active');
            });
        });

        // Filter buttons
        document.getElementById('applyFilterBtn').addEventListener('click', () => {
            this.applyFilter();
        });

        document.getElementById('clearFilterBtn').addEventListener('click', () => {
            this.clearFilter();
        });

        // Export button
        document.getElementById('exportGeoJSONBtn').addEventListener('click', () => {
            this.exportGeoJSON();
        });

        // Reset button
        document.getElementById('resetBtn').addEventListener('click', () => {
            this.reset();
        });
    }

    initElementTypes() {
        const elementTypes = [
            { id: 'airspace',         name: 'Airspace',         icon: 'fa-cloud' },
            { id: 'airport',          name: 'Airport',          icon: 'fa-plane' },
            { id: 'waypoint',         name: 'Waypoint',         icon: 'fa-map-marker-alt' },
            { id: 'vor',              name: 'VOR',              icon: 'fa-broadcast-tower' },
            { id: 'ndb',              name: 'NDB',              icon: 'fa-signal' },
            { id: 'dme',              name: 'DME',              icon: 'fa-broadcast-tower' },
            { id: 'tacan',            name: 'TACAN',            icon: 'fa-broadcast-tower' },
            { id: 'route',            name: 'Route',            icon: 'fa-route' },
            { id: 'border',           name: 'Border',           icon: 'fa-border-style' },
            { id: 'organization',     name: 'Organization',     icon: 'fa-building' },
            { id: 'runway',           name: 'Runway',           icon: 'fa-road' },
            { id: 'runway_direction', name: 'RWY Direction',    icon: 'fa-directions' },
            { id: 'taxiway',          name: 'Taxiway',          icon: 'fa-road' },
            { id: 'apron',            name: 'Apron',            icon: 'fa-square' },
            { id: 'apron_geometry',   name: 'Apron Geometry',   icon: 'fa-draw-polygon' },
            { id: 'service',          name: 'Service',          icon: 'fa-concierge-bell' },
            { id: 'frequency',        name: 'Frequency',        icon: 'fa-broadcast-tower' },
            { id: 'unit',             name: 'Unit',             icon: 'fa-users' },
            { id: 'sid',              name: 'SID',              icon: 'fa-plane-departure' },
            { id: 'star',             name: 'STAR',             icon: 'fa-plane-arrival' },
            { id: 'approach',         name: 'Approach',         icon: 'fa-plane' },
            { id: 'ils',              name: 'ILS',              icon: 'fa-satellite-dish' },
            { id: 'marker',           name: 'Marker',           icon: 'fa-map-pin' },
            { id: 'obstacle',         name: 'Obstacle',         icon: 'fa-exclamation-triangle' },
            { id: 'holding',          name: 'Holding',          icon: 'fa-redo' },
            { id: 'msa_group',        name: 'MSA Group',        icon: 'fa-compass' },
            { id: 'airspace_assoc',   name: 'ASpace Assoc',     icon: 'fa-sitemap' },
        ];

        const grid = document.getElementById('elementGrid');
        grid.innerHTML = '';

        elementTypes.forEach(type => {
            const div = document.createElement('div');
            div.className = 'element-checkbox';
            div.innerHTML = `
                <input type="checkbox" id="elem_${type.id}" value="${type.id}">
                <i class="fas ${type.icon}"></i>
                <span>${type.name}</span>
                <span class="count" id="count_${type.id}">0</span>
            `;
            
            div.addEventListener('click', (e) => {
                if (e.target.tagName !== 'INPUT') {
                    const checkbox = div.querySelector('input');
                    checkbox.checked = !checkbox.checked;
                }
            });

            grid.appendChild(div);
        });
    }

    async handleFile(file) {
        if (!file.name.endsWith('.xml')) {
            this.showToast('Please select an XML file', 'error');
            return;
        }

        this.currentFile = file;
        this.showLoading(true);

        try {
            await this.parser.parseFile(file);
            this.onFileLoaded();
        } catch (error) {
            this.showToast('Error parsing file: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
        }
    }

    onFileLoaded() {
        const summary = this.parser.getSummary();
        
        // Update UI
        document.getElementById('toolbarTitle').textContent = this.currentFile.name;
        document.getElementById('statsGrid').style.display = 'grid';
        document.getElementById('filterSection').style.display = 'block';
        document.getElementById('exportSection').style.display = 'block';
        document.getElementById('resetBtn').style.display = 'block';

        // Update stats
        document.getElementById('totalElements').textContent = summary.totalFeatures;
        document.getElementById('fileSize').textContent = this.formatFileSize(this.currentFile.size);

        // Update element counts
        for (let [type, count] of Object.entries(summary.elementCounts)) {
            const countEl = document.getElementById(`count_${type}`);
            if (countEl) {
                countEl.textContent = count;
            }
        }

        // Render on map - use applyFilter to respect current filter state
        this.applyFilter();

        this.showToast(`Loaded ${summary.totalFeatures} features from ${this.currentFile.name}`, 'success');
    }

    applyFilter() {
        const checkboxes = document.querySelectorAll('#elementGrid input[type="checkbox"]:checked');
        const selectedTypes = Array.from(checkboxes).map(cb => cb.value);

        let filtered;
        if (selectedTypes.length === 0) {
            // If nothing selected:
            // In 'include' mode, show no features.
            // In 'exclude' mode, show all features (effectively a clear filter).
            filtered = (this.filterMode === 'include') ? [] : this.parser.features;
        } else {
            filtered = this.parser.filterByTypes(selectedTypes, this.filterMode);
        }
        
        // Update displays
        this.mapRenderer.renderFeatures(filtered);
        this.updateTable(filtered);
        this.updateJSONView(filtered);

        this.showToast(`Showing ${filtered.length} features`, 'success');
    }

    clearFilter() {
        document.querySelectorAll('#elementGrid input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });

        // After clearing checkboxes, apply filter to show nothing (in include mode)
        this.applyFilter();

        this.showToast('Filter cleared', 'success');
    }

    updateTable(features) {
        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';

        // Show first 1000 rows for performance
        const displayFeatures = features.slice(0, 1000);

        displayFeatures.forEach(feature => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><span class="badge badge-${feature.type}">${feature.type}</span></td>
                <td>${feature.codeId || feature.icao || feature.mid || 'N/A'}</td>
                <td>${feature.name || feature.txtName || 'N/A'}</td>
                <td>${this.getFeatureDetails(feature)}</td>
            `;
            tbody.appendChild(row);
        });

        if (features.length > 1000) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="4" style="text-align: center; color: var(--secondary-color);">
                    ... and ${features.length - 1000} more rows
                </td>
            `;
            tbody.appendChild(row);
        }
    }

    getFeatureDetails(feature) {
        const details = [];
        
        if (feature.codeType) details.push(`Type: ${feature.codeType}`);
        if (feature.city) details.push(`City: ${feature.city}`);
        if (feature.frequency) details.push(`Freq: ${feature.frequency}`);
        if (feature.position) details.push(`Pos: ${feature.position.lat.toFixed(2)}, ${feature.position.lon.toFixed(2)}`);
        if (feature.designator) details.push(`Designator: ${feature.designator}`);
        
        return details.join(' | ') || 'N/A';
    }

    updateJSONView(features) {
        const jsonContent = document.getElementById('jsonContent');
        // Show first 100 features in JSON view
        const displayFeatures = features.slice(0, 100);
        jsonContent.textContent = JSON.stringify(displayFeatures, null, 2);
        
        if (features.length > 100) {
            jsonContent.textContent += `\n\n... and ${features.length - 100} more features`;
        }
    }

    exportGeoJSON() {
        const features = this.parser.features;
        const geojson = this.parser.toGeoJSON(features);
        
        const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'aixm_export.geojson';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showToast('GeoJSON exported successfully', 'success');
    }

    reset() {
        this.parser = new AIXMParser();
        this.currentFile = null;
        this.mapRenderer.clear();
        
        document.getElementById('toolbarTitle').textContent = 'No file loaded';
        document.getElementById('statsGrid').style.display = 'none';
        document.getElementById('filterSection').style.display = 'none';
        document.getElementById('exportSection').style.display = 'none';
        document.getElementById('resetBtn').style.display = 'none';
        document.getElementById('tableBody').innerHTML = '';
        document.getElementById('jsonContent').textContent = 'Load an AIXM file to see parsed data...';
        
        document.querySelectorAll('#elementGrid input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });

        document.querySelectorAll('[id^="count_"]').forEach(el => {
            el.textContent = '0';
        });

        this.showToast('Reset complete', 'success');
    }

    showLoading(show) {
        const overlay = document.getElementById('loadingOverlay');
        if (show) {
            overlay.classList.add('active');
        } else {
            overlay.classList.remove('active');
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AIXMApp();
});
