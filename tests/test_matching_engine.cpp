#include "me/types.hpp"
#include <gtest/gtest.h>

TEST(Sanity, TypesCompile) {
    me::Order o{1, me::Side::Buy, me::OrderType::Limit, 100, 10, 0};
    EXPECT_EQ(o.quantity, 10u);
}