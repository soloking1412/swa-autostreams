from fractions import Fraction as F

from autostreams import fip0118 as fip
from autostreams.headroom import table, usable
from autostreams.weights import apply_write, residual, validate


def test_gate_targets_match_the_fip_table():
    expected = ["3500", "9450", "25515", "68890.5", "186004.35", "502211.745",
                "1355971.7115", "3661123.62105"]
    assert [fip.gate_target(s) for s in range(8)] == [F(x) for x in expected]


def test_bootstrap_quarter_schedules_no_burn():
    base = fip.bootstrap_records()
    q = fip.EPOCHS_PER_QUARTER
    for e in (0, q // 3, q - 1, q):
        assert residual(base, e) == 0
    assert base[fip.SERVICE_ID].at(q) == fip.W2_BASE


def test_consensus_weight_rests_on_its_floor_after_nine_quarters():
    base = fip.bootstrap_records()
    end = fip.RAMP_QUARTERS * fip.EPOCHS_PER_QUARTER
    assert base[fip.CONSENSUS_ID].at(end) == fip.W1_FLOOR
    assert base[fip.CONSENSUS_ID].at(end * 2) == fip.W1_FLOOR


def test_gate_lag_is_about_seventeen_days():
    assert fip.GATE_LAG * 30 / 86_400 == 17


def test_full_gate_run_is_a_valid_schedule_and_ends_with_no_burn():
    base = fip.bootstrap_records()
    writes = fip.gate_writes(lambda q: True, 12)
    assert len(writes) == fip.GATE_STEPS
    assert not validate(base, writes)
    recs = base
    for w in writes:
        recs = apply_write(recs, w)
    late = 12 * fip.EPOCHS_PER_QUARTER
    assert recs[fip.SERVICE_ID].at(late) == fip.W2_CAP
    assert residual(recs, late) == 0


def test_a_stream_that_takes_the_gate_step_makes_the_gate_write_invalid():
    # FIP-0118 3.1.1: a new stream that uses part of 1 - w1 blocks the gate.
    from autostreams.weights import WeightRecord, Write

    base = fip.bootstrap_records()
    q3 = fip.MAINNET.quarter_start(3)
    greedy = Write(q3, {3: WeightRecord.constant(F(4, 100), q3)})
    gate = fip.gate_writes(lambda q: q == 2, 3)
    assert not validate(base, gate)
    assert validate(base, [greedy] + gate)


def test_headroom_numbers_used_in_the_docs():
    rows = {(r.scenario, r.quarter): r for r in table()}
    assert rows[("every gate passes", 12)].residual_max == 0
    assert max(r.residual_max for r in table() if r.scenario == "every gate passes") < F(6, 100)
    assert rows[("no gate passes", 12)].residual_min == F(40, 100)
    assert rows[("every other gate passes", 8)].residual_min == F(15, 100)


def test_usable_keeps_one_gate_step_free():
    assert usable(F(12, 100), F(20, 100)) == F(7, 100)
    assert usable(F(3, 100), F(20, 100)) == 0
    assert usable(F(3, 100), fip.W2_CAP) == F(3, 100)
