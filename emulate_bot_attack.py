"""
SmartVote AI Security - Realistic Bot Attack Emulation Script
=============================================================
This script emulates real-world automated bot attacks and contrasts them
against legitimate human voting sessions to demonstrate the Random Forest ML model.
"""

import sys
import time
import json
import requests

# Ensure UTF-8 output on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_URLS = [
    "http://127.0.0.1:8001/api/v1/ml/predict-anomaly",
    "http://127.0.0.1:8000/api/v1/ml/predict-anomaly"
]

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_session(session_name, payload):
    print(f"\n[>] Sending Session Vector for: [{session_name}]")
    print(f"  Inputs: age={payload['voter_age']}, time_delta={payload['time_delta_sec']}s, "
          f"failed_otp={payload['failed_otp_attempts']}, face_match={payload['face_match_confidence']*100:.0f}%, "
          f"ip_risk={payload['ip_risk_score']}, device_changes={payload['device_change_count']}")
    
    response = None
    last_err = None
    start_t = time.time()
    
    for url in API_URLS:
        try:
            res = requests.post(url, json=payload, timeout=3)
            if res.status_code == 200:
                response = res
                break
        except Exception as e:
            last_err = e
            
    elapsed_ms = (time.time() - start_t) * 1000
    
    if response is None:
        print(f"❌ Connection Error: Backend API not reachable at port 8001 or 8000. Make sure FastAPI (main.py) is running.")
        return
            
    data = response.json()
    status_symbol = "🚨 BLOCKED" if data["is_anomaly"] else "🟢 CLEARED"
    prob_pct = data["anomaly_probability"] * 100
    
    print(f"  Result: {status_symbol} | Status: {data['status']}")
    print(f"  Random Forest Anomaly Probability: {prob_pct:.1f}%")
    print(f"  Execution Latency: {elapsed_ms:.1f} ms")
    print(f"  Reasons Flagged: {', '.join(data['reasons'])}")

def main():
    print_header("SMARTVOTE AI - REALISTIC BOT ATTACK EMULATOR")
    
    # 1. Legitimate Human Session
    human_payload = {
        "voter_id": "VOTER1001",
        "voter_age": 28,
        "time_delta_sec": 24.5,
        "login_frequency_last_hour": 1,
        "face_match_confidence": 0.95,
        "failed_otp_attempts": 0,
        "ip_risk_score": 0.05,
        "device_change_count": 0,
        "keystroke_delay_ms": 210.0,
        "mouse_movement_entropy": 0.88,
        "face_liveness_score": 0.94,
        "is_vpn_or_proxy": 0,
        "viewport_screen_ratio": 0.92
    }
    test_session("Legitimate Human Voter Session", human_payload)
    
    # 2. Single Automated Bot Attack
    bot_payload = {
        "voter_id": "VOTER1001",
        "voter_age": 28,
        "time_delta_sec": 0.8,
        "login_frequency_last_hour": 12,
        "face_match_confidence": 0.42,
        "failed_otp_attempts": 3,
        "ip_risk_score": 0.88,
        "device_change_count": 3,
        "keystroke_delay_ms": 12.0,
        "mouse_movement_entropy": 0.15,
        "face_liveness_score": 0.35,
        "is_vpn_or_proxy": 1,
        "viewport_screen_ratio": 0.45
    }
    test_session("Automated Credential Botnet Attack", bot_payload)
    
    # 3. Burst Bot Attack Emulation (5 Bot Sessions)
    print_header("EMULATING MULTI-BOT BURST ATTACK (5 Sessions)")
    bot_burst = [
        {"id": "BOT_ATTACK_01", "age": 30, "delta": 0.5, "otp": 2, "face": 0.50, "ip": 0.90, "dev": 2, "key": 15.0, "ent": 0.12, "live": 0.30, "vpn": 1, "vp": 0.40},
        {"id": "BOT_ATTACK_02", "age": 45, "delta": 1.1, "otp": 4, "face": 0.35, "ip": 0.95, "dev": 4, "key": 8.0, "ent": 0.08, "live": 0.25, "vpn": 1, "vp": 0.35},
        {"id": "BOT_ATTACK_03", "age": 22, "delta": 0.3, "otp": 3, "face": 0.60, "ip": 0.75, "dev": 1, "key": 20.0, "ent": 0.18, "live": 0.40, "vpn": 1, "vp": 0.50},
        {"id": "BOT_ATTACK_04", "age": 55, "delta": 0.9, "otp": 2, "face": 0.40, "ip": 0.82, "dev": 3, "key": 10.0, "ent": 0.10, "live": 0.32, "vpn": 1, "vp": 0.38},
        {"id": "BOT_ATTACK_05", "age": 33, "delta": 0.7, "otp": 5, "face": 0.30, "ip": 0.99, "dev": 5, "key": 5.0, "ent": 0.05, "live": 0.20, "vpn": 1, "vp": 0.30},
    ]
    
    for b in bot_burst:
        payload = {
            "voter_id": b["id"],
            "voter_age": b["age"],
            "time_delta_sec": b["delta"],
            "login_frequency_last_hour": 10,
            "face_match_confidence": b["face"],
            "failed_otp_attempts": b["otp"],
            "ip_risk_score": b["ip"],
            "device_change_count": b["dev"],
            "keystroke_delay_ms": b["key"],
            "mouse_movement_entropy": b["ent"],
            "face_liveness_score": b["live"],
            "is_vpn_or_proxy": b["vpn"],
            "viewport_screen_ratio": b["vp"]
        }
        test_session(f"Bot Instance [{b['id']}]", payload)
        time.sleep(0.3)
        
    print_header("EMULATION COMPLETE - View live results in Admin Security Center (admin.html)")

if __name__ == "__main__":
    main()
