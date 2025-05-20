import os
import struct
from . import config

# Path to store sensor history data
config.createFolder("/apps/sensor_app/history")
_HISTORY_PATH = "/apps/sensor_app/history/virtual_sensor"

_STRUCT_INFO = {
    "length": 7, # Length of the sensor data structure
    "struct":[("timestamp", "I"), ("measure_id", "B"), ("temperature", "h")] # Structure of the sensor data
}

_live_info = {} # Dictionary to store live sensor information
_record_info = {} # Dictionary to store last record information
_history_data = {} # Dictionary to store history data

def set_live_info(sensor_id, info):
    # Update live sensor information
    _live_info[sensor_id] = info

def get_live_info(sensor_id):
    # Get live sensor information
    return _live_info.get(sensor_id, {})

def remove_live_info(sensor_id):
    # Remove live sensor information
    if sensor_id not in _live_info: return
    del _live_info[sensor_id]

def set_record_info(sensor_id, s_info, save_now=False):
    # Update record information
    _record_info[sensor_id] = s_info
    if save_now: save_sensor_history_data(sensor_id)

def get_record_info(sensor_id):
    # Get record information
    return _record_info.get(sensor_id, {})

def clear_record_info(sensor_id):
    # Remove record information
    if sensor_id in _record_info: del _record_info[sensor_id]

def set_sensor_history_data(sensor_id, s_info):
    # Add a new record to the sensor's history data
    if sensor_id not in _history_data:
        _history_data[sensor_id] = {"data": b"", "dev_model": s_info["dev_model"]}

    # Store data in little-endian format, specify endianness, otherwise struct will default to memory alignment
    # For example, _fmt: IBh, expected length is 7, aligned length is 8
    fmt = "<"
    data = []
    record_data = {}

    # Generate the packing format and data, as well as the latest record information
    for attr_fmt in _STRUCT_INFO["struct"]:
        fmt += attr_fmt[1]
        data.append(s_info[attr_fmt[0]])
        record_data[attr_fmt[0]] = s_info[attr_fmt[0]]

    # Pack history data
    byte_data = struct.pack(fmt, *data)
    temporary_data = _history_data[sensor_id]["data"] + byte_data
    max_len = config._MAX_HISTORY_MEASUREMENTS * _STRUCT_INFO["length"]
    curr_len = len(temporary_data)
    # A single node can store up to MAX_HISTORY_MEASUREMENTS data
    if curr_len > max_len:
        temporary_data = temporary_data[curr_len - max_len:]

    _history_data[sensor_id]["data"] = temporary_data

    # Update record data
    set_record_info(sensor_id, record_data, True)

def get_sensor_history_data(sensor_id=None):
    # Get history data for one or all sensors
    res = {}
    # If sensor_id is None, get the history data of all sensors
    if sensor_id is None: data_source = _history_data
    else: data_source = {sensor_id: _history_data.get(sensor_id, {})}

    for s_id, s_info in data_source.items():
        if not s_info: continue
        res[s_id] = []
        fmt = "<" + "".join([i[1] for i in _STRUCT_INFO["struct"]])
        byte_datas = s_info["data"]
        while byte_datas:
            # Parse single measurement data
            info = struct.unpack(fmt, byte_datas[: _STRUCT_INFO["length"]])
            res[s_id].append({_STRUCT_INFO["struct"][i][0]: info[i] for i in range(len(info))})
            byte_datas = byte_datas[_STRUCT_INFO["length"]:]

    return res

def clear_sensor_history_data(sensor_id):
    # Remove all history data for a sensor
    if sensor_id in _history_data: del _history_data[sensor_id]
    config.remove(f"{_HISTORY_PATH}/{sensor_id}.data")

def save_sensor_history_data(sensor_id=None):
    # Save sensor history data to file
    try:
        if sensor_id is None: data_source = _history_data
        else: data_source = {sensor_id: _history_data.get(sensor_id, {})}

        for s_id, s_info in data_source.items():
            if not s_info: continue
            file_name = f"{_HISTORY_PATH}/{s_id}.data"

            try:
                buff = bytes([s_info["dev_model"]]) + s_info["data"]
                with open(file_name, "wb+") as f: f.write(buff)
            except Exception as e:
                print(f"save_sensor_history_data error: {str(e)}")
                # If file save fails, delete the oldest record
                s_info["data"] = s_info["data"][_STRUCT_INFO["length"]:]

    except Exception as e:
        print(f"save_sensor_history_data error: {str(e)}")

def load_sensor_history_data():
    # Load sensor history data from files
    global _history_data
    try:
        config.createFolder(_HISTORY_PATH)
        for resource in os.ilistdir(_HISTORY_PATH):
            # Filter out files/directories that do not meet the requirements
            if resource[1] != 0x8000 or not resource[0].endswith(".data"): continue
            with open(f"{_HISTORY_PATH}/{resource[0]}", "rb+") as f: data_bytes = f.read()

            s_id = resource[0].split(".")[0]
            s_info = _history_data.get(s_id, {})
            s_info["dev_model"] = data_bytes[0]
            s_info["data"] = data_bytes[1:] + s_info.get("data", b"")

            if not s_info["data"]: return

            _history_data[s_id] = s_info
            set_record_info(s_id, get_sensor_history_data(s_id)[s_id][-1])
    except Exception as e:
        print(f"load_sensor_history_data error: {str(e)}")

def clear_cache(sensor_id):
    # Clear the cache for a given sensor ID
    clear_record_info(sensor_id)
    clear_sensor_history_data(sensor_id)
