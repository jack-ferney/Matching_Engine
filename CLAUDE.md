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

## Status (update as phases complete)
- **Phases 0–7 COMPLETE** — engine done, **31/31 GoogleTest cases green**.
  - Core types (`Order`/`Trade`, integer `Price` ticks, engine-stamped `Seq`).
  - Order book: `std::map` levels + `std::list` FIFO + `unordered_map` id index;
    `rest`/`cancel`/`reduce` all O(1) via the index.
  - Matching: price-time priority both sides, executes at the **resting** price.
  - Order types: Limit (rests), Market (cancels remainder), IOC (cancels remainder),
    FOK (atomic — `fillable_quantity` pre-check in `submit`, rejects if can't fully fill).
- **Phases 8–14 REMAINING**: 8 demo app, 9 CSV replay CLI, 10 Python tooling
  (generator/backtester/visualizer), 11 benchmark (p50/p99/p99.9), 12 optimization
  pass (object pool, flat-array levels — with before/after numbers), 13 README, 14 CI.

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
