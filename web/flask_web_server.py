#!/usr/bin/env python3

from flask import Flask, request, jsonify, send_from_directory
import os
import requests

app = Flask(__name__, static_folder=None)  # Disable default static
NAV2_API_URL = "http://localhost:8000"

# ─── PRIORITY 1: STATIC FILES ─────────────────────────────────────────────────
@app.route('/static/<path:filename>')
def serve_static(filename):
    static_path = os.path.join(os.getcwd(), 'templates', 'static', filename)
    if os.path.exists(static_path):
        return send_from_directory(os.path.dirname(static_path), filename)
    return "Static file not found: " + static_path, 404

# ─── PRIORITY 2: ROOT ─────────────────────────────────────────────────────────
@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
def catch_all(path):
    if path == 'index.html' or path == '':
        return send_from_directory(os.path.join(os.getcwd(), 'templates'), 'index.html')
    return "Not found: " + path, 404

# ─── API ROUTES (lowest priority) ─────────────────────────────────────────────
@app.route('/goto', methods=['POST'])
def goto():
    data = request.get_json() or {}
    target = data.get("target")
    if not target:
        return jsonify({"error": "Missing target"}), 400
    
    try:
        r = requests.post(f"{NAV2_API_URL}/nav2_send_goal", json={"target": target}, timeout=10)
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def status():
    try:
        r = requests.get(f"{NAV2_API_URL}/status", timeout=3)
        return jsonify(r.json())
    except:
        return jsonify({"status": "disconnected"}), 200

@app.route('/locations')
def locations():
    try:
        r = requests.get(f"{NAV2_API_URL}/locations", timeout=3)
        return jsonify(r.json())
    except:
        return jsonify({
            "home": {"x": 0.0, "y": 0.0}
        })

if __name__ == '__main__': 
    print("CWD:", os.getcwd())
    print("Static path:", os.path.join(os.getcwd(), 'templates', 'static', 'style.css'))
    print("🌐 http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
