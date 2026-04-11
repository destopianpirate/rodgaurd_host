/**
 * ═══════════════════════════════════════════════════════════
 * RoadGuard — Dashboard v5.1.5 (Phase 8 Refinements)
 * Advanced Pothole Recognition System
 * ═══════════════════════════════════════════════════════════
 */

// ─── Config ────────────────────────────────────────────────
const CONFIG = {
    API_BASE: 'http://localhost:5000/api',
    REFRESH_INTERVAL: 3,
    DEFAULT_CENTER: { lat: 28.6139, lng: 77.2090 },
    DEFAULT_ZOOM: 15,
    MAP_ID: 'DEMO_MAP_ID'
};

// ─── State ─────────────────────────────────────────────────
let map = null;
let infoWindow = null;
let markers = {}; // id -> AdvancedMarkerElement
let potholeData = [];
let countdown = CONFIG.REFRESH_INTERVAL;
let refreshTimerTracker = null;

// Settings State
let currentMapStyle = 'roadmap';
let vfxLevel = 'ultra';
let radarActive = true;

// Location & Speed
let myLocationMarker = null;
let currentLocation = null;
let followMode = true;

// ─── Severity Config ───────────────────────────────────────
const SEVERITY_CONFIG = {
    critical: { color: '#ef4444', label: 'Critical', scale: 1.4, icon: '🔴' },
    high: { color: '#f97316', label: 'High', scale: 1.2, icon: '🟠' },
    medium: { color: '#eab308', label: 'Medium', scale: 1.0, icon: '🟡' },
    low: { color: '#22c55e', label: 'Low', scale: 0.8, icon: '🟢' }
};

// ─── Boot ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTheme(); // Initialize theme first
    spawnParticles();
    initMap();
    setupEventListeners();
    startAutoRefresh();
});

// ══════════════════════════════════════════════════════════
// THEME MANAGEMENT
// ══════════════════════════════════════════════════════════
function initTheme() {
    const saved = localStorage.getItem('roadguard-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('roadguard-theme', next);
    showToast(`Switched to ${next} mode`, 'info');
}

// ══════════════════════════════════════════════════════════
// PARTICLE ANIMATION
// ══════════════════════════════════════════════════════════
function spawnParticles() {
    const container = document.getElementById('particles');
    if (!container) return;
    const N = 22;
    for (let i = 0; i < N; i++) {
        const dot = document.createElement('div');
        dot.className = 'particle';
        const size = Math.random() * 4 + 2;
        dot.style.cssText = `
            width:${size}px; height:${size}px;
            left:${Math.random() * 100}%;
            top:${Math.random() * 100}%;
            animation-delay:${Math.random() * 8}s;
            animation-duration:${6 + Math.random() * 10}s;
            opacity:${0.1 + Math.random() * 0.3};
        `;
        container.appendChild(dot);
    }
}

// ══════════════════════════════════════════════════════════
// MAP INITIALIZATION (GOOGLE MAPS)
// ══════════════════════════════════════════════════════════
async function initMap() {
    try {
        const { Map, InfoWindow } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

        map = new Map(document.getElementById("map"), {
            zoom: CONFIG.DEFAULT_ZOOM,
            center: CONFIG.DEFAULT_CENTER,
            mapId: CONFIG.MAP_ID,
            mapTypeId: currentMapStyle,
            disableDefaultUI: false,
            backgroundColor: '#0f172a',
            gestureHandling: 'greedy',
            padding: { top: 96, left: 416, right: 16, bottom: 16 },
            mapTypeControlOptions: {
                position: google.maps.ControlPosition.TOP_LEFT
            }
        });

        // CUSTOM TRACKPAD PANNING (Two-finger swipe)
        const mapDiv = document.getElementById("map");
        mapDiv.addEventListener('wheel', (e) => {
            if (!e.ctrlKey) { // Panning (Two-finger swipe)
                e.preventDefault();
                map.panBy(e.deltaX, e.deltaY);
                followMode = false;
                updateFollowBtn();
            }
            // If ctrlKey is true, let Google Maps handle the zoom (Pinch-to-zoom)
        }, { passive: false });

        // Add radar container reposition logic to map center sync
        map.addListener('idle', () => {
            updateVisibleStats();
            syncRadarPosition();
        });

        infoWindow = new InfoWindow();

        // Manual drag disables follow
        map.addListener('dragstart', () => {
            followMode = false;
            updateFollowBtn();
        });

        startLiveLocation();
        initWeatherSystem();
        loadAllData();
        showToast('RoadGuard Intelligence Loaded', 'success');

    } catch (err) {
        console.error('Map init failed:', err);
        showToast('Google Maps failed to load', 'error');
    }
}

// ══════════════════════════════════════════════════════════
// SEARCH (GOOGLE PLACES)
// ══════════════════════════════════════════════════════════
async function initSearch() {
    const { Autocomplete } = await google.maps.importLibrary("places");
    const input = document.getElementById('mapSearchInput');
    if (!input) return;

    const autocomplete = new Autocomplete(input, {
        fields: ["geometry", "name"],
        types: ["geocode"]
    });

    autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();
        if (!place.geometry || !place.geometry.location) return;

        map.setCenter(place.geometry.location);
        map.setZoom(17);
        followMode = false;
        updateFollowBtn();
        showToast(`Navigated to ${place.name}`, 'info');
    });
}

// ══════════════════════════════════════════════════════════
// LIVE LOCATION & SPEED
// ══════════════════════════════════════════════════════════
function startLiveLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(onLocationUpdate, (e) => console.warn(e),
            { enableHighAccuracy: true, timeout: 10000, maximumAge: 3000 });
    }
}

function onLocationUpdate(pos) {
    const { latitude: lat, longitude: lng, speed } = pos.coords;
    currentLocation = { lat, lng };

    updateMyLocationMarker(lat, lng);

    if (followMode && map) {
        map.panTo(currentLocation);
    }
}

async function updateMyLocationMarker(lat, lng) {
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    if (!myLocationMarker) {
        const content = document.createElement('div');
        content.className = 'my-location-dot';
        content.innerHTML = '<div class="loc-outer"></div><div class="loc-inner"></div>';

        myLocationMarker = new AdvancedMarkerElement({
            map,
            position: { lat, lng },
            content,
            title: "Your Location",
            zIndex: 100
        });
    } else {
        myLocationMarker.position = { lat, lng };
    }
}

// ══════════════════════════════════════════════════════════
// DATA MANAGEMENT
// ══════════════════════════════════════════════════════════
async function loadAllData() {
    try {
        const [statsRes, activeRes, resolvedRes] = await Promise.all([
            fetch(`${CONFIG.API_BASE}/stats`),
            fetch(`${CONFIG.API_BASE}/potholes?status=active`),
            fetch(`${CONFIG.API_BASE}/potholes?status=resolved`)
        ]);

        const stats = await statsRes.json();
        const active = await activeRes.json();
        const resolved = await resolvedRes.json();

        potholeData = [...active.map(p => ({ ...p, status: 'active' })), ...resolved.map(p => ({ ...p, status: 'resolved' }))];

        updateMarkers();
        updateSeverityBars(stats.severity_breakdown);
        updateVisibleStats();

    } catch (err) {
        console.error('Data sync failed:', err);
    }
}

async function updateMarkers() {
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    const currentIds = new Set(potholeData.map(p => p.id));
    Object.keys(markers).forEach(id => {
        if (!currentIds.has(parseInt(id))) {
            markers[id].map = null;
            delete markers[id];
        }
    });

    potholeData.forEach((p, i) => {
        const isResolved = p.status === 'resolved';

        const cfg = SEVERITY_CONFIG[p.severity] || SEVERITY_CONFIG.medium;
        const color = isResolved ? '#64748b' : cfg.color;

        if (!markers[p.id]) {
            const root = document.createElement('div');
            root.className = 'marker-wrapper';
            // Staggered Entry Animation
            root.style.animationDelay = `${(i % 50) * 15}ms`;
            root.innerHTML = `
                <div class="pothole-marker ${isResolved ? 'resolved' : ''}" style="
                    background: ${color}; 
                    width: ${24 * cfg.scale}px; height: ${24 * cfg.scale}px;
                    box-shadow: 0 0 12px ${color}80;
                "></div>
                ${p.verified_count > 1 && !isResolved ? `<div class="marker-badge">✓${p.verified_count}</div>` : ''}
                ${isResolved ? `<div class="marker-badge resolved">FIX</div>` : ''}
            `;

            const marker = new AdvancedMarkerElement({
                map,
                position: { lat: p.lat, lng: p.lng },
                content: root,
                title: `${cfg.label} Pothole`,
            });

            // HOVER & CLICK SUPPORT
            root.addEventListener('mouseenter', () => openSidebar(p, isResolved));
            marker.addListener('click', () => {
                followMode = false;
                updateFollowBtn();
                openSidebar(p, isResolved);
            });

            markers[p.id] = marker;
        } else {
            markers[p.id].map = map;
            markers[p.id].position = { lat: p.lat, lng: p.lng };
        }
    });
}

// ══════════════════════════════════════════════════════════
// MAP STATS (ALL DATA)
// ══════════════════════════════════════════════════════════
function updateVisibleStats() {
    if (!map) return;

    // Filter to only potholes visible in the current map viewport
    const bounds = map.getBounds();
    let visibleData = potholeData;
    if (bounds) {
        visibleData = potholeData.filter(p => {
            const pos = new google.maps.LatLng(p.lat, p.lng);
            return bounds.contains(pos);
        });
    }

    const activeData = visibleData.filter(p => p.status === 'active');
    const resolvedData = visibleData.filter(p => p.status === 'resolved');

    animateCounter('totalPotholes', activeData.length);
    animateCounter('resolvedPotholes', resolvedData.length);

    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    activeData.forEach(p => counts[p.severity]++);
    updateSeverityBars(counts);

    // Feed uses only viewport-visible data
    const feed = visibleData.sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at)).slice(0, 30);
    renderFeed(feed);

    // Phase 12 new features
    calcRiskScore(visibleData);
    renderTimeline();
}

function renderFeed(items) {
    const feed = document.getElementById('detectionFeed');
    if (!items.length) {
        feed.innerHTML = '<div class="feed-empty"><div class="feed-empty-icon">📍</div>No hazards in view</div>';
        return;
    }

    feed.innerHTML = items.map((p, i) => {
        const cfg = SEVERITY_CONFIG[p.severity] || SEVERITY_CONFIG.medium;
        return `
            <div class="feed-item" onclick="zoomToPothole(${p.lat}, ${p.lng}, '${p.id}')">
                <div class="feed-icon" style="background:${cfg.color}15; color:${cfg.color}">
                    ${cfg.icon}
                </div>
                <div class="feed-details">
                    <div class="feed-location">${p.description || `Pothole at ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}`}</div>
                    <div class="feed-meta">
                        <span>${p.severity.toUpperCase()}</span>
                        <span>${formatAgo(p.detected_at)}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function zoomToPothole(lat, lng, id) {
    if (!map) return;
    followMode = false;
    updateFollowBtn();

    map.panTo({ lat, lng });
    map.setZoom(19);

    if (markers[id]) {
        // Simple bounce effect
        google.maps.event.trigger(markers[id], 'click');
    }
}

function focusPothole(id) {
    const p = potholeData.find(x => x.id === id);
    if (p && map) {
        map.panTo({ lat: p.lat, lng: p.lng });
        map.setZoom(18);
        followMode = false;
        updateFollowBtn();
        openSidebar(p, p.status === 'resolved');
    }
}

// ══════════════════════════════════════════════════════════
// SIDEBAR
// ══════════════════════════════════════════════════════════
function openSidebar(p, isResolved) {
    const cfg = SEVERITY_CONFIG[p.severity] || SEVERITY_CONFIG.medium;
    document.getElementById('psSeverityIcon').textContent = { low: '🟢', medium: '🟡', high: '🟠', critical: '🔴' }[p.severity] || '🕳️';
    document.getElementById('psId').textContent = `#${p.id}`;

    const dot = document.getElementById('psStatusDot');
    const text = document.getElementById('psStatusText');
    const banner = document.getElementById('psStatusBanner');

    if (isResolved) {
        banner.className = 'ps-status-banner resolved';
        banner.style.borderColor = '#64748b';
        banner.style.background = 'rgba(100,116,139,0.1)';
        dot.style.background = '#64748b';
        text.textContent = 'Resolved Hazard';
    } else {
        banner.className = 'ps-status-banner';
        banner.style.borderColor = '#ef4444';
        banner.style.background = 'rgba(239,68,68,0.1)';
        dot.style.background = '#ef4444';
        text.textContent = 'Active Hazard';
    }

    const tBar = document.getElementById('psThreatBar');
    const tPct = { low: 25, medium: 50, high: 75, critical: 100 }[p.severity];
    tBar.style.width = `${tPct}%`;
    tBar.style.backgroundColor = cfg.color;
    document.getElementById('psThreatText').textContent = cfg.label;
    document.getElementById('psThreatText').style.color = cfg.color;

    document.getElementById('psDetectedAt').textContent = new Date(p.detected_at).toLocaleString();
    document.getElementById('psReportedBy').textContent = p.reported_by || 'Auto-Scanner';
    document.getElementById('psVerifiedCount').textContent = `${p.verified_count} vehicles`;
    document.getElementById('psCoords').textContent = `${p.lat.toFixed(6)}, ${p.lng.toFixed(6)}`;

    const confVal = (p.confidence || 0.85) * 100;
    document.getElementById('psConfBar').style.width = `${confVal}%`;
    document.getElementById('psConfBar').style.backgroundColor = cfg.color;
    document.getElementById('psConfVal').textContent = `${confVal.toFixed(0)}%`;

    document.getElementById('potholeSidebar').classList.add('open');
    document.getElementById('psOverlay').classList.add('visible');
}

function closeSidebar() {
    document.getElementById('potholeSidebar').classList.remove('open');
    document.getElementById('psOverlay').classList.remove('visible');
}

// ══════════════════════════════════════════════════════════
// SMART SEEDING & CONNECTIVITY
// ══════════════════════════════════════════════════════════
async function performSmartSeed() {
    if (!map) return;
    showToast('Initializing Smart Scan...', 'info');

    // Use current location or map center
    const center = currentLocation || { lat: map.getCenter().lat(), lng: map.getCenter().lng() };

    // Try to get nearby places from Google for realistic names,
    // but always proceed even if Places API fails
    let places = [];
    try {
        const service = new google.maps.places.PlacesService(map);
        places = await new Promise((resolve) => {
            service.nearbySearch({
                location: { lat: center.lat, lng: center.lng },
                radius: 1000,
                type: ['restaurant', 'cafe', 'park', 'shopping_mall', 'tourist_attraction']
            }, (results, status) => {
                if (status === google.maps.places.PlacesServiceStatus.OK && results) {
                    resolve(results
                        .filter(r => r && r.geometry && r.geometry.location)
                        .slice(0, 10)
                        .map(r => ({
                            name: r.name || 'Unknown Place',
                            lat: typeof r.geometry.location.lat === 'function' ? r.geometry.location.lat() : r.geometry.location.lat,
                            lng: typeof r.geometry.location.lng === 'function' ? r.geometry.location.lng() : r.geometry.location.lng
                        }))
                    );
                } else {
                    console.warn('Places API returned:', status);
                    resolve([]);
                }
            });
        });
    } catch (e) {
        console.warn('Places API error, proceeding without:', e);
    }

    // Always call the backend, regardless of whether Places worked
    try {
        const res = await fetch(`${CONFIG.API_BASE}/seed`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: center.lat,
                lng: center.lng,
                places: places
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(`Smart Scan complete: ${data.potholes} hazards seeded`, 'success');
            await loadAllData();
        } else {
            showToast('Smart Scan failed: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (e) {
        console.error('Smart Seed fetch error:', e);
        showToast('Sync failure: Is server running?', 'error');
    }
}

async function clearAllPotholes() {
    if (!confirm('Wipe database? This will remove all detected hazards.')) return;
    try {
        const res = await fetch(`${CONFIG.API_BASE}/clear`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('Database reset complete', 'success');
            potholeData = [];
            Object.keys(markers).forEach(id => {
                markers[id].map = null;
                delete markers[id];
            });
            loadAllData();
        }
    } catch (e) {
        showToast('Reset failed', 'error');
    }
}

// ══════════════════════════════════════════════════════════
// HELPERS & EVENTS
// ══════════════════════════════════════════════════════════
function setupEventListeners() {

    document.getElementById('closeSidebar').addEventListener('click', closeSidebar);
    document.getElementById('psOverlay').addEventListener('click', closeSidebar);
    document.getElementById('seedBtn').addEventListener('click', performSmartSeed);
    document.getElementById('clearBtn').addEventListener('click', clearAllPotholes);
    document.getElementById('refreshBtn').addEventListener('click', () => {
        countdown = CONFIG.REFRESH_INTERVAL;
        loadAllData();
        showToast('Manual refresh triggered', 'info');
    });

    // Sidebar Action Buttons
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(potholeData, null, 2));
            const dl = document.createElement('a');
            dl.setAttribute("href", dataStr);
            dl.setAttribute("download", "pothole_report.json");
            document.body.appendChild(dl);
            dl.click();
            dl.remove();
            showToast('Report Exported Successfully', 'success');
        });
    }

    const droneBtn = document.getElementById('droneBtn');
    if (droneBtn) {
        droneBtn.addEventListener('click', () => {
            showToast('Drone Dispatch Initiated. Scanning Sector...', 'success');
        });
    }

    const routeBtn = document.getElementById('routeBtn');
    if (routeBtn) {
        routeBtn.addEventListener('click', () => {
            showToast('Calculating Optimal Patrol Route...', 'success');
        });
    }

    // Button ripple effect
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', function (e) {
            const ripple = document.createElement('span');
            ripple.className = 'ripple-effect';
            const rect = btn.getBoundingClientRect();
            ripple.style.left = `${e.clientX - rect.left}px`;
            ripple.style.top = `${e.clientY - rect.top}px`;
            btn.appendChild(ripple);
            setTimeout(() => ripple.remove(), 700);
        });
    });

    // Phase 13: Card Spotlight Effect
    document.addEventListener('mousemove', e => {
        document.querySelectorAll('.card').forEach(card => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

function startAutoRefresh() {
    // Refresh the weather every 10 minutes (600,000 ms) automatically
    updateWeatherLocation(); // Fetch immediately on boot
    setInterval(updateWeatherLocation, 600000);

    refreshTimerTracker = setInterval(() => {
        if (CONFIG.REFRESH_INTERVAL === 0) return; // Disabled

        countdown--;
        const el = document.getElementById('countdown');
        if (el) el.textContent = countdown;

        if (countdown <= 0) {
            countdown = CONFIG.REFRESH_INTERVAL;
            loadAllData();
        }
    }, 1000);
}

function animateCounter(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const prev = parseInt(el.textContent) || 0;
    if (prev !== target) {
        el.style.animation = 'none';
        el.offsetHeight; // reflow
        el.style.animation = 'number-pop 0.5s ease';
    }
    const duration = 800;
    const startTime = performance.now();
    function update(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        el.textContent = Math.floor(progress * (target - prev) + prev);
        if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
}

function updateSeverityBars(breakdown) {
    const total = Object.values(breakdown).reduce((a, b) => a + b, 0) || 1;
    for (const [sev, count] of Object.entries(breakdown)) {
        const barId = `vBar${sev.charAt(0).toUpperCase() + sev.slice(1)}`;
        const countId = `count${sev.charAt(0).toUpperCase() + sev.slice(1)}`;
        const bar = document.getElementById(barId);
        const countEl = document.getElementById(countId);
        const pct = (count / total) * 100;

        if (bar) bar.style.height = `${pct}%`;
        if (countEl) countEl.innerHTML = count;
    }
}

function showToast(msg, type) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const t = document.createElement('div');
    t.className = `toast toast-${type}`;
    t.textContent = msg;
    container.appendChild(t);
    setTimeout(() => {
        t.style.opacity = '0';
        setTimeout(() => t.remove(), 400);
    }, 3000);
}

function formatAgo(iso) {
    const diff = Date.now() - new Date(iso);
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return `${Math.floor(diff / 3600000)}h ago`;
}

// ══════════════════════════════════════════════════════════
// WEATHER API INTEGRATION (Live Location, 10 min refresh)
// ══════════════════════════════════════════════════════════
let lastWeatherFetch = 0;
let weatherInterval = null;

function initWeatherSystem() {
    // Fetch immediately on load
    fetchWeatherForCurrentLocation();

    // Set up 10-minute interval (600,000 ms)
    if (weatherInterval) clearInterval(weatherInterval);
    weatherInterval = setInterval(fetchWeatherForCurrentLocation, 600000);
}

function fetchWeatherForCurrentLocation() {
    const roadTextEl = document.getElementById('roadConditionText');
    if (roadTextEl) roadTextEl.textContent = 'Checking conditions...';

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                // Update our global currentLocation just in case
                currentLocation = { lat, lng };
                updateWeatherLocation(lat, lng);
            },
            (error) => {
                console.warn("Geolocation failed for weather. Falling back to map center.", error);
                // Fallback to map center if geolocation is denied or fails
                if (map) {
                    updateWeatherLocation(map.getCenter().lat(), map.getCenter().lng());
                } else {
                    const descEl = document.getElementById('weatherDesc');
                    if (descEl) descEl.textContent = 'Location Required';
                    if (roadTextEl) roadTextEl.textContent = 'Enable location for weather';
                }
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 } // 5 min cache is fine for weather
        );
    } else {
        // Fallback for no geolocation support
        if (map) updateWeatherLocation(map.getCenter().lat(), map.getCenter().lng());
    }
}

async function updateWeatherLocation(rawLat, rawLng) {
    if (!rawLat || !rawLng) return;

    // MET Norway API requires max 4 decimals for lat/lon, high precision causes 400 Bad Request
    const lat = Number(rawLat).toFixed(4);
    const lng = Number(rawLng).toFixed(4);

    try {
        const url = `https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=${lat}&lon=${lng}`;
        const res = await fetch(url, {
            headers: {
                'Accept': 'application/json',
                'User-Agent': 'RoadGuardDashboard/1.0 (placeholder@example.com)'
            }
        });

        if (!res.ok) throw new Error(`MET Norway API returned ${res.status}`);
        const data = await res.json();
        const timeseries = data.properties.timeseries;

        // Current conditions
        const currentData = timeseries[0].data;
        const temp = currentData.instant.details.air_temperature;
        let descRaw = currentData.next_1_hours
            ? currentData.next_1_hours.summary.symbol_code
            : (currentData.next_6_hours ? currentData.next_6_hours.summary.symbol_code : 'cloudy');

        // Icon & description mapping
        let icon = '⛅', descStr = 'Cloudy';
        if (descRaw.includes('clearsky')) { icon = '☀️'; descStr = 'Clear Sky'; }
        else if (descRaw.includes('partlycloudy')) { icon = '⛅'; descStr = 'Partly Cloudy'; }
        else if (descRaw.includes('cloudy')) { icon = '☁️'; descStr = 'Cloudy'; }
        else if (descRaw.includes('rainshowers')) { icon = '🌦️'; descStr = 'Showers'; }
        else if (descRaw.includes('rain')) { icon = '🌧️'; descStr = 'Rain'; }
        else if (descRaw.includes('snow')) { icon = '❄️'; descStr = 'Snow'; }
        else if (descRaw.includes('fog')) { icon = '🌫️'; descStr = 'Fog'; }
        else if (descRaw.includes('thunder')) { icon = '⛈️'; descStr = 'Thunderstorm'; }

        // ── Rain History Analysis (last 5 hours) ──
        const now = new Date();
        let rainInLast1Hr = false;
        let rainInLast5Hr = false;
        const currentlyRaining = descRaw.includes('rain') || descRaw.includes('snow');

        // Check past timeseries entries for precipitation
        for (let i = 0; i < Math.min(timeseries.length, 6); i++) {
            const entry = timeseries[i];
            const entryTime = new Date(entry.time);
            const hoursAgo = (now - entryTime) / 3600000;

            // Check symbol codes for rain indicators
            const sym1 = entry.data.next_1_hours?.summary?.symbol_code || '';
            const precip = entry.data.next_1_hours?.details?.precipitation_amount || 0;
            const isRainy = sym1.includes('rain') || sym1.includes('snow') || precip > 0;

            if (hoursAgo <= 1 && isRainy) rainInLast1Hr = true;
            if (hoursAgo <= 5 && isRainy) rainInLast5Hr = true;
        }

        // Determine road condition
        let roadCondition = 'Dry';
        let roadClass = 'dry';
        if (currentlyRaining || rainInLast1Hr) {
            roadCondition = '🌊 Wet Roads — Active precipitation';
            roadClass = 'wet';
        } else if (rainInLast5Hr) {
            roadCondition = '💧 May be Wet — Rain in last 5 hours';
            roadClass = 'may-wet';
        } else {
            roadCondition = '☀️ Dry Roads — No recent precipitation';
            roadClass = 'dry';
        }

        // Update UI elements
        const tempEl = document.getElementById('weatherTemp');
        const descEl = document.getElementById('weatherDesc');
        const iconEl = document.getElementById('weatherIcon');
        const roadTextEl = document.getElementById('roadConditionText');
        const roadDotEl = document.querySelector('.road-dot');

        if (tempEl) tempEl.textContent = `${Math.round(temp)}°C`;
        if (descEl) descEl.textContent = descStr;
        if (iconEl) iconEl.textContent = icon;
        if (roadTextEl) roadTextEl.textContent = roadCondition;
        if (roadDotEl) {
            roadDotEl.className = 'road-dot ' + roadClass;
        }

        lastWeatherFetch = Date.now();
    } catch (e) {
        console.warn('MET Norway Weather fetch failed:', e);
        const descEl = document.getElementById('weatherDesc');
        const roadTextEl = document.getElementById('roadConditionText');
        if (descEl) descEl.textContent = 'Weather Unavailable';
        if (roadTextEl) roadTextEl.textContent = 'Could not fetch conditions';
    }
}

// Trigger initial fetch when DOM loads if needed, but idle listener handles it early.

// ══════════════════════════════════════════════════════════
// ROAD RISK SCORE & UI LOGIC
// ══════════════════════════════════════════════════════════
function calcRiskScore(visible) {
    if (!visible.length) {
        animateCounter('riskScore', 0);
        updateGrade(0, '#22c55e', 'SAFE', 'A', 0);
        closeAlert();
        return;
    }

    const weights = { critical: 10, high: 5, medium: 2, low: 1 };
    let score = visible.reduce((acc, p) => acc + (weights[p.severity] || 1), 0);
    let color = '#22c55e'; // Safe
    let label = 'SAFE';
    let gradeLetter = 'A';

    if (score > 50) { score = 100; color = '#ef4444'; label = 'CRITICAL'; gradeLetter = 'F'; }
    else if (score > 20) { color = '#f97316'; label = 'WARNING'; gradeLetter = 'D'; }
    else if (score > 5) { color = '#eab308'; label = 'CAUTION'; gradeLetter = 'C'; }

    animateCounter('riskScore', score);
    const crits = visible.filter(p => p.severity === 'critical').length;
    updateGrade(score, color, label, gradeLetter, visible.length, crits);

    const hasCritical = visible.some(p => p.severity === 'critical' && p.status === 'active');
    if (hasCritical) {
        const worst = visible.find(p => p.severity === 'critical' && p.status === 'active');
        showAlertBanner(`Critical hazard at ${worst.lat.toFixed(4)}, ${worst.lng.toFixed(4)}`);
    } else {
        closeAlert();
    }
}

function updateGrade(score, color, label, gradeLetter, activeCount, critCount = 0) {
    const ring = document.getElementById('riskRing');
    if (ring) {
        const offset = 201 - (201 * (score / 100));
        ring.style.strokeDashoffset = Math.max(offset, 0);
        ring.style.stroke = color;
    }

    const lbl = document.getElementById('riskLabel');
    if (lbl) {
        lbl.textContent = label;
        lbl.style.color = color;
    }

    // Update Dynamic Safety Grade Card
    const gradeCircle = document.getElementById('safetyGradeCircle');
    if (gradeCircle) {
        gradeCircle.textContent = gradeLetter;
        gradeCircle.style.background = color;
    }

    const rAct = document.getElementById('riskActive');
    const rCrit = document.getElementById('riskCritical');
    if (rAct) rAct.textContent = activeCount;
    if (rCrit) rCrit.textContent = critCount;
}

// ══════════════════════════════════════════════════════════
// ALERT BANNER
// ══════════════════════════════════════════════════════════
function showAlertBanner(msg) {
    const banner = document.getElementById('alertBanner');
    const text = document.getElementById('alertText');
    if (!banner) return;
    if (text) text.textContent = msg;
    banner.classList.add('visible');
}

function closeAlert() {
    const banner = document.getElementById('alertBanner');
    if (banner) banner.classList.remove('visible');
}

// ══════════════════════════════════════════════════════════
// 24H DETECTION TIMELINE
// ══════════════════════════════════════════════════════════
function renderTimeline() {
    const container = document.getElementById('timelineBars');
    if (!container) return;

    const SLOTS = 24;
    const now = Date.now();
    const slotMs = 3600000; // 1 hour each
    const counts = new Array(SLOTS).fill(0);

    potholeData.forEach(p => {
        const age = now - new Date(p.detected_at).getTime();
        const slot = Math.floor(age / slotMs);
        if (slot >= 0 && slot < SLOTS) counts[SLOTS - 1 - slot]++;
    });

    const max = Math.max(...counts, 1);
    container.innerHTML = counts.map((c, i) => {
        const pct = (c / max) * 100;
        const isEmpty = c === 0;
        return `<div class="timeline-bar ${isEmpty ? 'empty-bar' : 'active-bar'}"
            style="height:${Math.max(pct, 6)}%;transition-delay:${i * 15}ms"
            title="${c} potholes detected ${SLOTS - i}h ago"></div>`;
    }).join('');
}

// ══════════════════════════════════════════════════════════
// PING: add sonar class when connected
// ══════════════════════════════════════════════════════════
function updatePingUI(ms) {
    const dot = document.getElementById('pingDot');
    const text = document.getElementById('pingText');
    const badge = document.getElementById('pingBadge');

    if (ms !== null) {
        const color = ms < 100 ? '#22c55e' : ms < 500 ? '#eab308' : '#ef4444';
        dot.style.background = color;
        dot.classList.add('connected');
        text.textContent = 'Connected';
        badge.textContent = `${ms}ms`;
        badge.style.color = color;
    } else {
        dot.style.background = '#64748b';
        dot.classList.remove('connected');
        text.textContent = 'Offline';
        badge.textContent = '--';
        badge.style.color = '#64748b';
    }
}
