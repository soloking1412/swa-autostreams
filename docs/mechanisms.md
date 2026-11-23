# Candidate designs

The study does not pick a weight signal in advance. It compares four families in simulation, under the same budget and write-path rules, and recommends one.

## Opening a stream

The same opening rule is used with every signal, so that the comparison is about the signal.

- **Cost.** A burn that rises each time a stream is opened and decays over time, as Bittensor does for subnets. On top of it, a refundable bond that is lost if the stream is closed for abuse.
- **What a stream is in f02.** An `EXPLICIT` stream with a writer contract and a share map of up to 64 wallets. The opener supplies the writer. The stream starts at weight zero.
- **Slots.** Six are open. When all are taken, a new opener can displace the stream with the lowest signal, provided that stream is past its immunity period.
- **Closing.** A displaced or dead stream is removed with `RemoveStream`. Balances already earned stay claimable through the tombstone, as FIP-0118 specifies.

## Weight signals

| | Signal | Why it might work | Main worry |
|---|---|---|---|
| A. Lock flow | Moving average of net FIL locked to the stream's vault. Negative flow gets nothing. | Closest to Taoflow, which is running in production. Lockers have capital at stake. | Lockers can route the stream's emissions back to themselves, so the lock earns a yield for nothing. |
| B. Gauge vote | Votes from FIL locked for a fixed term, as in Curve gauges. | Long locks make short attacks expensive. | Vote buying, and low turnout handing control to a few wallets. |
| C. Fee-burn indexed | Moving average of fees burned that can be traced to the stream's service contracts. Emission is capped at `k` times the fees burned. | With `k` at or below 1, a wash trader burns at least as much as they receive. | With `k` at or below 1 the reward may be too small to matter to a real service. |
| D. Hybrid | The smaller of the share from A or B and the cap from C. | An attacker has to move both signals. | More parameters, harder to explain. |

Signal C matters for one more reason. It lines the automatic streams up with what FIP-0118 already does for the service stream: weight follows measured payment. It also answers the question in [budget.md](budget.md) about spending the burn without proof, because every FIL handed out is matched by FIL already burned.

## Normalisation

Whatever the signal, the SWA turns signals into weights the same way:

1. Work out the usable residual for the coming period from the projected schedule (after the gate step, with one further step reserved).
2. Multiply by `alpha`.
3. Split that among streams in proportion to their signal, subject to a per-stream cap.
4. Limit each stream's change to the maximum slope.
5. Anything not allocated stays in the burn.

Step 1 uses the same projection f02 will run at queue time, so a write the SWA builds this way is not rejected.

## Safety rails

- A cap on any single stream's weight.
- A maximum slope, which limits how fast a weight can rise.
- A minimum lifetime before a stream can be displaced, and a minimum lifetime before it earns anything.
- A global switch: `alpha` set to zero through `SetGateParams`-style governance stops all automatic allocation. Existing weights then ramp down.
- The single-multisig cancel on every increase, described in [write-path.md](write-path.md).

## Streams that already exist

Consensus and service keep their FIP-defined records. The mechanism never writes the consensus record. It writes the service record only through the existing gate. A stream created by FIP in future can be marked as managed or unmanaged. Unmanaged streams are treated like `w1` and `w2`: their weight is taken off the top before the automatic budget is computed.
