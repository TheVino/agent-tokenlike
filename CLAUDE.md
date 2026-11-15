# Agent Tokenlike: Token Dungeon

Pixel-art pet that sits on the Windows screen (transparent overlay, always on top) and descends a roguelike
dungeon using the tokens spent in Claude Code as energy. Formerly TokenPet. Personal, unofficial project
(no ties to Anthropic).

**Language rule:** code, comments, identifiers, file names, commits and docs are always in **English**. Only the
conversation with the owner is in Portuguese (pt-BR). The game UI ships in pt-BR (default) and English.

## Files

- `tokenlike.py`: the app (tkinter). Token reading (`TokenReader`), state/saving, characters (built-in Slime +
  PNG loader) and the GUI (`PetApp`). `tkinter` is imported only in `run_gui()`, so the rest of the module is
  testable without a screen.
  Right click opens a custom pixel-art menu (`on_menu`: borderless `Toplevel` from `pixel_box`, golden frame
  with cut corners, icons from `art.py`, Size/Mode chips, checkboxes from `art.MENU_ART`), not `tk.Menu`.
  "Heroes…" opens the `show_heroes` grid, with the "Heroes" section (ours: `own_hero`, module in `heroes/`) and
  "Community" (imported: folder in `characters/` without a module, Petdex/Codex) (locked = silhouette + padlock +
  achievement; `hero_cards[key]` is None).
  "Show only when in use" (`state["only_when_used"]`, `adjust_visibility` in poll): `withdraw` after `HIDE_S`
  (5 min) without tokens (counted from `max(last_fed, opened_at)`; never mid-room or with an open choice),
  `deiconify` on the 1st token; while hidden the game goes on.
  "Start with Windows" (`startup_shortcut`): `.cmd` with pythonw in the Startup folder, menu only.
  Tray icon (`tray.py`, ctypes, Windows only; `start_tray` in `run_gui`, not in tests): a thread with a hidden
  window and `Shell_NotifyIconW`, icon = the Slime in `~/.tokenlike/icon.ico`; left click = `show`, right click
  = menu Show the pet / Quit. Clicks come through `events` (`listen_tray`, 150 ms after), since Tk is not thread-safe.
  Every `window()` is draggable by its title bar (`make_draggable`, `fleur` cursor); the position goes to
  `state["windows"][attr]` and `beside` reuses it while it is still on the virtual screen (`screen()`: all
  monitors, negative x allowed; otherwise beside the pet).
  Status, Achievements and Graveyard are pixel windows too (`window(attr, title)` + `beside`; attributes in
  `WINDOW_ATTRS`): `show_stats` (thumbnail, HP bar, one line per field of `STAT_LINES`/`stat_lines` with an icon
  from `art.STAT_ART` and cap, items with rarity glow and name on hover, consumed ones faded),
  `show_achievements` (cards, icon from `art.ACH_ART`, silhouette if missing, mini icons of what it unlocks) and
  `show_graveyard` (tombstones on a scrolling `Canvas`). "Items" opens `show_items`: cards on a `Canvas`
  (`item_card`), every possible rarity with `fx_text` and `consume` in the `RAR_COLOR` color, family from
  `item_family`/`FAMILIES`, filter All/Unlocked/Locked; locked (`item_unlocked`, same rule as the roll; demo
  unlocks everything) = silhouette + padlock + achievement, no values.
  "Profile" (1st menu row) opens `show_profile`: hero/run/HP, tamer level (`level`: floor(sqrt(lifetime energy
  `xp_total` / 1M)), `LEVEL_XP`), medals from `art.ACH_ART` in fixed cells (`icon(..., side=)`, name on hover),
  6 cards (today and lifetime energy, `streak_days`, runs, best, heroes N/20 + bosses), last 7 days bars
  (`usage_per_day`, XP from `usage_hist`, today in gold), limits via `limit_view` and a footer with
  `last_use`/`fmt_ago` and shortcuts. Pure functions tested in `test_limits.py`; all its texts live in `show_profile`.
  **Rounded corners:** everything uses `rounded_rect(cv, x0, y0, x1, y1, r, fill, outline, lw, tag, extra)`
  (pixel steps from `steps(r)`, straight rectangles only: no antialias against the key color). `pixel_box` draws
  the frame on a background Canvas (`WINDOW_R`); cards are `card_box()` (Canvas, `CARD_BG` inside, children
  `CARD_PAD` from the border, `backdrop(color)` on hover); buttons/filters are `chip()`; bars are `progress_bar()`
  (`.set(frac)`). Text that may not fit: `shorten` ("…") + `tooltip` (bubble on hover).
  Rule: **every new box uses these helpers and passes `tests/test_texts.py`** (`tests/_texts.py: check(window)`).
  Every scrolling window uses `scrollbar()` (pixel bar: drag, click the track, wheel, arrows). Icons via `icon()`
  (cache `self.icons`); `map_img`/`png_bytes` build a PNG and load it in one call (one `put` per pixel was slow).
- `i18n.py`: interface language (pt-BR default or English, `state["lang"]`, PT/EN chips in the menu).
  `t(text_en, **fmt)`: the English text is the key of the `PT` dictionary; without `fmt`, an already built text
  (event lines) is translated by template (`"Paid {n} gold"`). In `tokenlike.py` it is `_t`. Game data and
  records are in English; translation only happens at display time. `legacy_en` turns Portuguese texts saved by
  old versions into English. Switching language redraws the HUD and reopens the open windows (`change_lang`,
  `REOPEN`). **Every new visible text goes through `t()`/`_t()` and gets a `PT` entry** (`tests/test_i18n.py`
  fails otherwise; names are original in both languages, e.g. Empty Knight = Cavaleiro Oco).
- `legacy.py`: one-time conversion of saves from the Portuguese-key versions (`DATA_VERSION` 2). `migrate_state`
  maps keys and values with `KEYS` (+ `i18n.legacy_en` for saved display texts); `migrate_all` (in `run_gui`)
  rewrites `state.json` and `runs.jsonl` once, keeping `<name>.pt.bak`. `load_state` also migrates in memory.
- `dungeon.py`: game rules, pure and without GUI: energy, rooms, combat, items, achievements, death.
  `enter_room()` resolves a room and returns an event dict that the GUI only animates (`PetApp.play_room`).
- `art.py`: all the pixel art as text grids (`'.'` = transparent, letters = colors from `PAL`).
  Items, monsters, rooms, boss crown, `STAT_ART` (one per `stats()` field, plus `grow`) and `ACH_ART`
  (one per achievement). `BOSS_PAL` recolors monsters for bosses.
- `visual.py`: pure effects on pixel maps `{(x, y): "#rrggbb"}` (no tkinter): `thorns`, `drops`, `contour`,
  `tint`, `sticker`, `place_object` and `compose()`, which builds the pet with the stacked items' `look`
  (glow in the rarity color). `LOOK_BOX` limits the area: at each anchor only the most recent objects that fully
  fit stay (older ones at that anchor stop being drawn); the GUI only recomposes when the item list changes (`refresh_look`).
- `heroes/`: built-in 32 px heroes, one module per hero (`slime`, `ghost`, `doctor`, `witch`, `gravedigger`,
  `reaper`, `candle`, `mushroom`, `inquisitor`, `doll`, `knight`, `crow`, `alchemist`, `nun`, `scarecrow`,
  `golem`, `moth`, `frog`, `cat`, `octopus`) with: `PAL` (letter -> color), `FRAMES` (8 drawn states: idle, run_r,
  waving, jumping, failed, waiting, running, review; 4 to 6 32x32 frames each), `STAGES` (exactly 3: `title`,
  `floor`, `extra`; the 1st with `extra=None`; the Slime evolves on floors 1/4/10: Droplet, Slime, Slime King) and
  `ANCHOR` (per state and frame, integer `(x, y)` where the stage's `extra` is pasted).
  `heroes/common.py`: shared pieces (`z`, `?`, tear, `mirror`, `stamp`, `line`, `outline_cells`, `stroke`).
  Unlock by achievement: Ghost `boss1`, Doctor `poison1`, Witch `elements3`, Gravedigger `gold300`, Reaper
  `horde4`, Living Candle `burn1`, Mushroom `floor8full`, Inquisitor `floor15` (base HP 16), Doll `dodge10`,
  Empty Knight `block10` (base ATK 2, spd 8), Crow `bosses3` (meta, `meta["bosses"]`, spd 12), Alchemist
  `consume10`, Nun `die10` (meta, `meta["runs"]`), Scarecrow `helpers3` (helper 1), Golem `no_consume10` (DEF +1,
  HP +3, spd 8), Moth `legendaries3`, Frog `poison3`, Cat `floor13` (death or give-up on 13), Octopus
  `bosses3run`. That is 20 heroes of ours. `die()` calls `_check_achievements`. In `--demo` every hero is unlocked.
  Hero balance rule: each one passes the 1st boss in 30-50% (1,500 runs of that hero alone).
  `heroes/assemble.py`: `states()` builds the 9 states (`run_l` = `run_r` mirrored, never drawn) and `validate()`
  checks everything (4-6 frames, anchors, 32x32, 3 stages). `tools/make_sheets.py` writes
  `characters/<hero>/sheet1..3.png` (8x9 grid, 40 px cells, 4-6 frames per state, empty cells where frames are
  missing) and the preview `tools/out/preview_heroes.png`. The Ghost's old PNGs (`stage1.png`...) stay in the repo.
- **Hero trait** (`"trait"` in `character.json`, an object with `fx` fields; `"traço"` is still read): goes to
  `run["trait"]` in `new_run` and adds up in `stats()` like an item, but **without rarity scaling**. An invalid
  key or a non-numeric value invalidates the hero. `run["counters"]` keeps run counters (`dodges`, `blocks`,
  `poison_kills`, `burn_kills`, `horde4`; a tied horde of 4 does not count), for achievements and future traits.
- `characters/<folder>/character.json` + PNGs: extra heroes. The format is in `README.md`.
- `sheet.py`: spritesheet cutting (9 rows, `STATES`: idle, run_r, run_l, waving, jumping, failed, waiting,
  running, review). Hero = `characters/<folder>/spritesheet.png` (+ optional `character.json`) or a Petdex pet
  (`~/.petdex/pets/<slug>/`, `~/.codex/pets/<slug>/`, PNG only, `community=True`, "Community" menu; read only,
  never copied). In the GUI, `current_state` picks: pending choice `review` > fight `running` > death `failed`
  (before the tombstone) > rest/sleep `waiting` > `idle`; `waving` ~1 s after petting, `jumping` on evolution
  and after beating a boss. The PNG is decoded by `sheet.read_png` (zlib + struct, 8 bits; opaque = alpha > 128),
  not by Tk. Discovery (`all_characters`) only reads the header; the cut (`complete_stage`/`read_sheet`, cache by
  path+mtime, keeps only the reduced maps) runs in a thread when the hero becomes active, and an `after` swaps
  the look ("preparing hero…"). `refresh_look` composes only idle and the on-screen state right away; the other
  `states_fx` come on first read (cache `fx_cache` per state + items + status). Every state uses the same k and
  the pivot at the base of the trimmed box. The built-in Slime also has `states` (grid) and still blinks in idle;
  loose PNG heroes have no states. A `characters/slime` folder no longer replaces the built-in Slime (repeated keys keep the first).
- `tests/`: `test_limits.py` (statusline writes only the limits; reading, stale data, colors, time zone; profile
  functions), `test_migration.py` (copy from `~/.tokenpet` to `~/.tokenlike`; Portuguese-key save conversion),
  `test_reader.py` (log reading, dedup, art), `test_items.py` (rarity, stacking, take/consume, shield, caps,
  pending offer, 3-slot save migration), `test_records.py` (`run_record`, `runs.jsonl`), `test_balance_stats.py`
  (metrics and page), `test_combat.py`, `test_sheet.py` (cutting and PNG decoder; `tests/_png.py` writes real
  PNGs), `test_visual.py` (effects of `visual.py` and pet composition), `test_texts.py` (real Tk, worst-case data
  in every window and the HUD, in pt and en; the reusable check is `tests/_texts.py: check(window)`, cards on a
  Canvas tagged `card:<id>` via `extra=`), `test_i18n.py` (every `t()` key and every game data text with a PT
  translation, `fx_text` and event lines in EN, same `BALANCE_VERSION`) and `test_gui.py` (fake tkinter that runs
  the `after` callbacks, plays hundreds of rooms, dies, respawns, switches hero, tests interactive mode, language
  switch and the tray; uses `random.Random(SEED)` to be deterministic).
- `tools/simulate.py`: simulates 2,000 runs and shows the floor distribution, the rate of passing the 1st boss and the top killers.
  `tools/balance_stats.py`: writes `tools/out/balance_stats.html` and `.json` (gitignored) with simulated x real,
  items, pairs, deaths and heroes; `TARGETS` (balance targets) lives there.
  `tools/preview_art.py`: writes a PNG with every drawing (needs Pillow, development only).
  `tools/record_readme.py`: writes `docs/screenshot.png` and `docs/demo.gif` with the real app (temporary HOME,
  fake data, dark backdrop behind the pet; aborts without saving if another window shows up in the area). Do not touch the PC during the ~30 s.
- `README.md` (English, for GitHub). MIT license.
- `statusline.py`: optional Claude Code statusline (the user turns it on). Reads the JSON from stdin and writes
  only the official session (5h) and week limits to `~/.tokenlike/limits.json`. The pet reads them with
  `read_limits` on every poll and draws the Session/Week bars in the panel (green ≤50%, yellow ≤80%, red above).
  A new official reading calibrates a factor per window (`calibrate`, `state["calib"]`); without a recent reading
  (<10 min) it shows an estimated `~N%` (`limit_view`); without a factor, it shows the window's tokens and the
  bar (neutral `PEAK_COLOR`) is the fraction of **your peak** (`peak`, `state["peak"]`, kept beyond the 8 days),
  not of the real limit; the 5h session is rebuilt from the history (`sessions`: starts at the 1st use after the
  previous one ended). The statusline only runs in the terminal Claude Code. The energy bar slides to its value
  (`bar_frac` in the tick) and has a running shimmer (`draw_energy`). The bars always show.
- `.claude/skills/balance/`: `/balance` skill (reads the stats and proposes number changes, only edits with the owner's approval).
- `start.bat` (pythonw, no console), `demo.bat` (`--demo`: fake tokens, separate state).

## Commands

```
python tests/test_reader.py
python tests/test_items.py
python tests/test_visual.py
python tests/test_gui.py
python tests/test_migration.py
python tests/test_limits.py
python tests/test_records.py
python tests/test_balance_stats.py
python tests/test_combat.py
python tests/test_sheet.py
python tests/test_i18n.py
python tests/test_texts.py     # real Tk (skips without a screen): texts not clipped/overlapping, in pt and en
python tools/balance_stats.py  # stats page (sim x real); --no-open does not open the browser
python tools/simulate.py       # after touching balance/items/rooms
python tools/preview_art.py    # after touching art.py
python tokenlike.py --demo     # see it on the real screen
```

Run the tests after any change. When touching `dungeon.py`, also run the simulator.
`test_gui.py` fails if "error" shows up in `~/.tokenlike/tokenlike.log` (in a temporary HOME).

## Project rules (do not break)

1. **Privacy:** from Claude Code's `.jsonl` files (`~/.claude/projects/**`, or `CLAUDE_CONFIG_DIR`) only
   `message.usage` and the `timestamp` of each response are used (history in 5-min buckets, 8 days, in
   `state["usage_hist"]`). Never store, show or log prompt or response content. No network, no telemetry, no
   hooks, no changes to Claude Code's settings. Optional, manual exception: `statusline.py` is a statusline the
   **user** turns on in their own `settings.json`; it writes only `rate_limits` (percentage and reset of 5h/week)
   to `~/.tokenlike/limits.json`. The app only reads that file and never installs or edits the statusline.
2. **Standard library only** in the app (tkinter, json, ctypes etc.). Pillow is only allowed in `tools/`.
3. **Windows first:** transparency uses `-transparentcolor` with the key color `#ff00fe`. Text always on a solid
   rectangle (`PANEL_BG`); right on the key color, antialiasing leaves a pink fringe. Elsewhere the app falls back
   to a dark background.
4. **100% original art.** No characters, sprites or names from existing games (e.g. The Binding of Isaac).
   The mood is dark and cute roguelike, with its own identity.
5. **Not using it never punishes:** inactivity never kills the pet or removes progress, it only rests (heals)
   and sleeps. The danger stays inside the dungeon.
6. Dedup usage by `message.id:requestId`, because Claude Code writes the same response on several lines.
   Read only complete lines (ending in `\n`) and keep the offset of each file.

## How the pieces fit

- Token XP = input + output + cache creation + 10% of cache reads (`CACHE_READ_WEIGHT`). It becomes `run["energy"]`.
- `ROOM_COST` = 100k per room, at most 20 rooms stored. 5 rooms per floor, then the stairs; the boss comes in
  room 5 of floors that are multiples of 5.
- Evolution within the run by **floor** (the hero's `stage_floors`), with +4 max HP and +1 ATK.
- **Items stack:** `run["items"]` is a list of `{"key", "rar"}` with no limit (each item at most once per run).
  Rarity `common|rare|epic|legendary` multiplies the positive values of `fx` and of `consume` by `RAR_MULT`
  (negatives, `trap`, `area` and `attack_cost` do not scale; `grow` scales down: `ceil(N / RAR_MULT)`, floor 3);
  `_rarity_weights(floor)` rolls the rarity (the items' `luck` multiplies the rare, epic and legendary weights) and
  each item lists its possible `rarities`. 100 items: ~74 in 3 rarities, ~16 in 2 and 10 legendary only.
  Colors (`RAR_COLOR`): rare blue, epic purple, legendary gold.
- **Take or consume:** every offer (chest, mimic, boss, shop) can be taken (joins the list) or consumed
  (`consume`: `heal` heals right away, `shield` becomes a shield that absorbs damage before HP in `apply_damage`).
  `auto` mode (`state["mode"]`): `auto_choice` consumes a heal if HP < 40%, otherwise takes. `interactive` mode:
  the offer goes to `run["pending"]` (saved in the state) and the GUI opens the choice window; without an answer
  within `CHOICE_WINDOW_S` (30 s), the automatic rule decides when the next room is ready. Never enters a room
  with an open pending offer. Choices are `"take"` / `"consume"`.
- **Caps:** summed `energy` ≤ +100% (`MAX_ENERGY_BONUS`), trap multiplier in `TRAP_LIMITS` (0.25 to 3),
  dodge ≤ `MAX_DODGE`, crit ≤ `MAX_CRIT` (0.35), each element's chance ≤ `MAX_ELEM_CHANCE` (0.3),
  `block` ≤ `MAX_BLOCK` (2), `thorns` ≤ `MAX_THORNS` (0.5), `double` ≤ `MAX_DOUBLE` (0.25),
  `luck` ≤ `MAX_LUCK` (1.0), `discount` ≤ `MAX_DISCOUNT` (0.6). Caps apply to the total summed in `stats()`.
  Old 3-slot saves become common items in `migrate_run`.
- **Family `fx` fields** (all add up in `stats()`): `block` (hits cancelled at the start of each fight),
  `thorns` (fraction of the damage taken sent back), `heal_room`/`heal_floor` (HP when entering a room/going down
  the stairs), `attack_cost` (HP lost per pet attack, never kills), `fury` (+ATK for every 10% of missing HP),
  `double` (chance of a second hit), `helper` (damage of a helper that attacks once per round the lowest-HP enemy
  and cannot be targeted), `grow` (+1 ATK every N kills made after taking the item: `kills0` kept when taken),
  `luck` (rarity) and `discount` (shop, `shop_price`). `fx_text` shows them all; every item needs a text.
- **Round-based combat** (`dungeon.combat`, enemies are dicts from `make_foe`/`make_mimic`): each round,
  1) status damage (burn and poison, ignore the shield); 2) everyone acts by `spd`, highest first (tie: pet
  first, then list order). Pet: `PET_SPD` 10 (or the hero's `stats.spd`), `PET_CRIT`, `PET_CRITDMG`.
  Monster: `spd` = `MON_SPD` (base + per floor) x the monster's `spd_mult` (x `BOSS_SPD_BONUS` for bosses), fixed
  crit (`MON_CRIT`/`BOSS_CRIT`, damage `FOE_CRITDMG`). Whoever has **twice the target's speed** gains `DOUBLE_CRIT`
  chance and `critdmg` x2 (both ways; the slow skeleton takes a lot of crits).
- **Status:** bosses have an element (`BOSS_ELEMENT`: `fire|lightning|poison|ice`) and apply the status with
  `BOSS_STATUS_CHANCE` per hit; items with `burn|shock|poison|freeze` apply it on enemies (`ELEMENTS`,
  `STATUS_NAME`). Burn (`BURN`, `BURN_TURNS`) and poison (stacks of 1,2,3,4 damage, up to `POISON_MAX_STACKS`)
  take HP; shock (`SHOCK_CHANCE`) and freeze (`FREEZE_CHANCE`) skip turns. Death by Burn/Poison becomes `kind`
  "status" in the graveyard.
- **Hordes** (`"horde"` in `ROOM_WEIGHTS`, from `HORDE_MIN_FLOOR`): 2 to `horde_max(floor)` enemies with HP/ATK
  x `HORDE_MULT[n]`, gold x `HORDE_GOLD_MULT`, never a boss. Without `area` the pet hits the lowest-HP one; with `area`, all.
- **Tie:** the fight stops at `MAX_ROUNDS` (60); the pet clears the room, but without gold, kill, item or boss bonus.
- Meta-progression in `state["meta"]`: `achievements`, `graveyard` (last 50), `best`, `runs`, `next_char`, `bosses`.
  Items with `req` and heroes with `unlock` only come in after the achievement.
- State in `~/.tokenlike/state.json` (or `state-demo.json`), `data_version` 2. On the 1st run, if `~/.tokenlike`
  does not exist and `~/.tokenpet` (old name) does, `migrate_old_data()` copies the `state*.json` without deleting
  the old one. Atomic writes (tmp + replace). A lock file prevents two open instances.
- Run records: every finished run becomes a line in `~/.tokenlike/runs.jsonl` (demo: `runs-demo.jsonl`) via
  `dungeon.run_record`, with `dungeon.BALANCE_VERSION` (8-char hash of the balance numbers only).
  A number changed, the version changed and the real history restarts (`--all-versions` shows everything).
  The hash does not see formulas or numbers written in the code: when changing a combat rule/formula, bump
  `dungeon.RULES_REV` (now 8). Changing only a constant already changes the version by itself.
- Balance targets: in `TARGETS` of `tools/balance_stats.py` (pass the 1st boss 35-45%, p90 13-16, max <= 50).
  They are judged on the **calibration** (slime only, same as `simulate.py`, without and with achievements); the
  "sim" with all heroes mixed is informative only. Green/red item uses `vs_mean` (vs expected minus the items'
  mean). Run `python tools/balance_stats.py`, do not memorize numbers here.
- Last simulator result (`tools/simulate.py`, reference only, may be stale): 40-43% pass the 1st boss, p90 =
  floor 15, p99 = 20, max = 35-45. Deaths (without achievements): boss ~62%, monster ~19%, horde ~9%,
  status ~5%, mimic ~3%, trap ~1%. Items stack, the hero gets strong fast (`CHEST_ITEM_CHANCE` = 1.0,
  low `RAR_MULT`) and the bosses are what hold runs back (`BOSS_HP` = (55, 18), `BOSS_ATK` = (7.5, 3.1), i.e.
  `value + per_floor * (floor - BOSS_EVERY)`, minimum 1); the 2nd boss (floor 10) is the wall. `MON_ATK` = (1.5, 1.2).
  **Boss ramp:** after floor `BOSS_RAMP_FROM` (10), boss HP and ATK are also multiplied by
  `1 + BOSS_RAMP * (floor - 10)` (`BOSS_RAMP` = 0.07). It does not touch the 1st and 2nd bosses; it cuts the tail
  of runs with many items (without it, with 100 items, the max went past 200). To lengthen or shorten long runs, change it.
  Combat: `MON_SPD` = (6, 0.1), `BOSS_SPD_BONUS` = 1.1, `PET_CRIT` = 0.10, `BOSS_STATUS_CHANCE` = 0.15.
  Hordes: `HORDE_MULT` = {2: 0.75, 3: 0.6, 4: 0.5} is the owner's decision (do not change); what gets tuned is the
  "horde" weight (now 9 in `ROOM_WEIGHTS`), `horde_max` and `HORDE_GOLD_MULT`. Pet crit: the base only keeps
  `crit`/`critdmg` if the hero defines them; otherwise `stats()` uses `PET_CRIT`/`PET_CRITDMG`.
  Lever order: rarity, `consume`, chest/mimic/shop (`SHOP_PRICE`); in combat: status and crit, speeds, horde
  (weight, `horde_max`, `HORDE_GOLD_MULT`); only then `MON_*`/`BOSS_*`; for the tail (max), `BOSS_RAMP`. Hordes
  should stay between 5% and 35% of deaths and status above 0 (without being the majority).

## Adding things

- **New item:** drawing in `art.ITEM_ART[key]` (if the `look` uses art) and an entry in `dungeon.ITEMS` with
  `name` (English; add the PT translation to `i18n.PT`), `rarities`, `fx`, `consume` (`{"heal": n}` or
  `{"shield": n}`), `look` and optional `req`. `look` is one of the effects of `visual.py`:
  `{"type": "obj", "anchor": "right|left|top|front|float", "art": ...}`, `thorns`/`drops`/`outline` (`color`),
  `tint` (`color`, `amount`), `sticker` (`art`, `at`) or one of the elementals' **animated** ones: `flames`,
  `sparks`, `poison_drops`, `frost` (optional `color`; 3 phases computed once in `refresh_look` and swapped in the
  tick by the `FX_MS` clock). Helpers always use a floating `obj`.
  Families (each with at least 4 items, checked in `tests/test_items.py`): elementals (5 per element, animated
  look), defense (`block`, `thorns`, `dodge`), regeneration (`heal_room`, `heal_floor`, `lifesteal`), blood
  (`attack_cost` always with `atk` or `fury`), blows (`crit`, `critdmg`, `double`), area (`area`), helpers
  (`helper`), growth (`grow`) and luck/gold (`luck`, `gold`, `discount`). Every item needs an icon and a non-empty
  `fx_text`; names never repeat. Run `tools/simulate.py` and `tools/balance_stats.py` afterwards.
- **New monster:** drawing in `art.FOE_ART`, entry in `dungeon.MONSTERS`
  `(sprite, name, mult_hp, mult_atk, min_floor, spd_mult)` (+ boss name in `BOSS_NAMES` and element in
  `BOSS_ELEMENT`: `fire|lightning|poison|ice`; without an element the boss breaks `make_foe`).
- **Combat `fx` fields:** `spd`, `crit`, `critdmg`, `area` (bool, does not scale with rarity) and the per-hit
  chance of each element: `burn`, `shock`, `poison`, `freeze` (0..1, cap `MAX_ELEM_CHANCE`; `crit` cap `MAX_CRIT`),
  plus the family ones described in "How the pieces fit".
- **New room type:** `ROOM_WEIGHTS` + a branch in `enter_room` + the animation in `PetApp.play_room`.
- **New achievement:** `dungeon.ACHIEVEMENTS` + rule in `_check_achievements` + icon in `art.ACH_ART` (test).
- **New `fx`/`stats()` field:** icon in `art.STAT_ART` and a line in `tokenlike.STAT_LINES` (test).
- **New hero:** preferably a folder in `characters/` with PNGs and `character.json` (`stats` with optional
  `spd`, `unlock`, `stages[].floor`), or a module in `heroes/` validated by `heroes/assemble.py`.

## Before release

- Visual polish of the stats page and item/hero icons on it.
- Test interactive mode and the session/week bars on the real screen.

## Open ideas

- Unlockable heroes with their own mechanic (e.g. mimic chest).
- More rooms (rare event, secret room), more bosses with their own sprite, item synergies.
- More player choices (today only take/consume in interactive mode), sounds, run statistics.
