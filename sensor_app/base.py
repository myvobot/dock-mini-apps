import asyncio
import lvgl as lv
from . import product
from . import ui_page
from . import bluetooth

_PAGE_HOME = 0       # Home page
_PAGE_HISTORY = 1    # History data page
_PAGE_DETAILS = 2    # Device details page
_PAGE_TIPS = 3        # Tip page
_MAX_SELECTABLE = 8  # Maximum selectable count

_scr = None             # Initialize screen variable
_app_mgr = None         # Initialize app manager variable
_product_registry = {}  # Store product models information
_curr_page = _PAGE_HOME  # Current displayed page
_customize_font = {}    # Custom font handles

def load_font():
    """Load custom binary fonts."""
    try:
        _customize_font["probe_font"] = lv.binfont_create(
            "A:/apps/sensor_app/asset/font/font_probe_icon.bin"
        )
    except Exception as e:
        print(f"load font failed: {str(e)}")

def destroy_font():
    """Destroy all loaded binary fonts."""
    global _customize_font
    try:
        for font in _customize_font.values():
            lv.binfont_destroy(font)
        _customize_font = {}
    except Exception as e:
        print(f"destory font failed: {str(e)}")

async def init():
    """Initialize BLE callbacks and start scanning."""
    global _curr_page
    gap_name_callbacks = {}
    config = _app_mgr.config()
    selected_devices = config.get("selected", [])
    if not selected_devices:
        _curr_page = _PAGE_TIPS
        await page_access("on_start", _scr, _app_mgr)
        return

    # Collect and synchronize GAP name callbacks from each product model
    for p_name, p_model in _product_registry.items():
        if hasattr(p_model, "get_gap_name_callbacks"):
            gap_name_callbacks.update(p_model.get_gap_name_callbacks())

        if hasattr(p_model, "sync_selected_device"):
            p_model.sync_selected_device([dev["sensor_id"] for dev in selected_devices if "sensor_id" in dev and p_name == dev.get("product_name", "")])

    bluetooth.set_gap_name_callbacks(gap_name_callbacks)
    await bluetooth.start_scan()
    # Trigger UI page on_start handler
    await page_access("on_start", _scr, _app_mgr)

async def search_nearby_sensors(product_name, dev_model=None):
    """Scan nearby sensors for a given product."""
    if product_name not in _product_registry: return []

    p_model = _product_registry[product_name]
    if not hasattr(p_model, "get_sensor_found"): return []

    if hasattr(p_model, "get_gap_name_callbacks"):
        bluetooth.set_gap_name_callbacks(p_model.get_gap_name_callbacks())

    await bluetooth.start_scan(5000, 1)
    await bluetooth.wait_scan_complete()
    return p_model.get_sensor_found(dev_model)

def get_page_module(page=None):
    """Return the UI page module based on page index."""
    if page is None: page = _curr_page
    target = None
    if page == _PAGE_HOME: target = ui_page.home
    elif page == _PAGE_TIPS: target = ui_page.tips
    elif page == _PAGE_HISTORY: target = ui_page.history
    elif page == _PAGE_DETAILS: target = ui_page.details
    else: print(f"Unkown page: {page}")
    return target

async def page_access(handler, *args, **kwargs):
    """Call the specified handler on the current UI page."""
    try:
        page_module = get_page_module()
        if not page_module: return
        await getattr(page_module, handler)(*args, **kwargs)
    except AttributeError: pass # Handler not implemented for this page
    except Exception as e:
        print(f"page access failed: {str(e)}")

async def switch_page(page, *args, **kwargs):
    """Stop current page, switch index, then start new page."""
    global _curr_page
    try:
        await page_access("on_stop")
        _curr_page = page
        await page_access("on_start", _scr, _app_mgr, *args, **kwargs)
    except Exception as e:
        print(f"switch page failed: {str(e)}")

async def on_start():
    """App entry point: create screen and show loading UI."""
    global _scr
    if not _scr:
        _scr = lv.obj()
        _scr.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
        _app_mgr.enter_root_page()
        lv.screen_load(_scr)

    # Draw initialization screen
    loading = lv.label(_scr)
    loading.set_text("Initializing...")
    loading.set_style_text_font(lv.font_ascii_22, lv.PART.MAIN)
    loading.center()

    load_font()
    # Kick off BLE and page init asynchronously
    asyncio.create_task(init())

async def on_stop():
    """Tear down screen and BLE, then reset state."""
    global _scr, _curr_page

    if _scr: _scr.clean()
    exiting = lv.label(_scr)
    exiting.set_text("Exiting...")
    exiting.set_style_text_font(lv.font_ascii_22, lv.PART.MAIN)
    exiting.center()

    # Disable BLE scanning
    await bluetooth.stop_scan()

    # Clean up screen object
    if _scr:
        _scr.clean()
        _scr.delete_async()
        _scr = None
        _app_mgr.leave_root_page()

    # Ensure page-specific on_stop is called
    await page_access("on_stop")
    _curr_page = _PAGE_HOME
    destroy_font()
    bluetooth.set_gap_name_callbacks({})

    for p_name, p_model in _product_registry.items():
        if hasattr(p_model, "sync_selected_device"): p_model.sync_selected_device([])

async def on_boot(apm):
    """Initialize app manager and load product info & history."""
    global _app_mgr, _product_registry
    _app_mgr = apm
    await page_access("on_boot")

    _product_registry = product.get_product_registry()
    # Preload history data for each sensor model
    for p_name, p_model in _product_registry.items():
        if hasattr(p_model, "load_sensor_history_data"):
            p_model.load_sensor_history_data()

async def on_running_foreground():
    """Handle actions when the app is running in the foreground."""
    await page_access("on_running_foreground")
