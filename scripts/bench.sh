#!/usr/bin/env bash
# Run the matching-engine benchmark multiple times and report averaged stats.
# Discards one warm-up run, then runs $RUNS times; prints avg/median/min/max/sd.
#
# Usage: scripts/bench.sh [runs] [orders] [exe]
#   scripts/bench.sh                      # 12 runs, 2,000,000 orders
#   scripts/bench.sh 20 5000000
set -euo pipefail

RUNS="${1:-12}"
N="${2:-2000000}"
EXE="${3:-build/bench}"

[ -x "$EXE" ] || { echo "benchmark not found at $EXE -- build it first: cmake --build build" >&2; exit 1; }

"$EXE" "$N" >/dev/null    # discarded warm-up run

thr=(); p50=(); p99=(); p999=()
for ((i = 0; i < RUNS; i++)); do
  out="$("$EXE" "$N")"
  thr+=("$(echo "$out"  | grep 'throughput' | grep -oE '[0-9.]+' | tail -1)")
  p50+=("$(echo "$out"  | grep 'p50'        | grep -oE '[0-9]+'  | tail -1)")
  p99+=("$(echo "$out"  | grep 'p99 '       | grep -oE '[0-9]+'  | tail -1)")
  p999+=("$(echo "$out" | grep 'p99.9'      | grep -oE '[0-9]+'  | tail -1)")
done

stat() {  # avg median min max sd over the numeric args
  printf '%s\n' "$@" | sort -n | awk '
    { a[NR] = $1; sum += $1 }
    END {
      n = NR; mean = sum / n;
      med = (n % 2) ? a[int(n/2) + 1] : (a[n/2] + a[n/2 + 1]) / 2;
      for (i = 1; i <= n; i++) v += (a[i] - mean)^2;
      printf "avg %12.1f  median %12.1f  min %12.1f  max %12.1f  sd %10.1f",
             mean, med, a[1], a[n], sqrt(v / n);
    }'
}

echo "measured runs : $RUNS (after 1 warm-up), N = $N"
echo "throughput o/s: $(stat "${thr[@]}")"
echo "p50  (ns)     : $(stat "${p50[@]}")"
echo "p99  (ns)     : $(stat "${p99[@]}")"
echo "p99.9 (ns)    : $(stat "${p999[@]}")"
