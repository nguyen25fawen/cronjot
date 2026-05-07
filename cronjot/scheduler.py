"""Simple cron-expression scheduler for cronjot.

Parses a minimal cron expression (5 fields: min hour dom mon dow)
and determines whether a job should run at a given datetime.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


class CronExpression:
    """Parse and evaluate a 5-field cron expression."""

    FIELDS = ("minute", "hour", "dom", "month", "dow")
    RANGES = {
        "minute": (0, 59),
        "hour": (0, 23),
        "dom": (1, 31),
        "month": (1, 12),
        "dow": (0, 6),
    }

    def __init__(self, expression: str) -> None:
        self.expression = expression
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(
                f"Cron expression must have exactly 5 fields, got: {expression!r}"
            )
        self._fields: dict[str, set[int]] = {}
        for field, part in zip(self.FIELDS, parts):
            lo, hi = self.RANGES[field]
            self._fields[field] = self._parse_field(part, lo, hi)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_field(part: str, lo: int, hi: int) -> set[int]:
        """Return the set of integers matched by a single cron field part."""
        values: set[int] = set()
        for segment in part.split(","):
            step = 1
            if "/" in segment:
                segment, step_str = segment.split("/", 1)
                step = int(step_str)
            if segment == "*":
                start, end = lo, hi
            elif "-" in segment:
                start_str, end_str = segment.split("-", 1)
                start, end = int(start_str), int(end_str)
            else:
                val = int(segment)
                values.add(val)
                continue
            values.update(range(start, end + 1, step))
        return values

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def matches(self, dt: Optional[datetime] = None) -> bool:
        """Return True if *dt* (default: now) matches this expression."""
        if dt is None:
            dt = datetime.now()
        return (
            dt.minute in self._fields["minute"]
            and dt.hour in self._fields["hour"]
            and dt.day in self._fields["dom"]
            and dt.month in self._fields["month"]
            and dt.weekday() in self._fields["dow"]  # Mon=0 … Sun=6
        )

    def __repr__(self) -> str:  # pragma: no cover
        return f"CronExpression({self.expression!r})"
