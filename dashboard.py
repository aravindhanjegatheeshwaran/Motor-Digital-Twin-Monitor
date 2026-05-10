import os
import tkinter as tk
from collections import deque

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk

from config import (
    WINDOW_SIZE, UPDATE_INTERVAL_MS, IMAGES_DIR,
    COLOR_NORMAL, COLOR_FAULT, COLOR_BG, COLOR_PANEL,
    COLOR_ACCENT, COLOR_TEXT, COLOR_WARN, COLOR_GREY,
    TEMP_HIGH_LIMIT, HUMIDITY_LOW_LIMIT,
    CURRENT_ZERO_ALERT, VOLTAGE_LOW_LIMIT, VOLTAGE_HIGH_LIMIT,
)
from serial_reader import SerialReader
from data_processor import DataProcessor

class Dashboard:

    _WINDOW_W: int      = 1340
    _WINDOW_H: int      = 740
    _LEFT_PANEL_W: int  = 200
    _COLOR_WAITING: str = "#546e7a"
    _COLOR_NO_DEV: str  = "#e67e22"

    _SYSTEM_IMG_SIZE: tuple = (110, 110)
    _SENSOR_IMG_SIZE: tuple = (52, 52)
    _MOTOR_IMG_SIZE:  tuple = (68, 68)

    def __init__(
        self,
        serial_reader: SerialReader,
        data_processor: DataProcessor,
    ) -> None:
        self.reader    = serial_reader
        self.processor = data_processor

        self.x_vals:   deque = deque(maxlen=WINDOW_SIZE)
        self.temps:    deque = deque(maxlen=WINDOW_SIZE)
        self.humids:   deque = deque(maxlen=WINDOW_SIZE)
        self.currents: deque = deque(maxlen=WINDOW_SIZE)
        self.voltages: deque = deque(maxlen=WINDOW_SIZE)

        self._sample_count: int = 0

        self.root = tk.Tk()
        self._setup_window()
        self._load_all_images()
        self._build_layout()
        self._setup_graphs()
        self._start_animation()

    def _setup_window(self) -> None:
        self.root.title("Motor Digital Twin Monitor")
        self.root.configure(bg=COLOR_BG)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w  = min(self._WINDOW_W, sw)
        h  = min(self._WINDOW_H, sh - 40)
        self.root.geometry(f"{w}x{h}+0+0")
        self.root.minsize(900, 600)
        self.root.state("zoomed")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

    def _fallback_img(self, size: tuple, colour: str) -> ImageTk.PhotoImage:
        img = Image.new("RGBA", size, colour)
        return ImageTk.PhotoImage(img)

    def _load_img(self, filename: str, size: tuple, fallback_colour: str) -> ImageTk.PhotoImage:
        path = os.path.join(IMAGES_DIR, filename)
        if os.path.exists(path):
            try:
                img = Image.open(path).convert("RGBA").resize(size, Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            except Exception as exc:
                print(f"[Dashboard] Could not load '{filename}': {exc}")
        return self._fallback_img(size, fallback_colour)

    def _load_all_images(self) -> None:
        ss = self._SENSOR_IMG_SIZE
        sys_s = self._SYSTEM_IMG_SIZE
        mo = self._MOTOR_IMG_SIZE

        self.img_sys_normal = self._load_img("normal.png",  sys_s, COLOR_NORMAL)
        self.img_sys_fault  = self._load_img("fault.png",   sys_s, COLOR_FAULT)

        self.img_temp_normal    = self._load_img("temp_normal.png",    ss, COLOR_NORMAL)
        self.img_temp_high      = self._load_img("temp_high.png",      ss, COLOR_FAULT)
        self.img_hum_normal     = self._load_img("humidity_normal.png", ss, COLOR_NORMAL)
        self.img_hum_low        = self._load_img("humidity_low.png",    ss, COLOR_FAULT)
        self.img_current_normal = self._load_img("current_normal.png", ss, COLOR_NORMAL)
        self.img_current_high   = self._load_img("current_high.png",   ss, COLOR_FAULT)
        self.img_volt_normal    = self._load_img("voltage_normal.png", ss, COLOR_NORMAL)
        self.img_volt_fault     = self._load_img("voltage_fault.png",  ss, COLOR_FAULT)

        self.img_motor_on  = self._load_img("motor_on.png",  mo, COLOR_NORMAL)
        self.img_motor_off = self._load_img("motor_off.png", mo, COLOR_GREY)

    def _build_layout(self) -> None:
        title_bar = tk.Frame(self.root, bg=COLOR_ACCENT, pady=4)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        tk.Label(
            title_bar,
            text="  ⚙  Motor Digital Twin Monitor",
            font=("Helvetica", 12, "bold"),
            bg=COLOR_ACCENT, fg=COLOR_TEXT,
        ).pack(side=tk.LEFT, padx=10)

        self._threshold_label = tk.Label(
            title_bar,
            text=self._threshold_text(),
            font=("Courier", 7),
            bg=COLOR_ACCENT, fg="#a0b0c0",
        )
        self._threshold_label.pack(side=tk.RIGHT, padx=10)

        content = tk.Frame(self.root, bg=COLOR_BG)
        content.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 2))

        self._left = tk.Frame(
            content, bg=COLOR_PANEL,
            width=self._LEFT_PANEL_W,
            relief=tk.RIDGE, bd=2,
        )
        self._left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        self._left.pack_propagate(False)

        self._right = tk.Frame(content, bg=COLOR_BG)
        self._right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_left_panel()

        self._status_bar = tk.Label(
            self.root,
            text="Initializing…",
            font=("Courier", 8),
            bg=COLOR_ACCENT, fg="#a0b0c0",
            anchor=tk.W, padx=10, pady=3,
        )
        self._status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_left_panel(self) -> None:
        p = self._left

        self._sys_img_lbl = tk.Label(p, image=self.img_sys_normal, bg=COLOR_PANEL)
        self._sys_img_lbl.pack(pady=(6, 2))

        self._overall_badge = tk.Label(
            p, text="●  WAITING",
            font=("Helvetica", 10, "bold"),
            bg=self._COLOR_WAITING, fg="white",
            width=14, pady=4,
            relief=tk.RAISED, bd=2,
        )
        self._overall_badge.pack(pady=(3, 1), padx=10)

        self._fault_type_lbl = tk.Label(
            p, text="Awaiting sensor data…",
            font=("Helvetica", 7), wraplength=185,
            bg=COLOR_PANEL, fg=COLOR_WARN,
        )
        self._fault_type_lbl.pack(pady=(0, 3), padx=4)

        self._reconnect_btn = tk.Button(
            p,
            text="⟳  Reconnect Serial",
            font=("Helvetica", 7, "bold"),
            bg=COLOR_ACCENT, fg="white",
            activebackground="#1a5276",
            activeforeground="white",
            relief=tk.FLAT, cursor="hand2",
            command=self._on_reconnect,
            pady=4, padx=6,
        )
        self._reconnect_btn.pack(pady=(2, 5), padx=10, fill=tk.X)
        if self.reader.demo_mode:
            self._reconnect_btn.config(state=tk.DISABLED, text="Demo Mode — No Serial")

        tk.Frame(p, bg=COLOR_ACCENT, height=1).pack(fill=tk.X, padx=8, pady=3)
        tk.Label(
            p, text="Sensor Status",
            font=("Helvetica", 8, "bold"),
            bg=COLOR_PANEL, fg=COLOR_TEXT,
        ).pack(pady=(0, 1))

        self._card_temp    = self._make_sensor_card(p, "Temperature", self.img_temp_normal)
        self._card_hum     = self._make_sensor_card(p, "Humidity",    self.img_hum_normal)
        self._card_current = self._make_sensor_card(p, "Current",     self.img_current_normal)
        self._card_voltage = self._make_sensor_card(p, "Voltage",     self.img_volt_normal)

        tk.Frame(p, bg=COLOR_ACCENT, height=1).pack(fill=tk.X, padx=8, pady=3)
        tk.Label(
            p, text="Actuator Status",
            font=("Helvetica", 8, "bold"),
            bg=COLOR_PANEL, fg=COLOR_TEXT,
        ).pack(pady=(0, 1))

        self._card_motor = self._make_actuator_card(p, "Motor / Relay")

    def _make_sensor_card(
        self,
        parent: tk.Frame,
        label: str,
        image: ImageTk.PhotoImage,
    ) -> dict:
        card = tk.Frame(parent, bg=COLOR_PANEL, pady=2)
        card.pack(fill=tk.X, padx=8)
        img_lbl = tk.Label(card, image=image, bg=COLOR_PANEL)
        img_lbl.pack(side=tk.LEFT, padx=(2, 4))
        info = tk.Frame(card, bg=COLOR_PANEL)
        info.pack(side=tk.LEFT, fill=tk.X)
        tk.Label(
            info, text=label,
            font=("Helvetica", 8, "bold"),
            bg=COLOR_PANEL, fg=COLOR_TEXT,
        ).pack(anchor=tk.W)
        val_lbl = tk.Label(
            info, text="—",
            font=("Courier", 8),
            bg=COLOR_PANEL, fg=COLOR_NORMAL,
        )
        val_lbl.pack(anchor=tk.W)
        return {"img_lbl": img_lbl, "value_lbl": val_lbl}

    def _make_actuator_card(self, parent: tk.Frame, label: str) -> dict:
        card = tk.Frame(parent, bg=COLOR_PANEL, pady=2)
        card.pack(fill=tk.X, padx=8)
        img_lbl = tk.Label(card, image=self.img_motor_off, bg=COLOR_PANEL)
        img_lbl.pack(side=tk.LEFT, padx=(2, 4))
        info = tk.Frame(card, bg=COLOR_PANEL)
        info.pack(side=tk.LEFT, fill=tk.X)
        tk.Label(
            info, text=label,
            font=("Helvetica", 8, "bold"),
            bg=COLOR_PANEL, fg=COLOR_TEXT,
        ).pack(anchor=tk.W)
        state_lbl = tk.Label(
            info, text="Reported: —",
            font=("Courier", 8),
            bg=COLOR_PANEL, fg=COLOR_GREY,
        )
        state_lbl.pack(anchor=tk.W)
        return {"img_lbl": img_lbl, "state_lbl": state_lbl}

    def _setup_graphs(self) -> None:
        self._fig, axes = plt.subplots(
            4, 1,
            figsize=(7.5, 5.6),
            facecolor=COLOR_BG,
        )
        self._ax_t, self._ax_h, self._ax_c, self._ax_v = axes

        self._fig.subplots_adjust(
            hspace=0.72,
            left=0.10, right=0.97,
            top=0.97, bottom=0.05,
        )

        for ax in axes:
            ax.set_facecolor("#0d1117")
            ax.tick_params(colors=COLOR_TEXT, labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor(COLOR_ACCENT)

        self._ax_t.axhline(TEMP_HIGH_LIMIT,     color=COLOR_WARN, linestyle="--", linewidth=0.9,
                           label=f"> {TEMP_HIGH_LIMIT} °C")
        self._ax_h.axhline(HUMIDITY_LOW_LIMIT,  color=COLOR_WARN, linestyle="--", linewidth=0.9,
                           label=f"< {HUMIDITY_LOW_LIMIT} %")
        self._ax_c.axhline(CURRENT_ZERO_ALERT,  color=COLOR_WARN, linestyle="--", linewidth=0.9,
                           label="= 0 A (no current)")
        self._ax_v.axhline(VOLTAGE_LOW_LIMIT,  color="#e67e22", linestyle="--", linewidth=0.9,
                           label=f"< {VOLTAGE_LOW_LIMIT} V")
        self._ax_v.axhline(VOLTAGE_HIGH_LIMIT, color="#c0392b", linestyle="--", linewidth=0.9,
                           label=f"> {VOLTAGE_HIGH_LIMIT} V")

        self._ax_t.set_title("Temperature (°C)", color=COLOR_TEXT, fontsize=8, pad=2)
        self._ax_h.set_title("Humidity (%)",      color=COLOR_TEXT, fontsize=8, pad=2)
        self._ax_c.set_title("Current (A)",       color=COLOR_TEXT, fontsize=8, pad=2)
        self._ax_v.set_title("Voltage (V)",       color=COLOR_TEXT, fontsize=8, pad=2)

        for ax in axes:
            ax.legend(
                loc="upper right", fontsize=6,
                facecolor=COLOR_BG, labelcolor=COLOR_TEXT, framealpha=0.6,
            )

        (self._line_t,) = self._ax_t.plot([], [], color=COLOR_NORMAL, linewidth=1.4)
        (self._line_h,) = self._ax_h.plot([], [], color=COLOR_NORMAL, linewidth=1.4)
        (self._line_c,) = self._ax_c.plot([], [], color=COLOR_NORMAL, linewidth=1.4)
        (self._line_v,) = self._ax_v.plot([], [], color=COLOR_NORMAL, linewidth=1.4)

        self._canvas = FigureCanvasTkAgg(self._fig, master=self._right)
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _start_animation(self) -> None:
        self._anim = animation.FuncAnimation(
            self._fig,
            func=self._animate,
            interval=UPDATE_INTERVAL_MS,
            blit=False,
            cache_frame_data=False,
        )

    def _animate(self, _frame: int) -> None:
        latest_result: dict | None = None
        new_data = False

        while True:
            raw = self.reader.get_data()
            if raw is None:
                break
            parsed = self.processor.parse(raw)
            if parsed is None:
                continue
            t, h, m, I, V = parsed
            result = self.processor.evaluate(t, h, m, I, V)
            self.processor.log(result)

            self._sample_count += 1
            self.x_vals.append(self._sample_count)
            self.temps.append(t)
            self.humids.append(h)
            self.currents.append(I)
            self.voltages.append(V)
            new_data = True
            latest_result = result

        if latest_result is not None:
            self._update_left_panel(latest_result)
        else:
            if not self.reader.connected:
                self._show_no_device_status()
            elif self._sample_count == 0:
                self._show_waiting_status()

        if new_data:
            self._redraw_graphs(latest_result)

        self._status_bar.config(
            text=(
                f"  Serial: {self.reader.status_message}   │   "
                f"Temp >{TEMP_HIGH_LIMIT}°C  "
                f"Hum <{HUMIDITY_LOW_LIMIT}%  "
                f"I=0→alert  "
                f"V <{VOLTAGE_LOW_LIMIT} / >{VOLTAGE_HIGH_LIMIT}V   Motor: 1=ON 0=OFF"
            )
        )

    def _update_left_panel(self, result: dict) -> None:
        fault = result["overall_fault"]

        self._sys_img_lbl.config(
            image=self.img_sys_fault if fault else self.img_sys_normal
        )
        self._overall_badge.config(
            text="●  FAULT"  if fault else "●  NORMAL",
            bg =COLOR_FAULT  if fault else COLOR_NORMAL,
        )
        self._fault_type_lbl.config(
            text=result["fault_label"] or "",
            fg=COLOR_FAULT if fault else COLOR_NORMAL,
        )

        if result["high_temp"]:
            self._card_temp["img_lbl"].config(image=self.img_temp_high)
            self._card_temp["value_lbl"].config(
                text=f"{result['temperature']:.1f} °C  ▲ HIGH",
                fg=COLOR_FAULT,
            )
        else:
            self._card_temp["img_lbl"].config(image=self.img_temp_normal)
            self._card_temp["value_lbl"].config(
                text=f"{result['temperature']:.1f} °C  ✓ OK",
                fg=COLOR_NORMAL,
            )

        if result["low_humidity"]:
            self._card_hum["img_lbl"].config(image=self.img_hum_low)
            self._card_hum["value_lbl"].config(
                text=f"{result['humidity']:.1f} %  ▼ LOW",
                fg=COLOR_FAULT,
            )
        else:
            self._card_hum["img_lbl"].config(image=self.img_hum_normal)
            self._card_hum["value_lbl"].config(
                text=f"{result['humidity']:.1f} %  ✓ OK",
                fg=COLOR_NORMAL,
            )

        if result["no_current"]:
            self._card_current["img_lbl"].config(image=self.img_current_high)
            self._card_current["value_lbl"].config(
                text=f"{result['current']:.2f} A  ▲ CHECK",
                fg=COLOR_FAULT,
            )
        else:
            self._card_current["img_lbl"].config(image=self.img_current_normal)
            self._card_current["value_lbl"].config(
                text=f"{result['current']:.2f} A  ✓ OK",
                fg=COLOR_NORMAL,
            )

        if result["low_voltage"] or result["overvoltage"]:
            self._card_voltage["img_lbl"].config(image=self.img_volt_fault)
            tag = "▼ LOW" if result["low_voltage"] else "▲ HIGH"
            self._card_voltage["value_lbl"].config(
                text=f"{result['voltage']:.2f} V  {tag}",
                fg=COLOR_FAULT,
            )
        else:
            self._card_voltage["img_lbl"].config(image=self.img_volt_normal)
            self._card_voltage["value_lbl"].config(
                text=f"{result['voltage']:.2f} V  ✓ OK",
                fg=COLOR_NORMAL,
            )

        m = result["motor"]
        motor_is_on = (m == 1)
        self._card_motor["img_lbl"].config(
            image=self.img_motor_on if motor_is_on else self.img_motor_off
        )
        self._card_motor["state_lbl"].config(
            text=f"Reported: {'ON' if motor_is_on else 'OFF'}",
            fg=COLOR_NORMAL if motor_is_on else COLOR_GREY,
        )

    def _redraw_graphs(self, result: dict | None) -> None:
        if not self.x_vals:
            return
        x = list(self.x_vals)
        x_min, x_max = x[0], max(x[-1], x[0] + 1)

        def _margin(vals, factor, minimum):
            spread = max(vals) - min(vals)
            return max(spread * factor, minimum)

        y_t = list(self.temps)
        self._line_t.set_data(x, y_t)
        self._line_t.set_color(
            COLOR_FAULT if (result and result["high_temp"]) else COLOR_NORMAL
        )
        self._ax_t.set_xlim(x_min, x_max)
        m = _margin(y_t, 0.15, 5.0)
        self._ax_t.set_ylim(min(y_t) - m, max(y_t) + m)

        y_h = list(self.humids)
        self._line_h.set_data(x, y_h)
        self._line_h.set_color(
            COLOR_FAULT if (result and result["low_humidity"]) else COLOR_NORMAL
        )
        self._ax_h.set_xlim(x_min, x_max)
        m = _margin(y_h, 0.15, 5.0)
        self._ax_h.set_ylim(min(y_h) - m, max(y_h) + m)

        y_c = list(self.currents)
        self._line_c.set_data(x, y_c)
        self._line_c.set_color(
            COLOR_FAULT if (result and result["no_current"]) else COLOR_NORMAL
        )
        self._ax_c.set_xlim(x_min, x_max)
        m = _margin(y_c, 0.15, 0.5)
        self._ax_c.set_ylim(min(y_c) - m, max(y_c) + m)

        y_v = list(self.voltages)
        self._line_v.set_data(x, y_v)
        self._line_v.set_color(
            COLOR_FAULT if (result and (result["low_voltage"] or result["overvoltage"])) else COLOR_NORMAL
        )
        self._ax_v.set_xlim(x_min, x_max)
        m = _margin(y_v, 0.15, 1.0)
        self._ax_v.set_ylim(min(y_v) - m, max(y_v) + m)

    def _show_waiting_status(self) -> None:
        self._overall_badge.config(text="●  WAITING", bg=self._COLOR_WAITING)
        self._fault_type_lbl.config(text="Awaiting sensor data…", fg=COLOR_WARN)
        self._sys_img_lbl.config(image=self.img_sys_normal)

    def _show_no_device_status(self) -> None:
        self._overall_badge.config(text="●  NO DEVICE", bg=self._COLOR_NO_DEV)
        msg = self.reader.status_message
        if len(msg) > 38:
            msg = msg[:35] + "…"
        self._fault_type_lbl.config(text=msg, fg=self._COLOR_NO_DEV)
        self._sys_img_lbl.config(image=self.img_sys_fault)

    def _on_reconnect(self) -> None:
        if self.reader.demo_mode:
            return
        self.reader.reconnect()
        self._show_waiting_status()
        self._reconnect_btn.config(state=tk.DISABLED)
        self.root.after(4000, lambda: self._reconnect_btn.config(state=tk.NORMAL))

    def _threshold_text(self) -> str:
        return (
            f"Temp >{TEMP_HIGH_LIMIT}°C  "
            f"Hum <{HUMIDITY_LOW_LIMIT}%  "
            f"I =0 A → alert  "
            f"V <{VOLTAGE_LOW_LIMIT} / >{VOLTAGE_HIGH_LIMIT}V   "
            f"Motor: 1=ON, 0=OFF"
        )

    def run(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self) -> None:
        print("[Dashboard] Shutting down…")
        self.reader.stop()
        plt.close("all")
        self.root.quit()
        self.root.destroy()