"""
Batch Evaluation Runner
Reads test_prompts.json and runs all prompts against all providers.
Use this to quickly populate the dashboard with data.

Usage:
    python scripts/batch_run.py
"""

import json
import sys
import time
from pathlib import Path

import requests

API_BASE = "http://localhost:8000/api/v1"


def run_batch():
    prompts_path = Path(__file__).parent.parent / "data" / "test_prompts.json"
    prompts      = json.loads(prompts_path.read_text())

    print(f"\n🚀 Running {len(prompts)} prompts across 3 providers...\n")

    for i, item in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] {item['category'].upper()} — {item['prompt'][:60]}…")
        payload = {
            "prompt":    item["prompt"],
            "context":   item.get("context"),
            "category":  item["category"],
            "providers": ["groq", "cerebras", "mistral"],
        }
        try:
            r = requests.post(f"{API_BASE}/run", json=payload, timeout=90)
            r.raise_for_status()
            result = r.json()
            best = result.get("best_provider", "?")
            for res in result.get("results", []):
                p = res["provider"]
                print(f"  {p:8s} → overall={res['overall_score']:.2f} | latency={res['latency_ms']:.0f}ms")
            print(f"  ✅ Best: {best}\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
        time.sleep(1)  # gentle rate limiting

    print("✅ Batch run complete! Open the dashboard to view results.")


if __name__ == "__main__":
    run_batch()