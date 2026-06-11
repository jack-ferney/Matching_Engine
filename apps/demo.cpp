#include "me/matching_engine.hpp"
#include <iostream>

using namespace me;

static void print_book(const OrderBook& book) {
    std::cout << " ASKS (low->high):";
    for (const auto& [price, level] : book.asks()) std::cout << " " << level.total_qty << "@" << price;
    std::cout << "\n BIDS (high->low):";
    for (const auto& [price, level] : book.bids()) std::cout << " " << level.total_qty << "@" << price;
    std::cout << "\n";
}

static const char* type_str(OrderType t) {
    switch (t) {
        case OrderType::Limit:  return "LIMIT";
        case OrderType::Market: return "MARKET";
        case OrderType::IOC:    return "IOC";
        case OrderType::FOK:    return "FOK";
    }
    return "?";
}

// Submit an order, then print the trades it generated and the resulting book.
static void fire(MatchingEngine& e, const Order& o, const char* note) {
    std::cout << "\n>>> " << (o.side == Side::Buy ? "BUY  " : "SELL ")
              << type_str(o.type) << " qty " << o.quantity;
    if (o.type != OrderType::Market) std::cout << " @ " << o.price;
    std::cout << "\n    (" << note << ")\n";

    SubmitResult r = e.submit(o);
    if (r.rejected) std::cout << "    >> REJECTED: could not fully fill (book untouched)\n";
    for (const auto& t : r.trades)
        std::cout << "    >> TRADE  " << t.quantity << " @ " << t.price
                  << "   [aggressor #" << t.aggressor_id << " hit resting #" << t.resting_id << "]\n";
    std::cout << "    filled=" << r.filled << "  resting=" << r.resting
              << "  cancelled=" << r.cancelled << "\n";
    print_book(e.book());
}

// A standard book: asks 5@100, 5@101, 5@102 and bids 5@99, 5@98.
static void seed(MatchingEngine& e) {
    e.submit({101, Side::Sell, OrderType::Limit, 100, 5, 0});
    e.submit({102, Side::Sell, OrderType::Limit, 101, 5, 0});
    e.submit({103, Side::Sell, OrderType::Limit, 102, 5, 0});
    e.submit({201, Side::Buy,  OrderType::Limit, 99,  5, 0});
    e.submit({202, Side::Buy,  OrderType::Limit, 98,  5, 0});
}

static void banner(const char* title) {
    std::cout << "\n========================================================\n"
              << " " << title
              << "\n========================================================\n"
              << " Fresh book:\n";
}

int main() {
    // 1. A marketable limit executes at the RESTING price (price improvement).
    {
        MatchingEngine e; banner("1. LIMIT cross -> price improvement"); seed(e); print_book(e.book());
        fire(e, {1, Side::Buy, OrderType::Limit, 101, 3, 0},
             "willing to pay 101, but best ask rests at 100 -> fills at 100");
    }

    // 2. A large limit sweeps two levels and rests its remainder as a new bid.
    {
        MatchingEngine e; banner("2. LIMIT sweeps two levels, rests remainder"); seed(e); print_book(e.book());
        fire(e, {2, Side::Buy, OrderType::Limit, 101, 12, 0},
             "takes 5@100 + 5@101, then rests the leftover 2 as a bid @101");
    }

    // 3. Market order ignores price, taking the best available liquidity.
    {
        MatchingEngine e; banner("3. MARKET order ignores price"); seed(e); print_book(e.book());
        fire(e, {3, Side::Buy, OrderType::Market, 0, 8, 0},
             "no price limit: lifts 5@100 then 3@101");
    }

    // 4. Market order that exhausts the book: the remainder is cancelled, not rested.
    {
        MatchingEngine e; banner("4. MARKET exhausts book -> remainder cancelled"); seed(e); print_book(e.book());
        fire(e, {4, Side::Buy, OrderType::Market, 0, 20, 0},
             "only 15 resting on the ask side; the other 5 are cancelled");
    }

    // 5. IOC: fills what it can now at its limit, cancels the rest, never rests.
    {
        MatchingEngine e; banner("5. IOC partial fill then cancel"); seed(e); print_book(e.book());
        fire(e, {5, Side::Buy, OrderType::IOC, 100, 8, 0},
             "limit 100 crosses only the 5@100; remaining 3 cancelled (does NOT rest)");
    }

    // 6. FOK rejected: not enough liquidity at/under the limit -> nothing happens.
    {
        MatchingEngine e; banner("6. FOK rejected (insufficient liquidity)"); seed(e); print_book(e.book());
        fire(e, {6, Side::Buy, OrderType::FOK, 100, 8, 0},
             "needs 8 at <=100 but only 5 exist -> rejected, ZERO trades, book unchanged");
    }

    // 7. FOK filled: enough liquidity across levels -> all-or-nothing fills.
    {
        MatchingEngine e; banner("7. FOK fills completely"); seed(e); print_book(e.book());
        fire(e, {7, Side::Buy, OrderType::FOK, 101, 10, 0},
             "needs 10 at <=101; exactly 5@100 + 5@101 available -> fills");
    }

    // 8. A resting sell crosses the bids (the symmetric direction).
    {
        MatchingEngine e; banner("8. SELL aggressor hits the bids"); seed(e); print_book(e.book());
        fire(e, {8, Side::Sell, OrderType::Limit, 99, 7, 0},
             "limit 99 crosses the 5@99 bid; the leftover 2 then rests as an ask @99");
    }

    // 9. Cancel a resting order in O(1) by id.
    {
        MatchingEngine e; banner("9. CANCEL a resting order"); seed(e); print_book(e.book());
        std::cout << "\n>>> cancel resting ask #101 (5 @ 100)\n";
        std::cout << "    cancel returned " << std::boolalpha << e.cancel(101) << "\n";
        print_book(e.book());
    }

    // 10. Reduce a resting order (it keeps its time priority).
    {
        MatchingEngine e; banner("10. REDUCE a resting order"); seed(e); print_book(e.book());
        std::cout << "\n>>> reduce resting bid #201 (5 @ 99) down to 2\n";
        std::cout << "    reduce returned " << std::boolalpha << e.reduce(201, 2) << "\n";
        print_book(e.book());
    }

    return 0;
}
