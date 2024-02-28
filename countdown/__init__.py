import time
import lvgl as lv

# App Name
NAME = "Countdown of App"

# LVGL widgets
scr = None
label = None

# Countdown parameters
DEFAULT_REMAINDER = 30
remainder = DEFAULT_REMAINDER

app_manager = None
last_recorded_time = 0
countdown_is_running = False

def get_settings_json():
    return {
        "category": "Other",
        "form": [{
            "type": "input",
            "default": str(DEFAULT_REMAINDER),
            "caption": "Countdown Timer Duration(s)",
            "name": "remainder",
            "attributes": {"maxLength": 6, "placeholder": "e.g., 300"},
        }]
    }

def reset_countdown():
    global remainder, countdown_is_running, last_recorded_time
    last_recorded_time = 0
    countdown_is_running = False
    remainder = int(app_manager.config().get("remainder", DEFAULT_REMAINDER))

def update_label():
    global label, remainder
    if label:
        label.set_text("{:02d}:{:02d}".format(remainder // 60, remainder % 60))

def event_handler(event):
    e_code = event.get_code()
    if e_code == lv.EVENT.KEY:
        e_key = event.get_key()
        if e_key == lv.KEY.ENTER:
            global countdown_is_running, last_recorded_time
            last_recorded_time = time.ticks_ms()
            countdown_is_running = not countdown_is_running

async def on_boot(app_mgr):
    """Called right after system boot."""
    global app_manager
    app_manager = app_mgr

async def on_stop():
    print('on stop')
    global scr
    if scr:
        scr.clean()
        scr.del_async()
        scr = None
    reset_countdown()

async def on_start():
    print('on start')
    global scr, label
    reset_countdown()

    scr = lv.obj()
    lv.scr_load(scr)

    label = lv.label(scr)
    update_label()
    label.center()

    scr.add_event(event_handler, lv.EVENT.ALL, None)

    group = lv.group_get_default()
    if group:
        group.add_obj(scr)
        lv.group_focus_obj(scr)
        group.set_editing(True)

async def on_running_foreground():
    """Called when the app is active, approximately every 200ms."""
    global remainder, last_recorded_time
    if not countdown_is_running or remainder <= 0:
        return

    current_time = time.ticks_ms()
    elapsed_time = time.ticks_diff(current_time, last_recorded_time) // 1000
    if elapsed_time > 0:
        remainder -= elapsed_time
        last_recorded_time = current_time
        remainder = max(remainder, 0)
        update_label()

