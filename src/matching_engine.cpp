#include "me/matching_engine.hpp"

namespace me {

bool MatchingEngine::crosses(Side side, Price incoming, Price resting) {
    if (side == Side::Buy) {
        return incoming >= resting;
    } else {
        return incoming <= resting;
    }
}

std::vector<Trade> MatchingEngine::match(Order& order) {
    std::vector<Trade> trades;
    Side side = order.side;
    bool is_market = order.type == OrderType::Market;

    auto match_against = [&](auto& opposite) {
        while (order.quantity > 0 && !opposite.empty()) {

            auto best = opposite.begin();

            Order& r = best->second.orders.front();

            if (crosses(side, order.price, best->first) || is_market) {
                auto quant = std::min(order.quantity, r.quantity);
                trades.push_back({order.id, r.id, best->first, quant, order.seq});
                order.quantity -= quant;
                r.quantity -= quant;
                best->second.total_qty -= quant;
                if (r.quantity == 0) {
                    book_.id_index_.erase(r.id);
                    best->second.orders.pop_front();
                }
                if (best->second.orders.empty()) opposite.erase(best);
            } else {
                break;
            }
        }
    };

    if (side == Side::Buy) match_against(book_.asks_);
    if (side == Side::Sell) match_against(book_.bids_);

    return trades;
}

SubmitResult MatchingEngine::submit(Order order) {
    order.seq = next_seq_++;
    SubmitResult sr;
    sr.trades = match(order);
    for (auto& t : sr.trades) sr.filled += t.quantity;
    if (order.quantity > 0 && order.type == OrderType::Limit) {
        book_.rest(order);
        sr.resting = order.quantity;
    } else {
        sr.cancelled = order.quantity;
    }
    return sr;
}

} // namespace me