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
    DEFAULT_CENTER: { lat: 23.2156, lng: 72.6869 },
    DEFAULT_ZOOM: 15,
    MAP_ID: 'DEMO_MAP_ID'
};

// ─── State ─────────────────────────────────────────────────
let map = null;
let infoWindow = null;

let markers = {}; // id -> AdvancedMarkerElement
let potholeData = []; // ACTIVE Hazards
let resolvedData = []; // RESOLVED Hazards for stats
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

// ─── SVG Icons ─────────────────────────────────────────────
const ICONS = {
    critical: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
    high: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
    medium: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
    low: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>',
    hole: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/></svg>',
    weather: {
        clear: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>',
        partly: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 19C19.9853 19 22 16.9853 22 14.5C22 12.1374 20.1843 10.2001 17.8687 10.0166C17.4323 6.64336 14.5668 4 11 4C7.13401 4 4 7.13401 4 11C4 11.2323 4.01132 11.4619 4.03348 11.6876C2.2646 12.3962 1 14.1287 1 16.25C1 18.8734 3.12665 21 5.75 21H16.5"></path></svg>',
        cloudy: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 19c2.485 0 4.5-2.015 4.5-4.5S19.985 10 17.5 10c-.39 0-.766.05-1.12.146C15.823 6.6 12.645 4 9 4 4.582 4 1 7.582 1 12s3.582 8 8 8h8.5z"></path></svg>',
        rain: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 19H9a7 7 0 1 1 6.71-9.9 4.502 4.502 0 0 1 1.79 8.9z"></path><path d="M16 21v2"></path><path d="M12 21v2"></path><path d="M8 21v2"></path></svg>',
        snow: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 17.5l-4-2M4 17.5l4-2M12 22v-4M20 6.5l-4 2M4 6.5l4 2M12 2v4M12 12l2.5-4.5M12 12L9.5 7.5M12 12l-4.5-1M12 12l-3.5 3M12 12l4.5 1M12 12l3.5 3"></path></svg>',
        fog: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12h16M4 16h16M4 8h16"></path></svg>',
        thunder: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 2L5 14h6l-1 10 10-14h-6L17 2z"></path></svg>'
    }
};

// ─── Severity Config ───────────────────────────────────────
const SEVERITY_CONFIG = {
    critical: { color: '#ef4444', label: 'Critical', scale: 1.4, icon: ICONS.critical },
    high: { color: '#f97316', label: 'High', scale: 1.2, icon: ICONS.high },
    medium: { color: '#f97316', label: 'Medium', scale: 1.0, icon: ICONS.medium },
    low: { color: '#22c55e', label: 'Low', scale: 0.8, icon: ICONS.low }
};

// ─── Boot ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initTheme(); // Initialize theme first
    spawnParticles();
    createTooltipDOM();
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
            streetViewControl: true,
            streetViewControlOptions: {
                position: google.maps.ControlPosition.RIGHT_BOTTOM
            },
            zoomControl: true,
            zoomControlOptions: {
                position: google.maps.ControlPosition.RIGHT_BOTTOM
            },
            fullscreenControl: true,
            fullscreenControlOptions: {
                position: google.maps.ControlPosition.RIGHT_TOP
            },
            backgroundColor: '#0f172a',
            gestureHandling: 'greedy',
            padding: { top: 96, left: 416, right: 16, bottom: 16 },
            mapTypeControlOptions: {
                position: google.maps.ControlPosition.TOP_LEFT
            }
        });



        // Add Live Location Button to Native Google Maps Controls
        const liveLocBtn = document.getElementById('liveLocationBtn');
        // Intentionally NOT adding to map.controls so we can position it via CSS natively

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
    // Immediately attempt a fast position fetch using IP fallback or fast navigator
    getLiveLocation();

    if (navigator.geolocation) {
        navigator.geolocation.watchPosition(onLocationUpdate, (e) => {
            console.warn("Watch geolocation failed, relying on IP fallback:", e);
        }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 3000 });
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
        myLocationMarker.map = map;
        myLocationMarker.position = { lat, lng };
    }
}

// ══════════════════════════════════════════════════════════
// ROBUST LIVE LOCATION HELPER
// ══════════════════════════════════════════════════════════
async function getLiveLocation() {
    if (currentLocation) return currentLocation;

    // Try browser geolocation
    if (navigator.geolocation) {
        try {
            const pos = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
            });
            currentLocation = { lat: pos.coords.latitude, lng: pos.coords.longitude };
            updateMyLocationMarker(currentLocation.lat, currentLocation.lng);
            if (followMode && map) map.panTo(currentLocation);
            return currentLocation;
        } catch (e) {
            console.warn("Browser geolocation failed or timed out, trying IP fallback...", e);
        }
    }

    // Fallback to IP-based location
    try {
        const res = await fetch('http://ip-api.com/json/');
        const data = await res.json();
        if (data.status === 'success') {
            currentLocation = { lat: data.lat, lng: data.lon };
            updateMyLocationMarker(currentLocation.lat, currentLocation.lng);
            if (followMode && map) map.panTo(currentLocation);
            return currentLocation;
        }
    } catch (e) {
        console.warn("IP geolocation failed", e);
    }

    // Ultimate fallback is the map center
    return { lat: map.getCenter().lat(), lng: map.getCenter().lng() };
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

        // Strictly separate: potholeData for ACTIVE Hazards (Map & Feed)
        potholeData = active.map(p => ({ ...p, status: 'active' }));
        // resolvedData for Stats & History
        resolvedData = resolved.map(p => ({ ...p, status: 'resolved' }));

        updateMarkers();
        updateSeverityBars(stats.severity_breakdown);
        updateVisibleStats();

    } catch (err) {
        console.error('Data sync failed:', err);
    }
}

async function updateMarkers() {
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    // Clear ANY marker that is not in the current ACTIVE potholeData
    const activeIds = new Set(potholeData.map(p => p.id));
    Object.keys(markers).forEach(id => {
        if (!activeIds.has(parseInt(id))) {
            if (markers[id]) markers[id].map = null;
            delete markers[id];
        }
    });

    // Create or update markers ONLY for items in potholeData (which is now only active)
    potholeData.forEach((p, i) => {
        const isResolved = p.status === 'resolved'; // Still check in case, though loadAllData filters it now
        if (isResolved) return; // Skip resolved markers entirely


        const cfg = SEVERITY_CONFIG[p.severity] || SEVERITY_CONFIG.medium;
        const color = cfg.color;

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

            // HOVER & CLICK SUPPORT (Tooltips instead of sidebar)
            root.addEventListener('mouseenter', (e) => showSmartTooltip(p, isResolved, e));
            root.addEventListener('mouseleave', () => {
                const tt = document.getElementById('smartTooltip');
                if (tt) {
                    tooltipTimeout = setTimeout(() => tt.classList.remove('visible'), 300);
                }
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

    // Filter to only active and resolved potholes visible in the current map viewport
    const bounds = map.getBounds();
    let visibleActive = potholeData;
    let visibleResolved = resolvedData;

    if (bounds) {
        visibleActive = potholeData.filter(p => bounds.contains(new google.maps.LatLng(p.lat, p.lng)));
        visibleResolved = resolvedData.filter(p => bounds.contains(new google.maps.LatLng(p.lat, p.lng)));
    }

    animateCounter('totalPotholes', visibleActive.length);
    animateCounter('resolvedPotholes', visibleResolved.length);

    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    visibleActive.forEach(p => counts[p.severity]++);
    updateSeverityBars(counts);

    // Feed uses only viewport-visible active data
    const feed = visibleActive.sort((a, b) => new Date(b.detected_at) - new Date(a.detected_at)).slice(0, 30);
    renderFeed(feed);

    // Phase 12 new features
    calcRiskScore(visibleActive);
    renderTimeline();
}

let lastFeedSignature = "";

function renderFeed(items) {
    const feed = document.getElementById('detectionFeed');
    
    // State Check: Only re-render the feed DOM if the data has actually changed
    const signature = items.map(p => p.id).join(',');
    if (signature === lastFeedSignature && items.length > 0) return;
    lastFeedSignature = signature;

    if (!items.length) {
        feed.innerHTML = `<div class="feed-empty"><div class="feed-empty-icon">${ICONS.hole}</div>No hazards in view</div>`;
        return;
    }

    feed.innerHTML = items.map((p, i) => {
        const cfg = SEVERITY_CONFIG[p.severity] || SEVERITY_CONFIG.medium;
        const resolvedTag = p.status === 'resolved' ? ' | RESOLVED' : '';
        return `
            <div class="feed-item anim-fade-in-up" style="animation-delay: ${i * 40}ms" onclick="zoomToPothole(${p.lat}, ${p.lng}, '${p.id}')">
                <div class="feed-icon" style="background:${cfg.color}15; color:${cfg.color}">
                    ${cfg.icon}
                </div>
                <div class="feed-details">
                    <div class="feed-location">${p.description || `Pothole at ${p.lat.toFixed(4)}, ${p.lng.toFixed(4)}`}</div>
                    <div class="feed-meta">
                        <span>${p.severity.toUpperCase()}${resolvedTag}</span>
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
// SMART TOOLTIP (HOVER)
// ══════════════════════════════════════════════════════════
let tooltipTimeout;

function createTooltipDOM() {
    if (document.getElementById('smartTooltip')) return;
    const tt = document.createElement('div');
    tt.id = 'smartTooltip';

    tt.addEventListener('mouseenter', () => clearTimeout(tooltipTimeout));
    tt.addEventListener('mouseleave', () => {
        tooltipTimeout = setTimeout(() => {
            tt.classList.remove('visible');
        }, 300);
    });

    document.body.appendChild(tt);
}

function showSmartTooltip(p, isResolved, e) {
    const tt = document.getElementById('smartTooltip');
    if (!tt) return;

    clearTimeout(tooltipTimeout);

    const cfg = SEVERITY_CONFIG[p.severity] || SEVERITY_CONFIG.medium;
    const firstDate = new Date(p.detected_at).toLocaleDateString();
    const lastVer = p.last_verified_at ? new Date(p.last_verified_at).toLocaleDateString() : firstDate;

    let btnHtml = '';
    if (!isResolved) {
        btnHtml = `<button class="st-action-btn" onclick="markManuallyResolved(${p.id})">Mark as Resolved</button>`;
    }

    // New optimized Glassmorphic Tooltip UI
    tt.innerHTML = `
        <div class="st-header" style="border-bottom: 1px solid ${cfg.color}40;">
            <div class="st-severity">
                <div class="st-icon-wrap" style="background: ${cfg.color}20; color: ${cfg.color};">
                    ${cfg.icon}
                </div>
                <span style="color: ${cfg.color}; font-weight: 800;">${cfg.label}</span>
            </div>
            <div class="st-status ${isResolved ? 'resolved' : 'active'}">${isResolved ? 'RESOLVED' : 'ACTIVE'}</div>
        </div>
        <div class="st-body">
            <div class="st-row">
                <span class="st-label">Vehicles Verified</span>
                <span class="st-val highlight">${p.verified_count}</span>
            </div>
            <div class="st-row">
                <span class="st-label">First Detected</span>
                <span class="st-val">${firstDate}</span>
            </div>
            <div class="st-row">
                <span class="st-label">Last Ping</span>
                <span class="st-val">${lastVer}</span>
            </div>
        </div>
        ${btnHtml}
    `;

    tt.id = 'smartTooltip';
    tt.className = 'visible glass-panel'; // ID styles handles the rest

    const rect = tt.getBoundingClientRect();
    let left = e.clientX + 20; // slightly more offset
    let top = e.clientY + 20;

    if (left + rect.width > window.innerWidth) {
        left = e.clientX - rect.width - 20;
    }
    if (top + rect.height > window.innerHeight) {
        top = e.clientY - rect.height - 20;
    }

    tt.style.left = `${left}px`;
    tt.style.top = `${top}px`;
}

async function markManuallyResolved(id) {
    const tt = document.getElementById('smartTooltip');
    if (tt) tt.classList.remove('visible');

    // Live Removal: Update local state immediately for instant feedback
    const pIndex = potholeData.findIndex(p => p.id === id);
    if (pIndex !== -1) {
        // Transfer from active to resolved locally
        const p = potholeData.splice(pIndex, 1)[0];
        p.status = 'resolved';
        resolvedData.push(p);
        
        // Remove marker from map immediately
        if (markers[id]) {
            markers[id].map = null;
            delete markers[id];
        }
        
        // Refresh UI stats and feed locally
        updateVisibleStats();
    }

    try {
        const res = await fetch(`${CONFIG.API_BASE}/potholes/${id}/resolve`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast('Hazard manually marked as resolved', 'success');
            // Final sync to ensure server state
            loadAllData();
        } else {
            showToast('Failed to resolve', 'error');
            loadAllData(); // Revert
        }
    } catch (e) {
        showToast('Network error resolving hazard', 'error');
        loadAllData(); // Revert
    }
}



// ══════════════════════════════════════════════════════════
// SMART SEEDING & CONNECTIVITY
// ══════════════════════════════════════════════════════════
async function performSmartSeed() {
    if (!map) return;
    showToast('Locating and initializing Smart Scan...', 'info');

    // Aggressively fetch physical location for Smart Seed
    let center = { lat: map.getCenter().lat(), lng: map.getCenter().lng() };

    if (navigator.geolocation) {
        try {
            const pos = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 8000
                });
            });
            center = { lat: pos.coords.latitude, lng: pos.coords.longitude };

            // Pan map securely to user's real location before seeding
            map.panTo(center);
            map.setZoom(16);
            updateMyLocationMarker(center.lat, center.lng);
        } catch (e) {
            console.warn("GPS fetch failed for Smart Seed. Falling back to map center.", e);
        }
    }

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

    // Theme toggle button
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);

    updateFollowBtn(); // Initialize button state on load

    const liveLocBtn = document.getElementById('liveLocationBtn');
    if (liveLocBtn) {
        liveLocBtn.addEventListener('click', () => {
            followMode = true;
            updateFollowBtn();
            if (currentLocation && map) {
                map.panTo(currentLocation);
                map.setZoom(17);
                showToast('Live tracking resumed', 'success');
            } else {
                showToast('Location not available yet', 'warning');
            }
        });
    }

    document.getElementById('closeSidebar').addEventListener('click', closeSidebar);
    document.getElementById('psOverlay').addEventListener('click', closeSidebar);
    const seedBtn = document.getElementById('seedBtn');
    if (seedBtn) seedBtn.addEventListener('click', performSmartSeed);
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) clearBtn.addEventListener('click', clearAllPotholes);
    document.getElementById('refreshBtn').addEventListener('click', () => {
        countdown = CONFIG.REFRESH_INTERVAL;
        loadAllData();
        showToast('Manual refresh triggered', 'info');
    });

    // Sidebar Action Buttons
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            const allData = [...potholeData, ...resolvedData];
            const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(allData, null, 2));
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
        document.querySelectorAll('.card, .glow-card, .panel, .stat-card').forEach(card => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

function updateFollowBtn() {
    const btn = document.getElementById('liveLocationBtn');
    if (!btn) return;
    if (followMode) {
        btn.classList.add('tracking');
    } else {
        btn.classList.remove('tracking');
    }
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
        let icon = ICONS.weather.partly, descStr = 'Cloudy';
        if (descRaw.includes('clearsky')) { icon = ICONS.weather.clear; descStr = 'Clear Sky'; }
        else if (descRaw.includes('partlycloudy')) { icon = ICONS.weather.partly; descStr = 'Partly Cloudy'; }
        else if (descRaw.includes('cloudy')) { icon = ICONS.weather.cloudy; descStr = 'Cloudy'; }
        else if (descRaw.includes('rainshowers')) { icon = ICONS.weather.rain; descStr = 'Showers'; }
        else if (descRaw.includes('rain')) { icon = ICONS.weather.rain; descStr = 'Rain'; }
        else if (descRaw.includes('snow')) { icon = ICONS.weather.snow; descStr = 'Snow'; }
        else if (descRaw.includes('fog')) { icon = ICONS.weather.fog; descStr = 'Fog'; }
        else if (descRaw.includes('thunder')) { icon = ICONS.weather.thunder; descStr = 'Thunderstorm'; }

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

        // Determine road condition & Project-Specific Warnings
        let roadCondition = 'Dry';
        let roadClass = 'dry';
        let extraWarning = '';

        if (currentlyRaining || rainInLast1Hr) {
            roadCondition = '🌊 Wet Roads — Active precipitation';
            roadClass = 'wet';
            extraWarning = '⚠️ High Pothole Risk: Water may obscure depth.';
        } else if (rainInLast5Hr) {
            roadCondition = '💧 May be Wet — Rain in last 5 hours';
            roadClass = 'may-wet';
            extraWarning = '⚠️ Moderate Pothole Risk: Puddles possible.';
        } else {
            roadCondition = '✅ Optimal scanning conditions';
            roadClass = 'dry';
            extraWarning = '';
        }

        // Temperature-based thermal sensor warnings
        if (temp > 40) {
            extraWarning += ' 🌡️ Thermal Sensor Warning: Ambient heat high.';
        } else if (temp < 5) {
            extraWarning += ' ❄️ Ice Risk: Black ice possible on roads.';
        }

        if (extraWarning) {
            roadCondition += ` <span class="weather-alert">${extraWarning}</span>`;
        }

        // Update UI elements
        const tempEl = document.getElementById('weatherTemp');
        const descEl = document.getElementById('weatherDesc');
        const iconEl = document.getElementById('weatherIcon');
        const roadTextEl = document.getElementById('roadConditionText');
        const roadDotEl = document.querySelector('.road-dot');

        if (tempEl) tempEl.textContent = `${Math.round(temp)}°C`;
        if (descEl) descEl.textContent = descStr;
        if (iconEl) iconEl.innerHTML = icon;
        if (roadTextEl) roadTextEl.innerHTML = roadCondition;
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
    else if (score > 5) { color = '#f97316'; label = 'CAUTION'; gradeLetter = 'C'; }

    animateCounter('riskScore', score);
    const crits = visible.filter(p => p.severity === 'critical').length;
    updateGrade(score, color, label, gradeLetter, visible.length, crits);

    const hasCritical = visible.some(p => p.severity === 'critical' && p.status === 'active');
    // Removed alert banner logic
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

// Banner logic removed from here

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

    [...potholeData, ...resolvedData].forEach(p => {
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
        const color = ms < 100 ? '#22c55e' : ms < 500 ? '#f97316' : '#ef4444';
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
