#!/usr/bin/env python3
"""
Schieberpuzzle-Löser  –  BFS / A*   mit tkinter GUI
Start:  python3 schieberpuzzle.py
"""
import tkinter as tk
from tkinter import messagebox
from collections import deque
import heapq, threading, time

# ─── Puzzle-Konstanten ────────────────────────────────────────────────────────
HOLES  = 7      # Immer 7 Löcher pro Element
TARGET = 3      # 0-basiert = Position 4 = Mitte

# ─── Farben ───────────────────────────────────────────────────────────────────
BG    = "#12131a"
PANEL = "#1c1f2e"
CARD  = "#252838"
FG    = "#dde2f0"
FG_D  = "#3c4260"
FG_M  = "#7880a0"
ACNT  = "#e94560"

EC = [                 # Element-Farben E1–E7
    "#e94560",         # Rot
    "#f0a030",         # Amber
    "#3dcc7e",         # Grün
    "#4488ff",         # Blau
    "#b844dd",         # Violett
    "#ff7744",         # Orange
    "#1ec8c8",         # Teal
]

# Kopplung-Zustände  0=keine  1=gleich  2=entgegen
CS = {
    0: (CARD,     FG_D,     FG_M),
    1: ("#143322", "#3dcc7e", "#3dcc7e"),
    2: ("#301414", "#e94560", "#e94560"),
}

# ─── Übersetzungen ────────────────────────────────────────────────────────────
T = {
"de": dict(
    title="Schieberpuzzle-Löser", lang="EN",
    n_elem="Anzahl Elemente", start_pos="Startposition (1–7)",
    coupling="Kopplungsregeln", mover=" bewegt →",
    c0="—", c1="↑↑  gleich", c2="↑↓  entgegen",
    solve="▶   Lösung berechnen", reset="↺   Zurücksetzen",
    sol="Lösung", init="Ausgangszustand",
    right="rechts →", left="← links",
    no_sol="Keine Lösung gefunden.",
    no_sol2="Mögliche Ursachen: Puzzle unlösbar oder Suchraum zu groß.",
    ready="Bereit.", run="Suche läuft …",
    steps="Schritte", step_lbl="Schrittliste",
    step="Schritt", of="von", x="×",
    err="Fehler", warn="Warnung",
    step_n="Schritt {i} / {n}  —  E{e} {d}",
),
"en": dict(
    title="Sliding Puzzle Solver", lang="DE",
    n_elem="Number of elements", start_pos="Start position (1–7)",
    coupling="Coupling rules", mover=" moves →",
    c0="—", c1="↑↑  same", c2="↑↓  opposite",
    solve="▶   Find Solution", reset="↺   Reset",
    sol="Solution", init="Initial state",
    right="right →", left="← left",
    no_sol="No solution found.",
    no_sol2="Possible causes: puzzle unsolvable or search space too large.",
    ready="Ready.", run="Searching …",
    steps="steps", step_lbl="Step list",
    step="Step", of="of", x="×",
    err="Error", warn="Warning",
    step_n="Step {i} / {n}  —  E{e} {d}",
),
}

# ─── Lösungslogik ─────────────────────────────────────────────────────────────
def build_effects(n, couplings):
    ef = {i: [] for i in range(n)}
    for (a, b), v in couplings.items():
        ef[a].append((b, 1 if v == 1 else -1))
    return ef

def apply_move(state, elem, d, ef, n):
    s = list(state)
    for idx, sign in [(elem, d)] + [(b, d*sg) for b, sg in ef[elem]]:
        p = s[idx] - sign
        if p < 0 or p >= HOLES:
            return None
        s[idx] = p
    return tuple(s)

def heuristic(state, target, n):
    return sum(abs(state[i] - target) for i in range(n))

def solve_bfs(start, ef, n, mx=1_400_000):
    goal = tuple([TARGET] * n)
    start = tuple(start)
    if start == goal:
        return []
    q = deque([(start, [])])
    vis = {start}
    while q:
        if len(vis) > mx:
            return None
        st, path = q.popleft()
        for e in range(n):
            for d in (1, -1):
                ns = apply_move(st, e, d, ef, n)
                if ns and ns not in vis:
                    np_ = path + [(e, d)]
                    if ns == goal:
                        return np_
                    vis.add(ns)
                    q.append((ns, np_))
    return None

def solve_astar(start, ef, n, mx=800_000):
    goal = tuple([TARGET] * n)
    start = tuple(start)
    if start == goal:
        return []
    h0 = heuristic(start, TARGET, n)
    heap = [(h0, 0, start, [])]
    best = {start: 0}
    steps = 0
    while heap and steps < mx:
        _, g, st, path = heapq.heappop(heap)
        steps += 1
        if st == goal:
            return path
        if best.get(st, 10**9) < g:
            continue
        for e in range(n):
            for d in (1, -1):
                ns = apply_move(st, e, d, ef, n)
                if ns is None:
                    continue
                ng = g + 1
                if ng < best.get(ns, 10**9):
                    best[ns] = ng
                    h = heuristic(ns, TARGET, n)
                    heapq.heappush(heap, (ng + h, ng, ns, path + [(e, d)]))
    return None

def compress(sol):
    """Aufeinanderfolgende gleiche Züge zusammenfassen."""
    if not sol:
        return []
    out = []
    ce, cd, cnt = sol[0][0], sol[0][1], 1
    for e, d in sol[1:]:
        if e == ce and d == cd:
            cnt += 1
        else:
            out.append((ce, cd, cnt))
            ce, cd, cnt = e, d, 1
    out.append((ce, cd, cnt))
    return out


# ─── App ──────────────────────────────────────────────────────────────────────
class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.lang    = "de"
        self.n       = 4                        # Anzahl Elemente
        self.starts  = [TARGET] * 7             # 0-basiert, default Mitte
        self.coups   = {}                       # (i,j) → 0|1|2
        self.solution     = None
        self.step_states  = []
        self.step_groups  = []                  # compressed
        self.cur_step     = 0
        self.effects      = None

        # Widget-Referenzen für Sprachumschaltung
        self._widgets = {}

        self.title(self.t("title"))
        self.configure(bg=BG)
        self.geometry("1220x860")
        self.minsize(900, 620)

        self._build()
        self._rebuild_left()

    # ── Hilfsfunktionen ───────────────────────────────────────────────────────
    def t(self, key, **kw):
        s = T[self.lang].get(key, key)
        return s.format(**kw) if kw else s

    def ec(self, i):
        """Element-Farbe (0-basiert)."""
        return EC[i % len(EC)]

    # ── Haupt-Layout ──────────────────────────────────────────────────────────
    def _build(self):
        # ── Kopfzeile ─────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=14, pady=(10, 0))
        self._widgets["title_lbl"] = tk.Label(
            hdr, text=self.t("title"), bg=BG, fg=FG,
            font=("Helvetica", 17, "bold"))
        self._widgets["title_lbl"].pack(side="left")

        self._widgets["lang_btn"] = tk.Button(
            hdr, text=self.t("lang"), bg=CARD, fg=FG_M,
            relief="flat", font=("Helvetica", 10, "bold"),
            padx=10, pady=4, cursor="hand2",
            activebackground=ACNT, activeforeground=FG,
            command=self._toggle_lang)
        self._widgets["lang_btn"].pack(side="right")

        sep = tk.Frame(self, bg=FG_D, height=1)
        sep.pack(fill="x", padx=14, pady=6)

        # ── Haupt-Pane ────────────────────────────────────────────────────────
        self.pane = tk.PanedWindow(
            self, orient="horizontal", bg=BG,
            sashwidth=8, sashrelief="flat")
        self.pane.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.left_outer = tk.Frame(self.pane, bg=BG)
        self.pane.add(self.left_outer, minsize=480)

        self.right_frame = tk.Frame(self.pane, bg=BG)
        self.pane.add(self.right_frame, minsize=420)
        self._build_right()

    # ── Linke Seite ───────────────────────────────────────────────────────────
    def _rebuild_left(self):
        for w in self.left_outer.winfo_children():
            w.destroy()

        # Scrollbarer Canvas
        canvas = tk.Canvas(self.left_outer, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(self.left_outer, orient="vertical",
                           command=canvas.yview, bg=BG)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _cw(e):
            canvas.itemconfig(win_id, width=e.width)
        inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", _cw)
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        PAD = 12

        # ── Abschnitt: Anzahl Elemente ────────────────────────────────────────
        self._widgets["n_lbl"] = self._section_head(inner, "n_elem")
        row = tk.Frame(inner, bg=BG)
        row.pack(fill="x", padx=PAD, pady=(0, 10))
        self._widgets["n_btns"] = []
        for v in (4, 5, 6, 7):
            b = tk.Button(
                row, text=str(v), width=5,
                bg=ACNT if v == self.n else CARD,
                fg=FG, relief="flat",
                font=("Helvetica", 13, "bold"),
                padx=8, pady=6, cursor="hand2",
                command=lambda v=v: self._set_n(v))
            b.pack(side="left", padx=4)
            self._widgets["n_btns"].append((v, b))

        # ── Abschnitt: Startposition ──────────────────────────────────────────
        self._widgets["sp_lbl"] = self._section_head(inner, "start_pos")
        self._start_frame = tk.Frame(inner, bg=BG)
        self._start_frame.pack(fill="x", padx=PAD, pady=(0, 10))
        self._build_start_rows()

        # ── Abschnitt: Kopplungsregeln ────────────────────────────────────────
        self._widgets["cp_lbl"] = self._section_head(inner, "coupling")
        self._coup_frame = tk.Frame(inner, bg=BG)
        self._coup_frame.pack(fill="x", padx=PAD, pady=(0, 10))
        self._build_coupling()

        # ── Buttons: Reset + Solve ────────────────────────────────────────────
        btm = tk.Frame(inner, bg=BG)
        btm.pack(fill="x", padx=PAD, pady=(6, 4))

        self._widgets["reset_btn"] = tk.Button(
            btm, text=self.t("reset"),
            bg=CARD, fg=FG_M, relief="flat",
            font=("Helvetica", 11), padx=14, pady=8, cursor="hand2",
            activebackground="#3a1818", activeforeground=ACNT,
            command=self._reset)
        self._widgets["reset_btn"].pack(side="left", padx=(0, 8))

        self._widgets["solve_btn"] = tk.Button(
            btm, text=self.t("solve"),
            bg=ACNT, fg=FG, relief="flat",
            font=("Helvetica", 12, "bold"), padx=20, pady=8, cursor="hand2",
            activebackground="#c73050",
            command=self._start_solve)
        self._widgets["solve_btn"].pack(side="left", fill="x", expand=True)

        self._widgets["status"] = tk.Label(
            inner, text=self.t("ready"), bg=BG, fg=FG_M,
            font=("Helvetica", 9))
        self._widgets["status"].pack(anchor="w", padx=PAD, pady=(2, 8))

    def _section_head(self, parent, key):
        f = tk.Frame(parent, bg=BG)
        f.pack(fill="x", pady=(12, 4))
        lbl = tk.Label(f, text=self.t(key).upper(),
                       bg=BG, fg=FG_M,
                       font=("Helvetica", 8, "bold"), anchor="w")
        lbl.pack(side="left", padx=12)
        tk.Frame(f, bg=FG_D, height=1).pack(side="left", fill="x",
                                              expand=True, padx=(6, 12))
        return lbl

    # ── Startposition-Reihen ──────────────────────────────────────────────────
    def _build_start_rows(self):
        for w in self._start_frame.winfo_children():
            w.destroy()
        self._start_btns = {}   # (i, pos) → Button

        for i in range(self.n):
            row = tk.Frame(self._start_frame, bg=BG)
            row.pack(fill="x", pady=3)

            # Element-Label mit Farbpunkt
            lbl = tk.Frame(row, bg=BG)
            lbl.pack(side="left")
            tk.Canvas(lbl, width=10, height=10, bg=BG,
                      highlightthickness=0).pack(side="left", padx=(0, 2))
            c = tk.Canvas(lbl, width=12, height=12, bg=BG,
                          highlightthickness=0)
            c.pack(side="left")
            c.create_oval(1, 1, 11, 11, fill=self.ec(i), outline="")
            tk.Label(lbl, text=f"E{i+1}", bg=BG, fg=self.ec(i),
                     font=("Helvetica", 11, "bold"), width=4,
                     anchor="w").pack(side="left")

            # 7 Positions-Buttons
            for pos in range(HOLES):
                sel = (self.starts[i] == pos)
                ecol = self.ec(i)
                b = tk.Button(
                    row,
                    text=str(pos + 1),
                    width=3,
                    bg=ecol if sel else CARD,
                    fg=BG if sel else FG_M,
                    relief="flat",
                    font=("Helvetica", 11, "bold" if sel else "normal"),
                    pady=4, cursor="hand2",
                    command=lambda i=i, p=pos: self._set_start(i, p))
                b.pack(side="left", padx=2)
                self._start_btns[(i, pos)] = b

    # ── Kopplungs-Matrix ──────────────────────────────────────────────────────
    def _build_coupling(self):
        for w in self._coup_frame.winfo_children():
            w.destroy()
        self._coup_btns = {}   # (i, j) → Button
        n = self.n

        # Kopf-Zeile
        hdr = tk.Frame(self._coup_frame, bg=BG)
        hdr.pack(fill="x", pady=(0, 2))
        tk.Label(hdr, text="", bg=BG, width=12).pack(side="left")
        for j in range(n):
            tk.Label(hdr, text=f"E{j+1}", bg=BG, fg=self.ec(j),
                     font=("Helvetica", 10, "bold"), width=10,
                     anchor="center").pack(side="left", padx=2)

        # Matrix-Zeilen
        for i in range(n):
            row = tk.Frame(self._coup_frame, bg=BG)
            row.pack(fill="x", pady=2)

            lbl_text = f"E{i+1}{self.t('mover')}"
            tk.Label(row, text=lbl_text, bg=BG, fg=self.ec(i),
                     font=("Helvetica", 10, "bold"), width=12,
                     anchor="w").pack(side="left")

            for j in range(n):
                if i == j:
                    tk.Label(row, text="●", bg=BG, fg=FG_D,
                             width=10).pack(side="left", padx=2)
                    continue
                state = self.coups.get((i, j), 0)
                bg, fg, _ = CS[state]
                texts = {0: self.t("c0"), 1: self.t("c1"), 2: self.t("c2")}
                b = tk.Button(
                    row,
                    text=texts[state],
                    width=9,
                    bg=bg, fg=fg, relief="flat",
                    font=("Helvetica", 9),
                    pady=5, cursor="hand2",
                    command=lambda i=i, j=j: self._toggle_coup(i, j))
                b.pack(side="left", padx=2)
                self._coup_btns[(i, j)] = b

    # ── Rechte Seite ─────────────────────────────────────────────────────────
    def _build_right(self):
        rf = self.right_frame

        self._widgets["sol_lbl"] = tk.Label(
            rf, text=self.t("sol"), bg=BG, fg=FG,
            font=("Helvetica", 13, "bold"))
        self._widgets["sol_lbl"].pack(anchor="w", padx=8, pady=(4, 4))

        # Visualisierung
        self.viz = tk.Canvas(rf, bg=PANEL, height=240, highlightthickness=0)
        self.viz.pack(fill="x", padx=8, pady=4)
        self.viz.bind("<Configure>", lambda _: self._draw_cur())

        # Schritt-Info
        self._widgets["step_info"] = tk.Label(
            rf, text="—", bg=BG, fg=FG,
            font=("Helvetica", 11))
        self._widgets["step_info"].pack(pady=(4, 0))

        # Navigation
        nav = tk.Frame(rf, bg=BG)
        nav.pack(pady=6)
        for sym, cmd in [("⏮", self._go_first), ("◀", self._go_prev),
                         ("▶", self._go_next),  ("⏭", self._go_last)]:
            tk.Button(nav, text=sym, command=cmd,
                      bg=CARD, fg=FG, relief="flat",
                      font=("Helvetica", 14), width=3,
                      activebackground=ACNT, cursor="hand2"
                      ).pack(side="left", padx=3)
        self.bind("<Left>",  lambda _: self._go_prev())
        self.bind("<Right>", lambda _: self._go_next())
        self.bind("<Home>",  lambda _: self._go_first())
        self.bind("<End>",   lambda _: self._go_last())

        # Schrittliste
        self._widgets["sl_lbl"] = tk.Label(
            rf, text=self.t("step_lbl"), bg=BG, fg=FG_M,
            font=("Helvetica", 10))
        self._widgets["sl_lbl"].pack(anchor="w", padx=8)

        txt_frame = tk.Frame(rf, bg=BG)
        txt_frame.pack(fill="both", expand=True, padx=8, pady=4)

        self.step_txt = tk.Text(
            txt_frame,
            bg=PANEL, fg=FG,
            font=("Courier", 13),
            relief="flat",
            state="disabled",
            wrap="none",
            selectbackground=ACNT,
            selectforeground=FG,
            spacing1=4, spacing3=4,
            cursor="arrow")
        vsb = tk.Scrollbar(txt_frame, orient="vertical",
                           command=self.step_txt.yview, bg=BG)
        self.step_txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.step_txt.pack(fill="both", expand=True)

        # Text-Tags (Farben pro Element + Highlight)
        for i in range(7):
            self.step_txt.tag_configure(
                f"e{i}", foreground=EC[i],
                font=("Courier", 13, "bold"))
        self.step_txt.tag_configure(
            "cnt", foreground=FG_M,
            font=("Courier", 13))
        self.step_txt.tag_configure(
            "dir", foreground=FG,
            font=("Courier", 13))
        self.step_txt.tag_configure(
            "sel", background=ACNT,
            foreground=FG)
        self.step_txt.tag_configure(
            "head", foreground=FG_M,
            font=("Courier", 11))

        self.step_txt.bind("<Button-1>", self._on_txt_click)

    # ── State-Änderungen ─────────────────────────────────────────────────────
    def _set_n(self, n):
        if n == self.n:
            return
        self.n = n
        # Coupling-Einträge für entfernte Elemente löschen
        self.coups = {(i, j): v for (i, j), v in self.coups.items()
                      if i < n and j < n}
        self._rebuild_left()

    def _set_start(self, i, pos):
        old = self.starts[i]
        if old == pos:
            return
        self.starts[i] = pos
        # Alte und neue Buttons aktualisieren
        for p, old_pos in [(old, True), (pos, False)]:
            btn = self._start_btns.get((i, p))
            if btn:
                sel = (not old_pos)  # pos=new is selected, old=False
                ecol = self.ec(i)
                btn.configure(
                    bg=ecol if sel else CARD,
                    fg=BG if sel else FG_M,
                    font=("Helvetica", 11, "bold" if sel else "normal"))
        # Korrektur: Buttons direkt setzen
        for p2 in range(HOLES):
            btn = self._start_btns.get((i, p2))
            if btn:
                sel = (self.starts[i] == p2)
                ecol = self.ec(i)
                btn.configure(
                    bg=ecol if sel else CARD,
                    fg=BG if sel else FG_M,
                    font=("Helvetica", 11, "bold" if sel else "normal"))

    def _toggle_coup(self, i, j):
        self.coups[(i, j)] = (self.coups.get((i, j), 0) + 1) % 3
        state = self.coups[(i, j)]
        bg, fg, _ = CS[state]
        texts = {0: self.t("c0"), 1: self.t("c1"), 2: self.t("c2")}
        btn = self._coup_btns.get((i, j))
        if btn:
            btn.configure(text=texts[state], bg=bg, fg=fg)

    def _reset(self):
        self.n = 4
        self.starts = [TARGET] * 7
        self.coups  = {}
        self.solution    = None
        self.step_states = []
        self.step_groups = []
        self.cur_step    = 0
        self.effects     = None
        self._clear_solution()
        self._rebuild_left()

    def _toggle_lang(self):
        self.lang = "en" if self.lang == "de" else "de"
        self.title(self.t("title"))
        self._widgets["title_lbl"].configure(text=self.t("title"))
        self._widgets["lang_btn"].configure(text=self.t("lang"))
        self._widgets["sol_lbl"].configure(text=self.t("sol"))
        self._widgets["sl_lbl"].configure(text=self.t("step_lbl"))
        # Links komplett neu aufbauen (enthält alle übersetzten Labels)
        self._rebuild_left()
        # Schrittliste neu schreiben wenn Lösung vorhanden
        if self.solution:
            self._fill_step_list()
            self._update_step_info()

    # ── Solve ─────────────────────────────────────────────────────────────────
    def _start_solve(self):
        self._widgets["solve_btn"].configure(state="disabled",
                                        text="…")
        self._widgets["status"].configure(text=self.t("run"))
        threading.Thread(target=self._solve_thread, daemon=True).start()

    def _solve_thread(self):
        try:
            n = self.n
            starts = self.starts[:n]

            if all(s == TARGET for s in starts):
                self.after(0, self._already_solved)
                return

            coupling = {}
            for (i, j), v in self.coups.items():
                if i < n and j < n and v != 0:
                    coupling[(i, j)] = v
            self.effects = build_effects(n, coupling)

            ss = HOLES ** n
            t0 = time.time()
            if ss <= 1_400_000:
                self.after(0, lambda: self._widgets["status"].configure(
                    text=f"BFS  –  {ss:,} Zustände"))
                sol = solve_bfs(starts, self.effects, n)
                if sol is None:
                    self.after(0, lambda: self._widgets["status"].configure(
                        text="A* …"))
                    sol = solve_astar(starts, self.effects, n)
            else:
                self.after(0, lambda: self._widgets["status"].configure(
                    text=f"A*  –  {ss:,} Zustände"))
                sol = solve_astar(starts, self.effects, n)
            elapsed = time.time() - t0

            if sol is None:
                self.after(0, lambda: (
                    self._widgets["status"].configure(text=self.t("no_sol")),
                    messagebox.showwarning(
                        self.t("warn"),
                        self.t("no_sol") + "\n" + self.t("no_sol2"))))
                return

            state = tuple(starts)
            states = [state]
            for e, d in sol:
                state = apply_move(state, e, d, self.effects, n)
                states.append(state)

            self.solution    = sol
            self.step_states = states
            self.step_groups = compress(sol)
            self.cur_step    = 0

            total = len(sol)
            self.after(0, lambda: (
                self._widgets["status"].configure(
                    text=f"✓  {total} {self.t('steps')}  "
                         f"({len(self.step_groups)} Gruppen)  "
                         f"–  {elapsed:.2f} s"),
                self._fill_step_list(),
                self._show_step(0)))
        except Exception as ex:
            import traceback
            tb = traceback.format_exc()
            self.after(0, lambda: messagebox.showerror(
                self.t("err"), f"{ex}\n\n{tb}"))
        finally:
            self.after(0, lambda: self._widgets["solve_btn"].configure(
                state="normal", text=self.t("solve")))

    def _already_solved(self):
        self._widgets["status"].configure(text="✓  0 Schritte")
        self._widgets["solve_btn"].configure(state="normal",
                                        text=self.t("solve"))
        self.solution    = []
        self.step_states = [tuple(self.starts[:self.n])]
        self.step_groups = []
        self.cur_step    = 0
        self._fill_step_list()
        self._show_step(0)

    # ── Schrittliste ─────────────────────────────────────────────────────────
    def _fill_step_list(self):
        txt = self.step_txt
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        n = self.n

        # Kopfzeile: Ausgangszustand
        txt.insert("end", f"  {self.t('init')}\n", "head")
        txt.insert("end", "  " + self._state_str(self.step_states[0], n) + "\n\n",
                   "head")

        # Gruppen
        group_starts = []   # Zeilen-Index jeder Gruppe (für Klick-Navigation)
        cur_step = 0        # laufender Schritt-Index in step_states
        for gi, (e, d, cnt) in enumerate(self.step_groups):
            group_starts.append(txt.index("end"))
            # "  3×  E2  ← links"
            cnt_str = f"  {cnt}{self.t('x')}  "
            e_str   = f"E{e+1}  "
            d_str   = (self.t("left") if d == -1 else self.t("right")) + "\n"
            txt.insert("end", cnt_str, "cnt")
            txt.insert("end", e_str,   f"e{e}")
            txt.insert("end", d_str,   "dir")
            cur_step += cnt

        self._group_line_starts = group_starts
        txt.configure(state="disabled")

    def _state_str(self, state, n):
        parts = []
        for i in range(n):
            row = list("o" * HOLES)
            row[state[i]] = "X"
            parts.append("".join(row))
        return "  ".join(parts)

    # ── Schritt anzeigen ─────────────────────────────────────────────────────
    def _show_step(self, step_idx):
        if not self.step_states:
            return
        step_idx = max(0, min(step_idx, len(self.solution)))
        self.cur_step = step_idx
        self._draw_cur()
        self._update_step_info()
        self._highlight_group(step_idx)

    def _update_step_info(self):
        idx = self.cur_step
        total = len(self.solution)
        if idx == 0:
            self._widgets["step_info"].configure(text=self.t("init"))
        else:
            e, d = self.solution[idx - 1]
            dr = self.t("left") if d == -1 else self.t("right")
            self._widgets["step_info"].configure(
                text=self.t("step_n",
                            i=idx, n=total,
                            e=e+1, d=dr))

    def _highlight_group(self, step_idx):
        """Aktive Gruppe in der Liste hervorheben."""
        txt = self.step_txt
        txt.tag_remove("sel", "1.0", "end")
        if not self.step_groups or step_idx == 0:
            return
        # Welche Gruppe enthält step_idx?
        acc = 0
        for gi, (e, d, cnt) in enumerate(self.step_groups):
            acc += cnt
            if step_idx <= acc:
                if gi < len(self._group_line_starts):
                    line = self._group_line_starts[gi]
                    end  = f"{line.split('.')[0]}.end"
                    txt.tag_add("sel", line, end)
                    txt.see(line)
                break

    def _draw_cur(self):
        if self.step_states:
            self._draw_state(self.step_states[self.cur_step])

    def _draw_state(self, state):
        cv = self.viz
        cv.delete("all")
        cv.update_idletasks()
        W  = cv.winfo_width() or 560
        n  = self.n

        ROW   = 36
        PAD_Y = 12
        LBL_W = 52
        PAD_X = 10
        MAX_R = 12

        hole_w = min(MAX_R * 2, (W - PAD_X * 2 - LBL_W - 40) // HOLES)
        gap    = hole_w + 4
        r      = hole_w // 2

        total_h = PAD_Y * 2 + n * ROW
        cv.configure(height=max(180, total_h))

        for i in range(n):
            y    = PAD_Y + i * ROW + ROW // 2
            pos  = state[i]
            ec   = self.ec(i)
            done = (pos == TARGET)

            # Label
            cv.create_text(PAD_X + 4, y,
                           text=f"E{i+1}",
                           fill=ec,
                           font=("Helvetica", 11, "bold"),
                           anchor="w")

            ox = PAD_X + LBL_W
            for j in range(HOLES):
                cx = ox + j * gap
                is_pin    = (j == pos)
                is_target = (j == TARGET)

                if is_pin:
                    fill  = "#44cc88" if done else ec
                    out   = fill
                    ri    = r
                elif is_target:
                    fill  = PANEL
                    out   = "#5a6080"
                    ri    = r - 1
                else:
                    fill  = CARD
                    out   = CARD
                    ri    = r - 3

                cv.create_oval(cx - ri, y - ri,
                               cx + ri, y + ri,
                               fill=fill, outline=out,
                               width=2 if is_target and not is_pin else 1)

            # Pos-Text
            cv.create_text(ox + HOLES * gap + 6, y,
                           text=f"{pos+1}",
                           fill=FG_M if not done else "#44cc88",
                           font=("Helvetica", 10),
                           anchor="w")

    def _clear_solution(self):
        self._widgets["step_info"].configure(text="—")
        txt = self.step_txt
        txt.configure(state="normal")
        txt.delete("1.0", "end")
        txt.configure(state="disabled")
        self.viz.delete("all")

    # ── Klick in Schrittliste ─────────────────────────────────────────────────
    def _on_txt_click(self, event):
        if not self.step_groups:
            return
        idx = self.step_txt.index(f"@{event.x},{event.y}")
        row = int(idx.split(".")[0])
        # Finde Gruppe, deren Zeile ≤ row
        chosen = 0
        acc = 0
        for gi, (e, d, cnt) in enumerate(self.step_groups):
            if gi < len(self._group_line_starts):
                ln = int(self._group_line_starts[gi].split(".")[0])
                if ln <= row:
                    acc += cnt
                    chosen = acc
        self._show_step(chosen)

    # ── Navigation ────────────────────────────────────────────────────────────
    def _go_first(self): self._show_step(0)
    def _go_last(self):
        if self.solution is not None:
            self._show_step(len(self.solution))
    def _go_prev(self):
        if self.cur_step > 0:
            self._show_step(self.cur_step - 1)
    def _go_next(self):
        if self.solution and self.cur_step < len(self.solution):
            self._show_step(self.cur_step + 1)


# ─── Start ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
