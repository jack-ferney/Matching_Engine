# CLAUDE.md

Guidance for Claude Code working in this repo. Keep edits to this file terse.

## What this is
A C++20 limit-order-book matching engine + Python backtester, built from scratch
by following a 14-phase lab guide. It's the user's June–Aug 2026 portfolio project
for quant/SWE interviews (Jane Street). The goal is **deep understanding**, not just
a working binary — the user must be able to whiteboard the architecture from memory.

## How the user works (IMPORTANT — read first)
- **The user writes all the implementation code themselves.** Claude's role is to
  guide and review, NOT to write engine/test logic ahead of them.
- When asked "how do I X", "explain X", "walk me through X": explain the concept and
  the *why*, then let them write it.
- When asked "how does my X look" / "review X": read their code, point out bugs and
  omissions, show the *targeted* fix (a line or two), but don't rewrite whole functions.
- Writing tests on request is fine — tests are the spec. Write them to the *correct*
  behavior even if it exposes a gap in their current code (TDD); flag which will fail.
- Scaffolding/config (CMake, .vscode, .gitignore, this file) — fine to write directly.
- Suggesting test cases and small idiomatic improvements is welcome.
- Start every message with "Hi Jack"

## Status (update as phases complete)
- **Phases 0–9 COMPLETE.**
  - **0–7** engine, **31/31 GoogleTest green**. Core types (`Order`/`Trade`, integer
    `Price` ticks, engine-stamped `Seq`). Order book: `std::map` levels + `std::list`
    FIFO + `unordered_map` id index; `rest`/`cancel`/`reduce` all O(1). Matching:
    price-time priority both sides, executes at the **resting** price. Order types
    Limit/Market/IOC/FOK (FOK atomic via `fillable_quantity` pre-check in `submit`).
  - **8** `apps/demo.cpp`.
  - **9** `apps/replay.cpp` CSV replay CLI — reads `id,side,type,price,qty` on stdin,
    prints trades `aggressor_id,resting_id,price,qty,seq` on stdout. CMake target
    `replay` → `build\replay.exe`. Samples `apps/sample{1,2,3}.csv`. Parser matches
    UPPERCASE types + `B`/`S` sides; unknown type falls through to FOK.
- **Phase 10 IN PROGRESS** — Python tooling in `tools/`:
  - `generator.py` — synthetic flow; mid random-walk + side-aware passive/aggressive
    placement + weighted types. `--n/--seed/--out`.
  - `backtester.py` — `Backtester`: `register`/`register_from(mm_csv)`, `run(trades_csv)`,
    `on_trade` (signed-qty → cash/position), `pnl(mark)`, `summary()`, `equity_curve`,
    `fills`, `last_price`. CLI: `backtester.py trades.csv --mm mm.csv`.
  - `strategy.py` — open-loop market-maker; every `quote_every` steps emits passive
    bid/ask at mid±spread (qty `quote_qty`, ids ≥ 1_000_000), writes combined orders
    CSV + `id,side` sidecar. All knobs are CLI flags.
  - Tests: `tools/test_backtester.py` (17) + `tools/test_strategy.py` (12) +
    `tools/test_generator.py` (8) = **37 green**.
    Plain-assert harness (no pytest): `python tools/test_backtester.py`.
  - Pipeline: `strategy.py` → orders + mm csv; `Get-Content orders.csv | build\replay.exe
    | Set-Content trades.csv`; `backtester.py trades.csv --mm mm.csv`.
  - KNOWN LIMITATION: replay CSV is submit-only (no cancel) + pipeline is open-loop, so
    the MM can't manage inventory. Engine DOES have O(1) `cancel`/`reduce`
    (`matching_engine.hpp`) — limit is the CLI/harness, not the engine. Next: (1) cancel
    action in replay protocol for quote re-centering; (2) closed-loop interactive
    protocol for inventory-aware skewing.
  - REMAINING: `visualizer.py` (plot `equity_curve` + inventory path).
- **Phases 11–14 REMAINING**: 11 benchmark (p50/p99/p99.9), 12 optimization pass
  (object pool, flat-array levels — before/after numbers), 13 README, 14 CI.

## Layout
- `include/me/*.hpp` — public headers (declarations). Namespace `me`.
- `src/*.cpp` — implementations, compiled into static lib `me`.
- `tests/test_matching_engine.cpp` — GoogleTest suite (suites: `Sanity`, `Match`).
- `apps/` demo+replay (Phase 8–9) · `bench/` (Phase 11) · `tools/` Python (Phase 10).
- Headers go in `include/me/`, NOT a top-level folder. Include own headers with `""`,
  system/third-party with `<>`.

## Build & test (Windows, PowerShell 5.1)
```powershell
cmake --build build                                 # incremental; reconfigure only on CMake change
ctest --test-dir build --output-on-failure          # run all tests
.\build\unit_tests.exe --gtest_filter='Match.*'     # run a subset
```
First-time configure: `cmake -S . -B build -G Ninja` (downloads GoogleTest once).

## Environment gotchas
- **PowerShell 5.1**: no `&&` (use `;` or `; if ($?) { ... }`), no `<` redirection,
  `$null`/`$env:` not `/dev/null`/`$VAR`.
- Toolchain via Chocolatey: g++ 15.2 (MinGW, `C:\ProgramData\mingw64\mingw64\bin`),
  cmake 4.3, ninja 1.13. New terminals pick these up from machine PATH.
- Windows `sudo` is enabled but runs elevated commands in a *new window* — no captured
  output; verify results afterward.
- Build flags: `-Wall -Wextra -Wpedantic`, C++20 strict (no GNU extensions). Keep the
  build warning-clean (watch for unused vars, extra `;`, sign-compare — use `u` suffix).

## Git
- Remote `origin` = github.com/jack-ferney/Matching_Engine. `main` is protected
  (PRs required) — work on a branch, push, open PR, merge. One commit per phase,
  messages like `feat: market orders`.
