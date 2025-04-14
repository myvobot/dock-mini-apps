import time
import asyncio
import lvgl as lv
import peripherals
from . import base

NAME = "Pomodoro Timer"
CAN_BE_AUTO_SWITCHED = False # Whether the App supports auto-switching in carousel mode

_SCR_WIDTH, _SCR_HEIGHT = peripherals.screen.screen_resolution  # Get the screen size from peripherals

_scr = None  # Initialize screen variable
_app_mgr = None  # Initialize app manager variable
_pomo_timer = None # pomodoroTimer object
_pause_screen = None # Widget for pause screen


def get_settings_json():
    # Return settings configuration for the app
    return {
        "category": "Lifestyle",
        "form": [{
            "type": "input",
            "default": "25",
            "caption": "Focus Time (min)",
            "name": "focus",
            "attributes": {"maxLength": 25, "placeholder": ""},
            "tip": "",
        },{
            "type": "input",
            "default": "5",
            "caption": "Short Break Time (min)",
            "name": "break",
            "attributes": {"maxLength": 25, "placeholder": ""},
            "tip": "",
        },{
            "type": "input",
            "default": "30",
            "caption": "Long Break Time (min)",
            "name": "long_break",
            "attributes": {"maxLength": 25, "placeholder": ""},
            "tip": "After Work Cycle",
        }]
    }

async def hints_of_completion(times):
    # Screen and buzzer execute 'times' cycles of notification [screen off + buzzer on -> screen on + buzzer off]
    buzzer = peripherals.buzzer
    screen = peripherals.screen
    # Get current screen brightness
    prev_light = screen.brightness()
    # Acquire buzzer control
    buzzer.acquire()
    for i in range(times):
        screen.brightness(0)
        if buzzer.enabled: buzzer.set_volume(100)
        await asyncio.sleep_ms(250)
        screen.brightness(prev_light)
        if buzzer.enabled: buzzer.set_volume(0)
        # No need to wait after the last cycle
        if i < times - 1: await asyncio.sleep_ms(250)
    # Release buzzer control
    buzzer.release()

def update_pause_screen(pause, show_icon=True):
    # Show/remove pause screen
    global _pause_screen
    if pause:
        # Show pause screen
        if _pause_screen: _pause_screen.clean()

        _pause_screen = lv.obj(_scr)
        _pause_screen.set_size(_SCR_WIDTH, _SCR_HEIGHT)
        _pause_screen.set_style_border_width(0, lv.PART.MAIN)
        _pause_screen.set_style_bg_opa(lv.OPA._0, lv.PART.MAIN)
        _pause_screen.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
        _pause_screen.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)

        # Button guide icon
        _label = lv.label(_pause_screen)
        _label.set_text(lv.SYMBOL.PLAY)
        _label.align(lv.ALIGN.RIGHT_MID, 8, -70)

        _pomo_timer.toggle_state(_pomo_timer.STATE_PAUSED)
        # Check if pause icon should be displayed
        if not show_icon: return
        _pause_screen.set_style_bg_opa(lv.OPA._70, lv.PART.MAIN)

        icon_bytes_data = lv.image_dsc_t({'data_size': len(base._PAUSE_ICON), 'data': base._PAUSE_ICON})
        lv_img = lv.image(_pause_screen)
        lv_img.set_src(icon_bytes_data)
        lv_img.center()

    else:
        # Remove pause screen
        if _pause_screen:
            _pause_screen.clean()
            _pause_screen.delete_async()
            _pause_screen = None

        _pomo_timer.toggle_state(_pomo_timer.STATE_RUNNING)

def display_pomodoro_ui():
    # Display pomodoro timer UI
    if not _scr: return
    _scr.clean()

    # Get current mode/remaining time/completed focus sessions
    done_times = _pomo_timer.work_sessions
    config = _pomo_timer.mode_config[_pomo_timer.curr_mode]
    minute, second = divmod(_pomo_timer.remaining_time, 60)

    # Display current mode
    mode_label = lv.label(_scr)
    mode_label.set_text(config["label"])
    mode_label.align(lv.ALIGN.TOP_MID, 0, 2)
    mode_label.set_style_text_font(lv.font_ascii_22, lv.PART.MAIN)
    mode_label.set_style_text_color(lv.color_hex(0x0BB4ED), lv.PART.MAIN)

    # Display remaining time
    countdown = lv.label(_scr)
    countdown.align(lv.ALIGN.CENTER, 0, -20)
    countdown.set_text(f"{minute:02d}:{second:02d}")
    countdown.set_style_text_font(lv.font_numbers_92, lv.PART.MAIN)

    # Display tomato icons to show completed focus sessions
    icons_container = lv.obj(_scr)
    icons_container.set_size(260, 47)
    icons_container.align(lv.ALIGN.CENTER, 0, 68)
    icons_container.remove_flag(lv.obj.FLAG.SCROLLABLE)
    icons_container.set_style_pad_column(19, lv.PART.MAIN)
    icons_container.set_style_border_width(0, lv.PART.MAIN)
    icons_container.set_style_bg_opa(lv.OPA._0, lv.PART.MAIN)
    icons_container.set_style_layout(lv.LAYOUT.FLEX, lv.PART.MAIN)
    icons_container.set_style_flex_flow(lv.FLEX_FLOW.COLUMN_WRAP, lv.PART.MAIN)
    icons_container.set_style_flex_main_place(lv.FLEX_ALIGN.SPACE_EVENLY, lv.PART.MAIN)

    icon_bytes_data = lv.image_dsc_t({'data_size': len(base._POMODORO), 'data': base._POMODORO})
    icon_done_bytes_data = lv.image_dsc_t({'data_size': len(base._POMODORO_DONE), 'data': base._POMODORO_DONE})
    for i in range(done_times): lv.image(icons_container).set_src(icon_done_bytes_data)
    for i in range(_pomo_timer.SHORT_LIMIT + 1 - done_times): lv.image(icons_container).set_src(icon_bytes_data)

def event_handler(e):
    # Event callback for _scr widget
    code = e.get_code()
    if code == lv.EVENT.CLICKED:
        # Pause/resume countdown
        if _pomo_timer.is_paused: _pomo_timer.recorded_time = time.ticks_ms() // 1000
        update_pause_screen(not _pomo_timer.is_paused, True)

    elif code == lv.EVENT.FOCUSED:
        lv_group = lv.group_get_default()
        if lv_group.get_focused() != e.get_target_obj(): return
        # If the group is not in edit mode, set it to edit mode
        if not lv_group.get_editing(): lv_group.set_editing(True)

def choose_cb(res):
    # App notification event callback
    if res == lv.KEY.ENTER:
        # Keep previous info and continue countdown
        _pomo_timer.recorded_time = time.ticks_ms() // 1000
        display_pomodoro_ui()
        update_pause_screen(False)
    else:
        # Reset previous info and restart countdown
        _pomo_timer.reset()
        display_pomodoro_ui()
        update_pause_screen(True, False)

async def on_start():
    """Initialize the screen and load the UI when the app starts."""
    global _scr
    if not _scr:
        _scr = lv.obj()  # Create a new screen object
        _app_mgr.enter_root_page()  # Enter the root page of the app manager
        lv.screen_load(_scr)  # Load the screen

    _scr.add_event_cb(event_handler, lv.EVENT.ALL, None)
    _scr.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)  # Set background color to black

    lv.group_get_default().add_obj(_scr)
    lv.group_focus_obj(_scr)
    lv.group_get_default().set_editing(True)

    # Load app configuration
    _pomo_timer.load_config()
    if _pomo_timer.has_pending:
        # If there's previous session info, ask whether to continue
        _app_mgr.error("Unfinished Pomodoro",
                        "Would you like to continue where you left off, or start a new cycle?",
                        confirm = "Continue", cancel = "Reset", cb = choose_cb)

    else:
        # Display main page
        display_pomodoro_ui()
        update_pause_screen(True, False)

async def on_stop():
    """Clean up the screen and leave the app when it stops."""
    global _scr, _pause_screen
    if _scr:
        _scr.clean()  # Clean the screen
        _scr.delete_async()  # Delete the screen asynchronously
        _scr = None  # Reset the screen variable
        _app_mgr.leave_root_page()  # Leave the root page of the app manager

    # Set current state to 'paused'
    _pause_screen = None
    _pomo_timer.toggle_state(_pomo_timer.STATE_PAUSED)

async def on_boot(apm):
    """Initialize the app manager on boot."""
    global _app_mgr, _pomo_timer
    _app_mgr = apm  # Set the app manager
    _pomo_timer = base.pomodoroTimer(apm) # Instantiate pomodoroTimer class


async def on_running_foreground():
    """Handle actions when the app is running in the foreground."""
    # If main interface is not displayed or timer is paused, don't update
    if _scr.get_child_count() < 3 or _pomo_timer.is_paused: return

    now = time.ticks_ms() // 1000
    elapsed_time = now - _pomo_timer.recorded_time
    if elapsed_time > 0:
        # Update countdown text and tomato icons
        _pomo_timer.remaining_time -= elapsed_time
        _pomo_timer.recorded_time = now # Update last recorded time
        if _pomo_timer.remaining_time < 0: _pomo_timer.remaining_time = 0 # If remaining time < 0, set to 0
        # Update remaining time
        minute, second = divmod(_pomo_timer.remaining_time, 60)
        _scr.get_child(1).set_text(f"{minute:02d}:{second:02d}")

    if _pomo_timer.remaining_time <= 0:
        # If remaining time <= 0, notify and switch to next mode
        asyncio.create_task(hints_of_completion(5))
        _pomo_timer.handle_mode_change()
        display_pomodoro_ui()
        update_pause_screen(_pomo_timer.is_paused, False)
