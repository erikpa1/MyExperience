import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import json
import os
import datetime
import queue

from twin_event import PartPassed, PartFailed

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "broker_ip": "192.168.50.140",
    "port": 2883,
    "topic": "#",
    "output_file": "passed.log",
    "username": "ft",
    "password": "fischertechnik",
    "qos": 0,
}

COLORS = {
    # Backgrounds
    "bg": "#F0F4F8",
    "panel": "#FFFFFF",
    "panel2": "#F7F9FC",
    "input_bg": "#FFFFFF",
    "header_bg": "#1E3A5F",

    # Borders
    "border": "#D0D9E4",
    "border_dark": "#B0BEC5",

    # Text
    "text": "#1A2332",
    "text_dim": "#5A6A7E",
    "text_inv": "#FFFFFF",

    # Accents / status
    "accent": "#1A6FBF",
    "accent_hov": "#155399",
    "accent2": "#1B7E4A",
    "warn": "#B45309",
    "error": "#C0392B",
    "connected": "#1B7E4A",
    "disconn": "#C0392B",

    # Log row colours
    "log_ts": "#7A8FA6",
    "log_topic": "#1A6FBF",
    "log_payload": "#1A2332",
    "log_ok": "#1B7E4A",
    "log_warn": "#B45309",
    "log_error": "#C0392B",

    # Section header strip
    "sec_bg": "#EAF0F8",
    "sec_fg": "#1A6FBF",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            return {**DEFAULT_CONFIG, **data}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ── App ───────────────────────────────────────────────────────────────────────

class MQTTLoggerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MQTT Stream Logger")
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(920, 640)

        self.cfg = load_config()
        self.client = None
        self.connected = False
        self.log_file = None
        self.msg_count = 0
        self.msg_queue: queue.Queue = queue.Queue()

        self._build_styles()
        self._build_ui()
        self._poll_queue()

    # ── ttk Styles ────────────────────────────────────────────────────────────

    def _build_styles(self):
        st = ttk.Style()
        st.theme_use("clam")

        st.configure("TFrame", background=COLORS["bg"])
        st.configure("White.TFrame", background=COLORS["panel"])

        st.configure("TLabel",
                     background=COLORS["bg"],
                     foreground=COLORS["text"],
                     font=("Segoe UI", 10))
        st.configure("W.TLabel",
                     background=COLORS["panel"],
                     foreground=COLORS["text"],
                     font=("Segoe UI", 10))
        st.configure("WDim.TLabel",
                     background=COLORS["panel"],
                     foreground=COLORS["text_dim"],
                     font=("Segoe UI", 9))

        st.configure("Connect.TButton",
                     background=COLORS["accent"],
                     foreground=COLORS["text_inv"],
                     font=("Segoe UI", 10, "bold"),
                     borderwidth=0, focusthickness=0, padding=(14, 7))
        st.map("Connect.TButton",
               background=[("active", COLORS["accent_hov"]),
                           ("disabled", COLORS["border_dark"])],
               foreground=[("disabled", COLORS["text_dim"])])

        st.configure("Disconnect.TButton",
                     background=COLORS["error"],
                     foreground=COLORS["text_inv"],
                     font=("Segoe UI", 10, "bold"),
                     borderwidth=0, focusthickness=0, padding=(14, 7))
        st.map("Disconnect.TButton",
               background=[("active", "#A93226"),
                           ("disabled", COLORS["border_dark"])],
               foreground=[("disabled", COLORS["text_dim"])])

        st.configure("Save.TButton",
                     background=COLORS["border"],
                     foreground=COLORS["text"],
                     font=("Segoe UI", 9),
                     borderwidth=0, focusthickness=0, padding=(10, 5))
        st.map("Save.TButton",
               background=[("active", COLORS["border_dark"])])

        st.configure("TEntry",
                     fieldbackground=COLORS["input_bg"],
                     foreground=COLORS["text"],
                     insertcolor=COLORS["text"],
                     bordercolor=COLORS["border_dark"],
                     font=("Segoe UI", 10))
        st.configure("TCombobox",
                     fieldbackground=COLORS["input_bg"],
                     foreground=COLORS["text"],
                     background=COLORS["input_bg"],
                     selectbackground=COLORS["accent"],
                     font=("Segoe UI", 10))

    # ── UI layout ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=COLORS["header_bg"], height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="  MQTT  Stream Logger",
                 bg=COLORS["header_bg"], fg=COLORS["text_inv"],
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=16, pady=10)

        self.status_dot = tk.Label(hdr, text="●",
                                   bg=COLORS["header_bg"], fg="#F07070",
                                   font=("Segoe UI", 15))
        self.status_dot.pack(side="right", padx=(0, 16), pady=10)

        self.status_lbl = tk.Label(hdr, text="DISCONNECTED",
                                   bg=COLORS["header_bg"], fg="#EFC3C0",
                                   font=("Segoe UI", 9, "bold"))
        self.status_lbl.pack(side="right", padx=(0, 2), pady=10)

        # ── Body ──────────────────────────────────────────────────────────────
        body = tk.Frame(self.root, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # ── Left config panel ─────────────────────────────────────────────────
        left = tk.Frame(body, bg=COLORS["panel"],
                        highlightbackground=COLORS["border_dark"],
                        highlightthickness=1, width=292)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        self._section(left, "CONNECTION")
        self._field(left, "Broker IP", "ip_var", self.cfg["broker_ip"])
        self._field(left, "Port", "port_var", str(self.cfg["port"]))
        self._field(left, "Topic", "topic_var", self.cfg["topic"])

        self._section(left, "AUTHENTICATION")
        self._field(left, "Username", "user_var", self.cfg["username"])
        self._field(left, "Password", "pass_var", self.cfg["password"], show="•")

        tk.Label(left, text="  Default: ft / fischertechnik",
                 bg=COLORS["panel"], fg=COLORS["text_dim"],
                 font=("Segoe UI", 8, "italic")).pack(anchor="w", padx=12, pady=(0, 6))

        self._section(left, "OUTPUT FILE")
        file_row = tk.Frame(left, bg=COLORS["panel"])
        file_row.pack(fill="x", padx=12, pady=(0, 6))

        self.file_var = tk.StringVar(value=self.cfg["output_file"])
        fe = tk.Entry(file_row,
                      textvariable=self.file_var,
                      bg=COLORS["input_bg"], fg=COLORS["text"],
                      insertbackground=COLORS["text"],
                      relief="solid", bd=1,
                      font=("Segoe UI", 9))
        fe.pack(side="left", fill="x", expand=True)

        tk.Button(file_row, text="…",
                  bg=COLORS["border"], fg=COLORS["text"],
                  activebackground=COLORS["accent"],
                  activeforeground=COLORS["text_inv"],
                  font=("Segoe UI", 10), relief="flat", bd=0,
                  padx=6, pady=2,
                  command=self._browse_file,
                  cursor="hand2").pack(side="left", padx=(4, 0))

        self._section(left, "QOS LEVEL")
        qos_row = tk.Frame(left, bg=COLORS["panel"])
        qos_row.pack(fill="x", padx=12, pady=(0, 8))
        self.qos_var = tk.StringVar(value=str(self.cfg["qos"]))
        ttk.Combobox(qos_row, textvariable=self.qos_var,
                     values=["0", "1", "2"], width=8,
                     state="readonly").pack(side="left")

        tk.Frame(left, bg=COLORS["panel"]).pack(fill="both", expand=True)

        btn_frame = tk.Frame(left, bg=COLORS["panel"])
        btn_frame.pack(fill="x", padx=12, pady=12)

        self.connect_btn = ttk.Button(btn_frame,
                                      text="▶   Connect",
                                      style="Connect.TButton",
                                      command=self._toggle_connection)
        self.connect_btn.pack(fill="x", pady=(0, 6))

        ttk.Button(btn_frame, text="💾  Save Config",
                   style="Save.TButton",
                   command=self._save_config_ui).pack(fill="x")

        # ── Right log panel ───────────────────────────────────────────────────
        right = tk.Frame(body, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True)

        log_toolbar = tk.Frame(right, bg=COLORS["panel"],
                               highlightbackground=COLORS["border_dark"],
                               highlightthickness=1)
        log_toolbar.pack(fill="x", pady=(0, 6))

        tk.Label(log_toolbar, text="  Live Stream",
                 bg=COLORS["panel"], fg=COLORS["accent"],
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=4, pady=6)

        self.count_lbl = tk.Label(log_toolbar, text="0 messages",
                                  bg=COLORS["panel"], fg=COLORS["text_dim"],
                                  font=("Segoe UI", 9))
        self.count_lbl.pack(side="left", padx=8)

        tk.Button(log_toolbar, text="⌫  Clear",
                  bg=COLORS["panel"], fg=COLORS["text_dim"],
                  activebackground=COLORS["bg"],
                  activeforeground=COLORS["text"],
                  font=("Segoe UI", 9), relief="flat", bd=0,
                  padx=8, pady=4,
                  command=self._clear_log,
                  cursor="hand2").pack(side="right", padx=8, pady=4)

        self.auto_scroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(log_toolbar, text="Auto-scroll",
                       variable=self.auto_scroll_var,
                       bg=COLORS["panel"], fg=COLORS["text_dim"],
                       selectcolor=COLORS["panel"],
                       activebackground=COLORS["panel"],
                       font=("Segoe UI", 9),
                       relief="flat", bd=0).pack(side="right", padx=(0, 2))

        log_wrap = tk.Frame(right, bg=COLORS["panel"],
                            highlightbackground=COLORS["border_dark"],
                            highlightthickness=1)
        log_wrap.pack(fill="both", expand=True)

        self.log_box = scrolledtext.ScrolledText(
            log_wrap,
            bg=COLORS["panel2"],
            fg=COLORS["text"],
            font=("Consolas", 9),
            relief="flat", bd=0,
            insertbackground=COLORS["text"],
            state="disabled",
            wrap="none",
            padx=8, pady=6,
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text_inv"],
        )
        self.log_box.pack(fill="both", expand=True)

        self.log_box.tag_config("ts", foreground=COLORS["log_ts"])
        self.log_box.tag_config("topic", foreground=COLORS["log_topic"],
                                font=("Consolas", 9, "bold"))
        self.log_box.tag_config("payload", foreground=COLORS["log_payload"])
        self.log_box.tag_config("system", foreground=COLORS["log_warn"])
        self.log_box.tag_config("error", foreground=COLORS["log_error"])
        self.log_box.tag_config("ok", foreground=COLORS["log_ok"])

        # ── Status bar ────────────────────────────────────────────────────────
        sbar = tk.Frame(self.root, bg=COLORS["border"],
                        highlightbackground=COLORS["border_dark"],
                        highlightthickness=1, height=26)
        sbar.pack(fill="x", side="bottom")
        sbar.pack_propagate(False)

        self.bar_lbl = tk.Label(sbar, text="Ready.",
                                bg=COLORS["border"], fg=COLORS["text_dim"],
                                font=("Segoe UI", 9))
        self.bar_lbl.pack(side="left", padx=10)

        self.file_lbl = tk.Label(sbar, text="",
                                 bg=COLORS["border"], fg=COLORS["text_dim"],
                                 font=("Segoe UI", 9))
        self.file_lbl.pack(side="right", padx=10)

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _section(self, parent, title: str):
        sec = tk.Frame(parent, bg=COLORS["sec_bg"])
        sec.pack(fill="x", pady=(8, 0))
        tk.Label(sec, text=f"  {title}",
                 bg=COLORS["sec_bg"], fg=COLORS["sec_fg"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=4, pady=3)

    def _field(self, parent, label: str, var_name: str, default: str,
               show=None):
        tk.Label(parent, text=label,
                 bg=COLORS["panel"], fg=COLORS["text_dim"],
                 font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(6, 1))

        var = tk.StringVar(value=default)
        setattr(self, var_name, var)

        kw = dict(textvariable=var,
                  bg=COLORS["input_bg"], fg=COLORS["text"],
                  insertbackground=COLORS["text"],
                  relief="solid", bd=1,
                  font=("Segoe UI", 10))
        if show:
            kw["show"] = show

        entry = tk.Entry(parent, **kw)
        entry.pack(fill="x", padx=12, pady=(0, 2))

        entry.bind("<FocusIn>", lambda e, w=entry: w.config(
            highlightthickness=2,
            highlightbackground=COLORS["accent"],
            highlightcolor=COLORS["accent"]))
        entry.bind("<FocusOut>", lambda e, w=entry: w.config(
            highlightthickness=0))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _browse_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"),
                       ("Text files", "*.txt"),
                       ("All files", "*.*")],
            title="Choose output file",
        )
        if path:
            self.file_var.set(path)

    def _save_config_ui(self):
        save_config(self._gather_config())
        self._set_bar("✔  Config saved to config.json")

    def _gather_config(self) -> dict:
        try:
            port = int(self.port_var.get())
        except ValueError:
            port = DEFAULT_CONFIG["port"]
        try:
            qos = int(self.qos_var.get())
        except ValueError:
            qos = 0
        return {
            "broker_ip": self.ip_var.get().strip(),
            "port": port,
            "topic": self.topic_var.get().strip() or "#",
            "output_file": self.file_var.get().strip() or "failed.log",
            "username": self.user_var.get(),
            "password": self.pass_var.get(),
            "qos": qos,
        }

    def _toggle_connection(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        if mqtt is None:
            messagebox.showerror(
                "Missing dependency",
                "paho-mqtt is not installed.\n\nRun:  pip install paho-mqtt")
            return

        cfg = self._gather_config()
        self.cfg = cfg
        save_config(cfg)

        try:
            self.log_file = open(cfg["output_file"], "a", encoding="utf-8")
        except OSError as e:
            messagebox.showerror("File error", str(e))
            return

        self.client = mqtt.Client(client_id="mqtt_logger_ui", clean_session=True)

        if cfg["username"]:
            self.client.username_pw_set(cfg["username"], cfg["password"])

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self.connect_btn.config(state="disabled")
        self._set_bar(f"Connecting to {cfg['broker_ip']}:{cfg['port']} …")

        threading.Thread(target=self._connect_thread,
                         args=(cfg,), daemon=True).start()

    def _connect_thread(self, cfg):
        try:
            self.client.connect(cfg["broker_ip"], cfg["port"], keepalive=60)
            self.client.loop_start()
        except Exception as e:
            self.msg_queue.put(("error", f"Connection failed: {e}"))
            self.msg_queue.put(("state", "disconnected"))

    def _disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self.msg_count = 0
        self.count_lbl.config(text="0 messages")

    # ── MQTT callbacks (background thread) ────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            topic = self.cfg["topic"]
            qos = self.cfg["qos"]
            client.subscribe(topic, qos=qos)
            self.msg_queue.put(("ok", f"Connected — subscribed to '{topic}' (QoS {qos})"))
            self.msg_queue.put(("state", "connected"))
        else:
            codes = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username/password",
                5: "Not authorised",
            }
            self.msg_queue.put(("error",
                                f"Connect refused: {codes.get(rc, f'code {rc}')}"))
            self.msg_queue.put(("state", "disconnected"))

    def _on_disconnect(self, client, userdata, rc):
        self.msg_queue.put(("system",
                            "Disconnected" if rc == 0
                            else f"Unexpected disconnect (rc={rc})"))
        self.msg_queue.put(("state", "disconnected"))

    def _on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
        except Exception:
            payload = repr(msg.payload)
        self.msg_queue.put(("message", msg.topic, payload))

    # ── Queue consumer (main thread) ──────────────────────────────────────────

    def _poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                kind = item[0]
                if kind == "state":
                    self._apply_state(item[1])
                elif kind == "message":
                    _, topic, payload = item
                    self._append_message(topic, payload)
                elif kind in ("ok", "system", "error"):
                    self._append_system(item[1], kind)
        except queue.Empty:
            pass
        self.root.after(50, self._poll_queue)

    def _apply_state(self, state: str):
        if state == "connected":
            self.connected = True
            self.status_dot.config(fg="#5DDE8A")
            self.status_lbl.config(fg="#A8F0C0", text="CONNECTED")
            self.connect_btn.config(text="■   Disconnect",
                                    style="Disconnect.TButton",
                                    state="normal")
            self.file_lbl.config(text=f"→  {self.cfg['output_file']}")
        else:
            self.connected = False
            self.status_dot.config(fg="#F07070")
            self.status_lbl.config(fg="#EFC3C0", text="DISCONNECTED")
            self.connect_btn.config(text="▶   Connect",
                                    style="Connect.TButton",
                                    state="normal")
            self.file_lbl.config(text="")

    def _append_message(self, topic: str, payload: str):
        now = ts()
        self.msg_count += 1
        self.count_lbl.config(text=f"{self.msg_count} messages")

        # --- LOGIC TO CATCH part_pass_fail ---
        try:
            data = json.loads(payload)
            inner_payload = data.get("payload", {})

            if inner_payload:
                # Colors that indicate a PASS result
                PASS_COLORS = ["red", "white", "blue"]

                def is_active(val):
                    """Handle both boolean True and string 'true'"""
                    if isinstance(val, bool):
                        return val
                    if isinstance(val, str):
                        return val.lower() == "true"
                    return False

                # Check each pass color — both "active" AND "on" must be true
                detected_color = None
                for color in PASS_COLORS:
                    if color in inner_payload:
                        color_data = inner_payload[color]
                        if is_active(color_data.get("active")) and is_active(color_data.get("on")):
                            detected_color = color.upper()
                            break

                # Check fail state
                fail_data = inner_payload.get("fail", {})
                is_fail = is_active(fail_data.get("active")) or is_active(fail_data.get("on"))

                if detected_color:
                    print(inner_payload)
                    PartPassed(detected_color)
                elif is_fail:
                    PartFailed()

        except Exception:
            # If it's not JSON or parsing fails, just ignore and continue logging
            pass
        # --------------------------------------

        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{now}]  ", "ts")
        self.log_box.insert("end", topic, "topic")
        self.log_box.insert("end", "  →  ", "ts")
        self.log_box.insert("end", payload + "\n", "payload")
        self.log_box.configure(state="disabled")

        if self.auto_scroll_var.get():
            self.log_box.see("end")

        if self.log_file:
            try:
                self.log_file.write(f"[{now}] {topic}  {payload}\n")
                self.log_file.flush()
            except OSError:
                pass

        self._set_bar(f"Last:  {topic}")

    def _append_system(self, text: str, tag: str = "system"):
        now = ts()
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{now}]  ", "ts")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.configure(state="disabled")
        if self.auto_scroll_var.get():
            self.log_box.see("end")
        self._set_bar(text)

    def _set_bar(self, text: str):
        self.bar_lbl.config(text=text)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def on_close(self):
        self._disconnect()
        self.root.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = MQTTLoggerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
