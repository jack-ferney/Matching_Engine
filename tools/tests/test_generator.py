"""Structural tests for the synthetic order-flow generator.

Run from anywhere:  python tools/test_generator.py

These don't run the C++ engine -- they assert that generate() emits a
well-formed order stream that replay.exe can consume without crashing. The
focus is the CANCEL protocol added in Phase 10: cancel rows must be shaped
the way replay's parser expects (type==CANCEL, numeric id, empty
side/price/qty) and must reference real, still-live earlier orders.
"""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import generate

HEADER = ["id", "side", "type", "price", "qty"]
VALID_SIDES = {"B", "S"}
VALID_TYPES = {"LIMIT", "MARKET", "IOC", "FOK"}


def run(n=300, seed=1):
    """Run generate() into an in-memory buffer and parse the CSV rows."""
    buf = io.StringIO()
    generate(n, seed, buf)
    buf.seek(0)
    return list(csv.reader(buf))


def data_rows(rows):
    return rows[1:]


def cancels(rows):
    return [r for r in data_rows(rows) if r[2] == "CANCEL"]


def orders(rows):
    return [r for r in data_rows(rows) if r[2] != "CANCEL"]


def test_header():
    assert run()[0] == HEADER, run()[0]


def test_no_crash_across_seeds():
    """generate() must never raise -- covers the oid==1 empty-range edge and
    any other per-seed surprises. Sweeps a wide seed range incl. small n."""
    for seed in range(0, 100):
        run(n=300, seed=seed)
    for seed in range(0, 20):
        run(n=1, seed=seed)        # n==1: first oid, nothing earlier to cancel


def test_cancel_rows_wellformed():
    """Cancel rows: numeric id, and empty side/price/qty (replay only reads id)."""
    for r in cancels(run(n=1000, seed=3)):
        assert int(r[0]) >= 1, r            # id parses and is positive
        assert r[1] == "", r                # side empty
        assert r[3] == "", r                # price empty
        assert r[4] == "", r                # qty empty


def test_order_rows_wellformed():
    """Non-cancel rows still satisfy the original order invariants."""
    for r in orders(run(n=1000, seed=5)):
        oid, side, otype, price, qty = r
        assert side in VALID_SIDES, side
        assert otype in VALID_TYPES, otype
        int(price)                          # must parse
        assert int(qty) >= 1, qty


def test_market_orders_have_zero_price():
    for r in orders(run(n=1000, seed=7)):
        if r[2] == "MARKET":
            assert int(r[3]) == 0, r


def test_cancels_reference_live_orders():
    """Every CANCEL targets an id that was emitted as an order earlier and has
    not already been cancelled -- i.e. cancel a real resting order, never a
    phantom/gap id and never the same id twice.

    NOTE: this fails under random-id cancellation (it can pick a gap id from a
    prior cancel step, or cancel the same id twice). It passes once cancels
    pop the oldest *emitted* resting id from a FIFO queue.
    """
    rows = run(n=1500, seed=3)
    emitted, cancelled = set(), set()
    for r in data_rows(rows):
        oid = int(r[0])
        if r[2] == "CANCEL":
            assert oid in emitted, f"cancel for never-emitted id {oid}"
            assert oid not in cancelled, f"id {oid} cancelled twice"
            cancelled.add(oid)
        else:
            emitted.add(oid)
    assert cancelled, "no cancels exercised -- bump n or check cancel rate"


def test_reproducible_with_same_seed():
    assert run(seed=42) == run(seed=42)


def test_different_seed_differs():
    assert run(seed=1) != run(seed=2)


def main():
    tests = [
        test_header,
        test_no_crash_across_seeds,
        test_cancel_rows_wellformed,
        test_order_rows_wellformed,
        test_market_orders_have_zero_price,
        test_cancels_reference_live_orders,
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
