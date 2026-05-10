from config import DEMO_MODE, SERIAL_PORT, BAUD_RATE
from serial_reader import SerialReader
from data_processor import DataProcessor
from dashboard import Dashboard

def _print_banner() -> None:
    print()
    print("=" * 58)
    print("   Motor Digital Twin Monitor")
    print("=" * 58)
    if DEMO_MODE:
        print("   Mode    : DEMO  (simulated sensor data)")
    else:
        print("   Mode    : LIVE")
        print(f"   Port    : {SERIAL_PORT}")
        print(f"   Baud    : {BAUD_RATE}")
    print("=" * 58)
    print()

def main() -> None:
    _print_banner()

    reader    = SerialReader()
    processor = DataProcessor()

    reader.start()

    dashboard = Dashboard(reader, processor)
    dashboard.run()

if __name__ == "__main__":
    main()