import requests
import time

# --- Configuration ---
# This is the EXACT route we created on the backend
API_URL = "http://127.0.0.1:5000/api/hardware/scan"
# The secret key to prevent unauthorized devices from adding dummy attendance
API_KEY = "unipr_hardware_key_2026"

def send_fingerprint_scan(student_id):
    """
    Called by the hardware scanner driver whenever a fingerprint or RFID card is scanned.
    """
    payload = {
        "api_key": API_KEY,
        "student_id": student_id
    }
    
    try:
        print(f"Sending scan for {student_id}...")
        response = requests.post(API_URL, json=payload, timeout=5)
        
        # Check result
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print(f"✅ SUCCESS: {data.get('message')} | Status: {data.get('status')}")
            else:
                print(f"❌ FAILED: {data.get('error')}")
        else:
            print(f"❌ HTTP ERROR: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"🔌 CONNECTION ERROR: Could not connect to the Attendance server. Is it running?")

if __name__ == "__main__":
    print("🟢 Hardware Interface Started. Waiting for scans...")
    print("--------------------------------------------------")
    
    # -------------------------------------------------------------------------
    # Example Hardware Integration: 
    # Usually, a fingerprint SDK provides a callback function when a thumb is placed.
    # We simulate a device doing 3 scans over 5 seconds.
    # -------------------------------------------------------------------------
    
    scans_from_hardware = ["STU-001", "STU-002", "STU-999"] # Example Student IDs
    
    for fingerprint_id in scans_from_hardware:
        time.sleep(2) # Simulating time between students scanning
        send_fingerprint_scan(fingerprint_id)
        print("--------------------------------------------------")
