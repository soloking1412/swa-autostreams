# The budget for new streams

## Where the weight comes from

f02 pays three things each epoch: the consensus stream (`w1`), the service stream (`w2`) and whatever is left, which is burned (`w0 = 1 - w1 - w2`). A new stream needs a weight, and the sum of non-burn weights cannot pass 1. So every new stream is paid out of what would otherwise be burned.

The schedule is fixed by FIP-0118:

- `w1` falls in a straight line from 95% to 50% over 9 quarters.
- `w2` rises from 5% to 10% during the first quarter. After that it goes up 5 points each time a quarter's Filecoin Pay volume clears the gate target, up to 50%.
- A passed gate takes effect about 17 days after the quarter ends: 3 days to post volume, 7 days to verify, 7 days of timelock.

## Residual by scenario

`python -m autostreams.headroom` runs this schedule for three cases. Numbers are the smallest and largest residual inside each quarter, as a share of the block reward.

| Quarter | Every gate passes | Every other gate passes | No gate passes |
|---|---|---|---|
| Q1 | 0 | 0 | 0 |
| Q2 | 0 to 5.0 | 0 to 5.0 | 0 to 5.0 |
| Q4 | 0.9 to 5.9 | 5.0 to 10.0 | 10.0 to 15.0 |
| Q6 | 0.9 to 5.9 | 10.0 to 15.0 | 20.0 to 25.0 |
| Q8 | 0.9 to 5.9 | 15.0 to 20.0 | 30.0 to 35.0 |
| Q10 | 0 to 5.0 | 20.0 | 40.0 |
| Q12 | 0 | 15.0 | 40.0 |

The full table is in [`results/headroom.csv`](../results/headroom.csv).

When every gate passes, the residual is a sawtooth. It grows as `w1` ramps down during the quarter, then drops when the gate write lands. It never gets past 5.9% and it is gone for good once `w2` reaches 50%.

## What this means

The space for new streams is the same thing as service demand that has not been proven. That gives the mechanism a problem the RFP text does not spell out. In the good case for Filecoin there is nothing to distribute. In the bad case there is a lot, and handing it out is the opposite of the "don't spend without proof" rule that the burn exists to enforce.

The design has to take a position on two things.

**Priority.** Section 3.1.1 of the FIP says a gate write is rejected if a discretionary write "has taken part of the ceiling `1 - w1`", and names a new stream as one way that happens. An automatic mechanism must never cause that. The rule used here: automatic streams may only use the residual left after one full gate step (5 points) is set aside, for as long as `w2` is below its cap. The "usable" column in the CSV is the residual under that rule. With every gate passing it is zero in every quarter. With no gate passing it reaches 35%.

**How much of the burn to redirect.** Even the usable part should not all be handed out by default. The design has a parameter `alpha` between 0 and 1: automatic streams share at most `alpha` times the usable residual, and the rest is still burned. `alpha` is set by SWA Governance through a FIP. The simulation will report results across a range of `alpha` so the trade-off is visible, including the effect on net issuance.

## Open questions

- Should a stream's own proven demand be able to earn it room beyond `alpha`, the way volume earns `w2` its steps? The fee-burn indexed design in [mechanisms.md](mechanisms.md) is one way to do that.
- When `w2` steps up and the residual shrinks, which automatic streams give up weight, and in what order? Pro rata is the simple answer. Lowest signal first is the alternative.
