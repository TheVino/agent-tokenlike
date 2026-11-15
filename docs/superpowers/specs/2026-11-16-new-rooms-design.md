# New rooms and room choices: design

Date: 2026-11-16. Status: draft, waiting for the owner's approval.

## Intent

The owner wants three new feelings in a run, one per new room:

- **A rare surprise** you celebrate when you see it.
- **A risk that may pay off.**
- **A pause with a story.**

Two of the rooms carry **more player choices**, which is the first step toward the "more choices" idea. The story
lines are **collected in a Journal**, a compendium like the Graveyard.

## Goals

- **Secret Room** (`secret`, rare, about 2% of rooms):
  - a chest with an item of rare rarity or better, plus a lot of gold;
  - no risk;
  - achievement `secret3`: find 3 Secret Rooms (meta counter).
- **Cracked Idol** (`idol`), a choice between accept and decline:
  - **accept:** pay 25% of current HP (never kills, min 1 HP left). There is a 50% chance of an item rolled at epic or
    legendary (falling back to the best rarity the item allows). On a fail, a short curse: −1 ATK for the next 3
    rooms.
  - **decline:** nothing happens.
- **Traveler's Campfire** (`campfire`), a choice of 1 of 3 boons:
  - the pet meets a traveler, a ghost or a wanderer, who says one short original line;
  - the 3 boons are drawn from a small boon list, e.g. heal 30% of max HP, +1 DEF for the run, a pile of gold,
    +1 ATK for the next 5 rooms;
  - the line is stored in the Journal the first time it is heard.
- **Generalized pending choice:**
  - `run["pending"]` becomes a typed choice: `{"kind": "offer" | "idol" | "campfire", ...}`;
  - one choice window draws any kind;
  - one automatic rule per kind;
  - the 30 s window, "never enter a room with an open choice" and saving keep working as today.
- **Journal window** in the right-click menu:
  - one card per line, with who said it, the line, and the run and floor where it was first heard;
  - unheard lines show "???";
  - a counter "N/total".

## Non-goals

- Boss sprites and further choice rooms. They are separate projects that come next; this design only makes them
  cheap.
- Sounds (vetoed).
- Changing combat.

## Anti-goals

- The balance targets in `tools/balance_stats.py` `TARGETS` move. They stay: 35–45% pass the 1st boss, p90 13–16,
  max ≤ 50.
- The Idol becomes a must-accept or a must-decline. In automatic mode it should be close to neutral on average.
- The Campfire turns into a free full heal every floor.
- Any text not translated, any art or name taken from an existing game.
- The interactive mode's existing offer flow (take/consume) changing behaviour for the player.

## Approaches considered

- **A. Generalize the pending choice (picked by the owner).** `run["pending"]` gets a `kind` and per-kind options,
  so every future choice room only needs data and an auto rule.
- **B. A pending field and window per new room.** Rejected: it duplicates the window, timeout, save and auto rule for
  every new room.
- **C. New rooms always auto-resolve.** Rejected: it does not deliver "more choices".

## Design

### Pending choice

- `run["pending"]` shapes:
  - `{"kind": "offer", "key", "rar"}`: today's item offer. Old saves (no `kind`) are read as `"offer"` in `migrate_run`.
  - `{"kind": "idol", "cost": int}`, choices `"accept"` / `"decline"`.
  - `{"kind": "campfire", "line": key, "boons": [b1, b2, b3]}`, choices are the boon keys.
- `choose_pending(run, meta, choice)` dispatches on `kind`. `resolve_pending` uses `auto_choice(run, pending)`, which
  dispatches on `kind` too:
  - `offer`: today's rule.
  - `idol`: accept only if HP > 60% of max HP.
  - `campfire`: heal if HP < 50% of max HP, otherwise the first boon in a fixed priority order.
- `enter_room` never runs with an open pending choice (today's rule).
- The choice window (`show_choice`) draws a title, the room art, the line (campfire) and one chip per option, with
  an `fx`-style text for each.

### Temporary effects

- `run["temp"]`: a list of `{"fx": {...}, "rooms": n}`.
- `stats()` adds their `fx` (no rarity scaling, before the caps).
- `enter_room` decrements `rooms` after the room and drops the ones at 0.
- The idol curse and the "+1 ATK for 5 rooms" boon use it.

### Rooms

- `ROOM_WEIGHTS` gains `secret`, `idol` and `campfire`. The exact weights are tuned with the simulator.
- `idol` and `campfire` appear from floor 2 on.
- Each room gets a branch in `enter_room`, an animation in `PetApp.play_room`, and original art in `art.py`.
- Event lines in English with `PT` entries, e.g. "The idol cracks: {item}!", "The idol's curse bites.".

### Journal

- `dungeon.TALES`: about 16 original lines, `{key: {"who": ..., "text": ...}}`, English with PT translations. The tone
  is dark and cute, with no names from existing games.
- `meta["journal"][key] = {"run": id, "floor": n}` is written when a campfire line is first heard. A campfire
  prefers lines not yet heard.
- `show_journal`:
  - a scrolling window built with the GUI helpers;
  - a card per tale with an icon of who said it, and the line wrapped;
  - "???" when unheard;
  - it passes `tests/test_texts.py` in pt and en.

### Measuring

- `run_record` gains `rooms` counts per kind if not already there, for the new rooms.
- `tools/simulate.py` and `tools/balance_stats.py` show how often each new room appears and the idol's
  accept/success rates.
- `RULES_REV` goes up by 1.

### Tests

- `test_items.py`:
  - pending kinds, old-save `offer` migration;
  - auto rules per kind;
  - the idol never kills;
  - temp effects expire.
- `test_combat.py`: none expected.
- `test_gui.py`:
  - each new room plays;
  - the choice window for each kind;
  - the Journal opens;
  - a timeout resolves with the auto rule.
- `test_texts.py`: the choice window for each kind and the Journal, with worst-case data, in pt and en.
- `test_i18n.py`: every new text.

## Rules settled after the builder check (my calls, owner can override)

- **When the choice resolves:**
  - Idol and campfire effects apply when the choice resolves: inline in auto mode, or in `choose_pending` in
    interactive mode.
  - "Next N rooms" counts rooms entered **after** the choice resolves. Stairs do not count.
- **Idol success item:** it goes through the normal offer path (`deliver`). In interactive mode that opens a second,
  chained `offer` pending (take/consume).
  - `migrate_run` must only drop an `offer` pending whose `key` is unknown. It must keep the `idol` and `campfire`
    pendings.
- **Balance budget:** the new rooms take their weight from `monster`, so the room total stays the same.
  `simulate.py` must stay inside the targets with the new rooms in. Tune the new rooms' numbers first.
- **Idol at very low HP:** "accept" is offered only when current HP ≥ 4. Below that, the idol shows only "decline",
  and auto mode declines.
- **Counters:** `meta["secrets"]` counts Secret Rooms found. `run["rooms"]` holds per-kind counts and goes into
  `run_record` as a new `rooms` field; a new field is fine.
- **Tales:** a campfire prefers unheard tales. Once all are heard, it repeats at random.

## Left to the builder

- Exact numbers: weights, idol odds and cost, boon sizes, gold amounts. Set them with the simulator and the targets.
- The boon list (5 to 6 boons, small) and the 16 tales. The owner reviews the tales before merge.
- Art for the 3 rooms, the traveler/ghost/wanderer icons and the `secret3` achievement.
