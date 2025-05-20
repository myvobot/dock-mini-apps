import struct
import asyncio
import binascii
import clocktime
from . import config
from . import data_storage

_ADV_TYPE_CUSTOMDATA = 0xff # Custom data type for BLE advertisement

_selected_sensors = [] # List of selected sensor IDs
_discovered_sensors = {} # Dictionary to store discovered sensors
_display_active_effect_cb = None # Callback for displaying active effect

def sync_selected_device(devs):
    # Synchronize the selected sensors
    global _selected_sensors
    _selected_sensors = devs

def set_active_state_callback(cb):
    # Set the callback function for displaying the active effect
    global _display_active_effect_cb
    _display_active_effect_cb = cb

def get_sensor_found(dev_model):
    # Get the discovered sensor information for a specific model
    if dev_model not in _discovered_sensors: return []
    return _discovered_sensors[dev_model]

def decode_all_fields(payload):
    # Decode all fields in the BLE advertisement payload
    result = {}
    while payload:
        # Format: [data length{1(data type) + data length}, data type, data]
        if len(payload) < 2: break
        adv_len = payload[0]
        if adv_len != 0:
            adv_type = payload[1]
            adv_data = payload[2:adv_len + 1]

            if adv_type in result: result[adv_type].append(adv_data)
            else: result[adv_type] = [adv_data, ]

        payload = payload[adv_len + 1:]
    return result

def on_ble_broadcast(addr, rssi, adv_data):
    # Parse the BLE broadcast data
    adv_fields = decode_all_fields(adv_data)

    # Check if custom data exists in the advertisement
    custom_data = adv_fields.get(_ADV_TYPE_CUSTOMDATA, [])
    if len(custom_data) < 1: return
    custom_data = custom_data[0]
    if not custom_data: return

    # Parse the custom data fields
    model = custom_data[0] # Sensor model code
    measure_id = custom_data[1] # Measurement ID
    timestamp = clocktime.now() # Current timestamp
    sensor_id = f"00{binascii.hexlify(addr).decode().upper()}00" # Generate sensor ID from address

    # Check if the model is valid and timestamp is valid
    if model not in config._MODEL_CODE or timestamp < 0: return

    # Update the discovered sensor information
    if model not in _discovered_sensors:
        _discovered_sensors[model] = {sensor_id:{"rssi": rssi}}
    else:
        _discovered_sensors[model][sensor_id] = {"rssi": rssi}

    # Check if the sensor is in the selected sensor list
    if sensor_id not in _selected_sensors: return

    # Parse the remaining fields from custom data
    info = {
        "rssi": rssi,
        "dev_model": model,
        "timestamp": timestamp,
        "measure_id": measure_id,
        "btn_state": custom_data[4], # Button state
        "probe_state": custom_data[5], # Probe state
        "battery_percentage": custom_data[6], # Battery percentage
    }
    live_info = data_storage.get_live_info(sensor_id)
    info["temperature"] = struct.unpack("h", custom_data[2:4])[0] # Temperature value

    # Check if the measurement ID has changed
    if measure_id != live_info.get("measure_id", -1):
        # Update the history data if measurement ID changed
        data_storage.set_sensor_history_data(sensor_id, info)

    # Check if the active effect needs to be displayed
    if info.get("btn_state", 0) == 1 and \
        _display_active_effect_cb and \
        live_info.get("btn_state", 0) == 0:
        asyncio.create_task(_display_active_effect_cb(sensor_id))

    # Update the real-time data for the sensor
    data_storage.set_live_info(sensor_id, info)
