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
    Side side = order.side;
    if (order.type == OrderType::Limit) {
        // pick up here
    }
}

SubmitResult MatchingEngine::submit(Order order) {
    // to be implemented
}

} // namespace me