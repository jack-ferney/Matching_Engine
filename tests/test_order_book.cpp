#include "me/types.hpp"
#include "me/order_book.hpp"
#include <gtest/gtest.h>

TEST(Book, RestAndTopOfBook) {
    me::Order o1{1, me::Side::Buy, me::OrderType::Limit, 100, 10, 0};
    me::Order o2{2, me::Side::Sell, me::OrderType::FOK, 30, 10, 0};
    me::Order o3{3, me::Side::Buy, me::OrderType::Market, 100, 13, 0};
    me::Order o4{4, me::Side::Sell, me::OrderType::Limit, 20, 14, 0};
    
    me::OrderBook b1;

    EXPECT_EQ(b1.quantity_at(me::Side::Sell, 30), 0);
    EXPECT_EQ(b1.quantity_at(me::Side::Sell, 20), 0);
    EXPECT_EQ(b1.quantity_at(me::Side::Buy, 100), 0);
    
    b1.rest(o1);
    b1.rest(o2);
    b1.rest(o3);
    b1.rest(o4);
    
    EXPECT_EQ(b1.quantity_at(me::Side::Sell, 30), 10);
    EXPECT_EQ(b1.quantity_at(me::Side::Sell, 20), 14);
    EXPECT_EQ(b1.quantity_at(me::Side::Buy, 100), 23);

    EXPECT_NE(b1.quantity_at(me::Side::Buy, 30), 10);
    EXPECT_NE(b1.quantity_at(me::Side::Buy, 20), 14);
    EXPECT_NE(b1.quantity_at(me::Side::Sell, 100), 23);
}

TEST(Book, CancelRemovesOrderAndLevel) {
    me::OrderBook b;
    b.rest({1, me::Side::Buy, me::OrderType::Limit, 100, 10, 1});
    EXPECT_TRUE(b.cancel(1));                          // cancel succeeds
    EXPECT_FALSE(b.cancel(1));                         // second cancel of same id fails
    EXPECT_EQ(b.order_count(), 0u);                    // nothing left in the index
    EXPECT_EQ(b.quantity_at(me::Side::Buy, 100), 0u);  // level total is gone
    EXPECT_FALSE(b.best_bid().has_value());            // empty level was dropped
}


TEST(Book, ReduceShrinksQuantity) {
    me::OrderBook b;
    b.rest({1, me::Side::Buy, me::OrderType::Limit, 100, 10, 1});
    EXPECT_TRUE(b.reduce(1, 4));                        // 10 -> 4
    EXPECT_EQ(b.quantity_at(me::Side::Buy, 100), 4u);
}

TEST(Book, ReduceRejectsIncrease) {
    me::OrderBook b;
    b.rest({1, me::Side::Buy, me::OrderType::Limit, 100, 10, 1});
    EXPECT_FALSE(b.reduce(1, 20));                      // can't grow
    EXPECT_FALSE(b.reduce(1, 10));                      // equal is also rejected
    EXPECT_EQ(b.quantity_at(me::Side::Buy, 100), 10u);  // unchanged
}

TEST(Book, ReduceToZeroCancels) {
    me::OrderBook b;
    b.rest({1, me::Side::Buy, me::OrderType::Limit, 100, 10, 1});
    EXPECT_TRUE(b.reduce(1, 0));                        // delegates to cancel
    EXPECT_EQ(b.order_count(), 0u);
    EXPECT_FALSE(b.best_bid().has_value());             // level dropped
}

TEST(Book, ReduceUnknownIdFails) {
    me::OrderBook b;
    EXPECT_FALSE(b.reduce(999, 5));
}
