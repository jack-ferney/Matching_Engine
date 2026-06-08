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
    auto idx = id_index_.find(id);
    if (idx == id_index_.end()) return false;
    auto loc = idx->second;
    auto quant = loc.it->quantity;
    auto& lvl = (loc.side == Side::Buy) ? bids_[loc.price] : asks_[loc.price];
    lvl.total_qty = lvl.total_qty - quant;
    id_index_.erase(id);
    lvl.orders.erase(loc.it);
    if (lvl.orders.empty()) {
        (loc.side == Side::Buy) ? bids_.erase(loc.price) : asks_.erase(loc.price);
    }
    return true;
}

bool OrderBook::reduce(OrderId id, Quantity new_qty) {
    if (new_qty == 0) return cancel(id);
    auto idx = id_index_.find(id);
    if (idx == id_index_.end()) return false;
    auto loc = idx->second;
    if (new_qty >= loc.it->quantity) return false;
    auto delta = loc.it->quantity - new_qty;
    auto& lvl = (loc.side == Side::Buy) ? bids_[loc.price] : asks_[loc.price];
    lvl.total_qty = lvl.total_qty - delta;
    loc.it->quantity = new_qty;
    return true;
}

} // namespace me