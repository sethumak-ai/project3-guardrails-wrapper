"""
Replay evaluation.

For each of the 16 unique real attack prompts logged against the actual
ZenAssist bot (baseline + hardened runs combined), this replays the prompt
through the new guardrails pipeline. Instead of calling a live LLM, the
mocked "call_llm" returns the ORIGINAL response the real bot actually gave
at the time — so this tests one specific, honest question: if the
underlying model produced exactly what it produced back then, does the
guardrails wrapper catch or stop every case that originally succeeded?

This is not testing whether injectguard's input layer alone would catch
these (that's Project 2's own evaluation). It's testing the full wrapper,
including the output filter and enforcement layers, which exist
specifically to catch leaks that get past input scoring.
"""

import csv
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardrails.pipeline import run
from guardrails.rate_limiter import RateLimiter

INPUT_CSV = os.path.join(os.path.dirname(__file__), "replay_attack_set.csv")
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "replay_eval_results.json")


def main():
    rows = list(csv.DictReader(open(INPUT_CSV, encoding="utf-8")))
    results = []

    originally_succeeded = 0
    caught_by_wrapper = 0

    for row in rows:
        prompt = row["prompt"]
        original_response = row["original_response"]
        original_succeeded = row["original_succeeded"].strip().lower() == "yes"

        if original_succeeded:
            originally_succeeded += 1

        # Fresh limiter per prompt — this evaluates each attack in
        # isolation, not the rate-limiting effect of repeated attempts
        # (that's demonstrated separately in the unit tests / demo).
        limiter = RateLimiter()

        def mock_llm(text, _resp=original_response):
            return _resp

        result = run(prompt, mock_llm, limiter, use_judge=False)

        # Did the wrapper prevent the original leak from reaching the user?
        prevented = original_succeeded and (
            result.stopped_at in ("input_scan", "enforcement_pre", "output_filter", "enforcement_post")
        )
        if prevented:
            caught_by_wrapper += 1

        results.append({
            "id": row["id"],
            "category": row["attack_category"],
            "prompt": prompt,
            "original_succeeded": original_succeeded,
            "wrapper_stopped_at": result.stopped_at,
            "wrapper_final_response": result.final_response,
            "prevented_original_leak": prevented,
        })

    print(f"Unique prompts replayed: {len(rows)}")
    print(f"Originally succeeded (real bot leaked): {originally_succeeded}")
    print(f"Prevented by guardrails wrapper: {caught_by_wrapper}/{originally_succeeded}")

    json.dump(results, open(OUTPUT_JSON, "w"), indent=2)
    print(f"Wrote {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
