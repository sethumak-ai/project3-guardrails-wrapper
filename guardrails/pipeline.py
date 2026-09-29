"""
The guardrails pipeline — wraps ZenAssist end to end.

Flow for every user message:

  1. RATE LIMIT CHECK    — if the session is already locked out, stop here.
  2. INPUT LAYER          — injectguard.scan_prompt(). BLOCK/FLAG stops
                            here before the LLM is ever called, and counts
                            as a violation toward rate limiting.
  3. ENFORCEMENT (pre)    — even a PASS-ing input gets checked against
                            enforced topics. If matched, skip the LLM call
                            entirely and return the fixed safe response.
  4. LLM CALL             — only reached if steps 1-3 all cleared.
  5. OUTPUT FILTER        — scan the model's own response for leaked
                            secrets (exact or obfuscated), redact if found.
  6. ENFORCEMENT (post)   — backstop: if the model's response itself
                            drifted into an enforced topic even though the
                            input didn't, replace it with the safe template.

Every step is recorded so the UI can show a full reasoning trail, not just
a final verdict.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from injectguard import scan_prompt, Verdict

from . import output_filter, enforcement
from .rate_limiter import RateLimiter


@dataclass
class PipelineResult:
    final_response: str
    llm_called: bool
    stopped_at: str  # "rate_limit" | "input_scan" | "enforcement_pre" | "output_filter" | "enforcement_post" | "clean"
    trail: List[str] = field(default_factory=list)
    is_violation: bool = False


def run(
    user_input: str,
    call_llm,  # callable(user_input) -> str, only invoked if allowed through
    limiter: RateLimiter,
    use_judge: bool = False,
) -> PipelineResult:
    trail: List[str] = []

    # 1. Rate limit check
    if limiter.is_locked_out():
        trail.extend(limiter.reasoning_trail())
        return PipelineResult(
            final_response=(
                "This session has been temporarily locked due to repeated "
                "policy-violating requests. Please contact support directly "
                "if you need assistance."
            ),
            llm_called=False,
            stopped_at="rate_limit",
            trail=trail,
            is_violation=False,
        )

    # 2. Input layer — injectguard
    scan_result = scan_prompt(user_input, use_judge=use_judge, judge_backend="ollama")
    trail.append(f"[injectguard] verdict={scan_result.verdict.name} risk_score={scan_result.risk_score:.2f}")
    trail.extend(scan_result.reasoning_trail())

    if scan_result.verdict != Verdict.PASS:
        limiter.record_violation()
        trail.extend(limiter.reasoning_trail())
        response = (
            "I'm not able to process that request. Please contact support "
            "directly if you need assistance."
            if scan_result.verdict == Verdict.BLOCK
            else "Could you rephrase that? I want to make sure I'm helping "
                 "with a standard support request."
        )
        return PipelineResult(
            final_response=response,
            llm_called=False,
            stopped_at="input_scan",
            trail=trail,
            is_violation=True,
        )

    # 3. Enforcement — pre-LLM check on the input itself
    pre_enforce = enforcement.check(user_input)
    trail.extend(pre_enforce.reasoning_trail())
    if pre_enforce.enforced:
        limiter.record_violation()
        trail.extend(limiter.reasoning_trail())
        return PipelineResult(
            final_response=pre_enforce.safe_response,
            llm_called=False,
            stopped_at="enforcement_pre",
            trail=trail,
            is_violation=True,
        )

    # 4. LLM call
    raw_response = call_llm(user_input)
    trail.append("[pipeline] LLM called — input cleared all pre-checks")

    # 5. Output filter — catch leaked secrets in the response
    filter_result = output_filter.scan_output(raw_response)
    trail.extend(filter_result.reasoning_trail())
    if filter_result.leaked:
        limiter.record_violation()
        trail.extend(limiter.reasoning_trail())
        return PipelineResult(
            final_response=filter_result.redacted_text,
            llm_called=True,
            stopped_at="output_filter",
            trail=trail,
            is_violation=True,
        )

    # 6. Enforcement — backstop on the model's own response
    post_enforce = enforcement.check(raw_response)
    trail.extend(post_enforce.reasoning_trail())
    if post_enforce.enforced:
        limiter.record_violation()
        trail.extend(limiter.reasoning_trail())
        return PipelineResult(
            final_response=post_enforce.safe_response,
            llm_called=True,
            stopped_at="enforcement_post",
            trail=trail,
            is_violation=True,
        )

    return PipelineResult(
        final_response=raw_response,
        llm_called=True,
        stopped_at="clean",
        trail=trail,
        is_violation=False,
    )
