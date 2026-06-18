import random, csv, argparse, statistics
from collections import deque

STEPS = [-8, -5, -2, 0, 2, 5, 8]            # mid-move grid (calm regime)
STEP_WEIGHTS = [1, 2, 7, 9, 7, 2, 1]
ORDER_TYPES = ["LIMIT", "MARKET", "IOC", "FOK"]
TYPE_WEIGHTS = [9, 3, 1, 1]


def effective_spread(spread, k, moves):
    sigma = statistics.pstdev(moves) if len(moves) > 1 else 0
    return spread + round(k * sigma)


def post_quotes(order_writer, mm_writer, live_ids, next_mm_id, mid, eff_spread, quote_qty):
    for qid in live_ids:
        order_writer.writerow([qid, "", "CANCEL", "", ""])
    live_ids.clear()
    for side, px in (("B", mid - eff_spread), ("S", mid + eff_spread)):
        qid = next_mm_id
        next_mm_id += 1
        order_writer.writerow([qid, side, "LIMIT", px, quote_qty])
        mm_writer.writerow([qid, side])
        live_ids.append(qid)
    return next_mm_id


def step_mid(mid, stormy, p_storm, p_calm, storm_mult, moves):
    if stormy and random.random() < p_calm:
        stormy = False                                   # storm -> calm
    elif not stormy and random.random() < p_storm:
        stormy = True                                    # calm -> storm
    vol = storm_mult if stormy else 1
    dm = vol * random.choices(STEPS, STEP_WEIGHTS)[0]
    moves.append(dm)
    return mid + dm, stormy


def noise_order(mid, market_spread):
    side = random.choice(["B", "S"])
    otype = random.choices(ORDER_TYPES, TYPE_WEIGHTS)[0]
    if otype == "MARKET":
        price = 0
    elif side == "B":
        price = mid + random.randint(-(market_spread // 2), market_spread)
    else:
        price = mid - random.randint(-(market_spread // 2), market_spread)
    qty = random.randrange(1, 50, 1)
    return side, otype, price, qty


def run_strategy(n, seed, market_spread, spread, quote_every, quote_qty,
                 p_storm, p_calm, storm_mult, W, k, out_orders, out_mm):
    random.seed(seed)
    mid = 10000
    stormy = False
    moves = deque(maxlen=W)
    live_ids = []
    next_mm_id = 1000000

    order_writer = csv.writer(out_orders)
    order_writer.writerow(["id", "side", "type", "price", "qty"])
    mm_writer = csv.writer(out_mm)
    mm_writer.writerow(["id", "side"])

    for oid in range(1, n + 1):
        if oid % quote_every == 0:
            eff_spread = effective_spread(spread, k, moves)
            next_mm_id = post_quotes(order_writer, mm_writer, live_ids,
                                     next_mm_id, mid, eff_spread, quote_qty)
        if oid % 2 == 0:
            mid, stormy = step_mid(mid, stormy, p_storm, p_calm, storm_mult, moves)
        side, otype, price, qty = noise_order(mid, market_spread)
        order_writer.writerow([oid, side, otype, price, qty])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--market_spread", type=int, default=6)
    p.add_argument("--spread", type=int, default=15)
    p.add_argument("--quote_every", type=int, default=10)
    p.add_argument("--quote_qty", type=int, default=10)
    p.add_argument("--p_storm", type=float, default=0.005)   # calm -> storm per mid-update (avg calm ~200 updates)
    p.add_argument("--p_calm", type=float, default=0.02)     # storm -> calm per mid-update (avg storm ~50 updates)
    p.add_argument("--storm_mult", type=int, default=3)      # storm step size vs calm
    p.add_argument("--W", type=int, default=30)              # vol window (recorded mid-moves)
    p.add_argument("--k", type=float, default=2.0)           # spread sensitivity to vol (ticks per unit sigma)
    p.add_argument("--out_orders", default="order.csv")
    p.add_argument("--out_mm", default="mm_out.csv")
    args = p.parse_args()

    with open(args.out_orders, "w", newline="") as f_orders, \
         open(args.out_mm, "w", newline="") as f_mm:
        run_strategy(args.n, args.seed, args.market_spread, args.spread,
                     args.quote_every, args.quote_qty, args.p_storm, args.p_calm,
                     args.storm_mult, args.W, args.k, f_orders, f_mm)
