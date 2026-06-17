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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strategy import run_strategy

MM_BASE = 1_000_000
VALID_SIDES = {"B", "S"}
VALID_TYPES = {"LIMIT", "MARKET", "IOC", "FOK"}


def generate(n=200, seed=1, spread=10, quote_every=10, quote_qty=10):
    """Run the strategy into in-memory buffers and parse both CSVs."""
    o, m = io.StringIO(), io.StringIO()
    run_strategy(n, seed, spread, quote_every, quote_qty, o, m)
    o.seek(0)
    m.seek(0)
    orders = list(csv.reader(o))
    mm = list(csv.reader(m))
    return orders, mm


def split(orders):
    """Return (header, noise_rows, mm_rows) from the combined order stream."""
    header, rows = orders[0], orders[1:]
    noise = [r for r in rows if int(r[0]) < MM_BASE]
    mm = [r for r in rows if int(r[0]) >= MM_BASE]
    return header, noise, mm


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
        assert side in VALID_SIDES, side
        assert otype in VALID_TYPES, otype
        int(price)                       # must parse
        assert int(qty) >= 1, qty


def test_reproducible_with_same_seed():
    assert generate(seed=42) == generate(seed=42)


def test_different_seed_differs():
    assert generate(seed=1) != generate(seed=2)


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
