"""Structural tests for the market-making strategy generator.

Run from anywhere:  python tools/test_strategy.py

These don't run the C++ engine -- they assert that run_strategy() emits a
well-formed, self-consistent pair of CSVs (the combined order stream and the
registration sidecar). The invariants here are what the rest of the pipeline
relies on: id ranges, the sidecar matching the MM orders, quotes straddling mid.
"""
import csv
import io
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategy import run_strategy, step_mid

MM_BASE = 1_000_000
VALID_SIDES = {"B", "S"}
VALID_TYPES = {"LIMIT", "MARKET", "IOC", "FOK"}


def generate(n=200, seed=1, spread=10, quote_every=10, quote_qty=10,
             market_spread=6, p_storm=0.005, p_calm=0.02, storm_mult=3, W=30, k=0):
    """Run the strategy into in-memory buffers and parse both CSVs.

    k defaults to 0 (vol-scaling off) so the structural tests see a static
    spread; the vol-scaling tests below turn it on explicitly.
    """
    o, m = io.StringIO(), io.StringIO()
    run_strategy(n, seed, market_spread, spread, quote_every, quote_qty,
                 p_storm, p_calm, storm_mult, W, k, o, m)
    o.seek(0)
    m.seek(0)
    orders = list(csv.reader(o))
    mm = list(csv.reader(m))
    return orders, mm


def split(orders):
    """Return (header, noise_rows, mm_quote_rows) -- CANCEL rows excluded from mm."""
    header, rows = orders[0], orders[1:]
    noise = [r for r in rows if int(r[0]) < MM_BASE]
    mm = [r for r in rows if int(r[0]) >= MM_BASE and r[2] != "CANCEL"]
    return header, noise, mm


def mm_cancels(orders):
    """MM-range CANCEL rows, in stream order."""
    return [r for r in orders[1:] if int(r[0]) >= MM_BASE and r[2] == "CANCEL"]


def straddles(orders):
    """Full quote width (ask - bid) for each MM bid/ask pair, in stream order."""
    _, _, mm_orders = split(orders)
    return [int(mm_orders[i + 1][3]) - int(mm_orders[i][3])
            for i in range(0, len(mm_orders), 2)]


def test_headers():
    orders, mm = generate()
    assert orders[0] == ["id", "side", "type", "price", "qty"], orders[0]
    assert mm[0] == ["id", "side"], mm[0]


def test_noise_order_count():
    """One noise order per step."""
    orders, _ = generate(n=200, quote_every=10)
    _, noise, _ = split(orders)
    assert len(noise) == 200, len(noise)


def test_mm_order_count():
    """Two MM quotes per quote block; sidecar has one row each."""
    orders, mm = generate(n=200, quote_every=10)
    _, _, mm_orders = split(orders)
    expected = 2 * (200 // 10)
    assert len(mm_orders) == expected, len(mm_orders)
    assert len(mm) - 1 == expected, len(mm) - 1     # minus header


def test_mm_ids_reserved_and_contiguous():
    """MM ids start at MM_BASE and increment by one, no gaps."""
    orders, _ = generate(n=200, quote_every=10)
    _, _, mm_orders = split(orders)
    ids = [int(r[0]) for r in mm_orders]
    assert ids == list(range(MM_BASE, MM_BASE + len(ids))), ids[:5]


def test_noise_ids_contiguous():
    orders, _ = generate(n=200)
    _, noise, _ = split(orders)
    ids = [int(r[0]) for r in noise]
    assert ids == list(range(1, 201)), ids[:5]


def test_quotes_straddle_mid_by_spread():
    """Each bid/ask pair is exactly 2*spread apart (bid=mid-s, ask=mid+s)."""
    spread = 10
    orders, _ = generate(n=200, quote_every=10, spread=spread)
    _, _, mm_orders = split(orders)
    for i in range(0, len(mm_orders), 2):
        bid, ask = mm_orders[i], mm_orders[i + 1]
        assert bid[1] == "B" and ask[1] == "S", (bid, ask)
        assert int(ask[3]) - int(bid[3]) == 2 * spread, (bid[3], ask[3])


def test_mm_qty_is_constant():
    orders, _ = generate(quote_qty=7)
    _, _, mm_orders = split(orders)
    assert all(int(r[4]) == 7 for r in mm_orders), [r[4] for r in mm_orders[:5]]


def test_sidecar_matches_mm_orders():
    """Every (id, side) in the sidecar matches an MM order, and vice versa."""
    orders, mm = generate()
    _, _, mm_orders = split(orders)
    from_orders = {(int(r[0]), r[1]) for r in mm_orders}
    from_sidecar = {(int(r[0]), r[1]) for r in mm[1:]}
    assert from_orders == from_sidecar, (from_orders ^ from_sidecar)


def test_market_orders_have_zero_price():
    orders, _ = generate(n=500)
    _, noise, _ = split(orders)
    for r in noise:
        if r[2] == "MARKET":
            assert int(r[3]) == 0, r


def test_all_fields_valid():
    orders, _ = generate(n=500)
    for r in orders[1:]:
        oid, side, otype, price, qty = r
        if otype == "CANCEL":            # cancel rows carry only an id
            assert side == "" and price == "" and qty == "", r
            continue
        assert side in VALID_SIDES, side
        assert otype in VALID_TYPES, otype
        int(price)                       # must parse
        assert int(qty) >= 1, qty


def test_recenter_cancels_prior_quotes():
    """Each quote cycle after the first CANCELs exactly the previous bid/ask pair,
    in order, and cancel rows are well-formed (id only)."""
    orders, _ = generate(n=200, quote_every=10)
    _, _, mm_quotes = split(orders)
    quote_ids = [int(r[0]) for r in mm_quotes]
    cancel_ids = [int(r[0]) for r in mm_cancels(orders)]
    # every quote pair except the final un-cancelled one gets pulled, in order
    assert cancel_ids == quote_ids[:-2], (cancel_ids[:4], quote_ids[:4])
    for r in mm_cancels(orders):
        assert r[1] == "" and r[3] == "" and r[4] == "", r


def test_reproducible_with_same_seed():
    assert generate(seed=42) == generate(seed=42)


def test_different_seed_differs():
    assert generate(seed=1) != generate(seed=2)


def test_no_orphan_quotes():
    """Every posted quote is later cancelled except the final still-live pair;
    no cancel targets a never-posted id, and none is cancelled twice. This is
    the live_ids quote-machine invariant the closed loop will depend on."""
    orders, _ = generate(n=300, seed=2, quote_every=10)
    _, _, mm_quotes = split(orders)
    posted = [int(r[0]) for r in mm_quotes]
    cancelled = [int(r[0]) for r in mm_cancels(orders)]
    assert len(cancelled) == len(set(cancelled)), "an id was cancelled twice"
    assert set(cancelled) <= set(posted), "cancel for a never-posted id"
    live = set(posted) - set(cancelled)
    assert live == set(posted[-2:]), live      # only the last round stays resting


def test_vol_scaling_off_is_constant():
    """k=0 disables vol-scaling: every quote straddles exactly 2*spread, even
    through a stormy market."""
    spread = 12
    orders, _ = generate(n=2000, seed=3, spread=spread, k=0, storm_mult=4)
    s = straddles(orders)
    assert s, "no quotes produced"
    assert all(x == 2 * spread for x in s), sorted(set(s))


def test_vol_scaling_widens_and_breathes():
    """k>0: eff_spread tracks realized vol -- quote widths exceed 2*spread, vary
    over time, and are wider on average than the k=0 control on the same seed."""
    spread = 12
    s0 = straddles(generate(n=2000, seed=3, spread=spread, k=0, storm_mult=4)[0])
    sk = straddles(generate(n=2000, seed=3, spread=spread, k=4, storm_mult=4)[0])
    assert max(sk) > 2 * spread, max(sk)                 # widened by vol
    assert len(set(sk)) > 1, "eff_spread never varied"   # breathes
    assert sum(sk) / len(sk) > sum(s0) / len(s0), (sum(sk), sum(s0))


def _move_series(n, seed, p_storm, p_calm, storm_mult):
    """Drive step_mid() directly and collect the realized mid moves."""
    random.seed(seed)
    moves, mid, stormy = [], 10000, False
    for _ in range(n):
        mid, stormy = step_mid(mid, stormy, p_storm, p_calm, storm_mult, moves)
    return moves


def _rolling_std_var(seq, w=25):
    """Variance of the rolling volatility over non-overlapping windows --
    large when vol comes in bursts, ~0 when vol is uniform."""
    stds = [statistics.pstdev(seq[i:i + w]) for i in range(0, len(seq) - w + 1, w)]
    return statistics.pvariance(stds) if len(stds) > 1 else 0.0


def test_volatility_clusters():
    """Regime-switching produces clustering, not just fat tails: the variance of
    rolling volatility is materially higher than an IID control built by
    shuffling the *same* moves (identical marginal, no time structure)."""
    moves = _move_series(8000, seed=1, p_storm=0.02, p_calm=0.05, storm_mult=5)
    clustered = _rolling_std_var(moves)
    control = moves[:]
    random.seed(99)
    random.shuffle(control)
    shuffled = _rolling_std_var(control)
    assert clustered > 1.5 * shuffled, (clustered, shuffled)


def main():
    tests = [
        test_headers,
        test_noise_order_count,
        test_mm_order_count,
        test_mm_ids_reserved_and_contiguous,
        test_noise_ids_contiguous,
        test_quotes_straddle_mid_by_spread,
        test_mm_qty_is_constant,
        test_sidecar_matches_mm_orders,
        test_market_orders_have_zero_price,
        test_all_fields_valid,
        test_recenter_cancels_prior_quotes,
        test_no_orphan_quotes,
        test_vol_scaling_off_is_constant,
        test_vol_scaling_widens_and_breathes,
        test_volatility_clusters,
        test_reproducible_with_same_seed,
        test_different_seed_differs,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: got {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
