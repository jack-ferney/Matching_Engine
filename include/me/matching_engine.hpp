#pragma once
#include "me/types.hpp"
#include "me/order_book.hpp"
#include <vector>

namespace me {

struct SubmitResult {
    std::vector<Trade> trades;
    Quantity filled{0}, resting{0}, cancelled{0};
    bool rejected{false};   // only for FOK that can't fully fill
};

class MatchingEngine {
public:
    SubmitResult submit(Order order);

    bool cancel(OrderId id) { return book_.cancel(id); }
    bool reduce(OrderId id, Quantity q) { return book_.reduce(id, q); }
    const OrderBook& book() const { return book_; }

private:
    static bool crosses(Side, Price incoming, Price resting_px);
    Quantity fillable_quantity(const Order& order) const;

    std::vector<Trade> match(Order& order);
    OrderBook book_;
    Seq next_seq_{1};
};

} // namespace me