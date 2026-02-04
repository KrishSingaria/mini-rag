import requests
import time
import json

# --- CONFIGURATION ---
BASE_URL = "http://127.0.0.1:8000"
RESET_URL = f"{BASE_URL}/reset"
INGEST_URL = f"{BASE_URL}/ingest"
CHAT_URL = f"{BASE_URL}/chat"

# 1. The Knowledge Base (The "Truth")
KNOWLEDGE_BASE = """
*** PROJECT TITAN: INTERNAL MEMO ***
Project Titan is a secret initiative to develop a solar-powered coffee machine for deep-space missions.
Lead Engineer: Dr. Aris Thorne.
Budget: $5.2 Billion.
Key Feature: "Zero-G Brewing" technology using centrifugal force to separate liquid from grounds.
Launch Date: Expected Q3 2028 onboard the Mars Vessel 'Ares V'.
Constraints: Cannot use boiling water (safety hazard); uses super-heated steam instead.
"""

# 2. The Test Set (Questions & What you expect to see)
test_cases = [
    {
        "type": "Specific (Fact)",
        "question": "What is the budget for Project Titan?",
        "expected": "$5.2 Billion"
    },
    {
        "type": "Specific (Reasoning)",
        "question": "How does it brew coffee without gravity?",
        "expected": "Centrifugal force / Zero-G Brewing"
    },
    {
        "type": "Specific (Constraint)",
        "question": "Why can't they use boiling water?",
        "expected": "Safety hazard / Uses steam instead"
    },
    {
        "type": "General Knowledge (Hybrid Test)",
        "question": "Who is the CEO of Tesla?",
        "expected": "Elon Musk (Should answer from general knowledge)"
    },
    {
        "type": "Out of Context (Hallucination Check)",
        "question": "What is the top speed of the X-9000 Scooter?",
        "expected": "Should say not found or answer generically (Project Titan doc doesn't mention scooters)"
    }
]

def run_evaluation():
    print("STARTING EVALUATION...\n")

    # STEP 1: Reset Database
    print(f"Resetting Knowledge Base...", end=" ")
    try:
        requests.post(RESET_URL)
        print("Done.")
    except Exception as e:
        print(f"Failed (Is server running?): {e}")
        return

    # STEP 2: Ingest Data
    print(f"Ingesting Knowledge Base...", end=" ")
    try:
        res = requests.post(INGEST_URL, json={"text": KNOWLEDGE_BASE})
        if res.status_code == 200:
            print(f"Success ({len(KNOWLEDGE_BASE)} chars)")
        else:
            print(f"Failed: {res.text}")
            return
    except Exception as e:
        print(f"Error: {e}")
        return

    # STEP 3: Ask Questions
    print("\nRunning Q/A Test Set...")
    print("="*80)

    # A. format the combined query
    combined_query = "Please answer these questions individually:\n"
    for i, test in enumerate(test_cases):
        combined_query += f"{i+1}. {test['question']}\n"

    print(f"Sending Payload:\n{combined_query.strip()}")
    print("-" * 40)

    start_t = time.time()
    try:
        # B. Hit the Chat Endpoint ONCE
        response = requests.post(CHAT_URL, json={"question": combined_query}).json()
        latency = time.time() - start_t
        
        actual_answer = response.get("answer", "Error: No answer")
        citations = response.get("citations", [])
        
        # C. Print the Model's Full Response
        print(f"🤖 Model Response ({latency:.2f}s):")
        print(actual_answer)
        print("-" * 40)
        
        # D. Print Citations
        if citations:
            print(f"Citations Used: {len(citations)}")
            for c in citations:
                print(f"   - [{c['id']}] {c['text'][:50]}...")
        else:
            print(f"Citations: None (General Knowledge or Logic).")

        # E. Manual Check
        print("\nComparison (Check above answer against these):")
        for i, test in enumerate(test_cases):
            print(f"   Q{i+1} Expected: '{test['expected']}'")

    except Exception as e:
        print(f"Error asking batch question: {e}")

    print("\nEVALUATION COMPLETE.")

if __name__ == "__main__":
    run_evaluation()