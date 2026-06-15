import argparse, random, csv, sys

def generate(n, seed, out):
    random.seed(seed)
    mid = 10000
    writer = csv.writer(out)
    writer.writerow(["id","side","type","price","qty"])
    offset = 12
    for oid in range(1, n+1):
        mid += random.choice([-2,0,2])
        side = random.choice(["B","S"])
        otype = random.choices(["LIMIT","MARKET","IOC","FOK"], [9,1,1,1])[0]
        aggressive = random.random() < 0.25            # ~25% cross the spread; rest are passive
        if otype == "MARKET":
            price = 0
        elif side == "B":
            price = mid + random.randint(0, offset) if aggressive \
                else mid - random.randint(1, offset)     # passive bid sits below mid
        else:  # "S"
            price = mid - random.randint(0, offset) if aggressive \
                else mid + random.randint(1, offset)     # passive ask sits above mid

        qty = random.randrange(1, 1000, 1)
        writer.writerow([oid, side, otype, price, qty])

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=1000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    if args.out:
        with open(args.out, "w", newline="") as f:
            generate(args.n, args.seed, f)
    else:
        generate(args.n, args.seed, sys.stdout)