#include "me/order_book.hpp"

namespace me {

Quantity OrderBook::quantity_at(Side side, Price price) const {
    if (side == Side::Buy) {
        auto it = bids_.find(price);
        return it != bids_.end() ? it->second.total_qty : 0;
    } else {
        auto it = asks_.find(price);
        return it != asks_.end() ? it->second.total_qty : 0;
    }
}

void OrderBook::rest(const Order& o) {
    auto& lvl = (o.side == Side::Buy) ? bids_[o.price] : asks_[o.price];
    lvl.orders.push_back(o);
    lvl.total_qty += o.quantity;
    Location loc{o.side, o.price, std::prev(lvl.orders.end())};
    id_index_[o.id] = loc;
}

bool OrderBook::cancel(OrderId id) {
    // Implementation goes here
}

bool OrderBook::reduce(OrderId id, Quantity q) {
    // Implementation goes here
}

} // namespace me