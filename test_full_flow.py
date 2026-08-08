import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/interview"
SESSION_ID = "my-test-session-1"

# Load a real candidate
candidates = json.load(open("data/candidates.json"))["candidates"]
candidate = candidates[0]

print("=== STARTING INTERVIEW ===")
r = requests.post(BASE_URL, json={"sessionId": SESSION_ID, "candidate": candidate})
print(r.status_code)
print(r.json()["reply"])
print()

done = r.json()["done"]
turn = 0

while not done:
    turn += 1
    time.sleep(1.5)  # small pause between turns to avoid hammering the API
    r = requests.post(BASE_URL, json={"sessionId": SESSION_ID, "message": "This is my test answer."})
    body = r.json()
    done = body["done"]
    print(f"--- Turn {turn} ---")
    print(body["reply"])
    print()
    if turn > 25:
        print("Safety stop -- something is looping.")
        break

print("=== INTERVIEW FINISHED ===")
print("Feedback:", r.json().get("feedback"))
print()

print("=== NOW TESTING THE FIX: sending one more message to the SAME session ===")
time.sleep(1.5)
r2 = requests.post(BASE_URL, json={"sessionId": SESSION_ID, "message": "test"})
print(r2.status_code)
print(r2.json())