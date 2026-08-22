import json
import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.evaluator import run_ai_evaluation

def main():
    print("--- RUNNING RECOVERAI PHASE 3 AI EVALUATION (v2.1 TEST SPLIT) ---")
    summary = run_ai_evaluation(sample_size=200)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
