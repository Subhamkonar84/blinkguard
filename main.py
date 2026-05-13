import tkinter as tk
from tkinter import messagebox  # noqa: F401 — needed for tk.messagebox
import threading
import queue
import sys
from blink_detector import BlinkDetector


def _get_screen_rects() -> list[tuple[int, int, int, int]]:
    """Return (x, y, w, h) for every connected display in tkinter coords."""
    try:
        from AppKit import NSScreen
        main_h = NSScreen.mainScreen().frame().size.height
        rects = []
        for s in NSScreen.screens():
            f = s.frame()
            x = int(f.origin.x)
            # AppKit origin is bottom-left; tkinter/Quartz origin is top-left
            y = int(main_h - f.origin.y - f.size.height)
            w = int(f.size.width)
            h = int(f.size.height)
            rects.append((x, y, w, h))
        return rects
    except Exception:
        # Fallback: single primary screen
        tmp = tk.Tk()
        tmp.withdraw()
        w, h = tmp.winfo_screenwidth(), tmp.winfo_screenheight()
        tmp.destroy()
        return [(0, 0, w, h)]


class BlinkGuardApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()          # invisible root window
        self.root.title("BlinkGuard")

        self.q      = queue.Queue()
        self.locked = False

        self.screen_rects = _get_screen_rects()

        self._setup_hud()
        self._setup_overlays()

        # Start the camera / detection thread
        self.detector = BlinkDetector(self.q)
        def _run_safe():
            try:
                self.detector.run()
            except Exception:
                import traceback
                self.q.put({'type': 'error', 'msg': traceback.format_exc()})
        threading.Thread(target=_run_safe, daemon=True).start()

        self.root.after(50, self._poll)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self.root.mainloop()

    # ------------------------------------------------------------------
    # HUD — small dark widget, top-right of primary screen, always on top
    # ------------------------------------------------------------------
    def _setup_hud(self):
        sx, sy, sw, _ = self.screen_rects[0]
        hud = tk.Toplevel(self.root)
        hud.overrideredirect(True)
        hud.attributes('-topmost', True)
        hud.attributes('-alpha', 0.88)
        hud.configure(bg='#0d0d0d')

        hud.geometry(f"165x82+{sx + sw - 180}+{sy + 20}")

        tk.Label(hud, text="BLINK GUARD",
                 fg='#3a3a3a', bg='#0d0d0d',
                 font=('Helvetica', 9, 'bold')).pack(pady=(9, 0))

        self.hud_count = tk.Label(hud, text="0 / min",
                                   fg='#ffffff', bg='#0d0d0d',
                                   font=('Helvetica', 20, 'bold'))
        self.hud_count.pack()

        self.hud_timer = tk.Label(hud, text="60s left",
                                   fg='#3a3a3a', bg='#0d0d0d',
                                   font=('Helvetica', 11))
        self.hud_timer.pack()

        self.hud = hud

    # ------------------------------------------------------------------
    # Overlays — one per screen, fullscreen white, shows timer + dots
    # ------------------------------------------------------------------
    def _setup_overlays(self):
        self.overlays: list[tk.Toplevel] = []
        self.overlay_dots: list[list[tk.Label]] = []
        self.overlay_timers: list[tk.Label] = []

        for sx, sy, sw, sh in self.screen_rects:
            ov = tk.Toplevel(self.root)
            ov.configure(bg='white')
            ov.overrideredirect(True)           # no title bar; lets us place on any screen
            ov.attributes('-topmost', True)
            ov.geometry(f"{sw}x{sh}+{sx}+{sy}")
            ov.protocol("WM_DELETE_WINDOW", lambda: None)
            ov.bind('<Command-w>', lambda e: 'break')

            # Centre frame
            frame = tk.Frame(ov, bg='white')
            frame.place(relx=0.5, rely=0.5, anchor='center')

            tk.Label(frame, text="Take a blink break",
                     bg='white', fg='#c0c0c0',
                     font=('Helvetica', 36, 'bold')).pack()

            tk.Label(frame, text="Blink 3 times rapidly to unlock",
                     bg='white', fg='#d8d8d8',
                     font=('Helvetica', 20)).pack(pady=(14, 0))

            timer_lbl = tk.Label(frame, text="60s until next check",
                                  bg='white', fg='#c0c0c0',
                                  font=('Helvetica', 16))
            timer_lbl.pack(pady=(10, 0))
            self.overlay_timers.append(timer_lbl)

            # Dot indicators — filled = blink registered
            dots: list[tk.Label] = []
            dot_row = tk.Frame(frame, bg='white')
            dot_row.pack(pady=24)
            for _ in range(3):
                lbl = tk.Label(dot_row, text="○",
                               bg='white', fg='#d8d8d8',
                               font=('Helvetica', 42))
                lbl.pack(side='left', padx=10)
                dots.append(lbl)
            self.overlay_dots.append(dots)

            ov.withdraw()
            self.overlays.append(ov)

    # ------------------------------------------------------------------
    # Message pump (runs on main/GUI thread via after())
    # ------------------------------------------------------------------
    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                self._handle(msg)
        except queue.Empty:
            pass
        self.root.after(50, self._poll)

    def _handle(self, msg: dict):
        kind = msg['type']

        if kind == 'update':
            count     = msg['count']
            remaining = msg['remaining']
            rapid     = msg['rapid']

            # HUD colour: green if on track, amber if lagging, red if low
            if count >= 20:
                color = '#00e676'
            elif count >= 10:
                color = '#ffab00'
            else:
                color = '#ff3d00'

            self.hud_count.config(text=f"{count} / min", fg=color)
            self.hud_timer.config(text=f"{remaining}s left")

            # Timer on every overlay screen
            for lbl in self.overlay_timers:
                lbl.config(text=f"{remaining}s until next check")

            # Update unlock dots when locked
            if self.locked:
                for dots in self.overlay_dots:
                    for i, lbl in enumerate(dots):
                        filled = i < rapid
                        lbl.config(
                            text='●' if filled else '○',
                            fg='#333333' if filled else '#d8d8d8',
                        )

        elif kind == 'lock':
            self.locked = True
            # Reset dots on all screens
            for dots in self.overlay_dots:
                for lbl in dots:
                    lbl.config(text='○', fg='#d8d8d8')
            self.hud.withdraw()
            for ov in self.overlays:
                ov.deiconify()
                ov.lift()
            self.overlays[0].focus_force()

        elif kind == 'unlock':
            self.locked = False
            for ov in self.overlays:
                ov.withdraw()
            self.hud.deiconify()

        elif kind == 'error':
            tk.messagebox.showerror("BlinkGuard — startup error", msg['msg'])
            self._quit()

    # ------------------------------------------------------------------
    def _quit(self):
        self.detector.stop()
        self.root.destroy()
        sys.exit(0)


if __name__ == '__main__':
    BlinkGuardApp()
