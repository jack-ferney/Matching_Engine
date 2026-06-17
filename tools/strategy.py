import random, csv, argparse, sys

def run_strategy(n, seed, spread, quote_every, quote_qty, out_orders, out_mm):
    random.seed(seed)
    mid = 10000
    order_writer = csv.writer(out_orders)
    order_writer.writerow(["id","side","type","price","qty"])
    mm_writer = csv.writer(out_mm)
    mm_writer.writerow(["id","side"])
    next_mm_id = 1000000
    for oid in range(1, n+1):
        if oid % quote_every == 0:
            if (next_mm_id > 1000000):
                order_writer.writerow([next_mm_id - 2, "", "CANCEL", "", ""])
                order_writer.writerow([next_mm_id - 1, "", "CANCEL", "", ""])
            bid_id = next_mm_id; next_mm_id += 1
            ask_id = next_mm_id; next_mm_id += 1
            order_writer.writerow([bid_id, "B", "LIMIT", mid - spread, quote_qty])
            order_writer.writerow([ask_id, "S", "LIMIT", mid + spread, quote_qty])
            mm_writer.writerow([bid_id, "B"])
            mm_writer.writerow([ask_id, "S"])
        mid += random.choice([-2,0,2])
        side = random.choice(["B","S"])
        otype = random.choices(["LIMIT","MARKET","IOC","FOK"], [9,1,1,1])[0]
        if otype == "MARKET":
            price = 0
        elif side == "B":
            price = mid + random.randint(-(spread//2), spread)
        else:  # "S"
            price = mid - random.randint(-(spread//2), spread)
        noise_qty = random.randrange(1, 50, 1)
        order_writer.writerow([oid, side, otype, price, noise_qty])
        
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--spread", type=int, default=10)
    p.add_argument("--quote_every", type=int, default=25)
    p.add_argument("--quote_qty", type=int, default=10)
    p.add_argument("--out_orders", default="order.csv")
    p.add_argument("--out_mm", default="mm_out.csv")
    args = p.parse_args()
    
    if args.out_orders:
        with open(args.out_orders, "w", newline="") as f_orders, \
              open(args.out_mm, "w", newline="") as f_mm:
            run_strategy(args.n, args.seed, args.spread, args.quote_every, args.quote_qty, f_orders, f_mm)