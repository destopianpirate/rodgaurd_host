"""
Pothole Detection & Road Safety Monitoring - Backend API Server
=====================================================================
Flask REST API with SQLite storage. Supports multi-vehicle collaborative
pothole verification — vehicles can verify, resolve, and discover potholes.
"""

import sqlite3
import os
import math
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'detections.db')

# Radius (meters) to consider two GPS coordinates as the "same pothole"
NEARBY_RADIUS_METERS = 30


# ─── Database Helpers ────────────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database tables with verification support."""
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS potholes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            severity TEXT DEFAULT 'medium',
            confidence REAL DEFAULT 0.0,
            area_ratio REAL DEFAULT 0.0,
            image_url TEXT,
            description TEXT,
            detected_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            verified_count INTEGER DEFAULT 0,
            last_verified_at TEXT,
            reported_by TEXT DEFAULT 'unknown',
            resolved_by TEXT,
            resolved_at TEXT,
            absent_count INTEGER DEFAULT 0
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            animal_type TEXT DEFAULT 'unknown',
            temperature REAL,
            confidence REAL DEFAULT 0.0,
            image_url TEXT,
            description TEXT,
            detected_at TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reported_by TEXT DEFAULT 'unknown'
        )
    """)
    db.commit()
    db.close()
    print("[DB] Database initialized with verification support.")


# ─── Geo Helpers ─────────────────────────────────────────────────────────────

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def find_nearby_pothole(db, lat, lng, radius_m=NEARBY_RADIUS_METERS):
    """Find the closest active pothole within the given radius."""
    rows = db.execute(
        "SELECT * FROM potholes WHERE status = 'active'"
    ).fetchall()
    
    best = None
    best_dist = float('inf')
    for row in rows:
        dist = haversine_distance(lat, lng, row["latitude"], row["longitude"])
        if dist < radius_m and dist < best_dist:
            best = row
            best_dist = dist
    return best, best_dist


# ─── Pothole Endpoints ───────────────────────────────────────────────────────

@app.route('/api/potholes', methods=['POST'])
def create_pothole():
    """Smart pothole reporting — verifies existing ones or creates new."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    lat = data.get('lat')
    lng = data.get('lng')
    if lat is None or lng is None:
        return jsonify({"error": "lat and lng are required"}), 400

    severity = data.get('severity', 'medium')
    confidence = data.get('confidence', 0.0)
    image_url = data.get('image_url', '')
    description = data.get('description', '')
    vehicle_id = data.get('vehicle_id', 'unknown')
    detected_at = data.get('detected_at', datetime.utcnow().isoformat())

    db = get_db()
    existing, distance = find_nearby_pothole(db, lat, lng)

    if existing:
        new_verified = existing["verified_count"] + 1
        # Upgrade severity if the new report says worse
        sev_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        final_severity = severity if sev_order.get(severity, 0) > sev_order.get(existing["severity"], 0) else existing["severity"]

        db.execute(
            "UPDATE potholes SET verified_count = ?, last_verified_at = ?, severity = ?, absent_count = 0 WHERE id = ?",
            (new_verified, detected_at, final_severity, existing["id"])
        )
        db.commit()
        return jsonify({"action": "verified", "id": existing["id"], "verified_count": new_verified, "severity": final_severity}), 200
    else:
        area_ratio = data.get('area_ratio', 0.0)
        cursor = db.execute(
            """INSERT INTO potholes (latitude, longitude, severity, confidence, area_ratio, 
               image_url, description, detected_at, reported_by, verified_count, last_verified_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 'active')""",
            (lat, lng, severity, confidence, area_ratio, image_url, description, detected_at, vehicle_id, detected_at)
        )
        db.commit()
        return jsonify({"action": "created", "id": cursor.lastrowid}), 201


@app.route('/api/potholes', methods=['GET'])
def get_potholes():
    """Get potholes with filtering by status and severity."""
    db = get_db()
    status = request.args.get('status', 'active')
    severity = request.args.get('severity')
    
    query = "SELECT * FROM potholes WHERE 1=1"
    params = []
    
    if status != 'all':
        query += " AND status = ?"
        params.append(status)
    if severity:
        query += " AND severity = ?"
        params.append(severity)
        
    query += " ORDER BY detected_at DESC"
    rows = db.execute(query, params).fetchall()
    
    return jsonify([{
        "id": r["id"], "lat": r["latitude"], "lng": r["longitude"],
        "severity": r["severity"], "confidence": r["confidence"],
        "area_ratio": r["area_ratio"], "detected_at": r["detected_at"],
        "status": r["status"], "verified_count": r["verified_count"],
        "reported_by": r["reported_by"], "description": r["description"]
    } for r in rows])


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get dashboard stats summary."""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM potholes WHERE status = 'active'").fetchone()[0]
    resolved = db.execute("SELECT COUNT(*) FROM potholes WHERE status = 'resolved'").fetchone()[0]
    
    severity_breakdown = {}
    for sev in ['low', 'medium', 'high', 'critical']:
        count = db.execute("SELECT COUNT(*) FROM potholes WHERE status = 'active' AND severity = ?", (sev,)).fetchone()[0]
        severity_breakdown[sev] = count
        
    return jsonify({
        "total_active": total,
        "total_resolved": resolved,
        "severity_breakdown": severity_breakdown
    })


# ─── Smart Seeding ──────────────────────────────────────────────────────────

@app.route('/api/seed', methods=['POST'])
def seed_data():
    """Smart Seed: Generate road-aligned demo potholes with contextual descriptions."""
    data = request.json or {}
    center_lat = data.get('lat', 28.6139)
    center_lng = data.get('lng', 77.2090)
    places = data.get('places', [])  # Now an array of dicts: {'name': '...', 'lat': ..., 'lng': ...}
    
    db = get_db()
    vehicles = ["ROADGUARD-01", "ROADGUARD-02", "PILOT-ALPHA", "TEST-CAR-X"]
    
    potholes_created = 0

    if places:
        # User is in an area with roads/businesses found by Google Places
        for place in places:
            # We spawn exactly AT the place's coordinates, maybe slightly wiggled (max ~10m) 
            # to simulate it being right outside the building on the road/curb.
            p_lat = place['lat'] + random.uniform(-0.0001, 0.0001)
            p_lng = place['lng'] + random.uniform(-0.0001, 0.0001)
                
            severity = random.choice(['low', 'medium', 'high', 'critical'])
            timestamp = (datetime.utcnow() - timedelta(hours=random.randint(1, 48))).isoformat()
            
            description = f"Reported hazard near {place['name']}"

            db.execute('''
                INSERT INTO potholes (latitude, longitude, severity, detected_at, status, description, confidence, reported_by, area_ratio, verified_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p_lat, p_lng, severity, timestamp, 'active',
                description, round(random.uniform(0.7, 0.99), 2),
                random.choice(vehicles), round(random.uniform(0.05, 0.4), 3),
                random.randint(1, 4)
            ))
            potholes_created += 1
    else:
        # Fallback if the user is in the middle of nowhere and Google Places returns ZERO_RESULTS
        num_potholes = random.randint(5, 10)
        for _ in range(num_potholes):
            p_lat = center_lat + random.uniform(-0.004, 0.004)
            p_lng = center_lng + random.uniform(-0.004, 0.004)
                
            severity = random.choice(['low', 'medium', 'high', 'critical'])
            timestamp = (datetime.utcnow() - timedelta(hours=random.randint(1, 48))).isoformat()
            description = f"Detected at road segment ({p_lat:.4f}, {p_lng:.4f})"

            db.execute('''
                INSERT INTO potholes (latitude, longitude, severity, detected_at, status, description, confidence, reported_by, area_ratio, verified_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p_lat, p_lng, severity, timestamp, 'active',
                description, round(random.uniform(0.7, 0.99), 2),
                random.choice(vehicles), round(random.uniform(0.05, 0.4), 3),
                random.randint(1, 4)
            ))
            potholes_created += 1

    db.commit()
    return jsonify({"status": "success", "potholes": potholes_created})


@app.route('/api/potholes/<int:pothole_id>/resolve', methods=['POST'])
def resolve_pothole(pothole_id):
    """Manually mark a pothole as resolved."""
    db = get_db()
    cursor = db.execute("UPDATE potholes SET status = 'resolved' WHERE id = ?", (pothole_id,))
    db.commit()
    if cursor.rowcount == 0:
        return jsonify({"status": "error", "message": "Pothole not found"}), 404
    return jsonify({"status": "success", "message": f"Pothole {pothole_id} resolved"})


@app.route('/api/clear', methods=['POST'])
def clear_data():
    """Delete all pothole records from the database."""
    db = get_db()
    db.execute("DELETE FROM potholes")
    db.commit()
    return jsonify({"status": "success", "message": "All potholes cleared"})


@app.route('/api/potholes/<int:pothole_id>', methods=['DELETE'])
def delete_pothole(pothole_id):
    """Delete a specific pothole record."""
    db = get_db()
    cursor = db.execute("DELETE FROM potholes WHERE id = ?", (pothole_id,))
    db.commit()
    if cursor.rowcount == 0:
        return jsonify({"status": "error", "message": "Pothole not found"}), 404
    return jsonify({"status": "success"})


@app.route('/api/potholes/<int:pothole_id>', methods=['PUT'])
def update_pothole(pothole_id):
    """Update a specific pothole record (Admin action)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    db = get_db()
    existing = db.execute("SELECT * FROM potholes WHERE id = ?", (pothole_id,)).fetchone()
    if not existing:
        return jsonify({"status": "error", "message": "Pothole not found"}), 404

    lat = data.get('lat', existing['latitude'])
    lng = data.get('lng', existing['longitude'])
    severity = data.get('severity', existing['severity'])
    confidence = data.get('confidence', existing['confidence'])
    status = data.get('status', existing['status'])
    description = data.get('description', existing['description'])

    db.execute(
        "UPDATE potholes SET latitude=?, longitude=?, severity=?, confidence=?, status=?, description=? WHERE id = ?",
        (lat, lng, severity, confidence, status, description, pothole_id)
    )
    db.commit()
    return jsonify({"status": "success"})



# ─── Health check ───────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

@app.route('/', methods=['GET'])
def index():
    return jsonify({"name": "RoadGuard API v2.1", "status": "running"})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
