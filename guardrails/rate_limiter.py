"""
Rate limiter — layer 4 of the guardrails wrapper.

Tracks flag/block events per session and locks the session out after too
many within a rolling window. A single blocked message is normal —
repeated blocked attempts in a short span is a pattern, and a real
fintech assistant should stop engaging entirely rather than keep giving
an attacker free tries at different phrasings.

Session-scoped and in-memory by design for this demo (matches Streamlit's
session_state model). A production deployment would back this with shared
storage (Redis, etc.) keyed by user/IP rather than a single process.
"""

import time
from dataclasses import dataclass, field
from typing import List

WINDOW_SECONDS = 120
MAX_VIOLATIONS = 3


@dataclass
class RateLimiter:
    violation_timestamps: List[float] = field(default_factory=list)

    def record_violation(self) -> None:
        self.violation_timestamps.append(time.time())

    def _recent_violations(self) -> List[float]:
        cutoff = time.time() - WINDOW_SECONDS
        self.violation_timestamps = [t for t in self.violation_timestamps if t >= cutoff]
        return self.violation_timestamps

    def is_locked_out(self) -> bool:
        return len(self._recent_violations()) >= MAX_VIOLATIONS

    def violations_in_window(self) -> int:
        return len(self._recent_violations())

    def reasoning_trail(self) -> List[str]:
        count = self.violations_in_window()
        if self.is_locked_out():
            return [f"[rate_limiter] {count} violations in {WINDOW_SECONDS}s window — session locked out"]
        return [f"[rate_limiter] {count}/{MAX_VIOLATIONS} violations in {WINDOW_SECONDS}s window"]
