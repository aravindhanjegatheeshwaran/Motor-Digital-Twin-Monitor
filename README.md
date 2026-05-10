# Motor Digital Twin Monitor

A real-time desktop Digital Twin dashboard for hardware motor monitoring systems, built with Python, Tkinter, and Matplotlib. The application visualises live sensor data received over serial communication, evaluates fault conditions, and logs all readings to CSV — with no external data sources required.

---

## Features

- **Real-time serial data ingestion** with automatic reconnection
- **4 live scrolling graphs** — Temperature, Humidity, Current, and Voltage — with dynamic fault-colour switching and threshold reference lines
- **Fault detection engine** evaluating 5 independent conditions with an overall NORMAL / FAULT status badge
- **Sensor status cards** with custom-generated PNG indicators that switch green ↔ red on fault
- **Motor/Relay actuator card** displaying the reported state (ON / OFF) without sending any commands back to the device
- **CSV live log** written on every run, capturing all readings and fault flags with millisecond timestamps
- **Demo mode** cycling through 5 realistic fault scenarios for testing without hardware
- **Dark theme UI** designed for engineering dashboards

---

## Screenshots

> Run `python generate_images.py` once to generate all UI assets, then `python main.py` to launch.

---

## Architecture

```
Motor Digital Twin Monitor/
├── config.py           # All constants, thresholds, and colour palette
├── serial_reader.py    # Threaded serial reader with auto-reconnect + demo loop
├── data_processor.py   # Frame parser, fault evaluator, CSV logger
├── dashboard.py        # Tkinter + Matplotlib live dashboard UI
├── main.py             # Entry point wiring all components together
├── generate_images.py  # Generates all PNG status card assets
├── images/             # Generated PNG assets (auto-created)
└── live_log.csv        # Runtime log (overwritten on each startup)
```

---

## Serial Frame Format

The application reads frames from a hardware device over UART:

```
0XZZ , t=<val> , h=<val> , m=<val> , I=<val> , V=<val> , 0XFF
```

| Field  | Description             | Type                  |
| ------ | ----------------------- | --------------------- |
| `0XZZ` | Frame header (required) | —                     |
| `t`    | Temperature (°C)        | float                 |
| `h`    | Humidity (%)            | float                 |
| `m`    | Motor/Relay state       | int (0 = ON, 1 = OFF) |
| `I`    | Current (Amperes)       | float                 |
| `V`    | Voltage (Volts)         | float                 |
| `0XFF` | Frame footer (required) | —                     |

Frames with a missing header/footer, wrong field count, unknown keys, or non-numeric values are silently dropped.

---

## Fault Conditions

| Sensor      | Condition   | Alert        |
| ----------- | ----------- | ------------ |
| Temperature | `t > 40 °C` | High Temp    |
| Humidity    | `h < 30 %`  | Low Humidity |
| Current     | `I == 0 A`  | No Current   |
| Voltage     | `V < 10 V`  | Low Voltage  |
| Voltage     | `V > 14 V`  | Overvoltage  |

The overall badge shows **FAULT** (red) if any single condition is active, otherwise **NORMAL** (green). The Motor/Relay state is display-only — the system never writes commands back to the device.

---

## Tech Stack

| Layer            | Technology                 |
| ---------------- | -------------------------- |
| Language         | Python 3.11+               |
| UI Framework     | Tkinter                    |
| Live Graphs      | Matplotlib (TkAgg backend) |
| Serial I/O       | PySerial                   |
| Image Generation | Pillow (PIL)               |
| Data Logging     | Python `csv` stdlib        |

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate UI assets

```bash
python generate_images.py
```

### 3. Configure serial port

Open `config.py` and set your port and baud rate:

```python
SERIAL_PORT = "COM3"   # Windows — or "/dev/ttyUSB0" on Linux
BAUD_RATE   = 9600
```

To test without hardware, enable demo mode:

```python
DEMO_MODE = True
```

### 4. Run the dashboard

```bash
python main.py
```

---

## Configuration Reference

All settings are centralised in `config.py`:

| Variable             | Default   | Description                                |
| -------------------- | --------- | ------------------------------------------ |
| `DEMO_MODE`          | `False`   | Enable simulated data (no hardware needed) |
| `SERIAL_PORT`        | `"COM3"`  | Serial port of the connected device        |
| `BAUD_RATE`          | `9600`    | Serial baud rate                           |
| `RECONNECT_DELAY`    | `3.0 s`   | Delay between reconnect attempts           |
| `WINDOW_SIZE`        | `100`     | Number of samples shown on each graph      |
| `UPDATE_INTERVAL_MS` | `200`     | Graph refresh rate (milliseconds)          |
| `TEMP_HIGH_LIMIT`    | `40.0 °C` | High temperature threshold                 |
| `HUMIDITY_LOW_LIMIT` | `30.0 %`  | Low humidity threshold                     |
| `VOLTAGE_LOW_LIMIT`  | `10.0 V`  | Low voltage threshold                      |
| `VOLTAGE_HIGH_LIMIT` | `14.0 V`  | Overvoltage threshold                      |

---

## Requirements

```
pyserial
matplotlib
pillow
```

---

## License

This project is open source and available under the [MIT License](LICENSE).
