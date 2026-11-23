# Notes on Bittensor

FIP-0118 says its design "is strongly inspired by the subnet model pioneered by Bittensor", and the RFP points to Bittensor as the reference for opening streams by market signal. These notes record what I have checked so far and where the two systems differ. The full comparison is a deliverable of the study.

## How Bittensor does it

- **Opening a subnet.** Anyone can register one by paying the current lock cost in TAO. The cost goes up when registrations are frequent and decays over time. According to the Taostats documentation (reviewed 2026-09-15) the whole cost now goes into the new subnet's liquidity pool.
- **Slots.** When the subnet limit is reached, a new registration removes the lowest-priced subnet that is out of its immunity period. Taostats gives the immunity period as 4 months and says registrations are at least 4 days apart.
- **Emission shares.** Since November 2025 ("Taoflow"), a subnet's share follows a moving average of net TAO staked into it: stake in minus stake out. Subnets with negative net flow get nothing. Before that, shares followed a moving average of each subnet's token price.

Sources: [Taostats subnet registration](https://taostats.io/docs/concepts/subnets/subnet-registration), [Taostats subnet deregistration](https://taostats.io/docs/concepts/subnets/subnet-deregistration), and press coverage of the Taoflow launch.

Not yet verified from a primary source: the exact averaging window for Taoflow (secondary sources say a 30-day half-life), the current subnet limit, and the later change from gross to net-of-protocol flows. These need to be read from the subtensor code before they are used in the comparison.

## Where Filecoin differs

| | Bittensor | Filecoin after FIP-0118 |
|---|---|---|
| Number of slots | On the order of a hundred | 8, with 6 free |
| What a slot gets | A share of all emissions | A share of the burn residual only, behind consensus and service |
| Update speed | Every block | One batch per period, 7 days after it is queued |
| Per-slot token | Each subnet has its own token and pool, so price and stake flow are natural signals | None. A stream is a share map |
| Who can stop a change | No one | Either SWA multisig, during the hold |
| Budget | Fixed | Shrinks as the service stream proves demand |

## What this suggests

- The opening rule (rising cost, immunity, lowest-signal displacement) carries over well. With only 6 slots, displacement matters more and the cost curve has to be steeper.
- Taoflow's signal needs a staking pool per subnet. A stream has none, so the lock-flow design in [mechanisms.md](mechanisms.md) has to add a vault per stream. That is new attack surface.
- Continuous reweighting does not carry over. Ramps written once a period are the replacement.
- Bittensor has no equivalent of the `w2` priority rule or of a budget that can go to zero. Those parts have to be designed fresh.

## To do

- Read the emission and registration code in subtensor and replace the secondary sources above.
- Collect what is publicly documented about gaming under price-based emissions and under Taoflow, and map each case to the list in [threats.md](threats.md).
