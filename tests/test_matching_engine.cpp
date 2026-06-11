#include "me/types.hpp"
#include "me/matching_engine.hpp"
#include <gtest/gtest.h>

using me::Side;
using me::OrderType;

// Helper: a limit order. seq is 0 -- the engine stamps it on submit.
static me::Order limit(me::OrderId id, Side s, me::Price px, me::Quantity q) {
    return {id, s, OrderType::Limit, px, q, 0};
}

TEST(Sanity, TypesCompile) {
    me::Order o{1, me::Side::Buy, me::OrderType::Limit, 100, 10, 0};
    EXPECT_EQ(o.quantity, 10u);
}

// ----------------------------------------------------------------------------
// 1. A buy below the best ask does NOT cross -- it just rests as a bid.
// ----------------------------------------------------------------------------
TEST(Match, NoCrossRests) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 105, 5));         // resting ask @ 105
    auto r = eng.submit(limit(2, Side::Buy, 100, 5)); // buy @ 100 < 105 -> no cross

    EXPECT_TRUE(r.trades.empty());
    EXPECT_EQ(r.filled, 0u);
    EXPECT_EQ(r.resting, 5u);
    EXPECT_EQ(eng.book().best_bid(), 100);            // it rested
    EXPECT_EQ(eng.book().best_ask(), 105);            // ask untouched
}

// ----------------------------------------------------------------------------
// 2. A cross executes at the RESTING order's price (price improvement).
// ----------------------------------------------------------------------------
TEST(Match, ExecutesAtRestingPrice) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 5));         // resting ask @ 100
    auto r = eng.submit(limit(2, Side::Buy, 105, 5)); // willing to pay up to 105

    ASSERT_EQ(r.trades.size(), 1u);
    EXPECT_EQ(r.trades[0].price, 100);                // executes at 100, NOT 105
    EXPECT_EQ(r.trades[0].aggressor_id, 2u);
    EXPECT_EQ(r.trades[0].resting_id, 1u);
    EXPECT_EQ(r.trades[0].quantity, 5u);
}

// ----------------------------------------------------------------------------
// 3. Exact fill: both orders fully consumed, nothing left in the book.
// ----------------------------------------------------------------------------
TEST(Match, ExactFillEmptiesBook) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 5));
    auto r = eng.submit(limit(2, Side::Buy, 100, 5));

    EXPECT_EQ(r.filled, 5u);
    EXPECT_EQ(r.resting, 0u);
    EXPECT_TRUE(eng.book().empty());
    EXPECT_EQ(eng.book().order_count(), 0u);
}

// ----------------------------------------------------------------------------
// 4. Aggressor smaller than resting order: resting order shrinks and remains.
// ----------------------------------------------------------------------------
TEST(Match, PartialFillRestingRemains) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 10));
    auto r = eng.submit(limit(2, Side::Buy, 100, 4));

    EXPECT_EQ(r.filled, 4u);
    EXPECT_EQ(r.resting, 0u);                          // buy fully filled
    EXPECT_EQ(eng.book().quantity_at(Side::Sell, 100), 6u); // 10 - 4
    EXPECT_EQ(eng.book().order_count(), 1u);
}

// ----------------------------------------------------------------------------
// 5. Price priority: aggressor hits the LOWEST ask first.
// ----------------------------------------------------------------------------
TEST(Match, PricePriorityLowestAskFirst) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 101, 5));         // worse price
    eng.submit(limit(2, Side::Sell, 100, 5));         // better price (lower)
    auto r = eng.submit(limit(3, Side::Buy, 101, 5));

    ASSERT_EQ(r.trades.size(), 1u);
    EXPECT_EQ(r.trades[0].resting_id, 2u);            // matched the 100 level first
    EXPECT_EQ(r.trades[0].price, 100);
    EXPECT_EQ(eng.book().best_ask(), 101);            // the 101 ask remains
}

// ----------------------------------------------------------------------------
// 6. Time priority: at equal price, the OLDEST resting order fills first.
// ----------------------------------------------------------------------------
TEST(Match, TimePriorityOldestFirst) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 5));         // arrived first
    eng.submit(limit(2, Side::Sell, 100, 5));         // arrived second
    auto r = eng.submit(limit(3, Side::Buy, 100, 5));

    ASSERT_EQ(r.trades.size(), 1u);
    EXPECT_EQ(r.trades[0].resting_id, 1u);            // oldest filled first
    EXPECT_EQ(eng.book().quantity_at(Side::Sell, 100), 5u); // id 2 still resting
    EXPECT_FALSE(eng.cancel(1));                       // id 1 is gone
    EXPECT_TRUE(eng.cancel(2));                        // id 2 still cancellable
}

// ----------------------------------------------------------------------------
// 7. A large limit sweeps TWO levels, emits two trades, rests the remainder.
// ----------------------------------------------------------------------------
TEST(Match, SweepsTwoLevelsAndRests) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 5));
    eng.submit(limit(2, Side::Sell, 101, 5));
    auto r = eng.submit(limit(3, Side::Buy, 101, 12)); // wants 12

    ASSERT_EQ(r.trades.size(), 2u);
    EXPECT_EQ(r.trades[0].price, 100);                // lowest first
    EXPECT_EQ(r.trades[0].quantity, 5u);
    EXPECT_EQ(r.trades[1].price, 101);                // then next level
    EXPECT_EQ(r.trades[1].quantity, 5u);
    EXPECT_EQ(r.filled, 10u);
    EXPECT_EQ(r.resting, 2u);                          // 12 - 10 rests
    EXPECT_EQ(eng.book().best_bid(), 101);            // remainder rested as a bid
    EXPECT_EQ(eng.book().quantity_at(Side::Buy, 101), 2u);
    EXPECT_FALSE(eng.book().best_ask().has_value());  // both asks consumed
}

// ----------------------------------------------------------------------------
// 8. The limit price STOPS the sweep: cross one level, next is too expensive,
//    remainder rests (does not keep eating the book).
// ----------------------------------------------------------------------------
TEST(Match, LimitPriceStopsSweep) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 5));
    eng.submit(limit(2, Side::Sell, 110, 5));         // above the buy's limit
    auto r = eng.submit(limit(3, Side::Buy, 100, 12));

    ASSERT_EQ(r.trades.size(), 1u);                   // only the 100 level crossed
    EXPECT_EQ(r.filled, 5u);
    EXPECT_EQ(r.resting, 7u);                          // 12 - 5 rests @ 100
    EXPECT_EQ(eng.book().best_bid(), 100);
    EXPECT_EQ(eng.book().best_ask(), 110);            // 110 ask untouched
}

// ----------------------------------------------------------------------------
// 9. Sell side is symmetric: a sell crosses resting bids at the BID price.
// ----------------------------------------------------------------------------
TEST(Match, SellSideCrossesBidsAtRestingPrice) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Buy, 100, 5));          // resting bid @ 100
    auto r = eng.submit(limit(2, Side::Sell, 95, 5)); // willing to sell down to 95

    ASSERT_EQ(r.trades.size(), 1u);
    EXPECT_EQ(r.trades[0].price, 100);                // executes at the bid (resting) price
    EXPECT_EQ(r.trades[0].aggressor_id, 2u);
    EXPECT_EQ(r.trades[0].resting_id, 1u);
    EXPECT_TRUE(eng.book().empty());
}

// ----------------------------------------------------------------------------
// 10. A fully-filled resting order leaves NO dangling id_index_ entry.
//     (Guards against use-after-free on a later cancel.)
// ----------------------------------------------------------------------------
TEST(Match, FilledRestingLeavesNoIndexEntry) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 5));
    eng.submit(limit(2, Side::Buy, 100, 5));          // fully consumes id 1

    EXPECT_EQ(eng.book().order_count(), 0u);          // index empty
    EXPECT_FALSE(eng.cancel(1));                       // cancelling filled id fails cleanly
}

// ----------------------------------------------------------------------------
// 11. Sweeping multiple resting orders at the SAME price in FIFO order.
// ----------------------------------------------------------------------------
TEST(Match, SweepsSameLevelInFifoOrder) {
    me::MatchingEngine eng;
    eng.submit(limit(1, Side::Sell, 100, 3));         // oldest
    eng.submit(limit(2, Side::Sell, 100, 3));
    eng.submit(limit(3, Side::Sell, 100, 3));         // newest
    auto r = eng.submit(limit(4, Side::Buy, 100, 7)); // takes 3 + 3 + 1

    ASSERT_EQ(r.trades.size(), 3u);
    EXPECT_EQ(r.trades[0].resting_id, 1u);            // FIFO: 1, then 2, then 3
    EXPECT_EQ(r.trades[1].resting_id, 2u);
    EXPECT_EQ(r.trades[2].resting_id, 3u);
    EXPECT_EQ(r.trades[2].quantity, 1u);              // last one partially filled
    EXPECT_EQ(r.filled, 7u);
    EXPECT_EQ(eng.book().quantity_at(Side::Sell, 100), 2u); // 9 - 7 left on id 3
}
