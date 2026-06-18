#include "me/matching_engine.hpp"
#include <iostream>
#include <sstream>
#include <string>

using namespace me;

static Side parse_side(const std::string& str) {
    return (str == "B" || str == "BUY") ? Side::Buy : Side::Sell;
}

static OrderType parse_order_type(const std::string& str) {
    if (str == "LIMIT") return OrderType::Limit;
    if (str == "MARKET") return OrderType::Market;
    if (str == "IOC") return OrderType::IOC;
    return OrderType::FOK;
}

int main() {
    MatchingEngine e;
    std::cout << "aggressor_id,resting_id,price,qty,seq\n";

    std::string line;
    while (std::getline(std::cin, line)) {
        if (line.empty()) continue;
        if (line.rfind("id", 0) == 0) continue;

        std::stringstream ss(line);
        std::string id, side, type, price, qty;
        std::getline(ss,id,',');
        std::getline(ss,side,',');
        std::getline(ss,type,',');
        std::getline(ss,price,',');
        std::getline(ss,qty,',');

        if (type == "CANCEL") {
            e.cancel(static_cast<OrderId>(std::stoull(id)));
            continue;
        }

        Order o{
            static_cast<OrderId>(std::stoull(id)),
            parse_side(side),
            parse_order_type(type),
            static_cast<Price>(std::stoull(price)),
            static_cast<Quantity>(std::stoull(qty)),
            0
        };

        auto r = e.submit(o);
        for (const auto& t : r.trades) {
            std::cout << t.aggressor_id << ',' << t.resting_id << ',' << t.price << ',' << t.quantity << ',' << t.seq << "\n";
        }
    }

    return 0;
}

// namespace me