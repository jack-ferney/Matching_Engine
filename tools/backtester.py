import csv, argparse

class Backtester:
    def __init__(self):
        self.position = 0
        self.cash = 0
        self.fills = 0
        self.last_price = 0
        self.my_ids = {}
        self.equity_curve = []
        self.position_curve = []
        self.max_abs_position = 0
        self.aggressor_fills = 0
        self.passive_fills = 0
        self.first_price = None         # fair-value anchor: first market price seen
        
    def register(self, order_id, side):
        self.my_ids[order_id] = side
        
    def register_from(self, mm_path):
        with open(mm_path, newline="") as f:
            reader = csv.reader(f)
            next(reader)
            for oid, side in reader:
                self.register(int(oid), side)

    def run(self, trades_path):
        with open(trades_path, newline="") as f:
            reader = csv.reader(f)
            next(reader)                       # skip the header row
            for row in reader:
                aggressor_id, resting_id, price, qty, seq = row
                self.on_trade(int(aggressor_id), int(resting_id),
                            int(price), int(qty), int(seq))
    
    def on_trade(self, aggressor_id, resting_id, price, qty, seq):
        if aggressor_id in self.my_ids:
            my_side = self.my_ids[aggressor_id]
            self.update(price, qty, seq, my_side)
            self.aggressor_fills += qty
        elif resting_id in self.my_ids:
            my_side = self.my_ids[resting_id]
            self.update(price, qty, seq, my_side)
            self.passive_fills += qty
        if self.first_price is None:
            self.first_price = price
        self.last_price = price

    def update(self, price, qty, seq, my_side):
        if my_side == "B":
            signed = qty
        else:
            signed = -qty
        self.cash -= price * signed
        self.position += signed
        self.max_abs_position = max(self.max_abs_position, abs(self.position))
        self.fills += 1
        self.equity_curve.append((seq, self.pnl(price)))
        self.position_curve.append((seq, self.position))
        
    def summary(self):
        ref = self.first_price if self.first_price is not None else self.last_price
        spread_pnl = self.cash + self.position * ref   # inventory marked at start -> spread capture
        return {
            "position": self.position,
            "max_abs_position": self.max_abs_position,
            "cash": self.cash,
            "fills": self.fills,
            "pnl": self.pnl(self.last_price),
            "spread_pnl": spread_pnl,
            "inv_drift": self.pnl(self.last_price) - spread_pnl,
            "aggressive_fills": self.aggressor_fills,
            "passive_fills": self.passive_fills
        }
        
    def pnl(self, mark):
        return self.cash + self.position * mark
    
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("trades")          # path to trades.csv
    p.add_argument("--mm", default=None)
    args = p.parse_args()
    bt = Backtester()
    if args.mm:
        bt.register_from(args.mm)
        bt.run(args.trades)
        print(bt.summary())