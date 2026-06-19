cmake_minimum_required(VERSION 3.20)
project(matching_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

add_compile_options(-Wall -Wextra -Wpedantic)

add_library(me STATIC src/order_book.cpp src/matching_engine.cpp)          # sources added as I go...
target_include_directories(me PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(demo apps/demo.cpp)
target_link_libraries(demo PRIVATE me)

add_executable(replay apps/replay.cpp)
target_link_libraries(replay PRIVATE me)

add_executable(bench bench/bench_engine.cpp)
target_link_libraries(bench PRIVATE me)

include(FetchContent)
FetchContent_Declare(googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG        v1.15.2)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()
add_executable(unit_tests tests/test_matching_engine.cpp
tests/test_order_book.cpp)
target_link_libraries(unit_tests PRIVATE me GTest::gtest_main)
include(GoogleTest)
gtest_discover_tests(unit_tests)