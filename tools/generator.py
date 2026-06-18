import argparse, random, csv, sys
from collections import deque

def generate(n, seed, out):
    random.seed(seed)
    mid = 10000
    writer = csv.writer(out)
    writer.writerow(["id","side","type","price","qty"])
    offset = 12
    resting = deque()
    for oid in range(1, n+1):
        if (len(resting) > 0 and random.choices(["y","n"], [1,10])[0] == "y"):
            writer.writerow([resting.popleft(), "", "CANCEL", "", ""])
            continue
        mid += random.choice([-2,0,2])
        side = random.choice(["B","S"])
        otype = random.choices(["LIMIT","MARKET","IOC","FOK"], [9,2,1,1])[0]
        aggressive = random.random() < 0.15            # ~15% cross the spread; rest are passive
        if otype == "MARKET":
            price = 0
        elif side == "B":
            price = mid + random.randint(0, offset) if aggressive \
                else mid - random.randint(1, offset)     # passive bid sits below mid
        else:  # "S"
            price = mid - random.randint(0, offset) if aggressive \
                else mid + random.randint(1, offset)     # passive ask sits above mid
        if otype == "LIMIT" and not aggressive:
            resting.append(oid)
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