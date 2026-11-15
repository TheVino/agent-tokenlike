# Item Synergies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add family sets, element reactions and named item pairs as synergies, a collection tab, achievements
and per-synergy measuring, without moving the balance targets.

**Architecture:** A `SYNERGIES` table in `dungeon.py`. Sets and pairs are checked from `run["items"]` and
their `fx` is summed in `stats()`, like the hero trait. Reactions are one rule in `combat()`. Discovery lives in
`run["synergies"]` and `meta["synergies"]`. The GUI only shows what the rules return.

**Tech Stack:** Python 3 standard library (tkinter). Tests are plain `assert` scripts run with `python tests/<file>.py`.

**Spec:** `docs/superpowers/specs/2026-11-15-item-synergies-design.md`. Read it first. Its "Rules settled
after the builder check" section is binding.

## Global Constraints

- Code, comments, identifiers, commits: English. Every visible text goes through `t()`/`_t()` with a `PT` entry
  in `i18n.py`, and names are original in both languages.
- Standard library only in the app; Pillow only in `tools/`.
- Balance targets in `tools/balance_stats.py` `TARGETS` stay unchanged:
  - 35–45% pass the 1st boss;
  - p90 between floors 13 and 16;
  - max ≤ 50.
- Caps apply to the final totals in `stats()`. No synergy lifts a stat past `MAX_*`.
- Every new box uses `card_box`/`chip`/`rounded_rect`/`shorten`+`tooltip`/`scrollbar`, and passes
  `tests/test_texts.py`.
- New `fx`/`stats()` field: icon in `art.STAT_ART`, line in `tokenlike.STAT_LINES`, text in `fx_text`.
- New achievement: `dungeon.ACHIEVEMENTS` + rule in `_check_achievements` + icon in `art.ACH_ART`.
- Run all tests after each task (commands in `CLAUDE.md`). Run `tools/simulate.py` after any `dungeon.py` change.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- **An old save without synergy keys loads and plays.** `migrate_run` and the meta loader fill in
  `run["synergies"] = []` and `meta["synergies"] = {}` (Task 3 test).
- **An interactive-mode take records discovery.** The GUI path through `resolve_pending` must reach
  `note_synergies` (Task 3 test on `resolve_pending`; Task 5 `test_gui` check).
- **Blood 2 never makes `attack_cost` negative.** `stats()` clamps `attack_cost` to ≥ 0 (Task 1 test).
- **A secret synergy never leaks.** Its name, hint and icons are not shown in pt or en until it is in
  `meta["synergies"]` (Task 5 test).
- **No reaction on a dead enemy.** The killing hit triggers no reaction, and Toxic Fumes/Conductor never pick a dead
  enemy (Task 2 test).

---

### Task 1: Synergy table, sets and pairs in `stats()`

**Files:**
- Modify: `dungeon.py`:
  - `FAMILIES`, `item_family` and `SYNERGIES` go near `ITEMS`;
  - `active_synergies` goes near `stats`;
  - change `stats()` and `_balance_version()`.
- Modify: `tokenlike.py`: delete `FAMILIES`/`item_family` and use `M.FAMILIES`/`M.item_family`.
- Modify: `art.py` (`STAT_ART["status_turns"]`), `tokenlike.py` (`STAT_LINES`), `i18n.py` (PT entries).
- Test: `tests/test_items.py`

**Interfaces:**
- Produces:
  - `dungeon.FAMILIES` (same tuple as today);
  - `dungeon.item_family(key: str) -> str`;
  - `dungeon.SYNERGIES: dict[str, dict]` (fields in the spec: `name`, `kind`, `req`, `fx`, `secret`, `hint`);
  - `dungeon.active_synergies(run: dict) -> list[str]` (sets and pairs only, in `SYNERGIES` order);
  - a new stats field `status_turns: int`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_items.py`:

```python
# synergies: data
S = M.SYNERGIES
assert sum(1 for s in S.values() if s["kind"] == "set") == 18
assert sum(1 for s in S.values() if s["kind"] == "pair") == 8
secret = [k for k, s in S.items() if s.get("secret")]
assert len(secret) == 3 and all(S[k]["kind"] == "pair" for k in secret)
for k, s in S.items():
    assert s["name"] and (s.get("secret") or s["hint"]), k
    if s["kind"] == "pair":
        a, b = s["req"]["items"]
        assert a in M.ITEMS and b in M.ITEMS and M.item_family(a) != M.item_family(b), k
        assert "Basic" not in (M.item_family(a), M.item_family(b)), k
assert len({s["name"] for s in S.values()} | {it["name"] for it in M.ITEMS.values()}) == len(S) + len(M.ITEMS)
# sets switch on at exactly 2 and 4
fam = "Defense"
keys = [k for k in M.ITEMS if M.item_family(k) == fam][:4]
r = M.new_run("slime", {}, 9)
def sets_on(r): return [k for k in M.active_synergies(r) if S[k]["kind"] == "set" and S[k]["req"]["family"] == fam]
for n, want in ((1, 0), (2, 1), (3, 1), (4, 2)):
    r["items"] = [{"key": k, "rar": "common"} for k in keys[:n]]
    assert len(sets_on(r)) == want, (n, sets_on(r))
# caps hold with every synergy on
r = M.new_run("slime", {}, 10); r["items"] = [{"key": k, "rar": "legendary"} for k in M.ITEMS]
st = M.stats(r)
assert st["crit"] <= M.MAX_CRIT and st["block"] <= M.MAX_BLOCK and st["double"] <= M.MAX_DOUBLE
assert st["thorns"] <= M.MAX_THORNS and st["luck"] <= M.MAX_LUCK and st["attack_cost"] >= 0
# a pair turns on only with both items
pk = next(k for k, s in S.items() if s["kind"] == "pair"); a, b = S[pk]["req"]["items"]
r = M.new_run("slime", {}, 11); r["items"] = [{"key": a, "rar": "common"}]
assert pk not in M.active_synergies(r)
r["items"].append({"key": b, "rar": "common"}); assert pk in M.active_synergies(r)
```

- [ ] **Step 2: Run** `python tests/test_items.py`. Expected: `AttributeError: module 'dungeon' has no attribute 'SYNERGIES'`.

- [ ] **Step 3: Implement.**
  - **Move.** Move `FAMILIES` and `item_family` to `dungeon.py` unchanged.
  - **Sets.** Add the 18 set entries, keys `<family_slug>2` / `<family_slug>4` (e.g. `defense2`). The `fx` start
    values below are tuned in Task 4:

    | Family | 2 items | 4 items |
    |---|---|---|
    | Elemental | `{"elem_boost": 0.03}` | `{"status_turns": 1}` |
    | Defense | `{"block": 1}` | `{"thorns": 0.1}` |
    | Regeneration | `{"heal_floor": 2}` | `{"heal_room": 1}` |
    | Blood | `{"attack_cost": -1}` | `{"fury": 1}` |
    | Strikes | `{"crit": 0.03}` | `{"double": 0.05}` |
    | Area | `{"atk": 1}` | `{"atk": 1, "critdmg": 0.25}` |
    | Helper | `{"helper": 1}` | `{"helper": 2}` |
    | Growth | `{"maxhp": 4}` | `{"atk": 2}` |
    | Luck & gold | `{"luck": 0.1}` | `{"gold": 0.25, "discount": 0.1}` |

    - These swaps are allowed by the spec's swap rule: Area, Growth and Luck 4 have no new mechanic.
    - Write each set's `hint` as "Have 2 Defense items" (the 4-step says 4).
  - **Pairs.** Pick 8 pair entries from existing items. Each pair crosses two different non-Basic families and has a
    thematic link. Its `fx` is small (at most the size of one common item of either family).
    - Mark 3 of them `secret: True`.
    - Their hint is "Have <item A> and <item B>".
  - **`active_synergies(run)`** counts `item_family` over `run["items"]`.
  - **`stats()`** sums the active entries' `fx` after the trait and items, with no rarity scaling. Then:
    - `elem_boost` adds to each element whose summed chance is > 0. It is not an output field.
    - `status_turns` is a new output field, default 0.
    - Clamp `attack_cost` to ≥ 0.
  - **Hash.** Add `SYNERGIES` (`kind`, `req`, `fx` only) to the `_balance_version` blob.
  - **Field display.** `status_turns` gets an icon, a `STAT_LINES` line and `fx_text` text. Add PT entries for every
    new name, hint and text.

- [ ] **Step 4: Run** `python tests/test_items.py`, `python tests/test_i18n.py`, `python tests/test_gui.py`.
  Expected: all pass.

- [ ] **Step 5: Commit.** `feat(synergies): family sets and named pairs in stats()`

### Task 2: Element reactions in `combat()`

**Files:**
- Modify: `dungeon.py`: reaction entries in `SYNERGIES`, `_apply_status`, `combat()`, `RULES_REV` 8 → 9.
- Test: `tests/test_combat.py`

**Interfaces:**
- Consumes: `SYNERGIES`, and `st["status_turns"]` from Task 1.
- Produces:
  - 6 entries with `kind: "reaction"` and `req: {"status": [a, b]}`;
  - every combat step dict gains `"reaction": <synergy key> | None`.

- [ ] **Step 1: Write the failing tests.** Append to `tests/test_combat.py`, using the file's `foe()`/`pet()`
  helpers and a seeded `random.Random`. One assert block per reaction:
  - **Shatter** (`burn` on a frozen foe): a step has `reaction == "shatter"`, the extra damage equals the pet ATK,
    and the foe's `freeze` is 0 afterwards.
  - **Toxic Fumes** (`burn` + `poison`): every other *living* foe gains 1 poison stack, and a dead foe gains none.
  - **Overload** (`burn` + `shock`): an extra dot step of `round(BURN[0] + BURN[1] * f)` right away.
  - **Conductor** (`shock` + `freeze`): another living foe gets `shock`.
  - **Jolt Venom** (`shock` + `poison`): the poison stacks grow by 1, never past `POISON_MAX_STACKS`.
  - **Frostbite** (`poison` + `freeze`): `freeze` grows by 1 turn.
  - **Edge cases:**
    - Re-applying a status the foe already has gives no reaction.
    - A status put on by a reaction never triggers a second reaction (count `reaction` steps == 1).
    - The killing hit gives no reaction.
    - Statuses on the pet never react.
  - **Status duration:** `status_turns` 1 makes a fresh burn last `BURN_TURNS + 1`.

  Pin the setup by putting the first status straight into `foe["status"]` and giving the pet that element's
  chance 1.0.

- [ ] **Step 2: Run** `python tests/test_combat.py`. Expected: FAIL, because no step has a `reaction` key.

- [ ] **Step 3: Implement.**
  - **Entries.** Add the 6 reaction entries; names, keys and effects come from the spec table. Keys: `shatter`,
    `toxic_fumes`, `overload`, `conductor`, `jolt_venom`, `frostbite`.
  - **Where it fires.** In the pet's hit, take the set of statuses the foe already has *before* the element rolls.
    Each newly applied status that is not in that set reacts with the first status of the set, in `STATUS_NAME`
    order.
  - **Effects.**
    - Use `_apply_status` straight for effects, so they never re-enter the reaction check.
    - `_apply_status` takes an extra `turns_bonus: int = 0` (from `st["status_turns"]`).
  - **Steps.** Record the reaction on its own step: `who="pet"`, `reaction=key`, `dmg` = its damage or 0.
  - **`RULES_REV`** goes to 9.

- [ ] **Step 4: Run** `python tests/test_combat.py`, `python tests/test_gui.py`, `python tools/simulate.py`.
  Expected: tests pass. Note the simulator's pass-boss rate for Task 4.

- [ ] **Step 5: Commit.** `feat(synergies): element reactions in combat`

### Task 3: Discovery, records and achievements

**Files:**
- Modify: `dungeon.py`:
  - `new_run`, `new_meta`, `migrate_run`, meta loading;
  - a new `note_synergies`;
  - calls in `enter_room` and `resolve_pending`;
  - `run_record`, `ACHIEVEMENTS`, `_check_achievements`.
- Modify: `art.py` (`ACH_ART` × 3), `i18n.py`.
- Test: `tests/test_items.py`, `tests/test_records.py`

**Interfaces:**
- Consumes: `active_synergies` (Task 1) and step `reaction` (Task 2).
- Produces:
  - `note_synergies(run: dict, meta: dict, ev: dict, extra: list[str] = ()) -> None`;
  - `run["synergies"]: list[str]`;
  - `meta["synergies"]: dict[str, {"runs": int, "first_run": int}]`;
  - `ev["synergies"]: list[{"key": str, "new": bool}]`, plus a log line in `ev["lines"]`;
  - `run_record(...)["synergies"]`;
  - achievements `synergy5`, `reactions_all`, `synergies3run`.

- [ ] **Step 1: Write the failing tests.**
  - `test_items.py`, discovery:
    - Taking the 2nd Defense item via `resolve_offer` + `note_synergies` puts `defense2` in `run["synergies"]`,
      `meta["synergies"]["defense2"] == {"runs": 1, "first_run": run["id"]}`, and `ev["synergies"]` has
      `{"key": "defense2", "new": True}`.
    - Calling `note_synergies` again adds nothing (no duplicate, no new event).
    - A new run with the same items gives `runs == 2` and `new` False.
    - `extra=["shatter"]` records the reaction the same way.
  - `test_items.py`, interactive path:
    - A pending offer resolved by `resolve_pending(run, meta)` that completes a set records it.
  - `test_items.py`, old saves:
    - `migrate_run` on a run dict without `"synergies"` gives `[]`.
    - The meta loader on a meta without `"synergies"` gives `{}`.
  - `test_items.py`, achievements:
    - 5 keys in `meta["synergies"]` grant `synergy5`.
    - All 6 reaction keys grant `reactions_all`.
    - 3 keys in `run["synergies"]` grant `synergies3run`.
  - `test_records.py`: `run_record(...)["synergies"] == run["synergies"]`.

- [ ] **Step 2: Run** both files. Expected: FAIL on `note_synergies` missing.

- [ ] **Step 3: Implement.**
  - **What `note_synergies` does.** It adds keys from `active_synergies(run)` + `extra` that are not yet in
    `run["synergies"]`. It updates `meta`, appends to `ev["synergies"]` and adds the line to `ev["lines"]`.
  - **Log lines.**
    - "Synergy: {name}!", or "New synergy: {name}!" when it is a first discovery.
    - Translate them the same way the existing item-name event lines are translated.
  - **Call sites.**
    - `enter_room` calls it once at the end. `extra` = the `reaction` keys of `ev["hits"]` (combat runs once per
      room, at `dungeon.py:991`).
    - `resolve_pending` calls it after resolving.
  - **Achievements.** The 3 new ones are checked in `_check_achievements`, wherever it already runs.

- [ ] **Step 4: Run** every test file. Expected: all pass.

- [ ] **Step 5: Commit.** `feat(synergies): discovery, run records and achievements`

### Task 4: Measuring and tuning

**Files:**
- Modify: `tools/simulate.py`, `tools/balance_stats.py` (+ `tests/test_balance_stats.py`), and `dungeon.py`
  (synergy numbers only).

**Interfaces:**
- Consumes: `run_record["synergies"]` (Task 3).
- Produces: the share of runs per synergy in `simulate.py`'s output; a "Synergies" section in the stats page and in
  the `.json` (`data["synergies"]["sim"|"real"][key] = {"n", "median_with", "median_without"}`).

- [ ] **Step 1: Write the failing test.** In `tests/test_balance_stats.py`, `collect(...)` on a small sim has
  `"synergies"` with an entry for some set key, and `make_html` contains `<h2>Synergies</h2>`.

- [ ] **Step 2: Run** it. Expected: FAIL.

- [ ] **Step 3: Implement.**
  - **Stats code.** The `simulate.py` print and the stats section, with the synergy name and the item/family icon
    via the existing `_item_icon`.

- [ ] **Step 4: Tune.**
  - Run `python tools/balance_stats.py --no-open` and check the calibration rows against `TARGETS`.
  - If they are off, change **synergy numbers only** (Task 1 table, pair `fx`, reaction damage). Repeat.
  - If the targets still fail with every synergy at its smallest sensible value, stop and report to the owner with
    the numbers. Do not touch other balance constants without the owner.

- [ ] **Step 5: Run** every test file. Expected: all pass. **Commit:** `feat(synergies): measuring and tuning`

### Task 5: Synergies tab and GUI lines

**Files:**
- Modify: `tokenlike.py`:
  - `show_items`: "Items | Synergies" chips;
  - a new `synergy_card`;
  - event log line color;
  - a `show_stats` line;
  - a `show_profile` counter.
- Modify: `i18n.py`.
- Test: `tests/test_texts.py`, `tests/test_gui.py`

**Interfaces:**
- Consumes: `SYNERGIES`, `meta["synergies"]`, `run["synergies"]`, `ev["synergies"]`.
- Produces: `PetApp.synergy_card(cv, x, y, key) -> None`. The canvas is tagged `card:<key>` via `extra=`, like
  `item_card`.

- [ ] **Step 1: Write the failing tests.**
  - `test_gui.py`:
    - The Items window has an "Items"/"Synergies" chip pair. Switching draws one `card:<key>` per `SYNERGIES` entry.
    - With an empty `meta["synergies"]`, the canvas text of a secret card is exactly "???", and no text contains
      its name or hint. Check in pt and en.
    - After a room whose `ev["synergies"]` is non-empty, the log shows the line.
    - The Status window lists an active synergy's name.
  - `test_texts.py`: open the Synergies tab with worst-case data:
    - every synergy discovered;
    - long names;
    - 999 runs.

    Then run `check(window)` in pt and en.

- [ ] **Step 2: Run** both. Expected: FAIL.

- [ ] **Step 3: Implement.**
  - **Card icons.** Pair → the 2 item icons. Set → the `STAT_ART` icon of the family's first field. Reaction → the
    2 status icons.
  - **Card text.** Name, the effect via `fx_text` (reactions: a short fixed English text with a PT entry),
    "Active in {n} runs" and "Discovered in run #{n}".
  - **Locked.** Silhouette plus the hint.
  - **Secret.** "???" only.
  - **Log.** A new discovery uses the gold color already used for rare events.
  - **Profile.** The counter "Synergies {n}/{total}".

- [ ] **Step 4: Run** every test file, then `python tokenlike.py --demo`. Open the tab and look at it on the screen.
  Expected: tests pass, and nothing is clipped.

- [ ] **Step 5: Commit.** `feat(synergies): synergies tab and GUI lines`

### Task 6: Docs

**Files:**
- Modify: `CLAUDE.md`:
  - a "Synergies" bullet under "How the pieces fit";
  - a "New synergy" entry under "Adding things";
  - `RULES_REV` now 9;
  - the test list.
- Modify: `README.md` (one feature line).

- [ ] **Step 1:** Write the docs, run every test file once more, and commit: `docs: synergies`.
