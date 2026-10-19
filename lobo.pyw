"""
LOBO – a Dynamic-Island style productivity widget at the top of your screen.

  * Move cursor to top-center edge  -> island appears
  * Click the pill                   -> expands Tasks / Notes panel
  * Click outside                    -> collapses back to pill
  * Esc                              -> collapse
  * Right-click pill                 -> Quit

Data saved next to this script as LOBO_data.json.
"""
import json
import math
import os
import sys
import time
import tkinter as tk
import tkinter.font as tkfont
import random

# ── paths ──────────────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE  = os.path.join(SCRIPT_DIR, "LOBO_data.json")

# ── palette ────────────────────────────────────────────────────────────────────
BG        = "#0b0b10"
ROW       = "#171722"
BORDER    = "#2a2a3a"
FG        = "#f4f4fa"
DIM       = "#8b8ba6"
ACC       = "#ffd700"   # bright gold
ACC2      = "#ffb300"   # warm amber
BODY      = "#ffe27d"   # sunshine yellow
BODY_DONE = "#ffd700"   # gold when all done
BLUSH     = "#ffb347"   # warm orange blush
INK       = "#2a1a10"   # dark ink
TRANS     = "#010203"   # transparent key colour

PILL_W, PILL_H = 260, 44
OPEN_W, OPEN_H = 370, 480
TOP_GAP   = 6
HEADER_H  = 44
TRIGGER_HALF = 120


# ── helpers ────────────────────────────────────────────────────────────────────
def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    ca = [int(a[i:i+2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(ca[i] + (cb[i]-ca[i])*t) for i in range(3))


def rrect(c, x1, y1, x2, y2, r, **kw):
    r = max(0, min(r, (x2-x1)/2, (y2-y1)/2))
    pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r, x2,y2-r, x2,y2,
           x2-r,y2, x1+r,y2, x1,y2, x1,y2-r, x1,y1+r, x1,y1]
    return c.create_polygon(pts, smooth=True, **kw)


def star(c, cx, cy, r, **kw):
    k = r * 0.3
    pts = [cx,cy-r, cx+k,cy-k, cx+r,cy, cx+k,cy+k,
           cx,cy+r, cx-k,cy+k, cx-r,cy, cx-k,cy-k]
    return c.create_polygon(pts, **kw)


def heart(c, cx, cy, size, col, tags=""):
    pts = []
    for i in range(32):
        a = math.pi * 2 * i / 32
        x = size * (16 * math.sin(a)**3) / 16
        y = -size * (13*math.cos(a) - 5*math.cos(2*a) - 2*math.cos(3*a) - math.cos(4*a)) / 16
        pts.extend([cx+x, cy+y])
    if len(pts) >= 6:
        c.create_polygon(pts, fill=col, outline="", smooth=True, tags=tags)


def sparkle(c, cx, cy, r, col, t, tags=""):
    angle = t * 2
    pts = []
    for i in range(8):
        a = angle + math.pi * i / 4
        radius = r if i % 2 == 0 else r * 0.35
        pts.extend([cx + math.cos(a)*radius, cy + math.sin(a)*radius])
    c.create_polygon(pts, fill=col, outline="", tags=tags)


# ── scrollable list ────────────────────────────────────────────────────────────
class ScrollList(tk.Frame):
    def __init__(self, master, bg_col):
        super().__init__(master, bg=bg_col)
        self.cv    = tk.Canvas(self, bg=bg_col, highlightthickness=0, bd=0, yscrollincrement=24)
        self.inner = tk.Frame(self.cv, bg=bg_col)
        self.win   = self.cv.create_window((0,0), window=self.inner, anchor="nw")
        self.cv.pack(fill="both", expand=True)
        self.inner.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>",   lambda e: self.cv.itemconfigure(self.win, width=e.width))


# ── main app ───────────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LOBO")
        self.withdraw()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.sw = self.winfo_screenwidth()

        self._trans_key = self._setup_transparency()
        self.configure(bg=self._trans_key)
        self.cv = tk.Canvas(self, bg=self._trans_key, highlightthickness=0, bd=0, cursor="hand2")
        self.cv.place(x=0, y=0, relwidth=1, relheight=1)

        fam = "Segoe UI" if sys.platform.startswith("win") else "Helvetica"
        self.f_text  = tkfont.Font(family=fam, size=10)
        self.f_done  = tkfont.Font(family=fam, size=10, overstrike=True)
        self.f_bold  = tkfont.Font(family=fam, size=10, weight="bold")
        self.f_small = tkfont.Font(family=fam, size=9)
        self.f_head  = tkfont.Font(family=fam, size=11, weight="bold")
        self.f_num   = tkfont.Font(family=fam, size=15, weight="bold")
        self.f_x     = tkfont.Font(family=fam, size=13)
        self.f_brand = tkfont.Font(family=fam, size=9, weight="bold")

        # data
        self.tasks, self.notes = [], []
        self.load()
        self.tab = "tasks"

        # animation
        self.cw = self.ch = 6.0
        self.cw = 44.0
        self.vw = self.vh = 0.0
        self.tw, self.th = PILL_W, PILL_H
        self.moving      = False
        self.visible     = False
        self.state       = "hidden"
        self.bounce      = 0.0
        self.idle_since  = None
        self.hidden_at   = 0.0
        self.content_item = None

        # particles
        self.particles   = []
        self.tail_phase  = 0.0

        self._build_content()
        self._build_menu()

        self.cv.bind("<Button-1>", self.on_click)
        self.cv.bind("<Button-3>", self.on_right)
        self.cv.bind("<Button-2>", self.on_right)
        self.bind_all("<Escape>",     lambda e: self.close_to_pill())
        self.bind_all("<MouseWheel>", self.on_wheel)
        self.bind_all("<Button-4>",   self.on_wheel)
        self.bind_all("<Button-5>",   self.on_wheel)
        self.bind("<FocusOut>", self._on_focus_out)

        self.show()
        self.loop()

    # ── transparency ───────────────────────────────────────────────────────────
    def _setup_transparency(self):
        try:
            if sys.platform.startswith("win"):
                self.attributes("-transparentcolor", TRANS)
                return TRANS
            if sys.platform == "darwin":
                self.attributes("-transparent", True)
                return "systemTransparent"
        except tk.TclError:
            pass
        return BG

    # ── menu ───────────────────────────────────────────────────────────────────
    def _build_menu(self):
        self.menu = tk.Menu(self, tearoff=0, bg=ROW, fg=FG,
                            activebackground=ACC, activeforeground=BG,
                            bd=0, font=self.f_text)
        self.menu.add_command(label="Quit LOBO", command=self.destroy)

    # ── data ───────────────────────────────────────────────────────────────────
    def load(self):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                d = json.load(f)
            self.tasks = [t for t in d.get("tasks", []) if isinstance(t, dict) and "t" in t]
            for t in self.tasks:
                t["d"] = bool(t.get("d"))
            self.notes = [str(n) for n in d.get("notes", [])]
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"tasks": self.tasks, "notes": self.notes},
                          f, ensure_ascii=False, indent=2)
            os.replace(tmp, DATA_FILE)
        except OSError:
            pass

    def counts(self):
        left  = sum(1 for t in self.tasks if not t["d"])
        total = len(self.tasks)
        return left, total

    # ── main loop ──────────────────────────────────────────────────────────────
    def loop(self):
        self.poll()
        if self.visible:
            if self.moving:
                self.step()
            if self.bounce > 0:
                self.bounce = max(0.0, self.bounce - 0.028)
            self.tail_phase += 0.09
            self._update_particles()
            self.draw()
        fast = self.moving or self.bounce > 0 or bool(self.particles)
        self.after(16 if fast else 40, self.loop)

    def poll(self):
        px, py = self.winfo_pointerxy()
        now     = time.time()
        trigger = py <= 2 and abs(px - self.sw / 2) <= TRIGGER_HALF
        if self.state == "hidden":
            if trigger and now - self.hidden_at > 0.3:
                self.show()
            return
        left_edge = (self.sw - self.cw) / 2
        inside = (left_edge - 8 <= px <= left_edge + self.cw + 8) and py <= TOP_GAP + self.ch + 8
        if inside or trigger:
            self.idle_since = None
            return
        if self.idle_since is None:
            self.idle_since = now
            return
        if self.state == "pill" and now - self.idle_since > 1.0:
            self.hide()

    # ── focus-out collapse ────────────────────────────────────────────────────
    def _on_focus_out(self, _e):
        if self.state == "open":
            self.after(150, self._check_focus_loss)

    def _check_focus_loss(self):
        if self.state != "open":
            return
        try:
            if self.focus_get() is None:
                self.close_to_pill()
        except KeyError:
            self.close_to_pill()

    # ── spring animation ───────────────────────────────────────────────────────
    def apply_geometry(self):
        w, h = int(round(self.cw)), int(round(self.ch))
        self.geometry(f"{w}x{h}+{int((self.sw-w)/2)}+{TOP_GAP}")

    def step(self):
        K, D = 0.18, 0.68
        self.vw = (self.vw + (self.tw - self.cw) * K) * D
        self.vh = (self.vh + (self.th - self.ch) * K) * D
        self.cw = max(20.0, self.cw + self.vw)
        self.ch = max(4.0,  self.ch + self.vh)
        settled = (abs(self.tw-self.cw) < 0.8 and abs(self.th-self.ch) < 0.8
                   and abs(self.vw) < 0.5 and abs(self.vh) < 0.5)
        if settled:
            self.cw, self.ch = float(self.tw), float(self.th)
            self.vw = self.vh = 0.0
        self.apply_geometry()
        if self.state == "open" and self.content_item is None \
                and self.ch >= self.th * 0.92 and self.cw >= self.tw * 0.95:
            self.show_content()
        if settled:
            self.moving = False
            if self.state == "hidden":
                self.withdraw()
                self.visible = False
            elif self.state == "open":
                self.show_content()

    # ── particles ──────────────────────────────────────────────────────────────
    def _emit(self, kind, cx, cy, n, cols, extra=None):
        for _ in range(n):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(0.8, 2.5)
            p = {
                "x": cx + random.uniform(-5, 5),
                "y": cy + random.uniform(-5, 5),
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed,
                "life": 1.0, "maxlife": 1.0,
                "col": random.choice(cols),
                "kind": kind,
                "size": random.uniform(2.0, 4.5),
            }
            if extra:
                p.update(extra())
            self.particles.append(p)

    def _emit_sparkles(self, cx, cy, n=8):
        self._emit("sparkle", cx, cy, n, [ACC, ACC2, BODY_DONE, "#ffffff"],
                   extra=lambda: {"t": random.uniform(0, math.pi)})

    def _emit_hearts(self, cx, cy, n=6):
        for _ in range(n):
            angle = random.uniform(-math.pi, 0)
            speed = random.uniform(1.2, 3.0)
            self.particles.append({
                "x": cx + random.uniform(-10, 10), "y": cy,
                "vx": math.cos(angle)*speed*0.5,
                "vy": math.sin(angle)*speed - 0.5,
                "life": 1.0, "maxlife": 1.0,
                "col": random.choice([ACC2, BLUSH, BODY_DONE, ACC]),
                "kind": "heart", "size": random.uniform(2.5, 5.0),
            })

    def _emit_stars(self, cx, cy, n=5):
        self._emit("star", cx, cy, n, [BODY_DONE, ACC, "#ffffff"])

    def _update_particles(self):
        alive = []
        for p in self.particles:
            p["x"] += p["vx"];  p["y"] += p["vy"]
            p["vy"] += 0.08;    p["life"] -= 0.025
            if "t" in p:        p["t"] += 0.18
            if p["life"] > 0:   alive.append(p)
        self.particles = alive

    def _draw_particles(self, c):
        t_now = time.time()
        for p in self.particles:
            alpha = p["life"] / p["maxlife"]
            sz    = p["size"] * alpha
            if sz < 0.5:
                continue
            x, y, col = p["x"], p["y"], p["col"]
            k = p["kind"]
            if k == "heart":
                heart(c, x, y, sz, col, tags="hdr")
            elif k == "sparkle":
                sparkle(c, x, y, sz, col, p.get("t", t_now), tags="hdr")
            elif k == "star":
                star(c, x, y, sz, fill=col, outline="", tags="hdr")

    # ── state transitions ──────────────────────────────────────────────────────
    def show(self):
        if not self.visible:
            self.cw, self.ch = 44.0, 6.0
            self.vw = self.vh = 0.0
            self.apply_geometry()
            self.deiconify()
            self.visible = True
            self.attributes("-topmost", True)
            self.lift()
        self.state = "pill"
        self.tw, self.th = PILL_W, PILL_H
        self.moving = True
        self.idle_since = None
        self._emit_sparkles(self.sw / 2, PILL_H / 2, n=5)

    def hide(self):
        if self.state == "hidden":
            return
        self.hide_content()
        self.state = "hidden"
        self.tw, self.th = 44, 6
        self.moving = True
        self.hidden_at = time.time()

    def open(self):
        if self.state != "pill":
            return
        self.state = "open"
        self.tw, self.th = OPEN_W, OPEN_H
        self.moving = True
        self.idle_since = None
        self.focus_force()
        self._emit_sparkles(PILL_W / 2, PILL_H / 2, n=6)

    def close_to_pill(self):
        if self.state != "open":
            return
        self.hide_content()
        self.state = "pill"
        self.tw, self.th = PILL_W, PILL_H
        self.moving = True
        self.idle_since = time.time()

    def toggle(self):
        if self.state == "pill":
            self.open()
        elif self.state == "open":
            self.close_to_pill()

    def show_content(self):
        if self.content_item is not None:
            return
        self.refresh()
        self.content_item = self.cv.create_window(
            14, HEADER_H + 8, window=self.content, anchor="nw",
            width=OPEN_W - 28, height=OPEN_H - HEADER_H - 22)
        self.after(30, self.entry.focus_set)

    def hide_content(self):
        if self.content_item is not None:
            self.cv.delete(self.content_item)
            self.content_item = None

    # ── events ─────────────────────────────────────────────────────────────────
    def on_click(self, e):
        if e.y <= HEADER_H:
            self.toggle()

    def on_right(self, e):
        if e.y <= HEADER_H:
            try:
                self.menu.tk_popup(e.x_root, e.y_root)
            finally:
                self.menu.grab_release()

    def on_wheel(self, e):
        if self.state != "open" or self.content_item is None:
            return
        d = -1 if (getattr(e, "delta", 0) > 0 or getattr(e, "num", 0) == 4) else 1
        self.list.cv.yview_scroll(d, "units")

    # ── drawing ────────────────────────────────────────────────────────────────
    def draw(self):
        c = self.cv
        c.delete("shape", "hdr")
        w, h = self.cw, self.ch

        border_col = mix(BORDER, ACC, self.bounce * 0.6)
        rrect(c, 1, 1, w-1, h-1, min(h/2, 28),
              fill=BG, outline=border_col, width=1, tags="shape")

        if h < 30 or w < 170:
            return

        t = time.time()
        left, total = self.counts()
        all_done = total > 0 and left == 0

        if self.state == "pill" and random.random() < 0.08:
            self._emit_sparkles(
                random.uniform(w*0.1, w*0.9),
                random.uniform(h*0.1, h*0.9), n=1)

        self._draw_face(28, HEADER_H / 2, t, all_done)

        x = 58
        if total == 0:
            c.create_text(x, 16, anchor="w", text="LOBO",
                          fill=ACC, font=self.f_head, tags="hdr")
            c.create_text(x, 32, anchor="w", text="No tasks yet",
                          fill=DIM, font=self.f_small, tags="hdr")

        elif all_done:
            r_col = mix(BODY_DONE, ACC2, (math.sin(t * 1.8) + 1) / 2)
            c.create_text(x, 16, anchor="w", text="LOBO",
                          fill=ACC, font=self.f_brand, tags="hdr")
            c.create_text(x+42, 22, anchor="w", text="All done!",
                          fill=r_col, font=self.f_head, tags="hdr")
            if random.random() < 0.12:
                self._emit_stars(x+20, 22, n=1)
        else:
            c.create_text(x, 12, anchor="w", text="LOBO",
                          fill=ACC, font=self.f_brand, tags="hdr")
            num = str(left)
            c.create_text(x, 30, anchor="w", text=num,
                          fill=mix(ACC, ACC2, self.bounce),
                          font=self.f_num, tags="hdr")
            nw = self.f_num.measure(num)
            c.create_text(x+nw+6, 31, anchor="w",
                          text="task left" if left == 1 else "tasks left",
                          fill=FG, font=self.f_small, tags="hdr")

        # chevron
        cx2, cy2 = w - 26, 22
        if self.state == "open":
            pts = (cx2-5, cy2+2, cx2, cy2-3, cx2+5, cy2+2)
        else:
            pts = (cx2-5, cy2-2, cx2, cy2+3, cx2+5, cy2-2)
        c.create_line(*pts, fill=DIM, width=2, capstyle="round",
                      joinstyle="round", tags="hdr")

        self._draw_particles(c)

    def _draw_face(self, cx, cy, t, done):
        c = self.cv
        bob  = math.sin(t * 3.4) * 1.8
        jump = -abs(math.sin((1-self.bounce)*math.pi*3)) * self.bounce * 7
        y    = cy + bob + jump
        sq   = 1 + 0.08 * math.sin(t * 3.4 + 1)
        rx, ry = 12.5*sq, 12.5/sq

        col = BODY_DONE if done else BODY
        c.create_oval(cx-rx, y-ry, cx+rx, y+ry, fill=col, outline="", tags="hdr")

        for sx in (-8.0, 8.0):
            bw = 3.5 + math.sin(t*2)*0.4
            c.create_oval(cx+sx-bw, y+2.5, cx+sx+bw, y+5.5,
                          fill=BLUSH, outline="", tags="hdr")

        look = math.sin(t * 0.85) * 1.6

        if done:
            for sx in (-4.5, 4.5):
                ex = cx + sx + look
                c.create_line(ex-3, y-0.5, ex, y-4, ex+3, y-0.5,
                              fill=INK, width=2.0, capstyle="round",
                              joinstyle="round", tags="hdr")
            c.create_arc(cx-4.5, y-1, cx+4.5, y+7.5,
                         start=180, extent=180, style="chord",
                         fill=INK, outline=INK, tags="hdr")
            for i, (ox, oy, sp, r0) in enumerate([
                    (+18,-10,5.5,3.5),(-17,-8,4.8,2.8),
                    (+14,-15,6.2,2.5),(-12,-14,5.0,3.0)]):
                rs = r0 + 1.8*math.sin(t*sp+i)
                star(c, cx+ox, y+oy, rs, fill=BODY_DONE, outline="", tags="hdr")
            if random.random() < 0.04:
                self._emit_hearts(cx, y-ry-5, n=2)
        else:
            blink = (t % 4.0) > 3.82
            ery   = 0.4 if blink else 2.2
            for sx in (-4.5, 4.5):
                ex = cx + sx + look
                c.create_oval(ex-2.0, y-2.5-ery, ex+2.0, y-2.5+ery,
                              fill=INK, outline="", tags="hdr")
            c.create_arc(cx-3.8, y+0.5, cx+3.8, y+7,
                         start=205, extent=130, style="arc",
                         outline=INK, width=1.6, tags="hdr")
            wink = 6.6 < (t % 7.0) < 6.85
            if wink:
                ex = cx + 4.5 + look
                c.create_line(ex-2, y-2.5, ex+2, y-2.5,
                              fill=INK, width=2.0, capstyle="round", tags="hdr")
            if random.random() < 0.025:
                self._emit_sparkles(cx + random.uniform(-14, 14), y-ry-3, n=1)

        if self.state == "pill" and self.ch > 20:
            tail_x = cx + math.sin(self.tail_phase) * 5
            c.create_line(cx, y+ry-1, tail_x, y+ry+5,
                          fill=mix(col, BLUSH, 0.5), width=2.5,
                          capstyle="round", tags="hdr")

    # ── panel UI ───────────────────────────────────────────────────────────────
    def _build_content(self):
        f = tk.Frame(self.cv, bg=BG)
        self.content = f

        # tab bar
        top = tk.Frame(f, bg=BG)
        top.pack(fill="x", pady=(0, 2))
        self.tab_btns = {}
        for key, label in (("tasks", "Tasks"), ("notes", "Notes")):
            b = tk.Label(top, text=label, font=self.f_bold, padx=10, pady=4, cursor="hand2")
            b.pack(side="left", padx=(0, 2))
            b.bind("<Button-1>", lambda e, k=key: self.set_tab(k))
            self.tab_btns[key] = b

        self.stat = tk.Label(top, text="", fg=DIM, bg=BG, font=self.f_small)
        self.stat.pack(side="right", padx=(0, 4))
        self.clear_btn = tk.Label(top, text="clear done", fg=DIM, bg=BG,
                                  font=self.f_small, cursor="hand2")
        self.clear_btn.bind("<Button-1>", lambda e: self.clear_done())
        self.clear_btn.bind("<Enter>",    lambda e: self.clear_btn.config(fg=ACC2))
        self.clear_btn.bind("<Leave>",    lambda e: self.clear_btn.config(fg=DIM))

        # entry row – pack FIRST so side="bottom" reserves space before the list expands
        row = tk.Frame(f, bg=ROW)
        row.pack(fill="x", side="bottom")
        self.entry = tk.Entry(row, bg=ROW, fg=FG, insertbackground=ACC,
                              relief="flat", bd=0, font=self.f_text,
                              highlightthickness=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 4), pady=8)
        add = tk.Label(row, text="+", bg=ACC, fg=BG, font=self.f_head,
                       width=3, cursor="hand2")
        add.pack(side="right", padx=5, pady=5)
        add.bind("<Button-1>", lambda e: self.add_item())
        self.entry.bind("<Return>", lambda e: self.add_item())
        self.entry_row = row

        # scrollable list – packed AFTER entry_row so it fills remaining space
        self.list = ScrollList(f, BG)
        self.list.pack(fill="both", expand=True)

    def entry_text(self):
        return self.entry.get().strip()

    # ── tab / data actions ────────────────────────────────────────────────────
    def set_tab(self, key):
        self.tab = key
        self.entry.delete(0, "end")
        self.refresh()

    def add_item(self):
        txt = self.entry_text()
        if not txt:
            return
        if self.tab == "tasks":
            self.tasks.append({"t": txt, "d": False})
            self.bounce = 1.0
            self._emit_hearts(28, HEADER_H/2, n=5)
            self._emit_sparkles(28, HEADER_H/2, n=4)
        else:
            self.notes.append(txt)
            self._emit_sparkles(28, HEADER_H/2, n=3)
        self.save()
        self.refresh(scroll_end=True)
        self.entry.delete(0, "end")
        self.after(10, self.entry.focus_set)

    def toggle_task(self, i):
        if 0 <= i < len(self.tasks):
            self.tasks[i]["d"] = not self.tasks[i]["d"]
            self.bounce = 1.0
            self._emit_hearts(28, HEADER_H/2, n=6)
            self._emit_sparkles(self.cw/2, self.ch/2, n=8)
            self._emit_stars(self.cw/2, self.ch/2, n=4)
            self.save()
            self.refresh()

    def del_task(self, i):
        if 0 <= i < len(self.tasks):
            del self.tasks[i]
            self.bounce = 1.0
            self._emit_sparkles(28, HEADER_H/2, n=4)
            self.save()
            self.refresh()

    def del_note(self, i):
        if 0 <= i < len(self.notes):
            del self.notes[i]
            self.save()
            self.refresh()

    def clear_done(self):
        self.tasks = [t for t in self.tasks if not t["d"]]
        self.bounce = 1.0
        self._emit_hearts(self.cw/2, self.ch/2, n=8)
        self.save()
        self.refresh()

    # ── refresh (render list) ─────────────────────────────────────────────────
    def refresh(self, scroll_end=False):
        for w in self.list.inner.winfo_children():
            w.destroy()

        if self.tab == "tasks":
            empty, msg = not self.tasks, "No tasks yet.\nAdd one below."
            for i, it in enumerate(self.tasks):
                self._task_row(i, it)
            left, total = self.counts()
            self.stat.config(text=f"{left} left  /  {total} total")
            if any(t["d"] for t in self.tasks):
                self.clear_btn.pack(side="right", padx=(0, 10))
            else:
                self.clear_btn.pack_forget()
        else:
            empty, msg = not self.notes, "No notes yet.\nJot something below."
            for i, n in enumerate(self.notes):
                self._note_row(i, n)
            self.stat.config(text=f"{len(self.notes)} note" +
                             ("" if len(self.notes) == 1 else "s"))
            self.clear_btn.pack_forget()

        if empty:
            tk.Label(self.list.inner, text=msg, fg=DIM, bg=BG,
                     font=self.f_text, justify="center").pack(pady=40)

        for k, b in self.tab_btns.items():
            on = k == self.tab
            b.config(bg=ACC if on else ROW, fg=BG if on else DIM)

        if scroll_end:
            self.list.cv.update_idletasks()
            self.list.cv.yview_moveto(1.0)

    # ── row builders ──────────────────────────────────────────────────────────
    def _x_btn(self, row, cmd):
        x = tk.Label(row, text="×", fg=DIM, bg=ROW, font=self.f_x,
                     cursor="hand2", padx=8)
        x.pack(side="right")
        x.bind("<Button-1>", lambda e: cmd())
        x.bind("<Enter>",    lambda e: x.config(fg=ACC2))
        x.bind("<Leave>",    lambda e: x.config(fg=DIM))

    def _task_row(self, i, it):
        done = it["d"]
        row  = tk.Frame(self.list.inner, bg=ROW)
        row.pack(fill="x", pady=2, padx=(0,4))
        box = tk.Canvas(row, width=24, height=24, bg=ROW,
                        highlightthickness=0, cursor="hand2")
        box.pack(side="left", padx=(8,6), pady=7)
        rrect(box, 3, 3, 21, 21, 6, fill=ACC if done else ROW, outline=ACC, width=2)
        if done:
            box.create_line(8, 12.5, 11.5, 16, 17, 8.5,
                            fill=BG, width=2.5, capstyle="round", joinstyle="round")
        box.bind("<Button-1>", lambda e, i=i: self.toggle_task(i))
        lbl = tk.Label(row, text=it["t"], bg=ROW,
                       fg=DIM if done else FG,
                       font=self.f_done if done else self.f_text,
                       wraplength=225, justify="left", anchor="w", cursor="hand2")
        lbl.pack(side="left", fill="x", expand=True, pady=6)
        lbl.bind("<Button-1>", lambda e, i=i: self.toggle_task(i))
        self._x_btn(row, lambda i=i: self.del_task(i))

    def _note_row(self, i, text):
        row = tk.Frame(self.list.inner, bg=ROW)
        row.pack(fill="x", pady=2, padx=(0,4))
        dot = tk.Canvas(row, width=24, height=24, bg=ROW, highlightthickness=0)
        dot.pack(side="left", padx=(8,6), pady=7)
        dot.create_oval(8, 8, 16, 16, fill=ACC2, outline="")
        tk.Label(row, text=text, bg=ROW, fg=FG, font=self.f_text,
                 wraplength=225, justify="left", anchor="w"
                 ).pack(side="left", fill="x", expand=True, pady=6)
        self._x_btn(row, lambda i=i: self.del_note(i))


if __name__ == "__main__":
    App().mainloop()
