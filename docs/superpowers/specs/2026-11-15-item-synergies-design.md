# Item synergies: design

Date: 2026-11-15. Status: draft, waiting for the owner's approval.

## Intent

Today items only add numbers in `dungeon.stats()`. Synergies make some combinations matter on purpose, and they
give the owner something to collect: a "Synergies" tab, discovery and new achievements.

The owner's words, as the guiding rule: the pet may get strong, **never absurd**. A synergy gives a run **more
chances**, not a guaranteed win.

## Goals

- Three kinds of synergy:
  - **Family sets:** 2 items of a family turn on a weak effect, 4 items turn on a strong one.
  - **Element reactions:** the pet applies a status to an enemy that already has another status.
  - **Named pairs:** two specific items with their own name.
- A "Synergies" tab in the Items window, used as a collection.
  - Each card shows the items or family involved, the effect, how many runs it was active in, and the run it was
    discovered in.
  - An undiscovered synergy is a silhouette with a hint, e.g. "2 Ice items and 1 Fire item".
  - **3 synergies are fully secret.** They show only "???" until the first activation.
- A line in the event log when a synergy turns on ("Synergy: Shatter!"). The first time, it reads
  "New synergy: Shatter!".
- New achievements:
  - `synergy5`: discover 5 synergies.
  - `reactions_all`: discover every element reaction.
  - `synergies3run`: have 3 synergies active in one run.
- The simulator and `tools/balance_stats.py` measure each synergy (how often it is active, and the final floor of
  runs that had it).

## Non-goals

- No new art on the pet's body for synergies (the item `look` already covers that).
- No unlocks (hero or item) from the new achievements, for now.
- No player choice tied to synergies (interactive mode stays take/consume).
- No sounds (the owner vetoed audio).

## Anti-goals (failure even if it works)

- Runs get much longer. The balance targets in `tools/balance_stats.py` `TARGETS` stay **unchanged**:
  - 35–45% of runs pass the 1st boss;
  - p90 between floors 13 and 16;
  - max ≤ 50.
- A synergy lifts a stat past its existing cap. Caps (`MAX_CRIT`, `MAX_BLOCK`, ...) apply to the final total, as today.
- A flat bonus that stacks with no limit. Prefer chance-based effects ("25% per hit...") and small steps.
- Text clipped in the new tab (`tests/test_texts.py` must cover it), or visible text without a `PT` entry.

## Approaches considered

- **A. Data table in `dungeon.py`, picked by the owner.**
  - Sets and pairs add an `fx` in `stats()`, like the hero trait.
  - Reactions are one rule in `combat()`.
  - It is pure and testable, the simulator measures it as is, and `BALANCE_VERSION` sees the numbers.
- **B. Synergy as an invisible item added to `run["items"]`.** Rejected: it pollutes the item list, the
  "collector" achievement, the records and the pet look.
- **C. Event hooks (`on_hit`, `on_kill`) with free code per synergy.** Rejected: each synergy becomes code and the
  balance hash cannot see the rules.

## Design

### Data

`dungeon.SYNERGIES: dict[key, dict]`. Each entry has:

- `name`: English. A PT translation goes in `i18n.PT`; names are original in both languages.
- `kind`: `"set" | "reaction" | "pair"`.
- `req`:
  - set: `{"family": <family name>, "n": 2 | 4}`. Each step of a family is its own entry, e.g. `bulwark2` and
    `bulwark4`.
  - reaction: `{"status": ["burn", "freeze"]}`.
  - pair: `{"items": [key_a, key_b]}`.
- `fx`:
  - sets and pairs: summed in `stats()` with no rarity scaling, like `run["trait"]`.
  - reactions: the effect parameters, e.g. `{"dmg_atk": 1.0}`.
- `secret: bool`. Exactly 3 entries are `True`.
- `hint`: English. Shown on the locked card. Not used for secret entries.

`item_family()` and `FAMILIES` move from `tokenlike.py` to `dungeon.py`, because sets need them in the rules.
The GUI imports them from there.

### Sets (my proposal; numbers are tuned with the simulator)

There are 9 families × 2 steps = 18 entries. One example per family:

| Family | 2 items | 4 items |
|---|---|---|
| Elemental | +3% chance for each element the pet already has | statuses last +1 turn |
| Defense | +1 `block` | +0.1 `thorns` |
| Regeneration | +1 `heal_floor` | +1 `heal_room` |
| Blood | `attack_cost` −1 | +1 `fury` |
| Strikes | +3% `crit` | +5% `double` |
| Area | +1 ATK when hitting 3 or more | helpers also hit with area |
| Helpers | +1 `helper` | helper inflicts the pet's statuses |
| Growth | `grow` counts 1 kill less | +1 ATK per boss killed this run |
| Luck & gold | +0.1 `luck` | +10% chance for a chest to give 2 items |

Effects that are not plain `fx` fields mean new `fx` fields. Each new field gets an icon in `art.STAT_ART`, a line in
`tokenlike.STAT_LINES` and an `fx_text`, as the rules for any new field require. The builder may swap an effect for a
simpler one with the same intent if the field costs too much. They write down any swap.

### Reactions (6, every pair of the 4 statuses)

A reaction triggers when the pet applies a status to an enemy that already has the other status. Only the pet
applies statuses to enemies; bosses only apply them to the pet, and reactions never happen on the pet.

| Pair | Name (proposal) | Effect |
|---|---|---|
| burn + freeze | Shatter | extra damage = pet ATK; removes the freeze |
| burn + poison | Toxic Fumes | 1 poison stack spreads to every other living enemy |
| burn + shock | Overload | an extra burn tick right away |
| shock + freeze | Conductor | shock jumps to another living enemy |
| shock + poison | Jolt Venom | +1 poison stack (respects `POISON_MAX_STACKS`) |
| poison + freeze | Frostbite | freeze lasts +1 turn |

A reaction is a combat rule, so it changes balance on its own. `RULES_REV` goes up by 1, and the simulator plus
`/balance` re-tune if needed.

The combat step list gets a `reaction` field, so the GUI can show it and `_count` can record it.

### Named pairs (8, of which 3 are secret)

- The builder picks 8 pairs of existing items. Each pair is from **two different families**, has a thematic link
  (name or look) and a small effect that keeps to the anti-goals.
- The 3 secret synergies are 3 of these pairs.
- The owner reviews the names before merging.

### Activation and discovery

- `active_synergies(run) -> list[key]` returns the sets and pairs whose condition holds right now. It is pure.
  Items never leave `run["items"]`, so once a set is on, it stays on for the run.
- `stats()` adds the `fx` of the active entries. They go after items and trait, and before the caps.
- `run["synergies"]` is a list of keys turned on this run, sets, pairs and reactions alike. It is saved in the state
  and goes into `run_record`, as the new `"synergies"` field.
- `meta["synergies"][key] = {"runs": n, "first_run": run_id}`. It is updated when a key enters `run["synergies"]`
  for the first time in the run.
  - For sets and pairs, that happens right after an item is taken.
  - For reactions, it happens at the end of the fight.
  - The event gets `ev["synergies"] = [{"key", "new": bool}]`.
- Old saves get `run["synergies"] = []` and `meta["synergies"] = {}` with `setdefault`. No migration is needed.

### GUI

- Items window (`show_items`): the "Items | Synergies" chips sit at the top. The existing All/Unlocked/Locked filter
  applies to the Items view.
- Synergy cards are built with `card_box`, `icon`, `shorten`/`tooltip` and `scrollbar`, as the house rules require.
  - The card shows the icons of the 2 required items, the family icon (sets) or the 2 status icons (reactions).
  - It also shows the name, the effect text (in the style of `fx_text`), "Active in N runs" and "Discovered in run #X".
  - Locked: silhouette and the hint. Secret: "???" with no icons.
- Event log: one line per newly active synergy, gold for a new discovery.
- Status window: one line listing the active synergies of the run (names, with "…" plus a tooltip if they do not fit).
- Profile: the heroes card already shows "N/20"; a "synergies N/total" counter fits in the same place.

### Measuring

- `tools/simulate.py` prints the share of runs with each synergy active.
- `tools/balance_stats.py` adds a "Synergies" section: sim/real runs with it, and the median final floor with and
  without it.

### Tests

- `test_items.py`:
  - set steps turn on at exactly 2 and 4;
  - caps still hold with every synergy on;
  - exactly 3 entries are secret;
  - every entry has a name, an effect text and a hint (if it is not secret);
  - every pair is made of existing items from 2 families.
- `test_combat.py`: each reaction triggers with a seeded RNG and does what its row says. A reaction never happens on
  the pet.
- `test_records.py`: `run_record` has `synergies`.
- `test_i18n.py` and `test_texts.py`: the new tab, worst-case data, in pt and en.
- `test_gui.py`: the tab opens and switches; the event line shows up.

## Rules settled after the builder check (my calls, owner can override)

- **Set counting:** a set counts items by `item_family(key)`, the same single family the item card shows.
  An item counts for one family only. "Basic" items have no set.
- **Effect swaps:** a row may be swapped for a simpler effect with the same intent whenever it needs new combat
  state, a new counter or a change to chest handling. Every family keeps both steps (2 and 4).
- **No reaction chains:**
  - A status put on by a reaction (Toxic Fumes, Conductor, Jolt Venom) never triggers another reaction.
  - At most one reaction per applied status. If the enemy already has two other statuses, the first in
    `STATUS_NAME` order wins.
- **Same status is not a reaction:** re-applying a status the enemy already has (a poison stack, a burn refresh)
  never triggers one. A reaction that ends a status (Shatter) just sets it to 0.
- **Reactions count like any other synergy:** for `synergies3run`, `synergy5`, "Active in N runs" and discovery.
  - The step carries `reaction`, so the GUI shows it during the fight animation.
  - The log line and the meta update come when the fight ends.
- **Secret:** only 3 of the named pairs. Sets and reactions are never secret.
- **Balance version:** the `SYNERGIES` numbers enter the `BALANCE_VERSION` hash like `ITEMS`, so tweaking a synergy
  restarts the real history. That is the project's rule for every balance number.

## Left to the builder

- Exact numbers for every effect, set by the simulator and the targets. Always remeasure after the change.
- The 8 pairs and their names. The owner approves the names.
- Icon art for the new `fx` fields and the 3 achievements.
- The order of work: data and rules first (measurable on their own), then the GUI.
