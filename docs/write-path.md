# Fitting weight changes into the queue

Bittensor recomputes subnet emission shares continuously. f02 cannot work that way: every SWA write waits 7 days, and only one weight batch of each kind can be pending. This note describes how automatic weight changes can work inside those rules.

## Ramps instead of frequent updates

A weight record is a clamped linear segment. So a reweight does not have to be a jump. Each period, the SWA writes a record that moves the weight in a straight line from where it is now to the new target by the end of the period, then holds.

This gives three things with one write per period:

- smoothing, because the weight moves gradually,
- a rate limit, because the SWA can cap the slope it is willing to write,
- predictability, because the full path is public 7 days before it starts.

`WeightRecord.ramp()` in [`autostreams/weights.py`](../autostreams/weights.py) builds this form.

## Two kinds of change, two write methods

**Reductions go with the gate.** When the quarterly gate passes, the SWA already sends an uncancellable `StepWeightRecords` write that raises `w2`. If automatic streams have to shrink to make room, their reduced records go in the same batch. f02 validates the batch as a whole, so the step and the reductions land together or not at all. A reduction only moves weight back to `w2` or to the burn, so making it uncancellable does not give anyone new power.

**Increases can be vetoed.** Raising an automatic stream's weight goes through `SetWeightRecords`. That write sits in the queue for 7 days, and either SWA multisig can cancel it alone. This is the emergency override the RFP asks about. It uses a power the multisigs already hold, so no new governance role is needed.

## Ordering inside a quarter

The deployed SWA will not run `quarterlyGateCheck` while a `SetWeightRecords` write is in its hold (`pendingWeightUntil` in `GateParams.sol`). An automatic increase queued at the wrong time would therefore delay the gate. The rule:

1. Quarter Q ends. Volume is posted and verified (10 days).
2. Anyone calls `quarterlyGateCheck` for Q. If it passes, the step write is queued, with any reductions in the same batch.
3. Only after the check for Q has run can the automatic reweight for Q be queued. It contains increases only, sized against the schedule as it will be after the step.
4. Both writes apply 7 days after they were queued.

FIP-0118 already asks for this kind of sequencing when governance changes the `w2` record by hand (section 3.1.1). The mechanism follows the same discipline in code.

## Write budget

There are 8 stream slots. Consensus and service use two, which leaves 6. Per quarter the mechanism needs at most:

- 1 step write (shared with the gate),
- 1 `SetWeightRecords` batch for increases,
- up to 6 `RegisterStream` writes and up to 4 `RemoveStream` writes in the extreme case.

That is 12 against a queue limit of 26. The spec will state the worst case exactly, including the tombstone reservations that removals need.

## Open questions

- If a multisig cancels the increase batch, the streams stay at their old weights for a quarter. Should the next period's ramp try to catch up, or start again from the current value? Starting again is safer and is the default here.
- A registration has to name its activation epoch at least 7 days ahead. Can a new stream start with weight zero and wait for the next reweight, so that opening a stream never needs room in the schedule? That looks right but needs checking against `RegisterStream` validation.
