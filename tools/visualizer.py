"""Visualize a backtest: the market-maker's equity curve (PnL) over the
matching-engine sequence, with its signed inventory path beneath it.

Usage:
    python tools/visualizer.py trades.csv --mm mm.csv --out pnl.png

Reads the same (trades.csv, mm.csv) pair the backtester consumes, replays a
Backtester to populate equity_curve / position_curve, and renders a two-panel
PNG: PnL on top (gains/losses shaded), signed inventory below (long/short
shaded) with the +/- max|position| risk envelope. The title strip carries the
spread-vs-drift decomposition so the chart reads on its own.
"""
import argparse
import os
import sys

import matplotlib
matplotlib.use("Agg")          # headless: write a PNG without needing a display
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtester import Backtester

PNL_LINE = "#2a9d8f"
GAIN = "#52b788"
LOSS = "#e76f51"
LONG = "#2a6f97"
SHORT = "#bc4749"


def _series(curve):
    """[(seq, val), ...] -> (np.array seqs, np.array vals); empty-safe."""
    if not curve:
        return np.array([]), np.array([])
    seqs, vals = zip(*curve)
    return np.asarray(seqs, dtype=float), np.asarray(vals, dtype=float)


def plot(bt, out_path, title="Market-Maker Backtest"):
    s = bt.summary()
    eq_x, eq_y = _series(bt.equity_curve)
    inv_x, inv_y = _series(bt.position_curve)
    eq_y = eq_y / 100.0          # cents -> dollars (display only; model stays integer cents)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        plt.style.use("default")

    fig, (ax_pnl, ax_inv) = plt.subplots(
        2, 1, sharex=True, figsize=(11, 7.2), dpi=130,
        gridspec_kw={"height_ratios": [3, 2]},
    )

    # ---- top panel: equity curve ----------------------------------------
    ax_pnl.plot(eq_x, eq_y, color=PNL_LINE, lw=1.9, zorder=3)
    if eq_y.size:
        ax_pnl.fill_between(eq_x, eq_y, 0, where=eq_y >= 0, interpolate=True,
                            color=GAIN, alpha=0.25)
        ax_pnl.fill_between(eq_x, eq_y, 0, where=eq_y < 0, interpolate=True,
                            color=LOSS, alpha=0.25)
        ax_pnl.scatter([eq_x[-1]], [eq_y[-1]], color=PNL_LINE, s=32, zorder=4)
        ax_pnl.annotate(f"PnL ${s['pnl']/100:,.2f}", (eq_x[-1], eq_y[-1]),
                        xytext=(-8, 8), textcoords="offset points", ha="right",
                        fontsize=10, fontweight="bold", color=PNL_LINE)
    ax_pnl.axhline(0, color="0.45", lw=1, ls="--", zorder=1)
    ax_pnl.set_ylabel("PnL   ($)")
    ax_pnl.margins(x=0.01)

    # ---- bottom panel: inventory path -----------------------------------
    ax_inv.plot(inv_x, inv_y, color="0.25", lw=1.2, drawstyle="steps-post", zorder=3)
    if inv_y.size:
        ax_inv.fill_between(inv_x, inv_y, 0, where=inv_y >= 0, step="post",
                            color=LONG, alpha=0.30, label="long")
        ax_inv.fill_between(inv_x, inv_y, 0, where=inv_y < 0, step="post",
                            color=SHORT, alpha=0.30, label="short")
        m = s["max_abs_position"]
        for y in (m, -m):
            ax_inv.axhline(y, color="0.6", lw=0.9, ls=":", zorder=1)
        ax_inv.annotate(f"max |pos| {m}", (inv_x[0], m), xytext=(2, 2),
                        textcoords="offset points", va="bottom", ha="left",
                        fontsize=9, color="0.45")
        ax_inv.legend(loc="upper left", fontsize=9, framealpha=0.85)
    ax_inv.axhline(0, color="0.45", lw=1, ls="--", zorder=1)
    ax_inv.set_ylabel("Inventory   (position)")
    ax_inv.set_xlabel("Matching-engine sequence")

    # ---- title + decomposition strip ------------------------------------
    strip = (f"fills {s['fills']}      spread_pnl ${s['spread_pnl']/100:,.2f}      "
             f"inv_drift ${s['inv_drift']/100:,.2f}      final pos {s['position']}")
    fig.suptitle(title, fontsize=15, fontweight="bold", y=0.975)
    fig.text(0.5, 0.93, strip, ha="center", fontsize=10, color="0.35")
    fig.subplots_adjust(top=0.89, bottom=0.085, left=0.09, right=0.965, hspace=0.07)

    fig.savefig(out_path)
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Plot a backtest's equity curve and inventory path.")
    p.add_argument("trades", help="path to trades.csv (replay output)")
    p.add_argument("--mm", required=True, help="path to the MM id,side sidecar")
    p.add_argument("--out", default="pnl.png", help="output PNG path")
    p.add_argument("--title", default="Market-Maker Backtest")
    args = p.parse_args()

    bt = Backtester()
    bt.register_from(args.mm)
    bt.run(args.trades)
    if not bt.fills:
        print("warning: no MM fills in this run -- nothing to plot", file=sys.stderr)
    out = plot(bt, args.out, args.title)
    print(f"wrote {out}   {bt.summary()}")
