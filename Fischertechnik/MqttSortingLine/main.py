import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import json
import os
import datetime
import queue

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

# ── Config ────────────────────────────────────────────────────────────────────
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "broker_ip": "192.168.1.1",
    "port": 2883,
    "topic": "#",
    "output_file": "mqtt_stream.log",
    "username": "",
    "password": "",
    "qos": 0,
}

COLORS = {
    "bg":        "#0d1117",
    "panel":     "#161b22",
    "border":    "#30363d",
    "accent":    "#58a6ff",
    "accent2":   "#3fb950",
    "warn":      "#d29922",
    "error":     "#f85149",
    "text":      "#e6edf3",
    "text_dim":  "#8b949e",
    "connected": "#3fb950",
    "disconn":   "#f85149",
    "input_bg":  "#21262d",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            cfg = {**DEFAULT_CONFIG, **data}
            return cfg
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# ── App ───────────────────────────────────────────────────────────────────────

class MQTTLoggerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MQTT Stream Logger")
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(860, 620)

        self.cfg = load_config()
        self.client = None
        self.connected = False
        self.log_file = None
        self.msg_count = 0
        self.msg_queue: queue.Queue = queue.Queue()

        self._build_styles()
        self._build_ui()
        self._poll_queue()

    # ── Styles ────────────────────────────────────────────────────────────────

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame",       background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"],
                        relief="flat")

        style.configure("TLabel",       background=COLORS["bg"],
                        foreground=COLORS["text"],
                        font=("Consolas", 10))
        style.configure("Panel.TLabel", background=COLORS["panel"],
                        foreground=COLORS["text"],
                        font=("Consolas", 10))
        style.configure("Head.TLabel",  background=COLORS["panel"],
                        foreground=COLORS["accent"],
                        font=("Consolas", 11, "bold"))
        style.configure("Dim.TLabel",   background=COLORS["panel"],
                        foreground=COLORS["text_dim"],
                        font=("Consolas", 9))
        style.configure("Stat.TLabel",  background=COLORS["bg"],
                        foreground=COLORS["text_dim"],
                        font=("Consolas", 9))

        style.configure("Accent.TButton",
                        background=COLORS["accent"], foreground="#0d1117",
                        font=("Consolas", 10, "bold"),
                        borderwidth=0, focusthickness=0, padding=(12, 6))
        style.map("Accent.TButton",
                  background=[("active", "#79c0ff"), ("disabled", "#30363d")],
                  foreground=[("disabled", COLORS["text_dim"])])

        style.configure("Danger.TButton",
                        background=COLORS["error"], foreground="#0d1117",
                        font=("Consolas", 10, "bold"),
                        borderwidth=0, focusthickness=0, padding=(12, 6))
        style.map("Danger.TButton",
                  background=[("active", "#ff7b72"), ("disabled", "#30363d")])

        style.configure("TEntry",
                        fieldbackground=COLORS["input_bg"],
                        foreground=COLORS["text"],
                        insertcolor=COLORS["text"],
                        bordercolor=COLORS["border"],
                        font=("Consolas", 10))

        style.configure("TCombobox",
                        fieldbackground=COLORS["input_bg"],
                        foreground=COLORS["text"],
                        background=COLORS["input_bg"],
                        selectbackground=COLORS["accent"],
                        font=("Consolas", 10))

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self.root, bg=COLORS["panel"], height=48)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        tk.Label(title_bar, text="⬡  MQTT STREAM LOGGER",
                 bg=COLORS["panel"], fg=COLORS["accent"],
                 font=("Consolas", 13, "bold")).pack(side="left", padx=18, pady=12)

        self.status_dot = tk.Label(title_bar, text="●",
                                   bg=COLORS["panel"], fg=COLORS["disconn"],
                                   font=("Consolas", 14))
        self.status_dot.pack(side="right", padx=6, pady=12)

        self.status_lbl = tk.Label(title_bar, text="DISCONNECTED",
                                   bg=COLORS["panel"], fg=COLORS["disconn"],
                                   font=("Consolas", 10, "bold"))
        self.status_lbl.pack(side="right", padx=(0, 4), pady=12)

        # Main area
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        # ── Left panel (config) ──
        left = tk.Frame(main, bg=COLORS["panel"],
                        highlightbackground=COLORS["border"],
                        highlightthickness=1, width=280)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        self._section(left, "CONNECTION")
        self._field(left, "Broker IP", "ip_var", self.cfg["broker_ip"])
        self._field(left, "Port",      "port_var", str(self.cfg["port"]))
        self._field(left, "Topic",     "topic_var", self.cfg["topic"])

        self._section(left, "AUTHENTICATION")
        self._field(left, "Username", "user_var",  self.cfg["username"])
        self._field(left, "Password", "pass_var",  self.cfg["password"],
                    show="•")

        self._section(left, "OUTPUT FILE")
        file_row = tk.Frame(left, bg=COLORS["panel"])
        file_row.pack(fill="x", padx=12, pady=(0, 4))

        self.file_var = tk.StringVar(value=self.cfg["output_file"])
        file_entry = tk.Entry(file_row, textvariable=self.file_var,
                              bg=COLORS["input_bg"], fg=COLORS["text"],
                              insertbackground=COLORS["text"],
                              font=("Consolas", 9),
                              relief="flat", bd=4)
        file_entry.pack(side="left", fill="x", expand=True)

        tk.Button(file_row, text="…",
                  bg=COLORS["border"], fg=COLORS["text"],
                  activebackground=COLORS["accent"], activeforeground="#0d1117",
                  font=("Consolas", 10), relief="flat", bd=0,
                  command=self._browse_file,
                  cursor="hand2").pack(side="left", padx=(4, 0))

        self._section(left, "QOS")
        qos_row = tk.Frame(left, bg=COLORS["panel"])
        qos_row.pack(fill="x", padx=12, pady=(0, 8))
        self.qos_var = tk.StringVar(value=str(self.cfg["qos"]))
        qos_cb = ttk.Combobox(qos_row, textvariable=self.qos_var,
                               values=["0", "1", "2"], width=6,
                               state="readonly")
        qos_cb.pack(side="left")

        # Spacer
        tk.Frame(left, bg=COLORS["panel"]).pack(fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(left, bg=COLORS["panel"])
        btn_frame.pack(fill="x", padx=12, pady=12)

        self.connect_btn = ttk.Button(btn_frame, text="▶  CONNECT",
                                       style="Accent.TButton",
                                       command=self._toggle_connection)
        self.connect_btn.pack(fill="x", pady=(0, 6))

        ttk.Button(btn_frame, text="↓  SAVE CONFIG",
                   style="Danger.TButton",
                   command=self._save_config_ui).pack(fill="x")

        # ── Right panel (log) ──
        right = tk.Frame(main, bg=COLORS["bg"])
        right.pack(side="left", fill="both", expand=True)

        log_header = tk.Frame(right, bg=COLORS["panel"],
                              highlightbackground=COLORS["border"],
                              highlightthickness=1)
        log_header.pack(fill="x", pady=(0, 4))

        tk.Label(log_header, text="LIVE STREAM",
                 bg=COLORS["panel"], fg=COLORS["accent"],
                 font=("Consolas", 10, "bold")).pack(side="left", padx=10, pady=6)

        self.count_lbl = tk.Label(log_header, text="0 messages",
                                   bg=COLORS["panel"], fg=COLORS["text_dim"],
                                   font=("Consolas", 9))
        self.count_lbl.pack(side="left", padx=6)

        tk.Button(log_header, text="⌫ Clear",
                  bg=COLORS["panel"], fg=COLORS["text_dim"],
                  activebackground=COLORS["border"],
                  activeforeground=COLORS["text"],
                  font=("Consolas", 9), relief="flat", bd=0,
                  command=self._clear_log,
                  cursor="hand2").pack(side="right", padx=10, pady=4)

        self.auto_scroll_var = tk.BooleanVar(value=True)
        tk.Checkbutton(log_header, text="Auto-scroll",
                       variable=self.auto_scroll_var,
                       bg=COLORS["panel"], fg=COLORS["text_dim"],
                       selectcolor=COLORS["input_bg"],
                       activebackground=COLORS["panel"],
                       font=("Consolas", 9),
                       relief="flat", bd=0).pack(side="right", padx=(0, 4))

        self.log_box = scrolledtext.ScrolledText(
            right,
            bg=COLORS["bg"], fg=COLORS["text"],
            font=("Consolas", 9),
            relief="flat", bd=0,
            insertbackground=COLORS["text"],
            state="disabled",
            wrap="none",
        )
        self.log_box.pack(fill="both", expand=True)

        # Tag colours
        self.log_box.tag_config("ts",      foreground=COLORS["text_dim"])
        self.log_box.tag_config("topic",   foreground=COLORS["accent"])
        self.log_box.tag_config("payload", foreground=COLORS["text"])
        self.log_box.tag_config("system",  foreground=COLORS["warn"])
        self.log_box.tag_config("error",   foreground=COLORS["error"])
        self.log_box.tag_config("ok",      foreground=COLORS["accent2"])

        # Status bar
        bar = tk.Frame(self.root, bg=COLORS["panel"],
                       highlightbackground=COLORS["border"],
                       highlightthickness=1, height=26)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.bar_lbl = tk.Label(bar, text="Ready.",
                                bg=COLORS["panel"], fg=COLORS["text_dim"],
                                font=("Consolas", 9))
        self.bar_lbl.pack(side="left", padx=10)

        self.file_lbl = tk.Label(bar, text="",
                                  bg=COLORS["panel"], fg=COLORS["text_dim"],
                                  font=("Consolas", 9))
        self.file_lbl.pack(side="right", padx=10)

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _section(self, parent, title):
        tk.Label(parent, text=title,
                 bg=COLORS["panel"], fg=COLORS["accent"],
                 font=("Consolas", 8, "bold")).pack(
            anchor="w", padx=12, pady=(12, 2))
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(
            fill="x", padx=12, pady=(0, 6))

    def _field(self, parent, label, var_name, default, show=None):
        tk.Label(parent, text=label,
                 bg=COLORS["panel"], fg=COLORS["text_dim"],
                 font=("Consolas", 8)).pack(anchor="w", padx=12)

        var = tk.StringVar(value=default)
        setattr(self, var_name, var)

        kw = dict(textvariable=var,
                  bg=COLORS["input_bg"], fg=COLORS["text"],
                  insertbackground=COLORS["text"],
                  font=("Consolas", 10),
                  relief="flat", bd=4)
        if show:
            kw["show"] = show

        tk.Entry(parent, **kw).pack(fill="x", padx=12, pady=(2, 6))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _browse_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"),
                       ("All files", "*.*")],
            title="Choose output file",
        )
        if path:
            self.file_var.set(path)

    def _save_config_ui(self):
        cfg = self._gather_config()
        save_config(cfg)
        self._set_bar("Config saved to config.json")

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
            "broker_ip":   self.ip_var.get().strip(),
            "port":        port,
            "topic":       self.topic_var.get().strip() or "#",
            "output_file": self.file_var.get().strip() or "mqtt_stream.log",
            "username":    self.user_var.get(),
            "password":    self.pass_var.get(),
            "qos":         qos,
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

        self.client = mqtt.Client(client_id="mqtt_logger_ui",
                                  clean_session=True)

        if cfg["username"]:
            self.client.username_pw_set(cfg["username"], cfg["password"])

        self.client.on_connect    = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message    = self._on_message

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
            qos   = self.cfg["qos"]
            client.subscribe(topic, qos=qos)
            self.msg_queue.put(("ok",    f"Connected — subscribed to '{topic}' (QoS {qos})"))
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

    def _apply_state(self, state):
        if state == "connected":
            self.connected = True
            self.status_dot.config(fg=COLORS["connected"])
            self.status_lbl.config(fg=COLORS["connected"], text="CONNECTED")
            self.connect_btn.config(text="■  DISCONNECT",
                                    style="Danger.TButton",
                                    state="normal")
            self.file_lbl.config(text=f"→ {self.cfg['output_file']}")
        else:
            self.connected = False
            self.status_dot.config(fg=COLORS["disconn"])
            self.status_lbl.config(fg=COLORS["disconn"], text="DISCONNECTED")
            self.connect_btn.config(text="▶  CONNECT",
                                    style="Accent.TButton",
                                    state="normal")
            self.file_lbl.config(text="")

    def _append_message(self, topic, payload):
        now = ts()
        self.msg_count += 1
        self.count_lbl.config(text=f"{self.msg_count} messages")

        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{now}] ", "ts")
        self.log_box.insert("end", topic,       "topic")
        self.log_box.insert("end", "  →  ",     "ts")
        self.log_box.insert("end", payload + "\n", "payload")
        self.log_box.configure(state="disabled")

        if self.auto_scroll_var.get():
            self.log_box.see("end")

        # Write to file
        if self.log_file:
            try:
                self.log_file.write(f"[{now}] {topic}  {payload}\n")
                self.log_file.flush()
            except OSError:
                pass

        self._set_bar(f"Last: {topic}")

    def _append_system(self, text, tag="system"):
        now = ts()
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{now}] ", "ts")
        self.log_box.insert("end", text + "\n", tag)
        self.log_box.configure(state="disabled")
        if self.auto_scroll_var.get():
            self.log_box.see("end")
        self._set_bar(text)

    def _set_bar(self, text):
        self.bar_lbl.config(text=text)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def on_close(self):
        self._disconnect()
        self.root.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = MQTTLoggerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()