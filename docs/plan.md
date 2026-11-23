# What comes next

## Done

- Model of weight records and f02's schedule check, with tests.
- FIP-0118 schedule and gate model.
- Burn residual analysis for three demand scenarios.
- First pass at constraints, write path, candidate designs and threat list.

## Next

**1. Finish the constraint model.** Add the pending-write queue (slots, cancellation, stranded writes), the stream cap and the tombstone reservation rule, and test them against the mocks in the solstice repo.

**2. Simulation.** An agent-based model with honest service streams, wash traders, Sybil openers, cartels and flash lockers. It sweeps `alpha`, the fee-burn multiple `k`, the averaging window, the immunity period and the opening cost curve, for each demand scenario and each of the four signals. Every write the simulated SWA proposes goes through the schedule check first. The first Solstice quarter ends around 18 January 2027, and its real volume data will be used to calibrate.

**3. Reference contract.** An SWA v2 written against `filecoin-project/solstice`:

- storage laid out so the repo's storage-layout check passes (append-only, ERC-7201 namespaces),
- Foundry invariant tests and Halmos checks for three properties: weights never sum above 1 at any breakpoint, no reachable state makes the gate's step write fail, and slot and queue limits hold,
- an upgrade rehearsal on a mainnet fork with the repo's `Rehearse.s.sol`.

**4. Run it against the real f02.** First on a local Lotus devnet. Lotus devnets can install a custom SWA through the `RewardSWA` genesis setting, with a 50-epoch timelock. Then on calibnet in shadow mode: the contract computes and publishes the writes it would queue, with no authority over the live SWA. Calibnet runs Solstice with one-day quarters and a six-hour hold, so about 30 full cycles fit in a month.

**5. Write-up.** A specification for the SWA change, the attack analysis, the Bittensor comparison, and a FIP draft for the community to take forward.

## Out of scope

Deploying anything to mainnet, and getting the FIP accepted. Both belong to the community and SWA Governance.
