import struct
import asyncio
import platform
from bleson import get_provider, Advertisement, Advertiser

class BLEAdvertiser:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        # Singleton pattern, ensure only one instance is created
        if cls._instance is None:
            cls._instance = super(BLEAdvertiser, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Avoid repeated initialization
        if self._initialized: return

        # Initialize BLE objects
        self.adapter = get_provider().get_adapter()
        self.advertiser = Advertiser(self.adapter)
        self.advertisement = Advertisement()
        self.advertiser.advertisement = self.advertisement

        # Initialize advertising information
        self.name = "SENSOR"
        self.measure_id = 0
        self.model_info = {
            "Windows": 0,
            "Linux": 1,
            "MAC": 2
        }
        self.model = self.model_info.get(platform.system(), 2)
        self.temperature = 0
        self.battery = 100
        self.btn_state = 0
        self.probe_state = 1
        self.measure_id = 0

        self._initialized = True

    def update_temperature(self, temperature):
        # Update temperature and auto-increment measure_id
        self.temperature = temperature
        self.measure_id += 1
        self.measure_id %= 256

    def update_battery(self, battery):
        # Update battery level
        self.battery = battery

    def update_btn_state(self, btn_state):
        # Update button state
        self.btn_state = btn_state

    def update_probe_state(self, probe_state):
        # Update probe state
        self.probe_state = probe_state

    def update_advertisement(self):
        # Construct BLE advertising data
        raw_data = b"\x02\x01\x06"
        raw_data += bytes([len(self.name) + 1]) + b"\x09" + self.name.encode()
        # [model: 1B, measure_id: 1B, temperature: 1h, btn_state: 1B, probe_state: 1B, battery: 1B]
        raw_data += b"\x08\xff" + struct.pack("2Bh3B", self.model, self.measure_id, self.temperature, self.btn_state, self.probe_state, self.battery)

        # Update BLE advertising data
        self.adapter.set_advertising_data(raw_data)

    def start(self):
        # Start BLE advertising
        self.advertiser.start()

    def stop(self):
        # Stop BLE advertising
        self.advertiser.stop()

if __name__ == "__main__":
    async def run():
        import random
        ble = BLEAdvertiser()
        ble.start()

        battery = 50
        update_time = 0
        temperature = random.randint(-3000, 10000)
        try:
            while True:
                # Update temperature, battery, and other states
                temperature += random.randint(-100, 100)
                btn_state = 1 if update_time % 50 == 0 else 0
                probe_state = 0 if update_time % 50 == 0 else 1
                battery = max(0, min(battery + random.randint(-1, 1), 100))

                ble.update_battery(battery)
                ble.update_btn_state(btn_state)
                ble.update_temperature(temperature)
                ble.update_probe_state(probe_state)

                # Update BLE advertising data
                ble.update_advertisement()

                # Print current state
                print(f"measure_id: {ble.measure_id}, temperature: {ble.temperature}, battery: {ble.battery}, btn_state: {ble.btn_state}, probe_state: {ble.probe_state}")

                await asyncio.sleep(5)
                update_time += 1
        except KeyboardInterrupt:
            print("advertiser stop")
            ble.stop()

    asyncio.run(run())
