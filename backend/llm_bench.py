import requests
import time

url = "http://localhost:8000/chat"
messages = [
    "Hi ARYA",
    "What do you know about me?",
    "Play Naa Ready song"
]

for msg in messages:
    print(f"\nSending: {msg}")
    t0 = time.time()
    try:
        r = requests.post(url, json={"message": msg}, timeout=60)
        r.raise_for_status()
        print(f"Reply: {r.json().get('reply')}")
    except Exception as e:
        print(f"Error: {e}")
    t1 = time.time()
    print(f"Time: {int((t1-t0)*1000)} ms")

print("\n--- REPORT ---")
try:
    report = requests.get("http://localhost:8000/performance/report").json()
    for k, v in report.items():
        print(f"{k}: {v} ms")
except Exception as e:
    print(f"Report Error: {e}")
