import asyncio
import lvgl as lv
import peripherals
from .. import base

# Get the screen resolution from peripherals
_SCR_WIDTH, _SCR_HEIGHT = peripherals.screen.screen_resolution

# Global references for screen, app manager and main container
_scr = None
_app_mgr = None
_container = None

def event_handler(e):
    """
    Handle LVGL events for the tips page.
        - ESC key: go back or exit the app.
        - FOCUSED: enable edit mode when the container is focused.
    """
    e_code = e.get_code()
    if e_code == lv.EVENT.KEY:
        e_key = e.get_key()
        if e_key == lv.KEY.ESC:
            # If no sensor is selected, exit the app; otherwise switch to home page
            if not _app_mgr.config().get("selected", []): asyncio.create_task(_app_mgr.exit())
            else: asyncio.create_task(base.switch_page(base._PAGE_HOME))
    elif e_code == lv.EVENT.FOCUSED:
        lv_group = lv.group_get_default()
        # If focused object is not our container, ignore
        if lv_group.get_focused() != e.get_target_obj(): return
        # If the group is not in edit mode, enable edit mode
        if not lv_group.get_editing(): lv_group.set_editing(True)

def display_tips():
    """
    Build and display the tips UI on the current screen.
    This includes a title, content message, navigation path, and a styled span note.
    """
    global _container
    # If container already exists, clear its children
    if _container: _container.clean()

    # Create a full-screen container
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

    # Title label at top center
    title = lv.label(_container)
    title.set_text("Tips")
    title.align(lv.ALIGN.TOP_MID, 0, 0)
    title.set_style_text_font(lv.font_ascii_bold_28, lv.PART.MAIN)
    title.set_style_text_color(lv.color_hex(0x007BFF), lv.PART.MAIN)

    # Main content message
    content = lv.label(_container)
    content.set_width(_SCR_WIDTH - 20)
    content.set_text("Please go to the application configuration page to select the Sensor.")
    content.align(lv.ALIGN.TOP_MID, 0, 40)

    # Path title label
    path_title = lv.label(_container)
    path_title.set_text("Path:")
    path_title.align_to(content, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 10)

    # Path detail label with highlighted color
    path = lv.label(_container)
    path.set_text("Settings App -> Application Settings")
    path.set_style_text_color(lv.color_hex(0x00B68A), lv.PART.MAIN)
    path.align_to(path_title, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 0)

    # Span group at bottom to show max selectable sensors note
    spangroup = lv.spangroup(_container)
    spangroup.align(lv.ALIGN.BOTTOM_MID, 0, 0)
    spangroup.set_size(_SCR_WIDTH - 10, _SCR_HEIGHT // 5)
    spangroup.set_style_text_font(lv.font_ascii_14, lv.PART.MAIN)
    spangroup.set_style_text_color(lv.color_hex(0x6C757D), lv.PART.MAIN)

    # Static text span
    span = spangroup.new_span()
    span.set_text("You can select a maximum of ")

    # Dynamic span for number of selectable sensors
    span = spangroup.new_span()
    span_style = span.get_style()
    span_style.set_text_font(lv.font_ascii_bold_18)
    span.set_text(f"{base._MAX_SELECTABLE} Sensors")
    span_style.set_text_color(lv.color_hex(0x007BFF))
    span_style.set_text_decor(lv.TEXT_DECOR.UNDERLINE)

    # Closing text span
    span = spangroup.new_span()
    span.set_text(" at the same time.")

    # Add container to default group and enable editing mode
    lv.group_get_default().add_obj(_container)
    lv.group_get_default().set_editing(True)

async def on_start(scr, app_mgr):
    """
    Initialization when the tips page starts:
        - Store screen and app manager references.
        - Display the tips UI.
    """
    global _scr, _app_mgr
    _scr = scr
    _app_mgr = app_mgr
    if app_mgr: app_mgr.leave_root_page()

    display_tips()

async def on_stop():
    """
    Cleanup when the tips page stops:
        - Clear the screen and reset globals.
    """
    global _scr, _container

    if _app_mgr: _app_mgr.enter_root_page()

    if _scr:
        _scr.clean()
        _scr = None
    _container = None
