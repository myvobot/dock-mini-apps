import asyncio
import lvgl as lv
import peripherals
from .. import base
from .. import product

# Get the screen resolution from peripherals
_SCR_WIDTH, _SCR_HEIGHT = peripherals.screen.screen_resolution

_scr = None         # main screen object
_app_mgr = None     # application manager instance
_curr_data = {}     # cached sensor data
_sensor_id = None   # currently selected sensor ID
_container = None   # container for detail page UI elements

def get_sensor_info(sensor_id):
    """
    Retrieve the configuration info for the given sensor ID.
    """
    config = _app_mgr.config()
    selected_devices = config.get("selected", [])
    for dev in selected_devices:
        if dev["sensor_id"] == sensor_id: return dev
    return {}

def event_handler(e):
    """
    Event handler for the detail page container.
        - ESC: return to home page
        - ENTER: switch to history data page
    """
    e_code = e.get_code()
    if e_code == lv.EVENT.KEY:
        e_key = e.get_key()
        if e_key == lv.KEY.ESC:
            # ESC: go back to home page
            asyncio.create_task(base.switch_page(base._PAGE_HOME))
        elif e_key == lv.KEY.ENTER:
            # ENTER: switch to history page for current sensor
            asyncio.create_task(base.switch_page(base._PAGE_HISTORY, _sensor_id))
    elif e_code == lv.EVENT.FOCUSED:
        lv_group = lv.group_get_default()
        # If focused object is not our container, ignore
        if lv_group.get_focused() != e.get_target_obj(): return
        # If the group is not in edit mode, enable edit mode
        if not lv_group.get_editing(): lv_group.set_editing(True)

async def show_details():
    """
    Build and display the detail page UI for the current sensor.
    """
    global _container, _curr_data
    if not _sensor_id: return
    sensor_info = get_sensor_info(_sensor_id)
    product_registry = product.get_product_registry()
    s_model = product_registry.get(sensor_info.get("product_name", None), None)
    if not s_model: return

    # Clean up existing container if any
    if _container: _container.clean()

    # Create a full‐screen container
    _container = lv.obj(_scr)
    _container.align(lv.ALIGN.TOP_LEFT, 0, 0)
    _container.set_size(_SCR_WIDTH, _SCR_HEIGHT)
    _container.set_style_radius(0, lv.PART.MAIN)
    _container.set_style_pad_all(0, lv.PART.MAIN)
    _container.remove_style(None, lv.PART.SCROLLBAR)
    _container.set_style_border_width(0, lv.PART.MAIN)
    _container.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    _container.add_event_cb(event_handler, lv.EVENT.ALL, None)
    _container.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)

    # If the model defines a show_details function, invoke it
    if hasattr(s_model, "show_details"): s_model.show_details(_container, sensor_info)

    # Add container to default group and enable editing mode
    lv.group_get_default().add_obj(_container)
    lv.group_get_default().set_editing(True)

    # Fetch initial sensor data if available
    if hasattr(s_model, "get_sensor_data"): _curr_data = s_model.get_sensor_data(_sensor_id)

async def on_start(scr, app_mgr, sensor_id):
    """
    Called when the detail page is started.
        - scr: the lvgl screen object
        - app_mgr: the application manager instance
        - sensor_id: ID of the sensor to display
    """
    global _scr, _app_mgr, _sensor_id, _container
    _scr = scr
    _app_mgr = app_mgr
    _sensor_id = sensor_id
    if app_mgr: app_mgr.leave_root_page()
    await show_details()

async def on_stop():
    """
    Called when the detail page is stopped.
    """
    global _scr, _sensor_id, _container

    if _app_mgr: _app_mgr.enter_root_page()

    if _scr:
        _scr.clean()
        _scr = None
    _sensor_id = None
    _container = None

async def on_running_foreground():
    """
    Periodic update when the app is in the foreground.
        - Refresh detail UI if sensor data has changed.
    """
    global _curr_data
    if not _sensor_id or not _container: return

    sensor_info = get_sensor_info(_sensor_id)
    product_registry = product.get_product_registry()
    s_model = product_registry.get(sensor_info.get("product_name", None), None)
    if not s_model: return

    # Fetch updated sensor data if available
    if not hasattr(s_model, "get_sensor_data"): tmp_data = {}
    else: tmp_data = s_model.get_sensor_data(_sensor_id)

    # If data hasn't changed, do nothing
    if _curr_data == tmp_data: return

    # Update the UI details if a method is provided
    if hasattr(s_model, "update_details"): s_model.update_details(sensor_info)
    _curr_data = tmp_data

    await asyncio.sleep_ms(100)
