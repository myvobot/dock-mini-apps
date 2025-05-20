import asyncio
import lvgl as lv
import peripherals
from .. import base
from .. import product

# Constants for screen resolution
_SCR_WIDTH, _SCR_HEIGHT = peripherals.screen.screen_resolution

_scr = None         # The main LVGL screen object
_app_mgr = None     # Application manager instance
_record_data = {}   # Cache for history record data
_sensor_id = None   # Currently selected sensor ID
_container = None   # Container for history page UI

def event_handler(e):
    """
    Handle events for the history container:
        - ESC: return to home page
        - ENTER: try next history view, or go to details if none
    """
    e_code = e.get_code()
    if e_code == lv.EVENT.KEY:
        e_key = e.get_key()
        if e_key == lv.KEY.ESC:
            # ESC: navigate back to home page
            asyncio.create_task(base.switch_page(base._PAGE_HOME))
        elif e_key == lv.KEY.ENTER:
            # ENTER: attempt to show next history page
            res = None
            try:
                sensor_info = get_sensor_info(_sensor_id)
                product_registry = product.get_product_registry()
                s_model = product_registry.get(sensor_info.get("product_name", None), None)

                if not hasattr(s_model, "show_history"): res = None
                else: res = s_model.show_history(_container, _sensor_id, sensor_info["dev_model"])
            except Exception as e:
                print(f"switch page fail.[{str(e)}]")

            # No more history views → go to details page
            if res is None: asyncio.create_task(base.switch_page(base._PAGE_DETAILS, _sensor_id))
    elif e_code == lv.EVENT.FOCUSED:
        lv_group = lv.group_get_default()
        if lv_group.get_focused() != e.get_target_obj(): return
        # If focused and not in edit mode, enable edit mode
        if not lv_group.get_editing(): lv_group.set_editing(True)

def get_sensor_info(sensor_id):
    """
    Retrieve the configuration info for the given sensor ID.
    """
    config = _app_mgr.config()
    selected_devices = config.get("selected", [])
    for dev in selected_devices:
        if dev["sensor_id"] == sensor_id: return dev
    return {}

async def show_history_page():
    """
    Display the history UI for the current sensor.
    """
    if not _sensor_id: return
    sensor_info = get_sensor_info(_sensor_id)
    product_registry = product.get_product_registry()
    s_model = product_registry.get(sensor_info.get("product_name", None), None)
    if not s_model: return

    global _container, _record_data
    if not _container:
        # Create full‐screen container for history
        _container = lv.obj(_scr)
        _container.remove_style(None, lv.PART.MAIN)
        _container.remove_style(None, lv.PART.SCROLLBAR)
        _container.set_size(_SCR_WIDTH, _SCR_HEIGHT)
        _container.set_style_border_width(0, lv.PART.MAIN)
        _container.align(lv.ALIGN.BOTTOM_MID, 0, 0)
        _container.remove_style(None, lv.PART.SCROLLBAR)
        _container.set_style_bg_opa(lv.OPA._0, lv.PART.MAIN)
        _container.set_scroll_snap_y(lv.SCROLL_SNAP.CENTER)
        _container.set_style_pad_all(0, lv.PART.MAIN)
        _container.add_event_cb(event_handler, lv.EVENT.ALL, None)

        # Add to default group and focus it
        lv.group_get_default().add_obj(_container)
        lv.group_focus_obj(_container)
        lv.group_get_default().set_editing(True)

    # Populate container via model.show_history
    if not hasattr(s_model, "show_history"): res = None
    else: res = s_model.show_history(_container, _sensor_id, sensor_info["dev_model"])

    # Cache record info if available
    if hasattr(s_model, "get_record_info"): _record_data = s_model.get_record_info(_sensor_id)

    # If no history view was returned, switch to detail page
    if res is None: asyncio.create_task(base.switch_page(base._PAGE_DETAILS, _sensor_id))

async def on_start(scr, app_mgr, sensor_id):
    """
    Called when the detail page is started.
        - scr: the lvgl screen object
        - app_mgr: the application manager instance
        - sensor_id: ID of the sensor to display
    """
    global _scr, _app_mgr, _sensor_id
    _scr = scr
    _app_mgr = app_mgr
    _sensor_id = sensor_id

    if app_mgr: app_mgr.leave_root_page()
    await show_history_page()

async def on_stop():
    """
    Called when history page stops: reset model and clean up UI.
    """
    global _scr, _container

    sensor_info = get_sensor_info(_sensor_id)
    product_registry = product.get_product_registry()
    s_model = product_registry.get(sensor_info.get("product_name", None), None)
    if s_model: await s_model.reset_history_info()

    if _app_mgr: _app_mgr.enter_root_page()

    if _scr:
        _scr.clean()
        _scr = None
    _container = None

async def on_running_foreground():
    """
    Refresh history data when app returns to foreground if data has changed.
    """
    global _record_data
    if not _sensor_id or not _container: return

    sensor_info = get_sensor_info(_sensor_id)
    product_registry = product.get_product_registry()
    s_model = product_registry.get(sensor_info.get("product_name", None), None)
    if not s_model: return

    if not hasattr(s_model, "get_record_info"): tmp_data = {}
    else: tmp_data = s_model.get_record_info(_sensor_id)

    if _record_data == tmp_data: return

    # Data changed → invoke model.refresh_history
    if hasattr(s_model, "refresh_history"): s_model.refresh_history(_sensor_id)
    _record_data = tmp_data

    await asyncio.sleep_ms(100)