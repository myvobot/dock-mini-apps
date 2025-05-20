from .ui_home import show_card
from .config import getProfile, get_sensor_models
from .ui_details import show_details, update_details
from .ui_history import reset_history_info, refresh_history, show_history
from .data_storage import get_live_info, get_record_info, load_sensor_history_data, remove_live_info, clear_cache
from .ble_broadcast import on_ble_broadcast, set_active_state_callback, sync_selected_device, get_sensor_found

_PRODUCT_NAME = "Virtual Sensor" # Product name constant
_SENSOR_GAP_NAME = "SENSOR"      # GAP name for sensor

def get_product_name():
    # Return the product name
    return _PRODUCT_NAME

def get_gap_name_callbacks():
    # Return a dictionary mapping GAP names to their broadcast handlers
    return {_SENSOR_GAP_NAME: on_ble_broadcast}

def get_profile(model):
    # Return the profile for a given model
    return getProfile(model)

def get_sensor_data(sensor_id):
    # Return the live information for a given sensor ID
    return get_live_info(sensor_id)

def delete_sensor_data(sensor_id):
    # Clear the cache for a given sensor ID
    remove_live_info(sensor_id)
    clear_cache(sensor_id)
