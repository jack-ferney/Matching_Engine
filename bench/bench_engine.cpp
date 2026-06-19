#include "me/matching_engine.hpp"

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <random>
#include <vector>

using namespace me;

using clk = std::chrono::steady_clock;

int main(int argc, char** argv) {
    const std::size_t N = (argc > 1) ? std::stoul(argv[1]) : 2'000'000;

    std::mt19937_64 rng(12345);
    std::uniform_int_distribution<int>      side_d(0, 1);
    std::uniform_int_distribution<Price>    price_d(9'900, 10'100);
    std::uniform_int_distribution<Quantity> qty_d(1, 100);

    std::vector<Order> orders;
    orders.reserve(N);
    for (std::size_t i=0; i<N; i++) {
        orders.push_back(
            Order {
                static_cast<OrderId>(i+1),
                side_d(rng) ? Side::Buy : Side::Sell,
                OrderType::Limit,
                price_d(rng),
                qty_d(rng),
                0
            }
        );
    }

    std::vector<std::uint64_t> latencies_ns;
    latencies_ns.reserve(N);

    MatchingEngine e;

    auto wall_start = clk::now();

    for (auto& o : orders) {
        auto t0 = clk::now();
        e.submit(o);
        auto t1 = clk::now();
        latencies_ns.push_back(
            std::chrono::duration_cast<std::chrono::nanoseconds>(t1-t0).count());
    }

    auto wall_end = clk::now();

    double secs = std::chrono::duration<double>(wall_end - wall_start).count();
    std::sort(latencies_ns.begin(), latencies_ns.end());
    auto pct = [&](double p) {
        return latencies_ns[static_cast<std::size_t>(p * (latencies_ns.size() - 1))];
    };

    std::cout << "orders            : " << N << "\n";
    std::cout << "wall time (s)     : " << secs << "\n";
    std::cout << "throughput (ord/s): " << static_cast<std::uint64_t>(N / secs) << "\n";
    std::cout << "latency p50  (ns) : " << pct(0.50)  << "\n";
    std::cout << "latency p99  (ns) : " << pct(0.99)  << "\n";
    std::cout << "latency p99.9(ns) : " << pct(0.999) << "\n";
    std::cout << "final book orders : " << e.book().order_count() << "\n";
    return 0;
}