# What f02 enforces

Section numbers refer to [FIP-0118](https://github.com/filecoin-project/FIPs/blob/master/FIPS/fip-0118.md). Contract references are to [filecoin-project/solstice](https://github.com/filecoin-project/solstice).

FIP-0118 puts the hard rules in f02, the reward actor, which only changes in a network upgrade. The SWA is an FEVM contract. It can be upgraded with a FIP, both SWA multisigs and a 7-day hold, and no network upgrade. This study keeps that split and tries to stay entirely on the SWA side.

## Limits f02 applies to every SWA write

| Rule | Value | Section |
|---|---|---|
| Non-burn weights sum to at most 1 at every epoch from the write's effective epoch on | `sum(w_i) <= 1` | 2.4.8 |
| Live streams, consensus included | 8 | 2.4.9 |
| Recipients in one share map | 64 | 2.4.9 |
| Payable rows across all tombstones | 256 | 2.4.6 |
| Pending writes | 26 | 2.4.9 |
| Delay before any SWA write applies | 7 days on mainnet | 2.4.7 |
| `RegisterStream` activation epoch | at least now + timelock | 2.4.9 |

Some details that matter for design:

- **One slot for schedule-wide writes.** `SetWeightRecords` and `StepWeightRecords` are keyed by operation, not by stream. Only one of each can be pending. To change a pending write you cancel it and queue again, which restarts the timelock (2.4.7).
- **Step writes cannot be cancelled.** `CancelPending` works on every pending write except `StepWeightRecords`. Either SWA multisig can cancel on its own.
- **Removals are rationed.** Each pending `RemoveStream` reserves at least 64 tombstone rows, so at most four can be in flight (2.4.9).
- **Weights are clamped linear segments.** A record is `{v_start, slope, t_start, floor, cap}`. f02 evaluates it every epoch with no input from the SWA, so a stuck SWA stops future changes but never the split itself (2.4.1).
- **Queue-time validation uses the projected schedule.** A new write is checked against the state as it will be once the already queued writes have applied. Two increases that each fit can still be rejected together (2.4.8).

[`autostreams/weights.py`](../autostreams/weights.py) implements the record evaluation and the schedule check. The sum of clamped linear functions is piecewise linear, so it is enough to check the breakpoints. `tests/test_weights.py` compares that shortcut with checking every epoch on 3,000 random schedules.

## What f02 does not check

f02 only checks that the caller is the SWA. It does not know or care which code path inside the SWA produced the write. Section 2.4.9 says the split between the gate path and the discretionary relays "is contract behavior, not an assertion f02 has to trust".

The rule that each new stream needs an accepted FIP lives in two places: the FIP text (section 4.4) and the SWA code, where `registerStream` requires both multisigs. Neither is in f02.

## Consequence

An automatic stream mechanism can be a second mechanism path in the SWA, next to the volume gate that already exists. Shipping it would take:

- one FIP that amends the per-change FIP rule in section 4.4 for this path and specifies the mechanism,
- an SWA code upgrade through the normal hold.

It would not need a change to f02, and so no work in Lotus, Forest or Venus. If the study finds an f02 change that would help, for example more than 8 streams, it will be written up separately as optional.

## Open questions

- f02 treats `SetWeightRecords` and `StepWeightRecords` as payload-identical. The plan in [write-path.md](write-path.md) puts records for more than one stream in a step write. This needs to be confirmed against the builtin-actors code, not just the FIP text.
- The stream id is "assigned by the SWA". The SWA needs an id scheme that never reuses an id after its tombstone is gone.
