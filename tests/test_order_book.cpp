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