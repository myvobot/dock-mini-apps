import time
import asyncio
import lvgl as lv
import peripherals
from .. import base
from .. import product
from micropython import const

# Display modes: single / dual / quad cards at once
_MODE_SINGLE = const(1)
_MODE_DUAL = const(2)
_MODE_QUAD = const(4)

# Duration (ms) to keep the focus style on a card after selection
_FOCUS_DURATION = const(180000)

# Screen resolution from peripherals
_SCR_WIDTH, _SCR_HEIGHT = peripherals.screen.screen_resolution

# Mapping of display mode to (card_size, alignments...)
_CARD_MODE_STYLES = {
    _MODE_SINGLE: [(_SCR_WIDTH, _SCR_HEIGHT), [lv.ALIGN.CENTER]],
    _MODE_DUAL: [(_SCR_WIDTH, (_SCR_HEIGHT // 2) - 1), [lv.ALIGN.TOP_MID, lv.ALIGN.BOTTOM_MID]],
    _MODE_QUAD: [((_SCR_WIDTH // 2) - 1, (_SCR_HEIGHT // 2) - 1), [lv.ALIGN.TOP_LEFT, lv.ALIGN.TOP_RIGHT, lv.ALIGN.BOTTOM_LEFT, lv.ALIGN.BOTTOM_RIGHT]]
}

_scr = None                     # Main LVGL screen object
_app_mgr = None                 # App manager instance
_focus_time = 0                 # Timestamp when a card was last focused
_focus_index = 0                # Index of currently focused sensor
_container = None               # Container for sensor cards
_devices_info = {}              # {sensor_id: {"refresh": ts, "curr_info": {...}}}
_selected_devices = []          # List of selected sensor configs
_display_mode = _MODE_SINGLE    # Number of cards shown at once

def check_selected_device():
    """
    Ensure there is at least one sensor selected.
    Show an info window if the selection is empty.
    """
    global _selected_devices
    config = _app_mgr.config()
    selected_devices = config.get("selected", [])
    if not selected_devices:
        asyncio.create_task(base.switch_page(base._PAGE_TIPS))
        return False

    _selected_devices = selected_devices
    return True

def sync_display_mode():
    """
    Synchronize `_display_mode` with app config.
    If not set, choose mode based on number of selected sensors.
    """
    global _display_mode
    total = len(_selected_devices)
    config = _app_mgr.config()
    display_mode = config.get("display_mode", None)

    if display_mode not in _CARD_MODE_STYLES:
        # Choose single/dual/quad based on total count
        display_mode = _MODE_SINGLE if total < 2 else _MODE_QUAD if total > 2 else _MODE_DUAL
        if display_mode is not None:
            config["display_mode"] = display_mode
            _app_mgr.config(config)
    _display_mode = display_mode

def get_display_sensors():
    """
    Get the sublist of sensors to render on current page,
    based on `_focus_index` and `_display_mode`.
    """
    group_index = _focus_index % _display_mode
    start = _focus_index - group_index
    end = _focus_index + _display_mode - group_index
    return _selected_devices[start : end]

def event_handler(e):
    """
    Handle key and click events on the card container:
        - Left/Right: move focus and update styling
        - Click: switch to history page
        - Focused: ensure LVGL group is in editing mode
    """
    global _focus_index, _focus_time
    e_code = e.get_code()
    if e_code == lv.EVENT.KEY:
        e_key = e.get_key()
        if e_key not in (lv.KEY.LEFT, lv.KEY.RIGHT): return
        # Remove previous focus style
        sensor_total = len(_selected_devices)
        last_group = _focus_index // _display_mode
        last_group_index = _focus_index % _display_mode
        _container.get_child(last_group_index).set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
        # Compute new focus index
        _focus_index = (_focus_index + (-1 if e_key == lv.KEY.LEFT else 1)) % (sensor_total + 1)
        curr_group = _focus_index // _display_mode

        # If page changed, re-render all cards; else just update one
        if last_group != curr_group: asyncio.create_task(render_sensors())
        else: _container.get_child(_focus_index % _display_mode).set_style_bg_color(lv.color_hex(0x5B5B5B), lv.PART.MAIN)
        _focus_time = time.ticks_ms()

    elif e_code == lv.EVENT.CLICKED:
        # On click: go to history page for focused sensor
        if _focus_index == len(_selected_devices):
            asyncio.create_task(base.switch_page(base._PAGE_TIPS))
        else:
            sensor_id = _selected_devices[_focus_index]["sensor_id"]
            asyncio.create_task(base.switch_page(base._PAGE_HISTORY, sensor_id))
    elif e_code == lv.EVENT.FOCUSED:
        lv_group = lv.group_get_default()
        if lv_group.get_focused() != e.get_target_obj(): return
        # If focused and not in edit mode, enable edit mode
        if not lv_group.get_editing(): lv_group.set_editing(True)

async def flash_active_card(sensor_id):
    """
    Temporarily highlight the card of the active sensor,
    then fade back after 2 seconds.
    """
    global _focus_index
    if not _container: return

    selected_sensors = [s["sensor_id"] for s in _selected_devices]
    if sensor_id not in selected_sensors: return

    # Switch focus to the active sensor and re-render
    _focus_index = selected_sensors.index(sensor_id)
    await render_sensors()
    target = _container.get_child(_focus_index % _display_mode)
    target.set_style_bg_color(lv.color_hex(0xFF8C2E), 0)

    # Wait before restoring
    await asyncio.sleep(2)

    # Only clear highlight if still showing and unchanged
    display_sensors = [s["sensor_id"] for s in get_display_sensors()]
    if sensor_id not in display_sensors or not _container: return
    if not target.get_style_bg_color(lv.PART.MAIN).eq(lv.color_hex(0xFF8C2E)): return
    target.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)

async def render_sensors(focus_style=True):
    """
    Render sensor cards in the container.
        - Create or clear cards based on `_display_mode`.
        - Call each product's `show_card` to populate content.
    """
    global _focus_time, _devices_info
    if not _container: return

    # If number of children doesn't match display_mode, rebuild cards
    if _container.get_child_count() != _display_mode:
        _container.clean()

        obj_style = _CARD_MODE_STYLES[_display_mode]
        # Create empty card objects
        for index in range(_display_mode):
            s_card = lv.obj(_container)
            s_card.set_size(*obj_style[0])
            s_card.set_scroll_dir(lv.DIR.VER)
            s_card.align(obj_style[1][index], 0, 0)
            s_card.set_style_radius(0, lv.PART.MAIN)
            s_card.set_style_pad_all(0, lv.PART.MAIN)
            s_card.remove_style(None, lv.STATE.PRESSED)
            s_card.remove_style(None, lv.STATE.FOCUS_KEY)
            s_card.set_style_border_width(0, lv.PART.MAIN)
            s_card.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
            s_card.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)


    # Reset device info map
    _devices_info = {}
    product_registry = product.get_product_registry()
    sensor_total = len(_selected_devices)
    group_index = _focus_index % _display_mode

    # Populate each card
    for index in range(_display_mode):
        s_card = _container.get_child(index)
        s_index = _focus_index + (index - group_index)

        # Apply focus background if needed
        bg_color = 0x5B5B5B if index == group_index and focus_style else 0x000000
        if _display_mode != _MODE_SINGLE: s_card.set_style_bg_color(lv.color_hex(bg_color), lv.PART.MAIN)

        # If beyond end, just clear the card
        if s_index == sensor_total:
            s_card.clean()
            tip_symbol = lv.label(s_card)
            tip_symbol.set_text("+")
            tip_symbol.set_style_text_font(lv.font_ascii_bold_48, lv.PART.MAIN)
            tip_symbol.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN)

            tip_label = lv.label(s_card)
            tip_label.set_text("Add a new sensor")
            tip_label.set_width(_CARD_MODE_STYLES[_display_mode][0][0])
            tip_label.set_style_text_font(lv.font_ascii_22, lv.PART.MAIN)
            tip_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN)

            tip_label.align(lv.ALIGN.CENTER, 0, 22)
            tip_symbol.align_to(tip_label, lv.ALIGN.OUT_TOP_MID, 0, -5)
            continue

        elif s_index > sensor_total:
            s_card.clean()
            s_card.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
            continue

        try:
            sensor = _selected_devices[s_index]
            model = product_registry.get(sensor["product_name"], None)
            if not model: continue
            if not hasattr(model, "show_card"): continue

            # Record last refresh time and snapshot of current data
            _devices_info[sensor["sensor_id"]] = {"refresh": time.ticks_ms(), "curr_info": {}}
            if hasattr(model, "get_sensor_data"): _devices_info[sensor["sensor_id"]]["curr_info"] = model.get_sensor_data(sensor["sensor_id"]).copy()

            # Call the brand-specific drawing method
            await model.show_card(s_card, sensor, _display_mode)
        except Exception as e:
            print(f"show card fail.[{str(e)}]")

    # Update focus timestamp
    _focus_time = time.ticks_ms()

async def show_home():
    """
    Build and display the home page:
        - Ensure there is at least one sensor.
        - Create the main container and optional dividing lines.
        - Render sensor cards without focus highlight initially.
    """
    global _container, _focus_index
    total = len(_selected_devices)
    if total < 1: return

    # Clear previous screen if any
    if _scr: _scr.clean()

    # Reset focus index if out of bounds
    if _focus_index > total: _focus_index = 0

    # Sync display mode with settings
    sync_display_mode()

    # Create container for sensor cards
    _container = lv.obj(_scr)
    _container.remove_style(None, lv.PART.MAIN)
    _container.remove_style(None, lv.PART.SCROLLBAR)
    _container.set_size(_SCR_WIDTH, _SCR_HEIGHT)
    _container.set_style_border_width(0, lv.PART.MAIN)
    _container.set_scroll_snap_y(lv.SCROLL_SNAP.CENTER)
    _container.set_style_bg_opa(lv.OPA._0, lv.PART.MAIN)
    _container.align(lv.ALIGN.BOTTOM_MID, 0, lv.PART.MAIN)
    _container.add_event_cb(event_handler, lv.EVENT.ALL, None)

    # Draw horizontal divider for dual/quad modes
    if _display_mode % 2 == 0:
        line_points = [{"x": 0, "y": 119}, {"x": 320, "y": 119}]
        line = lv.line(_scr)
        line.set_style_line_width(2, 0)
        line.set_points(line_points, len(line_points))  # Set the points
        line.set_style_line_color(lv.color_hex(0xBBBBBB), 0)

    # Draw vertical divider for quad mode
    if _display_mode % 4 == 0:
        line_points = [{"x": 159, "y": 0}, {"x": 159, "y": 240}]
        line = lv.line(_scr)
        line.set_style_line_width(2, 0)
        line.set_points(line_points, len(line_points))  # Set the points
        line.set_style_line_color(lv.color_hex(0xBBBBBB), 0)

    # Initial render without focus highlight
    await render_sensors(False)

    # Add container to input group and enable edit mode
    lv.group_get_default().add_obj(_container)
    lv.group_focus_obj(_container)
    lv.group_get_default().set_editing(True)

async def on_start(scr, app_mgr):
    """
    Called when the app starts:
        - Store screen and app manager references.
        - Check for selected sensors.
        - Register flash callback for active state.
        - Show the home page.
    """
    global _scr, _app_mgr
    _scr = scr
    _app_mgr = app_mgr

    # Ensure at least one sensor is selected
    if not check_selected_device(): return

    # Register callback to highlight active card
    for p_model in product.get_product_registry().values():
        if hasattr(p_model, "set_active_state_callback"):
            p_model.set_active_state_callback(flash_active_card)

    await show_home()

async def on_stop():
    """
    Called when the app stops:
        - Remove active-state callbacks.
        - Clean up screen and container.
    """
    global _scr, _container

    for p_model in product.get_product_registry().values():
        if hasattr(p_model, "set_active_state_callback"):
            p_model.set_active_state_callback(None)

    if _app_mgr: _app_mgr.leave_root_page()

    if _scr:
        _scr.clean()
        _scr = None
    _container = None

async def on_running_foreground():
    """
    Periodically called when app is in foreground:
        - For each visible sensor card:
            * Check if data has changed or 60s passed.
            * If so, update the card via `show_card`.
    """
    global _focus_time
    if not _container: return

    curr_time = time.ticks_ms()
    # Restore card background if focus highlight has expired
    if curr_time - _focus_time > _FOCUS_DURATION:
        d_color = lv.color_hex3(0x000)
        target = _container.get_child(_focus_index % _display_mode)
        if target.get_style_bg_color(lv.PART.MAIN) != d_color: target.set_style_bg_color(d_color, lv.PART.MAIN)
        _focus_time = curr_time

    # Update each displayed sensor card if needed
    for index, info in enumerate(get_display_sensors()):
        s_id = info["sensor_id"]
        s_info = _devices_info.get(s_id, {})
        s_card = _container.get_child(index)
        s_model = product.get_product_registry().get(info["product_name"], None)
        if not s_info or not s_model or not s_card: continue

        try:
            # Prepare new data snapshot
            tmp_info = {
                "refresh": curr_time,
                "curr_info": {}
            }

            if hasattr(s_model, "get_sensor_data"): tmp_info["curr_info"] = s_model.get_sensor_data(s_id).copy()

            # Only re-render if data changed or 60s elapsed
            if tmp_info["curr_info"] == s_info["curr_info"]:
                if tmp_info["refresh"] - s_info["refresh"] < 60000: continue

            await s_model.show_card(s_card, info, _display_mode)
            _devices_info[s_id] = tmp_info
        except Exception as e:
            print(f"show card fail.[{str(e)}]")

    await asyncio.sleep_ms(300)
