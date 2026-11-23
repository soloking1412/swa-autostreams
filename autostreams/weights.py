"""Weight records and the schedule check that f02 runs on every SWA write.

This follows FIP-0118 section 2.4.1 (ComputeWeight) and section 2.4.8
(schedule validation). Weights are kept as exact fractions. f02 stores them as
u64 fixed point with DENOM = 10**18, and to_fixed() gives that form.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping, Sequence

DENOM = 10**18
ONE = Fraction(1)


@dataclass(frozen=True)
class WeightRecord:
    """One stream weight: a linear segment clamped to [floor, cap]."""

    v_start: Fraction
    slope: Fraction  # change per epoch
    t_start: int
    floor: Fraction
    cap: Fraction

    def __post_init__(self) -> None:
        for name in ("v_start", "slope", "floor", "cap"):
            object.__setattr__(self, name, Fraction(getattr(self, name)))

    def well_formed(self) -> bool:
        """Per-record rule: 0 <= floor <= v_start <= cap <= 1."""
        return 0 <= self.floor <= self.v_start <= self.cap <= 1

    def at(self, epoch: int) -> Fraction:
        raw = self.v_start + self.slope * (epoch - self.t_start)
        return max(self.floor, min(self.cap, raw))

    def clamp_epochs(self) -> list[int]:
        """Epochs where the ramp meets its floor or cap and goes flat.

        A meeting point that falls between two epochs is returned as both
        neighbours, so a caller checking those epochs covers the kink.
        """
        if self.slope == 0:
            return []
        out: list[int] = []
        for bound in (self.floor, self.cap):
            x = self.t_start + (bound - self.v_start) / self.slope
            out.append(math.floor(x))
            out.append(math.ceil(x))
        return sorted(set(out))

    @staticmethod
    def constant(level, t_start: int = 0) -> "WeightRecord":
        level = Fraction(level)
        return WeightRecord(level, Fraction(0), t_start, level, level)

    @staticmethod
    def ramp(start, target, t_start: int, t_end: int) -> "WeightRecord":
        """Move linearly from start to target over [t_start, t_end], then hold."""
        start, target = Fraction(start), Fraction(target)
        if t_end <= t_start:
            raise ValueError("t_end must be after t_start")
        slope = (target - start) / (t_end - t_start)
        return WeightRecord(start, slope, t_start, min(start, target), max(start, target))


def to_fixed(x: Fraction) -> int:
    """Fraction to f02's fixed point, floored."""
    return (x.numerator * DENOM) // x.denominator


@dataclass(frozen=True)
class Write:
    """A queued change to the stream table.

    updates maps a stream id to its new record. None removes the stream, so its
    weight goes back to the burn residual.
    """

    effective_epoch: int
    updates: Mapping[int, WeightRecord | None]


Records = Mapping[int, WeightRecord]


def apply_write(records: Records, write: Write) -> dict[int, WeightRecord]:
    out = dict(records)
    for stream_id, record in write.updates.items():
        if record is None:
            out.pop(stream_id, None)
        else:
            out[stream_id] = record
    return out


def total(records: Records, epoch: int) -> Fraction:
    return sum((r.at(epoch) for r in records.values()), Fraction(0))


def residual(records: Records, epoch: int) -> Fraction:
    """The burn share w0 = 1 - sum of all other weights."""
    return ONE - total(records, epoch)


def _segment_points(records: Records, start: int, end: int | None) -> list[int]:
    """Epochs to check in [start, end). end=None means the segment never ends."""
    points = {start}
    for r in records.values():
        points.add(r.t_start)
        points.update(r.clamp_epochs())
    if end is None:
        # One point past the last breakpoint. Every weight is flat from there.
        points.add(max(points) + 1)
        return sorted(p for p in points if p >= start)
    points.add(end - 1)
    return sorted(p for p in points if start <= p < end)


def check_points(
    base: Records, writes: Sequence[Write], from_epoch: int
) -> list[tuple[int, Records]]:
    """Every (epoch, records in force) pair the schedule check has to look at."""
    ordered = sorted(writes, key=lambda w: w.effective_epoch)
    current = dict(base)
    pending = []
    for w in ordered:
        if w.effective_epoch <= from_epoch:
            current = apply_write(current, w)
        else:
            pending.append(w)

    out: list[tuple[int, Records]] = []
    start = from_epoch
    for w in pending:
        for p in _segment_points(current, start, w.effective_epoch):
            out.append((p, current))
        current = apply_write(current, w)
        start = w.effective_epoch
    for p in _segment_points(current, start, None):
        out.append((p, current))
    return out


@dataclass(frozen=True)
class Violation:
    epoch: int
    total: Fraction
    reason: str


def validate(
    base: Records, writes: Iterable[Write] = (), from_epoch: int = 0
) -> list[Violation]:
    """Check a projected schedule the way f02 does at queue time.

    Returns an empty list when the schedule is valid: every record is well
    formed and the non-burn weights sum to at most 1 at every epoch from
    from_epoch onward. Each weight is clamped linear, so the sum is piecewise
    linear and only the breakpoints need checking.
    """
    writes = list(writes)
    problems: list[Violation] = []

    seen: list[WeightRecord] = list(base.values())
    for w in writes:
        seen.extend(r for r in w.updates.values() if r is not None)
    for r in seen:
        if not r.well_formed():
            problems.append(Violation(r.t_start, r.v_start, "record out of band"))

    for epoch, records in check_points(base, writes, from_epoch):
        s = total(records, epoch)
        if s > 1:
            problems.append(Violation(epoch, s, "weights sum above 1"))
    return problems


def is_valid(base: Records, writes: Iterable[Write] = (), from_epoch: int = 0) -> bool:
    return not validate(base, writes, from_epoch)
