#pragma once
#include <cstdint>
#include <ostream>

namespace me {

using Price    = std::int64_t;   // integer price in cents
using Quantity = std::uint64_t;
using OrderId  = std::uint64_t;
using Seq      = std::uint64_t;  // engine-assigned arrival order = "time"

enum class Side : std::uint8_t { Buy, Sell };
enum class OrderType : std::uint8_t { Limit, Market, IOC, FOK };

struct Order {
    OrderId   id{};
    Side      side{};
    OrderType type{};
    Price     price{};      // not used for Market
    Quantity  quantity{};   // REMAINING qty; dynamic
    Seq       seq{};        // set by the engine
};

struct Trade {
    OrderId  aggressor_id{};
    OrderId  resting_id{};
    Price    price{};       // executes at the RESTING order's price
    Quantity quantity{};
    Seq      seq{};
};

} // namespace me