# Attacks to cover

This is the working list for the attack analysis. Each item will get a cost estimate, a simulated outcome and a mitigation or an accepted-risk note. For scale: one point of weight is worth about 200,000 FIL a year.

## On the weight signal

- **Self-dealing.** The party that controls a stream's share map also supplies the signal (locks FIL, votes, or pays fees to its own contract). Profit is emissions received minus cost of the signal. This is the central case for every design.
- **Double counting with the service stream.** A stream spends its emissions through Filecoin Pay. That raises an Orchestrator's FPV, which raises `w2` and the Orchestrator's share. The same FIL is rewarded twice.
- **Flash locking.** Lock just before the signal is read, unlock after. The moving average and a lock that must outlast the averaging window plus the timelock are the defences to test.
- **Timelock front-running.** Weights are public 7 days before they apply. Anyone can see which stream is about to gain and position for it.

## On slots

- **Sybil streams.** One party opens several streams to take more than the per-stream cap.
- **Slot squatting.** Holding slots with minimal signal so that competitors cannot enter. The rising opening cost and lowest-signal displacement are meant to price this out.
- **Displacement griefing.** Repeatedly opening streams to knock out a legitimate one just after its immunity ends.

## On governance and collusion

- **Cartels and bribes.** Lockers or voters coordinate, or are paid, to direct weight. The question is the cost of holding a given weight for a quarter compared with what it pays.
- **Veto abuse.** One multisig cancels every increase, every quarter. The mechanism still works for reductions, so weights only fall. This is visible on chain and is the same failure FIP-0118 already accepts for discretionary writes, but the effect should be stated.

## On f02's tables

- **Payable-row filling.** A hostile writer contract grows its stream's payable table to the 128-row cap. FIP-0118 limits the damage to that stream. The opening bond should cover the cost of draining it.
- **Removal starvation.** Large recipient unions raise tombstone reservations and cut how many removals can be in flight. This slows pruning. The analysis will bound the delay.

## On the gate

- **Blocking a `w2` step.** Any sequence of automatic writes after which the gate's step write fails validation. This must be impossible, not just unlikely. It is the first property the contract tests will check.
- **Delaying the gate.** An increase batch queued so that `quarterlyGateCheck` reverts while it is pending.

## Outside shocks

- **FIL price moves.** The gate target is in USD. Locks, burns and weights are in FIL. A sharp price move changes how expensive each attack is relative to its payoff.
- **A dead SWA.** f02 keeps paying the last written records. Streams written as ramps reach their target and hold. No automatic stream should be left on a rising ramp without a cap.
