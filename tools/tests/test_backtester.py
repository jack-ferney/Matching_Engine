"""Sanity tests for the backtester accounting.

Run from anywhere:  python tools/test_backtester.py
These exercise the PnL/position math directly via on_trade(), plus one run()
test that goes through CSV parsing. They assert the *correct* behavior, so a
failure means the engine is wrong, not the test.
"""
import os
import sys
import tempfile

# Make `import backtester` work regardless of the current working directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtester import Backtester


def test_buy_then_sell_roundtrip():
    """Buy 10@100 then sell 10@101: flat at the end, +10 realized."""
    bt = Backtester()
    bt.register(1, "B")          # my buy order
    bt.register(2, "S")          # my sell order
    bt.on_trade(1, 999, 100, 10, 1)   # I'm the aggressor, buy 10 @ 100
    bt.on_trade(2, 998, 101, 10, 2)   # I'm the aggressor, sell 10 @ 101

    assert bt.position == 0, bt.position
    assert bt.cash == 10, bt.cash
    assert bt.pnl(101) == 10, bt.pnl(101)
    # Each point is PnL *after* that fill settles. This is the reorder check:
    # buy leaves cash -1000 / pos 10 -> marked at 100 = 0; sell -> 10.
    assert bt.equity_curve == [(1, 0), (2, 10)], bt.equity_curve


def test_my_order_is_resting_side():
    """My order can be the resting side of a trade, not just the aggressor."""
    bt = Backtester()
    bt.register(5, "S")          # my resting sell
    bt.on_trade(999, 5, 100, 3, 1)    # someone hits my ask: I sell 3 @ 100

    assert bt.position == -3, bt.position
    assert bt.cash == 300, bt.cash


def test_foreign_trade_is_ignored():
    """A trade with none of my ids must not touch cash/position/curve."""
    bt = Backtester()
    bt.register(1, "B")
    bt.on_trade(50, 51, 100, 10, 1)   # neither id is mine

    assert bt.position == 0, bt.position
    assert bt.cash == 0, bt.cash
    assert bt.equity_curve == [], bt.equity_curve


def test_open_position_marked_to_market():
    """An unclosed position is valued at the mark passed to pnl()."""
    bt = Backtester()
    bt.register(1, "B")
    bt.on_trade(1, 999, 100, 5, 1)    # buy 5 @ 100, stay long

    assert bt.position == 5, bt.position
    assert bt.cash == -500, bt.cash
    assert bt.pnl(102) == 10, bt.pnl(102)   # -500 + 5*102


def test_run_parses_csv():
    """run() skips the header, casts strings to ints, and feeds on_trade."""
    bt = Backtester()
    bt.register(1, "B")
    bt.register(2, "S")
    content = (
        "aggressor_id,resting_id,price,qty,seq\n"
        "1,999,100,10,1\n"
        "2,998,101,10,2\n"
    )
    path = os.path.join(tempfile.gettempdir(), "bt_test_trades.csv")
    with open(path, "w", newline="") as f:
        f.write(content)
    try:
        bt.run(path)
    finally:
        os.remove(path)

    assert bt.position == 0, bt.position
    assert bt.cash == 10, bt.cash


def test_fills_counts_only_my_trades():
    """fills increments per *my* fill, never for foreign trades."""
    bt = Backtester()
    bt.register(1, "B")
    bt.on_trade(1, 999, 100, 5, 1)    # mine
    bt.on_trade(50, 51, 100, 5, 2)    # foreign
    assert bt.fills == 1, bt.fills


def test_last_price_updates_on_every_trade():
    """last_price tracks the most recent trade, even ones that aren't mine."""
    bt = Backtester()
    bt.register(1, "B")
    bt.on_trade(1, 999, 100, 5, 1)    # mine, price 100
    bt.on_trade(50, 51, 107, 5, 2)    # foreign, price 107
    assert bt.last_price == 107, bt.last_price


def test_last_price_defaults_to_zero():
    """A fresh backtester has no mark yet; summary PnL is flat 0."""
    bt = Backtester()
    assert bt.last_price == 0, bt.last_price
    assert bt.summary()["pnl"] == 0, bt.summary()


def test_summary_fields():
    """summary() reports position, cash, fills, and marked PnL."""
    bt = Backtester()
    bt.register(1, "B")
    bt.register(2, "S")
    bt.on_trade(1, 999, 100, 10, 1)
    bt.on_trade(2, 998, 101, 10, 2)
    assert bt.summary() == {"position": 0, "max_abs_position": 10, "cash": 10,
                            "fills": 2, "pnl": 10, "spread_pnl": 10, "inv_drift": 0,
                            "aggressive_fills": 20, "passive_fills": 0}, bt.summary()


def test_summary_marks_open_position_at_last_price():
    """An open position is valued at the last seen price, set by a foreign trade."""
    bt = Backtester()
    bt.register(1, "B")
    bt.on_trade(1, 999, 100, 5, 1)    # buy 5 @ 100, stay long
    bt.on_trade(50, 51, 110, 3, 2)    # foreign trade moves the mark to 110
    s = bt.summary()
    assert s["position"] == 5, s
    assert s["fills"] == 1, s          # foreign trade did not count as a fill
    assert s["pnl"] == 50, s           # -500 + 5*110


def test_multiple_buys_average_in():
    """Two buys at different prices accumulate; PnL marks the whole position."""
    bt = Backtester()
    bt.register(1, "B")
    bt.register(2, "B")
    bt.on_trade(1, 999, 100, 5, 1)
    bt.on_trade(2, 998, 102, 5, 2)
    assert bt.position == 10, bt.position
    assert bt.cash == -1010, bt.cash
    assert bt.pnl(102) == 10, bt.pnl(102)   # -1010 + 10*102


def test_short_then_cover():
    """Sell first (go short), then buy to flatten: realized PnL is the spread."""
    bt = Backtester()
    bt.register(1, "S")
    bt.register(2, "B")
    bt.on_trade(1, 999, 101, 10, 1)   # sell 10 @ 101 -> short
    bt.on_trade(2, 998, 100, 10, 2)   # buy 10 @ 100 -> flat
    assert bt.position == 0, bt.position
    assert bt.cash == 10, bt.cash
    assert bt.pnl(100) == 10, bt.pnl(100)


def test_equity_curve_length_matches_fills():
    """One equity point per fill; foreign trades add neither."""
    bt = Backtester()
    bt.register(1, "B")
    bt.register(2, "S")
    bt.on_trade(1, 999, 100, 10, 1)   # mine
    bt.on_trade(50, 51, 100, 10, 2)   # foreign
    bt.on_trade(2, 998, 101, 10, 3)   # mine
    assert len(bt.equity_curve) == bt.fills == 2, (bt.equity_curve, bt.fills)


def test_equity_curve_tracks_running_pnl():
    """Each point is cumulative PnL after that fill settles."""
    bt = Backtester()
    bt.register(1, "B")
    bt.register(2, "B")
    bt.register(3, "S")
    bt.on_trade(1, 999, 100, 10, 1)   # cash -1000, pos 10, mark 100 -> 0
    bt.on_trade(2, 998, 100, 10, 2)   # cash -2000, pos 20, mark 100 -> 0
    bt.on_trade(3, 997, 105, 20, 3)   # cash +100, pos 0, mark 105 -> 100
    assert bt.equity_curve == [(1, 0), (2, 0), (3, 100)], bt.equity_curve


def test_no_trades_summary_is_flat():
    """With no trades at all, everything is zero."""
    bt = Backtester()
    assert bt.summary() == {"position": 0, "max_abs_position": 0, "cash": 0, "fills": 0,
                            "pnl": 0, "spread_pnl": 0, "inv_drift": 0,
                            "aggressive_fills": 0, "passive_fills": 0}, bt.summary()


def test_register_from_reads_sidecar():
    """register_from() skips the header and loads every (id, side) pair."""
    bt = Backtester()
    content = "id,side\n1000000,B\n1000001,S\n"
    path = os.path.join(tempfile.gettempdir(), "bt_test_mm.csv")
    with open(path, "w", newline="") as f:
        f.write(content)
    try:
        bt.register_from(path)
    finally:
        os.remove(path)

    assert bt.my_ids == {1000000: "B", 1000001: "S"}, bt.my_ids


def test_register_from_then_run_books_fills():
    """End-to-end at the Python layer: sidecar + trades -> correct PnL."""
    bt = Backtester()
    mm = os.path.join(tempfile.gettempdir(), "bt_test_mm2.csv")
    trades = os.path.join(tempfile.gettempdir(), "bt_test_trades2.csv")
    with open(mm, "w", newline="") as f:
        f.write("id,side\n1000000,B\n1000001,S\n")
    with open(trades, "w", newline="") as f:
        f.write(
            "aggressor_id,resting_id,price,qty,seq\n"
            "500,1000000,100,10,1\n"      # my bid (1000000) is hit: I buy 10 @ 100
            "1000001,501,101,10,2\n"      # my ask (1000001) lifts: I sell 10 @ 101
        )
    try:
        bt.register_from(mm)
        bt.run(trades)
    finally:
        os.remove(mm)
        os.remove(trades)

    assert bt.position == 0, bt.position
    assert bt.cash == 10, bt.cash
    assert bt.fills == 2, bt.fills


def test_aggressive_vs_passive_volume():
    """aggressor_fills / passive_fills accumulate *volume*, split by whether my
    id was the aggressor or the resting side of each fill."""
    bt = Backtester()
    bt.register(1, "B")               # I aggress with this one
    bt.register(2, "S")               # this one rests and gets lifted
    bt.on_trade(1, 999, 100, 7, 1)    # I'm the aggressor: +7 aggressive
    bt.on_trade(888, 2, 101, 4, 2)    # someone lifts my resting ask: +4 passive
    assert bt.aggressor_fills == 7, bt.aggressor_fills
    assert bt.passive_fills == 4, bt.passive_fills


def test_counters_ignore_foreign_trades():
    """A trade with none of my ids touches neither counter."""
    bt = Backtester()
    bt.register(1, "B")
    bt.on_trade(50, 51, 100, 9, 1)
    assert bt.aggressor_fills == 0, bt.aggressor_fills
    assert bt.passive_fills == 0, bt.passive_fills


def main():
    tests = [
        test_buy_then_sell_roundtrip,
        test_my_order_is_resting_side,
        test_foreign_trade_is_ignored,
        test_open_position_marked_to_market,
        test_run_parses_csv,
        test_fills_counts_only_my_trades,
        test_last_price_updates_on_every_trade,
        test_last_price_defaults_to_zero,
        test_summary_fields,
        test_summary_marks_open_position_at_last_price,
        test_multiple_buys_average_in,
        test_short_then_cover,
        test_equity_curve_length_matches_fills,
        test_equity_curve_tracks_running_pnl,
        test_no_trades_summary_is_flat,
        test_register_from_reads_sidecar,
        test_register_from_then_run_books_fills,
        test_aggressive_vs_passive_volume,
        test_counters_ignore_foreign_trades,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: got {e}")
        except Exception as e:  # noqa: BLE001 - surface any unexpected error
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")

    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
