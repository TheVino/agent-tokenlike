---
name: balance
description: Checks the health of the game's balance (targets, green and red items, pairs, where runs die, simulated x real) and proposes number changes in dungeon.py. Use when the owner asks to "balance", for "balanceamento", "game health" or "item stats".
---

# Balance

Never edit a file without the owner's explicit approval. Report first, then propose.

## Steps

1. Run `python tools/balance_stats.py --no-open` (options: `--runs N`, `--real-dir DIR`, `--all-versions`).
2. Read `tools/out/balance_stats.json`. Keys:
   - `calibration.without_achievements` and `calibration.with_achievements`: slime only, same as `tools/simulate.py`. The targets are judged here.
   - `sim`, `sim_without_achievements` (all heroes mixed, informative only) and `real`. Each has `n`, `median`, `p90`, `max`, `passed_boss1`, `items_median`.
   - `targets`: `without_achievements`, `with_achievements` and `real`, with True/False per target (`null` for real without runs). Target values in `TARGETS` of `tools/balance_stats.py`.
   - `items.<key>.sim` / `.real`: `n`, `lasted`, `vs_expected` (raw), `vs_mean` (vs_expected minus the weighted mean of the items of that source), `quick_deaths`, `consumed_by_mode`.
   - `pairs.sim.best_items` / `pairs.sim.worst_items` (and `pairs.real.*`): `a`, `b`, `n`, `vs_expected`, `gain`. The worst never repeat the best.
   - `deaths.sim` / `deaths.real`: `per_floor`, `killers`, `per_kind` (monster, horde, boss, mimic, trap, status; "?" on old lines). `heroes.sim` / `heroes.real`: `n`, `median`, `p90` per hero.
   - `real_info`: `modes`, `gave_ups`, `ignored`, `other_versions`.
3. Report, briefly:
   - targets ✓/✗ for the calibration (without and with achievements) and for real;
   - green items (`vs_mean` > +1) and red ones (`vs_mean` < −1). Use `vs_mean`, not `vs_expected`: taking any item already helps, so the raw value is almost always positive. Ignore sim with a small `n`; real with `n` < 10 is low confidence, say so;
   - pairs that are too strong (`gain` > +1.5) and anti-synergies (`gain` < −1.5). A pair only counts with `n` >= 30;
   - where runs die (floor, killers and kind). Hordes should stay between 5% and 35% of deaths; status above 0 and never the majority;
   - sim x real difference, only if real has 10 runs or more. `gave_up` runs are already left out.
   "lasted" = floors the run lasted after taking the item. "vs expected" = lasted minus the mean remaining floors of the runs alive on that floor.
4. Propose number changes in `dungeon.py`, each with the reason and the expected effect. Lever order (the one in `CLAUDE.md`): rarity (`RAR_MULT`, weights) -> `consume` -> chest/mimic/shop (`SHOP_PRICE`); in combat: status and crit -> speeds -> horde (weight in `ROOM_WEIGHTS`, `horde_max`, `HORDE_GOLD_MULT`; `HORDE_MULT` belongs to the owner) -> only then the monster/boss curves (`MON_*`/`BOSS_*`). For the tail (max and very long runs), the lever is `BOSS_RAMP` (extra boss ramp after floor `BOSS_RAMP_FROM`), which does not touch the 1st and 2nd bosses. Change a little at a time.
   - **Green or red item:** change the item's own `fx` first, not the curves. Besides `atk`/`def`/`maxhp`/`dodge`/`gold`/`lifesteal`/`energy`/`trap`, each item can use the family fields: `spd`, `crit`, `critdmg`, `area`, `burn`/`shock`/`poison`/`freeze`, `block`, `thorns`, `heal_room`, `heal_floor`, `attack_cost`, `fury`, `double`, `helper`, `grow` (smaller = stronger), `luck` and `discount`. The caps (`MAX_CRIT`, `MAX_ELEM_CHANCE`, `MAX_BLOCK`, `MAX_THORNS`, `MAX_DOUBLE`, `MAX_LUCK`, `MAX_DISCOUNT`, `MAX_DODGE`) apply to the sum and only matter for stacked builds. `atk` and `critdmg` have no cap and stretch the tail; prefer capped attributes. Legendary-only items usually have `n` < 100: treat them as small samples. The `candle` and pure `energy`/`luck`/`gold`/`discount` items come out weak in the sim by nature (the sim does not use energy; gold only matters in the shop).
5. Wait for the owner's approval. Without an explicit "yes", edit nothing.
6. After editing: run every test in `tests/`, `python tools/simulate.py` and `python tools/balance_stats.py --no-open` again. Show before and after.
7. Warn that `BALANCE_VERSION` changed (if a formula or a number written in the code changed, bump `RULES_REV` in `dungeon.py`, now 8): the real history (`~/.tokenlike/runs.jsonl`) restarts on the new version; old runs only show with `--all-versions`.
