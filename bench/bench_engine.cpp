//
// bench_engine.cpp - throughput + latency percentiles for MatchingEngine::submit().
//
// Two separate passes, so neither measurement perturbs the other:
//   * THROUGHPUT - a clean loop with no per-op instrumentation, timed once with
//     steady_clock over the whole run (aggregate precision is ample).
//   * LATENCY    - a second pass over a fresh engine timing each submit() with the
//     x86 invariant TSC (__rdtscp). steady_clock quantizes to ~100 ns on Windows,
//     which would floor every sample; the TSC ticks at a constant rate and gives
//     sub-nanosecond resolution. The cost of the two TSC reads themselves is
//     measured and subtracted from every sample.
//
// submit() takes its Order by value, so the pre-generated vector is not mutated and
// both passes see identical input.
//
#include "me/matching_engine.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <limits>
#include <random>
#include <vector>
#include <x86intrin.h>  // __rdtscp (x86-64 only)

using namespace me;
using clk = std::chrono::steady_clock;

static inline std::uint64_t read_tsc() {
    unsigned int aux;
    const std::uint64_t t = __rdtscp(&aux);  // waits for prior instructions to retire
    (void)aux;
    return t;
}

// TSC ticks per nanosecond, calibrated against steady_clock over a fixed window.
static double calibrate_ticks_per_ns() {
    const auto c0 = clk::now();
    const std::uint64_t t0 = read_tsc();
    while (clk::now() - c0 < std::chrono::milliseconds(200)) { /* busy-wait */ }
    const std::uint64_t t1 = read_tsc();
    const auto c1 = clk::now();
    const double ns = std::chrono::duration<double, std::nano>(c1 - c0).count();
    return static_cast<double>(t1 - t0) / ns;
}

// Floor cost of two back-to-back TSC reads, in ticks - subtracted from each sample.
static std::uint64_t tsc_read_overhead() {
    std::uint64_t best = std::numeric_limits<std::uint64_t>::max();
    for (int i = 0; i < 100000; ++i) {
        const std::uint64_t a = read_tsc();
        const std::uint64_t b = read_tsc();
        best = std::min(best, b - a);
    }
    return best;
}

int main(int argc, char** argv) {
    const std::size_t N = (argc > 1) ? std::stoul(argv[1]) : 2'000'000;
    const double ticks_per_ns = calibrate_ticks_per_ns();
    const std::uint64_t overhead = tsc_read_overhead();

    std::mt19937_64 rng(12345);
    std::uniform_int_distribution<int>      side_d(0, 1);
    std::uniform_int_distribution<Price>    price_d(9'900, 10'100);  // tight band -> lots of crossing
    std::uniform_int_distribution<Quantity> qty_d(1, 100);

    // Pre-generate orders so RNG + construction stay out of both timed loops.
    std::vector<Order> orders;
    orders.reserve(N);
    for (std::size_t i = 0; i < N; ++i) {
        orders.push_back(Order{
            static_cast<OrderId>(i + 1),
            side_d(rng) ? Side::Buy : Side::Sell,
            OrderType::Limit,
            price_d(rng),
            qty_d(rng),
            0});
    }

    // ---- Pass 1: throughput (no per-op timing) ----
    MatchingEngine thr_engine;
    const auto wall_start = clk::now();
    for (auto& o : orders) thr_engine.submit(o);
    const auto wall_end = clk::now();
    const double secs = std::chrono::duration<double>(wall_end - wall_start).count();

    // ---- Pass 2: per-op latency via TSC (fresh engine) ----
    std::vector<std::uint64_t> latency_ticks;
    latency_ticks.reserve(N);
    MatchingEngine lat_engine;
    for (auto& o : orders) {
        const std::uint64_t t0 = read_tsc();
        lat_engine.submit(o);
        const std::uint64_t t1 = read_tsc();
        const std::uint64_t d = t1 - t0;
        latency_ticks.push_back(d > overhead ? d - overhead : 0);
    }

    std::sort(latency_ticks.begin(), latency_ticks.end());
    auto pct_ns = [&](double p) {
        const std::uint64_t t =
            latency_ticks[static_cast<std::size_t>(p * (latency_ticks.size() - 1))];
        return static_cast<std::uint64_t>(t / ticks_per_ns);
    };

    std::cout << "orders            : " << N << "\n";
    std::cout << "tsc GHz           : " << ticks_per_ns << "\n";
    std::cout << "wall time (s)     : " << secs << "\n";
    std::cout << "throughput (ord/s): " << static_cast<std::uint64_t>(N / secs) << "\n";
    std::cout << "latency p50  (ns) : " << pct_ns(0.50)  << "\n";
    std::cout << "latency p99  (ns) : " << pct_ns(0.99)  << "\n";
    std::cout << "latency p99.9(ns) : " << pct_ns(0.999) << "\n";
    std::cout << "final book orders : " << thr_engine.book().order_count() << "\n";
    return 0;
}
