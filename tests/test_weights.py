import random
from fractions import Fraction as F

from autostreams.weights import (
    WeightRecord,
    Write,
    apply_write,
    is_valid,
    residual,
    to_fixed,
    total,
    validate,
)


def test_compute_weight_clamps_both_sides():
    r = WeightRecord(F(1, 2), F(-1, 100), 10, F(1, 5), F(1, 2))
    assert r.at(0) == F(1, 2)       # before t_start it sits on the cap
    assert r.at(10) == F(1, 2)
    assert r.at(20) == F(2, 5)
    assert r.at(40) == F(1, 5)      # reaches the floor
    assert r.at(10_000) == F(1, 5)


def test_ramp_helper_hits_target_and_holds():
    r = WeightRecord.ramp(F(0), F(3, 100), 100, 200)
    assert r.at(100) == 0
    assert r.at(150) == F(3, 200)
    assert r.at(200) == F(3, 100)
    assert r.at(999) == F(3, 100)
    assert r.well_formed()


def test_fixed_point_is_exact_for_whole_percentages():
    assert to_fixed(F(5, 100)) == 5 * 10**16
    assert to_fixed(F(1)) == 10**18


def test_out_of_band_record_is_rejected():
    bad = WeightRecord(F(3, 5), F(0), 0, F(0), F(1, 2))  # v_start above cap
    assert validate({1: bad})


def test_sum_above_one_found_at_a_later_breakpoint():
    # Valid today, but stream 2 ramps up and crosses the limit at epoch 50.
    base = {
        1: WeightRecord.constant(F(3, 5)),
        2: WeightRecord.ramp(F(1, 5), F(1, 2), 0, 100),
    }
    assert total(base, 0) < 1
    problems = validate(base)
    assert problems and all(p.total > 1 for p in problems)


def test_pending_writes_are_checked_together():
    # Each increase fits on its own. Together they go past 1.
    base = {1: WeightRecord.constant(F(1, 2)), 2: WeightRecord.constant(F(1, 5))}
    a = Write(100, {2: WeightRecord.constant(F(2, 5), 100)})
    b = Write(120, {3: WeightRecord.constant(F(1, 5), 120)})
    assert is_valid(base, [a])
    assert is_valid(base, [b])
    assert not is_valid(base, [a, b])


def test_removal_returns_weight_to_the_burn():
    base = {1: WeightRecord.constant(F(1, 2)), 2: WeightRecord.constant(F(3, 10))}
    after = apply_write(base, Write(10, {2: None}))
    assert residual(base, 10) == F(1, 5)
    assert residual(after, 10) == F(1, 2)


def test_only_epochs_from_the_effective_epoch_count():
    # The sum is above 1 before epoch 50 and fine after it.
    base = {
        1: WeightRecord.constant(F(3, 5)),
        2: WeightRecord.ramp(F(3, 5), F(1, 5), 0, 50),
    }
    assert not is_valid(base, from_epoch=0)
    assert is_valid(base, from_epoch=50)


def _random_record(rng: random.Random, horizon: int) -> WeightRecord:
    lo, hi = sorted(F(rng.randint(0, 20), 40) for _ in range(2))
    start = F(rng.randint(int(lo * 40), int(hi * 40)), 40)
    slope = F(rng.randint(-6, 6), 400)
    return WeightRecord(start, slope, rng.randint(0, horizon), lo, hi)


def test_breakpoint_check_agrees_with_checking_every_epoch():
    rng = random.Random(118)
    horizon = 120
    disagreements = 0
    for _ in range(3000):
        base = {i: _random_record(rng, horizon) for i in range(1, rng.randint(2, 4))}
        writes = [
            Write(rng.randint(1, horizon), {rng.randint(1, 4): _random_record(rng, horizon)})
            for _ in range(rng.randint(0, 3))
        ]
        fast = is_valid(base, writes)

        slow = True
        ordered = sorted(writes, key=lambda w: w.effective_epoch)
        for e in range(0, horizon * 4):
            recs = base
            for w in ordered:
                if w.effective_epoch <= e:
                    recs = apply_write(recs, w)
            if total(recs, e) > 1:
                slow = False
                break
        disagreements += fast != slow
    assert disagreements == 0
