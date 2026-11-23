"""Parameters and the w1/w2 schedule from FIP-0118 (mainnet values)."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable

from .weights import WeightRecord, Write

CONSENSUS_ID = 1
SERVICE_ID = 2

EPOCHS_PER_QUARTER = 262_974
POST_PERIOD = 8_640           # 3 days
VERIFICATION_WINDOW = 20_160  # 7 days
SWA_TIMELOCK = 20_160         # 7 days

MAX_STREAMS = 8               # consensus included
MAX_RECIPIENTS = 64
MAX_TOMBSTONE_ROWS = 256
MAX_PENDING_WRITES = 26

W1_START = Fraction(95, 100)
W1_FLOOR = Fraction(50, 100)
RAMP_QUARTERS = 9

W2_START = Fraction(5, 100)
W2_BASE = Fraction(10, 100)
W2_STEP = Fraction(5, 100)
W2_CAP = Fraction(50, 100)
GATE_STEPS = int((W2_CAP - W2_BASE) / W2_STEP)  # 8

VOL_TARGET_ENTRY = Fraction(3500)
VOL_TARGET_RATIO = Fraction(27, 10)

# Earliest a passed gate can take effect after the measured quarter ends.
GATE_LAG = POST_PERIOD + VERIFICATION_WINDOW + SWA_TIMELOCK


@dataclass(frozen=True)
class Params:
    """Timing values. Mainnet by default; calibnet and devnets use shorter ones."""

    epochs_per_quarter: int = EPOCHS_PER_QUARTER
    gate_lag: int = GATE_LAG

    def quarter_start(self, q: int) -> int:
        """First epoch of quarter q, counted from activation. Quarters start at 1."""
        return (q - 1) * self.epochs_per_quarter

    def quarter_of(self, epoch: int) -> int:
        return epoch // self.epochs_per_quarter + 1


MAINNET = Params()


def gate_target(steps: int) -> Fraction:
    """USD volume needed for the next step-up, given steps already passed."""
    if not 0 <= steps < GATE_STEPS:
        raise ValueError("steps out of range")
    return VOL_TARGET_ENTRY * VOL_TARGET_RATIO**steps


def bootstrap_records(p: Params = MAINNET) -> dict[int, WeightRecord]:
    """The two records the Solstice migration installs."""
    slope = (W1_START - W1_FLOOR) / (RAMP_QUARTERS * p.epochs_per_quarter)
    return {
        CONSENSUS_ID: WeightRecord(W1_START, -slope, 0, W1_FLOOR, W1_START),
        SERVICE_ID: WeightRecord(W2_START, slope, 0, W2_START, W2_BASE),
    }


def gate_writes(
    passes: Callable[[int], bool], horizon_quarters: int, p: Params = MAINNET
) -> list[Write]:
    """The w2 step writes produced by the volume gate.

    passes(q) says whether quarter q clears its target. The first gated quarter
    is 2. Each check is assumed to run as early as allowed, so a pass applies
    gate_lag epochs after the quarter ends.
    """
    writes: list[Write] = []
    steps = 0
    for q in range(2, horizon_quarters + 1):
        if steps >= GATE_STEPS:
            break
        if not passes(q):
            continue
        steps += 1
        level = W2_BASE + steps * W2_STEP
        effective = p.quarter_start(q + 1) + p.gate_lag
        writes.append(
            Write(effective, {SERVICE_ID: WeightRecord.constant(level, p.quarter_start(q))})
        )
    return writes
