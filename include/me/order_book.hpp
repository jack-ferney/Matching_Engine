#pragma once
#include "me/types.hpp"
#include <list>
#include <map>
#include <unordered_map>
#include <optional>
#include <functional>

namespace me {

struct PriceLevel {
    std::list<Order> orders;
    Quantity total_qty{0};  // updated on rest/reduce/cancel; used for quick qty lookups
};

using BidMap = std::map<Price, PriceLevel, std::greater<Price>>;
using AskMap = std::map<Price, PriceLevel, std::less<Price>>;

class OrderBook {
public:
    struct Location { Side side; Price price; std::list<Order>::iterator it; };

    std::optional<Price> best_bid() const {
        return bids_.empty() ? std::nullopt : std::optional{bids_.begin()->first};
    }
    std::optional<Price> best_ask() const {
        return asks_.empty() ? std::nullopt : std::optional{asks_.begin()->first};
    }
    bool empty() const { return bids_.empty() && asks_.empty(); }
    std::size_t order_count() const { return id_index_.size(); }
    Quantity quantity_at(Side side, Price price) const; // used for finding quantity at a price level

    const BidMap& bids() const { return bids_; }
    const AskMap& asks() const { return asks_; }

    void rest(const Order& o);
    bool cancel(OrderId id);
    bool reduce(OrderId id, Quantity q);

private:
    BidMap bids_;
    AskMap asks_;
    std::unordered_map<OrderId, Location> id_index_;
    friend class MatchingEngine;
};

} // namespace me