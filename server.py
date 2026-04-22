from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import googlemaps
from datetime import datetime
import random
import time

app = Flask(__name__)
CORS(app)

# ============================================================
# GOOGLE MAPS CONFIGURATION
# ============================================================
GOOGLE_MAPS_KEY = "AIzaSyDOek4WbbXDFdMfWUI-3qOtFAxaGQvDE-U"
gmaps = None

try:
    if GOOGLE_MAPS_KEY and "AIza" in GOOGLE_MAPS_KEY:
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_KEY)
        print("✓ Google Maps Client Initialized")
except Exception as e:
    print(f"! Google Maps Initialization Failed: {e}")

# ============================================================
# EXPANDED LIVE TRAFFIC STATE (DELHI NCR REGION)
# ============================================================
# Detailed segments covering major Delhi-NCR corridors
TRAFFIC_STATE = {
    # CENTRAL & INNER RING
    "DLI_001": {"name": "Connaught Place Ring", "region": "Central", "v_count": 420},
    "DLI_002": {"name": "ITO Junction", "region": "Central", "v_count": 890},
    "DLI_003": {"name": "India Gate Circle", "region": "Central", "v_count": 310},
    "DLI_004": {"name": "Mandi House Roundabout", "region": "Central", "v_count": 250},
    
    # SOUTH & AIRPORT
    "DLI_010": {"name": "AIIMS Flyover", "region": "South", "v_count": 920},
    "DLI_011": {"name": "Nehru Place", "region": "South", "v_count": 780},
    "DLI_012": {"name": "Saket District Centre", "region": "South", "v_count": 450},
    "DLI_013": {"name": "NH-48 Mahipalpur", "region": "South", "v_count": 1100},
    "DLI_014": {"name": "IGI Airport T3 Link", "region": "South", "v_count": 560},
    "DLI_015": {"name": "IIT Flyover", "region": "South", "v_count": 680},
    
    # NORTH & WEST
    "DLI_020": {"name": "Kashmere Gate ISBT", "region": "North", "v_count": 950},
    "DLI_021": {"name": "Civil Lines", "region": "North", "v_count": 320},
    "DLI_022": {"name": "Rajouri Garden", "region": "West", "v_count": 740},
    "DLI_023": {"name": "Dwarka More", "region": "West", "v_count": 880},
    "DLI_024": {"name": "Janakpuri District Centre", "region": "West", "v_count": 610},
    
    # EAST & NOIDA
    "DLI_030": {"name": "Anand Vihar ISBT", "region": "East", "v_count": 1050},
    "DLI_031": {"name": "Akshardham Temple Link", "region": "East", "v_count": 680},
    "DLI_032": {"name": "DND Flyway (Noida Side)", "region": "Noida", "v_count": 890},
    "DLI_033": {"name": "Noida Sector 18 (GIP)", "region": "Noida", "v_count": 920},
    "DLI_034": {"name": "Botanical Garden", "region": "Noida", "v_count": 750},
    "DLI_035": {"name": "Greater Noida Expy (Sec 93)", "region": "Noida", "v_count": 540},
    
    # GURUGRAM & OTHERS
    "DLI_040": {"name": "IFFCO Chowk", "region": "Gurgaon", "v_count": 980},
    "DLI_041": {"name": "Cyber City (DLF Ph 3)", "region": "Gurgaon", "v_count": 1150},
    "DLI_042": {"name": "Sohna Road (Vatika)", "region": "Gurgaon", "v_count": 720},
    "DLI_043": {"name": "Golf Course Ext Rd", "region": "Gurgaon", "v_count": 410},
    "DLI_044": {"name": "Badshapur", "region": "Gurgaon", "v_count": 580},
}

# Add generated stats for each
for sid in TRAFFIC_STATE:
    s = TRAFFIC_STATE[sid]
    v_c = int(s["v_count"])
    s["v_count"] = v_c
    s["speed"] = max(5, min(80, 100 - (v_c // 12)))
    if v_c > 800: s["level"] = "high"
    elif v_c > 400: s["level"] = "medium"
    else: s["level"] = "low"

def update_traffic_engine():
    """Simulates realistic traffic fluctuations across the whole network."""
    for sid in TRAFFIC_STATE:
        s = TRAFFIC_STATE[sid]
        # Peak hours vs normal logic
        h = time.localtime().tm_hour
        is_peak = (8 <= h <= 10) or (17 <= h <= 20)
        
        flux = random.randint(-15, 15) if not is_peak else random.randint(10, 40)
        v_c = int(s["v_count"]) + flux
        v_c = max(50, min(1400, v_c))
        s["v_count"] = v_c
        
        # Recalculate speed and level
        speed = max(4, min(80, 100 - (v_c // 11)))
        s["speed"] = int(speed)
        if v_c > 850: s["level"] = "high"
        elif v_c > 450: s["level"] = "medium"
        else: s["level"] = "low"

# ============================================================
# API ROUTES
# ============================================================

@app.route('/', methods=['GET'])
def index():
    try:
        return send_file('index.html')
    except Exception as e:
        return jsonify({"error": str(e)}), 404

@app.route('/traffic', methods=['GET'])
def get_primary_stats():
    """Fetches real-time traffic from Google Maps or falls back to simulation."""
    update_traffic_engine()
    
    # Origins and Destinations for the primary corridor (CP to Airport)
    origin = "Connaught Place, Delhi"
    destination = "IGI Airport, Delhi"

    if gmaps:
        try:
            # Call Distance Matrix for LIVE Traffic
            now = datetime.now()
            result = gmaps.distance_matrix(
                origins=origin,
                destinations=destination,
                mode="driving",
                departure_time=now,
                traffic_model="pessimistic"
            )
            
            if result['status'] == 'OK':
                # Return the actual Google response for the dashboard to use
                return jsonify(result)
        except Exception as e:
            print(f"API Error: {e}")

    # Fallback to Local Simulation if API fails or is not configured
    air = TRAFFIC_STATE["DLI_013"] # NH-48 Mahipalpur area
    dist = 14.5
    travel_time = round((dist / max(5, int(air["speed"]))) * 60)
    
    return jsonify({
        "status": "OK",
        "rows": [{
            "elements": [{
                "distance": {"text": f"{dist} km", "value": dist*1000},
                "duration": {"text": f"{round(dist/80*60)} mins", "value": round(dist/80*3600)},
                "duration_in_traffic": {"text": f"{travel_time} mins", "value": travel_time*60},
                "status": "OK"
            }]
        }],
        "simulated": True
    })

@app.route('/segments', methods=['GET'])
def get_all_segments():
    """Returns the full Delhi NCR live traffic status."""
    update_traffic_engine()
    return jsonify(TRAFFIC_STATE)

@app.route('/simulate-incident', methods=['POST'])
def trigger_incident():
    data = request.json
    sid = data.get("id", "DLI_013")
    if sid in TRAFFIC_STATE:
        TRAFFIC_STATE[sid]["v_count"] = 1350 
        TRAFFIC_STATE[sid]["level"] = "high"
        TRAFFIC_STATE[sid]["speed"] = 3
        return jsonify({"status": "INCIDENT_REPORTED", "location": TRAFFIC_STATE[sid]["name"]})
    return jsonify({"error": "Location not found"}), 404

if __name__ == '__main__':
    print(f"NexRoute LIVE DELHI NCR ENGINE starting on http://127.0.0.1:5000")
    print(f"Monitoring {len(TRAFFIC_STATE)} locations...")
    app.run(debug=True, port=5000)
