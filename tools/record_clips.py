"""Records short clips of the real app (one per feature) for the README videos in video/.

Same idea as record_readme.py: temporary HOME, fake data, dark backdrop behind the transparent pet, aborts if
anything else shows up in the captured area. Each clip is a 1280x1080 area scaled 2x (nearest) to 2560x2160 so
the 4:2:0 chroma stays aligned with the pixel art. Needs Pillow and ffmpeg (development only).
Usage: python tools/record_clips.py [scene ...]     (no args = every scene). Do not touch the PC while it runs.
"""
import os, random, shutil, subprocess, sys, tempfile, time, types
from pathlib import Path

home = tempfile.mkdtemp()
os.environ["HOME"] = home
os.environ["USERPROFILE"] = home
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
import tkinter, tkinter.font  # noqa: E401,F401
from PIL import ImageGrab
import dungeon as M
import tokenlike as tp

BACKDROP = "#16131f"
OUT = REPO_ROOT / "video" / "features" / "assets" / "clips"   # copied to video/purpose too
FPS = 15
X0, Y0, W, H = 400, 140, 1280, 1080          # captured area on screen (the video crops/zooms it)
PET = (X0 + W - 520, Y0 + H - 420)           # pet on the right, windows open on the left
WIN = [X0 + 40, Y0 + 30]


class Forced(random.Random):
    """The room roll returns `force` when it is one of the options (lets each clip show one room kind)."""
    force = None

    def choices(self, population, weights=None, **kw):
        if self.force in population:
            return [self.force]
        return super().choices(population, weights, **kw)


tp.tk = tkinter
tp.DATA_DIR = Path(home) / ".tokenlike"
tp.LOG_FILE = tp.DATA_DIR / "tokenlike.log"
app = tp.PetApp(types.SimpleNamespace(demo=True, import_history=False, reset=False))
app.reader.poll = lambda: (0.0, 0)
app.refresh_limits = lambda: None
app.demo = False                              # no "(demo mode)" tags
app.rng = Forced(11)
rng = random.Random(7)

m = app.meta
m["achievements"] = ["floor5", "boss1", "mimic", "rich", "poison1", "burn1", "dodge10", "floor10", "secret3",
                     "elements3", "gold300", "block10", "synergy5"]
m["runs"], m["best"], m["bosses"] = 23, {"floor": 14, "room": 2}, 4
m["journal"] = {k: {"run": 3 + i, "floor": 2 + i % 7} for i, k in enumerate(list(M.TALES)[:9])}
m["synergies"] = {k: {"runs": 2 + i % 4, "first_run": 4 + i} for i, k in enumerate(list(M.SYNERGIES)[:14])}
m["graveyard"] = [{"killer": n, "floor": f, "room": r, "kind": k, "run": i + 1, "char": "slime", "items": [],
                   "gold": 40 + 9 * i, "kills": 12 + 5 * i, "date": "2026-11-1" + str(i)}
                  for i, (n, f, r, k) in enumerate([("Bone Tyrant", 10, 5, "boss"), ("Mimic", 6, 3, "mimic"),
                                                    ("Poison", 8, 2, "status"), ("Horde", 12, 4, "horde"),
                                                    ("Skeleton", 4, 1, "monster"), ("Spike trap", 3, 2, "trap")])]
now = time.time()
for d in range(8):
    tp.add_usage(app.state, now - d * 86400, 2.5e6 * (8 - d))
app.state.update(tokens_total=60e6, xp_total=48e6, daily={tp.date.today().isoformat(): 4e6})
app.limits = {"session": (38, now + 2 * 3600), "week": (61, now + 3 * 86400), "updated": now}
app.state["windows"] = {a: list(WIN) for a in tp.WINDOW_ATTRS}

backdrop = tkinter.Tk()
backdrop.overrideredirect(True)
backdrop.configure(bg=BACKDROP)
backdrop.geometry(f"{W}x{H}+{X0}+{Y0}")
backdrop.attributes("-topmost", True)


def wait(s):
    end = time.time() + s
    while True:
        app.root.update(); backdrop.update()
        if time.time() >= end:
            return
        time.sleep(0.01)


def on_top(*wins):
    for w in (app.root,) + wins:
        if w is not None:
            w.attributes("-topmost", True); w.lift()


def new_run(floor=1, room=0, items=0, energy=0.0, mode="auto", hero="slime"):
    m["next_char"] = hero
    app.state["mode"] = mode
    app.new_run(announce=False)
    app.run["items"] = [{"key": k, "rar": rng.choice(M.RARITIES)} for k in rng.sample(list(M.ITEMS), items)]
    app.run.update(floor=floor, room=room, gold=88, kills=21, stage=M.stage_for_floor(floor, app.char.stage_floors),
                   energy=energy)
    app.run["hp"] = M.stats(app.run)["maxhp"]
    app.busy_until = 0
    M._check_achievements(app.run, m, {"lines": []})   # the sample meta already earns some: no bubbles mid-clip
    app.load_images(); app.refresh_look(); app.update_panel()
    app.root.geometry(f"+{PET[0]}+{PET[1]}")


def record(name, seconds, during=None):
    """Grabs the area at FPS and pipes it to ffmpeg. `during(t)` runs once per frame (t = seconds since start)."""
    OUT.mkdir(parents=True, exist_ok=True)
    color = tuple(int(BACKDROP[i:i + 2], 16) for i in (1, 3, 5))
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-vf", "scale=iw*2:ih*2:flags=neighbor",
                           "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                           str(OUT / f"{name}.mp4")], stdin=subprocess.PIPE)
    start = time.time()
    for i in range(int(seconds * FPS)):
        if during:
            during(time.time() - start)
        wait(max(0.0, start + (i + 1) / FPS - time.time()))
        img = ImageGrab.grab((X0, Y0, X0 + W, Y0 + H), all_screens=True).convert("RGB")
        for box in ((0, 0, W, 6), (0, H - 6, W, H), (0, 0, 6, H), (W - 6, 0, W, H)):
            if [c for _, c in (img.crop(box).getcolors(1 << 16) or [])] != [color]:
                ff.stdin.close(); ff.wait()
                img.save(OUT / f"{name}-fail.png"); print(box)
                sys.exit(f"{name}: the screen changed during the capture; run it again without touching the PC.")
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); ff.wait()
    copy = REPO_ROOT / "video" / "purpose" / "assets" / "clips"
    copy.mkdir(parents=True, exist_ok=True)
    shutil.copy(OUT / f"{name}.mp4", copy)
    print(name + ".mp4")


def open_win(method, attr, seconds, name, before=None):
    if before:
        before()
    getattr(app, method)()
    w = getattr(app, attr)
    w.unbind("<FocusOut>")
    w.geometry(f"+{WIN[0]}+{WIN[1]}")
    on_top(w); wait(1.0)
    w.geometry(f"+{WIN[0]}+{WIN[1]}"); wait(0.5)    # the window places itself again once drawn
    print(name, w.winfo_width(), w.winfo_height())
    record(name, seconds)
    app.close_win(w); wait(0.3)


def feeding(t, every=0.7, xp=60_000):
    if int(t / every) != int((t - 1 / FPS) / every):
        app.feed(xp, int(xp))


def scene_tokens():           # the purpose: tokens become energy, energy becomes rooms
    new_run(); app.rng.force = "monster"; wait(0.5)
    record("tokens", 9, feeding)


def scene_fight():
    new_run(floor=3, items=4, energy=3.2e5); app.rng.force = "horde"; wait(0.3)
    record("fight", 7)


def scene_boss():
    new_run(floor=5, room=4, items=5, energy=1.1e5); wait(0.3)
    record("boss", 8)


def scene_chest():            # an item lands and shows on the pet
    new_run(floor=2, items=5, energy=2.1e5); app.rng.force = "chest"; wait(0.3)
    record("chest", 6)


def scene_look():             # a pet carrying many items
    new_run(floor=7, items=16); wait(1.5)
    record("look", 4)


def choice_scene(kind, name, pick):
    new_run(floor=3, items=6, energy=1.1e5, mode="interactive"); app.rng.force = kind; wait(0.3)

    def during(t):
        if app.choice_win is not None:
            on_top(app.choice_win)
            if t > 4.5 and app.run["pending"]:
                p = app.run["pending"]
                app.choose(pick(p))
    record(name, 8, during)


def scene_idol():
    choice_scene("idol", "idol", lambda p: "accept")


def scene_campfire():
    choice_scene("campfire", "campfire", lambda p: p["boons"][0] if p.get("boons") else "take")


def scene_secret():
    new_run(floor=4, items=6, energy=1.1e5); app.rng.force = "secret"; wait(0.3)
    record("secret", 6)


def scene_windows():
    new_run(floor=6, items=10)
    wait(1.0)
    app.items_tab = "items"
    open_win("show_items", "items_win", 4, "items")
    app.items_tab = "synergies"
    open_win("show_items", "items_win", 4, "synergies")
    open_win("show_heroes", "heroes_win", 4, "heroes")
    open_win("show_journal", "journal_win", 4, "journal")
    open_win("show_achievements", "ach_win", 3, "achievements")
    open_win("show_graveyard", "grave_win", 3, "graveyard")
    open_win("show_stats", "stats_win", 3, "stats")
    open_win("show_profile", "profile_win", 4, "profile")


SCENES = {k[6:]: v for k, v in dict(globals()).items() if k.startswith("scene_")}
app.lang_var.set("en"); app.change_lang()
app.root.geometry(f"+{PET[0]}+{PET[1]}")
wait(0.3); on_top(); wait(9)                  # skips the welcome bubble
for s in sys.argv[1:] or list(SCENES):
    SCENES[s]()
app.root.destroy(); backdrop.destroy()
