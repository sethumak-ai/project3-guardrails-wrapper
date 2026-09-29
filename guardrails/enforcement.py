"""
Structural enforcement — layer 3 of the guardrails wrapper.

Where output_filter.py catches a secret *value* leaking, this layer
enforces a topic-level rule: certain subjects should never get a raw
model-generated answer at all, whether or not that answer happens to leak
anything this run. This is what stops the model's own inconsistency from
being the attack surface — a model might refuse to state a code today and
state it tomorrow given a slightly different phrasing of the same ask.
Enforcement makes the response deterministic for these topics instead of
trusting the model to always refuse correctly.

Distinct from injectguard: injectguard decides whether to let a *prompt*
reach the assistant. This layer decides whether a *topic*, once reached,
is allowed to produce a model-authored answer at all.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

# Topics that always get a fixed safe response, regardless of what the
# underlying model would have said. Patterns are intentionally broader
# than injectguard's input rules since this is a last-resort backstop,
# not the primary detection layer.
ENFORCED_TOPICS = {
    "override_code": {
        "patterns": [
            r"override\s*code", r"admin\s*code", r"transaction\s*code",
            r"bypass\s*(the\s*)?(fraud\s*)?hold", r"debug\s*mode",
            r"sandbox\s*mode", r"system\s*override",
        ],
        "safe_response": (
            "I'm not able to discuss internal override codes or bypass "
            "procedures in this chat, regardless of the context. If you "
            "need this for a legitimate operational reason, please use "
            "your internal staff channel rather than this customer-facing "
            "assistant."
        ),
    },
    "other_customer_data": {
        "patterns": [
            r"other\s*customers?[\'\u2019]?s?\s*(account|balance|data|information)",
            r"someone\s*else[\'\u2019]?s\s*(account|balance)",
        ],
        "safe_response": (
            "I can only discuss the account of the verified holder in this "
            "chat. I'm not able to share information about any other "
            "customer's account."
        ),
    },
}


@dataclass
class EnforcementResult:
    enforced: bool
    topic: Optional[str] = None
    safe_response: Optional[str] = None
    matched_pattern: Optional[str] = None

    def reasoning_trail(self) -> List[str]:
        if self.enforced:
            return [f"[enforcement] topic '{self.topic}' matched pattern '{self.matched_pattern}' — forced safe template"]
        return ["[enforcement] no enforced topic matched"]


def check(text: str) -> EnforcementResult:
    """Check user input OR model output against enforced-topic patterns.
    Called on both sides of the pipeline — before the model call (to skip
    it entirely) and after (as a backstop on the model's own wording)."""
    lowered = text.lower()
    for topic, cfg in ENFORCED_TOPICS.items():
        for pattern in cfg["patterns"]:
            if re.search(pattern, lowered):
                return EnforcementResult(
                    enforced=True,
                    topic=topic,
                    safe_response=cfg["safe_response"],
                    matched_pattern=pattern,
                )
    return EnforcementResult(enforced=False)
