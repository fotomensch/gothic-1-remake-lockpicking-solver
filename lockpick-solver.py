#!/usr/bin/env python3
"""
Schieberpuzzle-Löser  –  BFS / A* mit tkinter-GUI
Starte mit:  python3 schieberpuzzle.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
from collections import deque
import heapq
import threading
import time

# ── Farben ────────────────────────────────────────────────────────────────────
BG          = "#1a1a2e"
PANEL       = "#16213e"
CARD        = "#0f3460"
ACCENT      = "#e94560"
ACCENT2     = "#7b5ea7"
FG          = "#eaeaea"
FG_DIM      = "#7788aa"
PIN_OK      = "#44cc88"
PIN_WRONG   = "#e94560"
HOLE_FILL   = "#243352"
TARGET_OUT  = "#7b5ea7"


# ── Lösungslogik ──────────────────────────────────────────────────────────────

def build_effects(n: int, coupling: dict) -> dict:
    """coupling: {(mover, affected): 'same'|'opposite'}  →  effects-dict"""
    effects: dict = {i: [] for i in range(n)}
    for (mover, affected), direction in coupling.items():
        effects[mover].append((affected, 1 if direction == "same" else -1))
    return effects


def apply_move(state: tuple, elem: int, direction: int,
               effects: dict, holes: list) -> tuple | None:
    """
    direction: +1 = Element nach rechts (Stift-Index sinkt)
               -1 = Element nach links  (Stift-Index steigt)
    Gibt neuen Zustand zurück oder None wenn ungültig.
    """
    new = list(state)
    moves = [(elem, direction)]
    for (aff, sign) in effects[elem]:
        moves.append((aff, direction * sign))
    for idx, d in moves:
        p = new[idx] - d
        if p < 0 or p >= holes[idx]:
            return None
        new[idx] = p
    return tuple(new)


def heuristic(state: tuple, targets: list) -> int:
    return sum(abs(state[i] - targets[i]) for i in range(len(state)))


def solve_bfs(start, targets, effects, holes, max_states=1_200_000):
    goal = tuple(targets)
    start = tuple(start)
    if start == goal:
        return []
    n = len(start)
    queue: deque = deque([(start, [])])
    visited: set = {start}
    while queue:
        if len(visited) > max_states:
            return None                      # Zustandsraum zu groß → A*
        state, path = queue.popleft()
        for elem in range(n):
            for d in (+1, -1):
                ns = apply_move(state, elem, d, effects, holes)
                if ns and ns not in visited:
                    np_ = path + [(elem, d)]
                    if ns == goal:
                        return np_
                    visited.add(ns)
                    queue.append((ns, np_))
    return None                              # kein Weg gefunden


def solve_astar(start, targets, effects, holes, max_steps=600_000):
    goal = tuple(targets)
    start = tuple(start)
    if start == goal:
        return []
    n = len(start)
    heap = [(heuristic(start, targets), 0, start, [])]
    best: dict = {start: 0}
    steps = 0
    while heap and steps < max_steps:
        f, g, state, path = heapq.heappop(heap)
        steps += 1
        if state == goal:
            return path
        if best.get(state, 10**9) < g:
            continue
        for elem in range(n):
            for d in (+1, -1):
                ns = apply_move(state, elem, d, effects, holes)
                if ns is None:
                    continue
                ng = g + 1
                if ng < best.get(ns, 10**9):
                    best[ns] = ng
                    h = heuristic(ns, targets)
                    heapq.heappush(heap, (ng + h, ng, ns, path + [(elem, d)]))
    return None


# ── Hauptfenster ──────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Schieberpuzzle-Löser")
        self.configure(bg=BG)
        self.geometry("1160x820")
        self.minsize(900, 600)

        self.n_var    = tk.IntVar(value=6)
        self.elem_cfg: list[dict] = []     # {holes, start, target}
        self.coup_var: dict       = {}     # (i,j) → StringVar
        self.solution : list | None = None
        self.step_states: list    = []
        self.effects  : dict | None = None
        self.holes_cfg: list      = []
        self.targets  : list      = []
        self.cur_step : int       = 0

        self._build_ui()
        self._rebuild()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Titelleiste
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(hdr, text="⚙  Schieberpuzzle-Löser",
                 bg=BG, fg=FG, font=("Helvetica", 17, "bold")).pack(side="left")
        tk.Label(hdr, text="BFS / A*",
                 bg=BG, fg=FG_DIM, font=("Helvetica", 10)).pack(side="left", padx=12)

        # Haupt-Pane
        pane = tk.PanedWindow(self, orient="horizontal", bg=BG,
                              sashwidth=7, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=10, pady=6)

        left = tk.Frame(pane, bg=BG)
        pane.add(left, minsize=440)
        self._build_left(left)

        right = tk.Frame(pane, bg=BG)
        pane.add(right, minsize=430)
        self._build_right(right)

    # ── Linke Spalte (Konfiguration) ──────────────────────────────────────────

    def _build_left(self, parent):
        tk.Label(parent, text="Konfiguration",
                 bg=BG, fg=ACCENT, font=("Helvetica", 12, "bold")
                 ).pack(anchor="w", padx=6, pady=(0, 6))

        # Elementanzahl
        top = tk.Frame(parent, bg=BG)
        top.pack(fill="x", padx=6, pady=4)
        tk.Label(top, text="Anzahl Elemente:", bg=BG, fg=FG,
                 font=("Helvetica", 11)).pack(side="left")
        sp = tk.Spinbox(top, from_=2, to=10, textvariable=self.n_var,
                        width=4, command=self._rebuild,
                        bg=CARD, fg=FG, buttonbackground=CARD,
                        font=("Helvetica", 11), relief="flat")
        sp.pack(side="left", padx=8)
        sp.bind("<Return>",    lambda _: self._rebuild())
        sp.bind("<FocusOut>",  lambda _: self._rebuild())

        # Scrollbarer Konfigurationsbereich
        self.cfg_canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical",
                            command=self.cfg_canvas.yview)
        self.cfg_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.cfg_canvas.pack(fill="both", expand=True, padx=6)
        self.cfg_frame = tk.Frame(self.cfg_canvas, bg=BG)
        self._cfg_win = self.cfg_canvas.create_window(
            (0, 0), window=self.cfg_frame, anchor="nw")
        self.cfg_frame.bind("<Configure>", self._on_cfg_resize)
        self.cfg_canvas.bind("<Configure>", self._on_canvas_resize)
        self.cfg_canvas.bind("<MouseWheel>",
                             lambda e: self.cfg_canvas.yview_scroll(
                                 int(-1*(e.delta/120)), "units"))

        # Solve-Button
        btn_frame = tk.Frame(parent, bg=BG)
        btn_frame.pack(fill="x", padx=6, pady=8)
        self.solve_btn = tk.Button(
            btn_frame, text="▶  Lösung berechnen",
            bg=ACCENT, fg="white", relief="flat",
            font=("Helvetica", 12, "bold"), padx=16, pady=8,
            activebackground="#c73050", cursor="hand2",
            command=self._start_solve)
        self.solve_btn.pack(fill="x")

        self.status_var = tk.StringVar(value="Bereit.")
        tk.Label(parent, textvariable=self.status_var, bg=BG, fg=FG_DIM,
                 font=("Helvetica", 9)).pack(anchor="w", padx=6)

    def _on_cfg_resize(self, _):
        self.cfg_canvas.configure(
            scrollregion=self.cfg_canvas.bbox("all"))

    def _on_canvas_resize(self, e):
        self.cfg_canvas.itemconfig(self._cfg_win, width=e.width)

    # ── Rechte Spalte (Lösung) ────────────────────────────────────────────────

    def _build_right(self, parent):
        tk.Label(parent, text="Lösung",
                 bg=BG, fg=ACCENT, font=("Helvetica", 12, "bold")
                 ).pack(anchor="w", padx=6, pady=(0, 6))

        # Visualisierungs-Canvas
        self.viz = tk.Canvas(parent, bg=PANEL, height=220,
                             highlightthickness=0)
        self.viz.pack(fill="x", padx=6, pady=4)
        self.viz.bind("<Configure>", lambda _: self._draw_state_cur())

        # Schrittinfo
        self.step_var = tk.StringVar(value="—")
        tk.Label(parent, textvariable=self.step_var,
                 bg=BG, fg=FG, font=("Helvetica", 11)).pack(pady=(4, 0))

        # Navigation
        nav = tk.Frame(parent, bg=BG)
        nav.pack(pady=6)
        for symbol, cmd in [("⏮", self._go_first), ("◀", self._go_prev),
                             ("▶", self._go_next),  ("⏭", self._go_last)]:
            tk.Button(nav, text=symbol, command=cmd,
                      bg=CARD, fg=FG, relief="flat",
                      font=("Helvetica", 14), width=3,
                      activebackground=ACCENT2, cursor="hand2"
                      ).pack(side="left", padx=3)
        self.bind("<Left>",  lambda _: self._go_prev())
        self.bind("<Right>", lambda _: self._go_next())
        self.bind("<Home>",  lambda _: self._go_first())
        self.bind("<End>",   lambda _: self._go_last())

        # Schrittliste
        tk.Label(parent, text="Schrittliste:", bg=BG, fg=FG_DIM,
                 font=("Helvetica", 10)).pack(anchor="w", padx=6)
        lf = tk.Frame(parent, bg=BG)
        lf.pack(fill="both", expand=True, padx=6, pady=4)
        self.lstbox = tk.Listbox(lf, bg=PANEL, fg=FG,
                                 selectbackground=ACCENT,
                                 font=("Courier", 10), relief="flat",
                                 activestyle="none")
        vsb2 = ttk.Scrollbar(lf, orient="vertical",
                             command=self.lstbox.yview)
        self.lstbox.configure(yscrollcommand=vsb2.set)
        vsb2.pack(side="right", fill="y")
        self.lstbox.pack(fill="both", expand=True)
        self.lstbox.bind("<<ListboxSelect>>", self._on_list_select)

    # ── Konfiguration neu aufbauen ────────────────────────────────────────────

    def _rebuild(self, *_):
        n = max(2, min(10, self.n_var.get()))
        self.n_var.set(n)

        # Alte Werte retten
        old = [{"holes": d["holes"].get(),
                "start": d["start"].get(),
                "target": d["target"].get()}
               for d in self.elem_cfg]

        self.elem_cfg = []
        for i in range(n):
            o = old[i] if i < len(old) else None
            h  = o["holes"]  if o else 7
            s  = o["start"]  if o else min(h, 4 + i % 3)
            t  = o["target"] if o else (h + 1) // 2
            self.elem_cfg.append({
                "holes":  tk.IntVar(value=h),
                "start":  tk.IntVar(value=s),
                "target": tk.IntVar(value=t),
            })

        new_coup: dict = {}
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                ov = self.coup_var.get((i, j))
                new_coup[(i, j)] = tk.StringVar(
                    value=(ov.get() if ov else "keine"))
        self.coup_var = new_coup

        self._draw_cfg()

    def _draw_cfg(self):
        for w in self.cfg_frame.winfo_children():
            w.destroy()
        n = len(self.elem_cfg)

        # ── Elemente ──────────────────────────────────────────────────────────
        sec = self._section(self.cfg_frame, "Elemente")
        hrow = tk.Frame(sec, bg=PANEL)
        hrow.pack(fill="x")
        for txt, w in [("Element", 9), ("Löcher", 8),
                        ("Start", 8), ("Ziel", 8)]:
            tk.Label(hrow, text=txt, bg=PANEL, fg=FG_DIM,
                     font=("Helvetica", 9), width=w).pack(side="left")
        for i, d in enumerate(self.elem_cfg):
            row = tk.Frame(sec, bg=PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"E{i+1}", bg=PANEL,
                     fg=ACCENT if i % 2 == 0 else ACCENT2,
                     font=("Helvetica", 10, "bold"), width=9).pack(side="left")
            for var, lo, hi in [(d["holes"], 3, 15),
                                  (d["start"],  1, 15),
                                  (d["target"], 1, 15)]:
                tk.Spinbox(row, from_=lo, to=hi, textvariable=var, width=5,
                           bg=CARD, fg=FG, buttonbackground=CARD,
                           font=("Helvetica", 10), relief="flat"
                           ).pack(side="left", padx=4)

        # ── Kopplungsregeln ───────────────────────────────────────────────────
        sec2 = self._section(self.cfg_frame,
                             "Kopplungsregeln  (Zeile bewegt → Spalte reagiert)")
        hrow2 = tk.Frame(sec2, bg=PANEL)
        hrow2.pack(fill="x")
        tk.Label(hrow2, text=" ", bg=PANEL, width=14).pack(side="left")
        for j in range(n):
            tk.Label(hrow2, text=f"E{j+1}", bg=PANEL, fg=FG_DIM,
                     font=("Helvetica", 9, "bold"), width=10).pack(side="left")

        for i in range(n):
            row = tk.Frame(sec2, bg=PANEL)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"E{i+1} bewegt:",
                     bg=PANEL, fg=ACCENT if i % 2 == 0 else ACCENT2,
                     font=("Helvetica", 10, "bold"),
                     width=14, anchor="w").pack(side="left")
            for j in range(n):
                if i == j:
                    tk.Label(row, text="  —  ", bg=PANEL, fg=FG_DIM,
                             width=10).pack(side="left")
                    continue
                var = self.coup_var[(i, j)]
                cb = ttk.Combobox(row, textvariable=var,
                                  values=["keine", "gleich", "entgegen"],
                                  width=9, state="readonly",
                                  font=("Helvetica", 9))
                cb.pack(side="left", padx=2)

        # Beispiel-Button
        bf = tk.Frame(sec2, bg=PANEL)
        bf.pack(fill="x", pady=(10, 2))
        tk.Button(bf, text="Beispiel laden (Original-Puzzle, 6 Elemente)",
                  bg=CARD, fg=FG, relief="flat",
                  font=("Helvetica", 9), cursor="hand2",
                  command=self._load_example).pack(side="left")

    def _section(self, parent, title: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=PANEL)
        outer.pack(fill="x", padx=4, pady=5)
        tk.Label(outer, text=title, bg=PANEL, fg=ACCENT2,
                 font=("Helvetica", 10, "bold")).pack(anchor="w",
                                                       padx=8, pady=(6, 2))
        inner = tk.Frame(outer, bg=PANEL)
        inner.pack(fill="x", padx=8, pady=(0, 8))
        return inner

    # ── Beispieldaten ─────────────────────────────────────────────────────────

    def _load_example(self):
        self.n_var.set(6)
        self._rebuild()
        starts  = [5, 5, 7, 5, 4, 2]
        targets = [4, 4, 4, 4, 4, 4]
        for i, d in enumerate(self.elem_cfg):
            d["holes"].set(7)
            d["start"].set(starts[i])
            d["target"].set(targets[i])
        rules = {
            (0, 5): "gleich",
            (1, 0): "gleich", (1, 2): "entgegen",
            (2, 0): "gleich", (2, 3): "entgegen", (2, 4): "entgegen",
            (3, 5): "gleich", (3, 1): "entgegen",
            (5, 3): "gleich", (5, 4): "entgegen",
        }
        for key, var in self.coup_var.items():
            var.set(rules.get(key, "keine"))

    # ── Solve ─────────────────────────────────────────────────────────────────

    def _start_solve(self):
        self.solve_btn.config(state="disabled", text="Berechne…")
        self.status_var.set("Suche läuft…")
        threading.Thread(target=self._solve_thread, daemon=True).start()

    def _solve_thread(self):
        try:
            n = len(self.elem_cfg)
            holes   = [d["holes"].get()    for d in self.elem_cfg]
            starts  = [d["start"].get() - 1 for d in self.elem_cfg]
            targets = [d["target"].get() - 1 for d in self.elem_cfg]

            # Validierung
            for i in range(n):
                if not (0 <= starts[i] < holes[i]):
                    self.after(0, lambda i=i: messagebox.showerror(
                        "Fehler",
                        f"E{i+1}: Startposition {starts[i]+1} "
                        f"außerhalb [1, {holes[i]}]"))
                    return
                if not (0 <= targets[i] < holes[i]):
                    self.after(0, lambda i=i: messagebox.showerror(
                        "Fehler",
                        f"E{i+1}: Zielposition {targets[i]+1} "
                        f"außerhalb [1, {holes[i]}]"))
                    return

            # Kopplungsregeln aufbauen
            coupling: dict = {}
            for (i, j), var in self.coup_var.items():
                v = var.get()
                if v == "gleich":
                    coupling[(i, j)] = "same"
                elif v == "entgegen":
                    coupling[(i, j)] = "opposite"
            self.effects = build_effects(n, coupling)

            # Zustandsraumgröße schätzen
            ss = 1
            for h in holes:
                ss *= h

            t0 = time.time()
            if ss <= 1_200_000:
                self.after(0, lambda: self.status_var.set(
                    f"BFS läuft … Zustandsraum ≤ {ss:,}"))
                sol = solve_bfs(starts, targets, self.effects, holes)
                if sol is None:
                    self.after(0, lambda: self.status_var.set(
                        "BFS: kein Ergebnis → A* …"))
                    sol = solve_astar(starts, targets, self.effects, holes)
            else:
                self.after(0, lambda: self.status_var.set(
                    f"A* läuft … Zustandsraum ≈ {ss:,}"))
                sol = solve_astar(starts, targets, self.effects, holes)
            elapsed = time.time() - t0

            if sol is None:
                self.after(0, lambda: (
                    self.status_var.set("Keine Lösung gefunden."),
                    messagebox.showwarning(
                        "Kein Ergebnis",
                        "Keine Lösung gefunden.\n"
                        "Mögliche Ursachen: Puzzle unlösbar, "
                        "Zustandsraum zu groß, oder Suchtiefe überschritten.")))
                return

            # Zustände für alle Schritte berechnen
            state = tuple(starts)
            states = [state]
            for elem, d in sol:
                state = apply_move(state, elem, d, self.effects, holes)
                states.append(state)

            self.solution    = sol
            self.step_states = states
            self.holes_cfg   = holes
            self.targets     = targets
            self.cur_step    = 0

            self.after(0, lambda: self._display_solution(elapsed))

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.after(0, lambda: messagebox.showerror("Fehler", f"{e}\n\n{tb}"))
        finally:
            self.after(0, lambda: self.solve_btn.config(
                state="normal", text="▶  Lösung berechnen"))

    # ── Ergebnis anzeigen ─────────────────────────────────────────────────────

    def _display_solution(self, elapsed: float):
        total = len(self.solution)
        alg   = "BFS" if total <= 200 else "A*"
        self.status_var.set(
            f"✓  {total} Schritte  |  {elapsed:.2f} s  |  {alg}")

        dir_lbl = {+1: "rechts →", -1: "← links"}

        self.lstbox.delete(0, "end")
        self.lstbox.insert("end",
            f"  Start   {self._state_str(self.step_states[0])}")
        for i, (elem, d) in enumerate(self.solution):
            s = self.step_states[i + 1]
            self.lstbox.insert(
                "end",
                f"  {i+1:3d}.  E{elem+1} {dir_lbl[d]:<12}"
                f"  {self._state_str(s)}")

        self._show_step(0)

    def _state_str(self, state: tuple) -> str:
        parts = []
        for i, pos in enumerate(state):
            h = self.holes_cfg[i]
            row = ["o"] * h
            row[pos] = "X"
            parts.append("".join(row))
        return "  ".join(parts)

    # ── Schrittanzeige ────────────────────────────────────────────────────────

    def _show_step(self, idx: int):
        if not self.step_states:
            return
        idx = max(0, min(idx, len(self.solution)))
        self.cur_step = idx
        total = len(self.solution)

        if idx == 0:
            self.step_var.set("Ausgangszustand")
        else:
            elem, d = self.solution[idx - 1]
            dr = "rechts →" if d == +1 else "← links"
            self.step_var.set(f"Schritt {idx} / {total}   —   E{elem+1} nach {dr}")

        self.lstbox.selection_clear(0, "end")
        self.lstbox.selection_set(idx)
        self.lstbox.see(idx)
        self._draw_state_cur()

    def _draw_state_cur(self):
        if not self.step_states:
            return
        self._draw_state(self.step_states[self.cur_step])

    def _draw_state(self, state: tuple):
        cv = self.viz
        cv.delete("all")
        cv.update_idletasks()
        W  = cv.winfo_width() or 600
        n  = len(state)
        hl = self.holes_cfg
        tg = self.targets

        ROW_H   = 34
        PAD_Y   = 14
        PAD_X   = 10
        LBL_W   = 46          # Platz für "E10 :"
        MAX_HOLE_W = 26

        max_h   = max(hl) if hl else 7
        hole_w  = min(MAX_HOLE_W, (W - PAD_X * 2 - LBL_W - 50) // max_h)
        hole_gap = hole_w + 3
        r       = hole_w // 2

        total_h = PAD_Y * 2 + n * ROW_H
        cv.config(height=max(180, total_h))

        for i in range(n):
            y    = PAD_Y + i * ROW_H + ROW_H // 2
            pos  = state[i]
            h    = hl[i]
            tgt  = tg[i]
            done = (pos == tgt)

            lbl_color = PIN_OK if done else (ACCENT if i % 2 == 0 else ACCENT2)
            cv.create_text(PAD_X + 4, y,
                           text=f"E{i+1}:", fill=lbl_color,
                           font=("Helvetica", 10, "bold"), anchor="w")

            ox = PAD_X + LBL_W
            for j in range(h):
                cx = ox + j * hole_gap
                is_pin    = (j == pos)
                is_target = (j == tgt)

                if is_pin:
                    fill  = PIN_OK if done else PIN_WRONG
                    out   = fill
                    ri    = r
                elif is_target:
                    fill  = PANEL
                    out   = TARGET_OUT
                    ri    = r - 1
                else:
                    fill  = HOLE_FILL
                    out   = HOLE_FILL
                    ri    = r - 2

                cv.create_oval(cx - ri, y - ri, cx + ri, y + ri,
                               fill=fill, outline=out, width=2 if is_target and not is_pin else 1)

            # Positionstext
            cv.create_text(ox + h * hole_gap + 8, y,
                           text=f"{pos+1}/{h}",
                           fill=FG_DIM, font=("Helvetica", 9), anchor="w")

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_first(self): self._show_step(0)
    def _go_last(self):  self._show_step(len(self.solution) if self.solution else 0)
    def _go_prev(self):  self._show_step(self.cur_step - 1)
    def _go_next(self):  self._show_step(self.cur_step + 1)

    def _on_list_select(self, _):
        sel = self.lstbox.curselection()
        if sel:
            self._show_step(sel[0])


# ── Einstiegspunkt ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
