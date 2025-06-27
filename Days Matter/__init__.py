import net
import asyncio
from . import ui
import clocktime
import lvgl as lv
from . import base

# App Name
NAME = "Days Matter"

CAN_BE_AUTO_SWITCHED = True

# App Icon
ICON = "A:apps/Days Matter/resources/icon.png"

# Global variables for app state management
scr = None  # Main screen object
app_mgr = None  # App manager instance

label = None  # UI label reference
ui_state = 0  # Current UI state: 0=list view, 1=detail view
days_list = []  # List of formatted day strings for display
last_index = 0  # Last selected item index
last_data_time = 0  # Timestamp of last data update
target_time_list = []  # List of target events with time calculations

def get_settings_json():
    return {
        "form": [{
            "type": "group",
            "caption": "Event List",
            "name": "event_list",
            "template":{
                "template_name_default": "New Event",
                "template_config": [
                {
                    "type": "input",
                    "default": "",
                    "caption": "Target Day",
                    "name": "target_day",
                    "tip": "Enter the target date in the format of YYYY-MM-DD",
                    "attributes": {"placeholder": "e.g., YYYY-MM-DD"},
                },{
                    "type": "select",
                    "default": "0",
                    "caption": "Repeat",
                    "name": "target_day_repeat",
                    "options":[("Never", "0"),("Yearly", "1"),("Monthly", "2")],
                    "tip": "Select the frequency of the event. Never means the event will only happen once."
                }
            ]},
            "attributes": {"maxLength": 10},
        },{
            "type": "checkbox",
            "default": ["new_year"],
            "caption": "Default Target Date",
            "name": "preset_target_date",
            "options":[(data[1], data[0]) for data in base.PRESET_TARGET_LIST],
        },{ 
            "type": "select",
            "default": "Light",
            "caption": "UI style",
            "name": "style",
            "tip": "Select what color style you want",
            "options":[("Light", "light"), ("Dark", "dark")],
        }]
    }

def get_target_time_list():
    """
    Get target time configuration and build the list of events to track.
    Handles both preset events and custom user-defined events.
    """
    # Get target time configuration
    preset_target_list = app_mgr.config().get("preset_target_date", [])
    event_name = app_mgr.config().get("event_name", "")
    target_day = app_mgr.config().get("target_day", "")
    target_day_repeat = app_mgr.config().get("target_day_repeat", "0")
    event_list = app_mgr.config().get("event_list", [])

    if event_name and target_day:
        event_list.append({"template_name": event_name, "target_day": target_day, "target_day_repeat": target_day_repeat})
        app_mgr.config()["event_name"] = ""
        app_mgr.config()["target_day"] = ""
        app_mgr.config()["target_day_repeat"] = "0"
        app_mgr.config()["event_list"] = event_list

    target_time_list = []
    # Add preset events
    for key in preset_target_list:
        target_time_list.append(base.PRESET_TARGET_ITEM[key])

    # Add custom events
    for event in event_list:
        event_time = base.get_event_time(event.get("template_name", ""), event.get("target_day", ""), event.get("target_day_repeat",""))
        if event_time:
            target_time_list.append(event_time)

    # Default to New Year if no events configured
    if not target_time_list:
        target_time_list = [base.PRESET_TARGET_ITEM["new_year"]]
    return target_time_list

def draw_event_handler(e):
    """
    Handle events in the detail view (when showing specific event).
    Currently handles ESC key to return to list view.
    """
    global ui_state
    code = e.get_code()
    if code == lv.EVENT.KEY:
        e_key = e.get_key()
        if e_key == lv.KEY.ESC:
            ui_state = 0
            print("back to list")
            asyncio.create_task(ui.show_days_list(scr, last_index, days_list, handle_event_cb))

def handle_event_cb(e):
    """
    Handle events in the list view.
    Manages item selection, focus, and navigation between views.
    """
    global last_index, ui_state, app_mgr
    style = app_mgr.config().get("style", "light")
    code = e.get_code()
    target = e.get_target_obj()
    if code == lv.EVENT.CLICKED:
        # Switch to detail view when item is clicked
        index = e.get_target_obj().get_index()
        last_index = index
        ui_state = 1
        asyncio.create_task(ui.show_days_matter(scr, target_time_list[index]["name"], target_time_list[index]["days_remaining"], target_time_list[index]["show_time_tuple"], draw_event_handler))
    elif code == lv.EVENT.FOCUSED:
        # Highlight focused item
        target.set_style_bg_color(lv.color_hex(ui.STYLES[style]["focused"]), 0)
        target.scroll_to_view(lv.ANIM.OFF)
    elif code == lv.EVENT.DEFOCUSED:
        # Remove highlight from unfocused item
        target.set_style_bg_color(lv.color_hex(ui.STYLES[style]["defocused"]), 0)
        target.scroll_to_view(lv.ANIM.OFF)

async def update_ui(now):
    """
    Update the UI with latest time calculations.
    """
    global target_time_list, last_data_time, days_list
    local_time = clocktime.datetime()

    # Update if refresh interval passed or at midnight (for day changes)
    if now - last_data_time > base.REFRESH_INTERVAL or (local_time[3] == 0 and local_time[4] == 0 and local_time[5] == 5):
        target_time_list = get_target_time_list()
        new_days_list = base.updata_days_remaining(target_time_list)
        last_data_time = now

        # Only update UI if data actually changed
        if new_days_list != days_list:
            days_list = new_days_list
            print("update ui")
            if ui_state == 0:
                # Update list view
                asyncio.create_task(ui.show_days_list(scr, last_index, days_list, handle_event_cb))
            else:
                # Update detail view
                asyncio.create_task(ui.show_days_matter(scr, target_time_list[last_index]["name"], target_time_list[last_index]["days_remaining"], target_time_list[last_index]["show_time_tuple"], draw_event_handler))

async def init():
    """
    Initialize the app and display initial UI.
    Shows error message if time is not synced.
    """
    global target_time_list, days_list, ui_state
    if clocktime.now() != -1:
        # Time is synced, proceed with normal initialization
        target_time_list = get_target_time_list()
        days_list = base.updata_days_remaining(target_time_list)
        await ui.show_days_list(scr, last_index, days_list, handle_event_cb)
    else:
        # Time not synced, show error
        await ui.show_error_msg(scr, "Time not synced.")

async def on_boot(apm):
    """
    App lifecycle: Called when app is first loaded.
    """
    global app_mgr
    app_mgr = apm
    await ui.on_boot(apm)

async def on_stop():
    """
    App lifecycle: Called when user leaves this app.
    Cleans up resources and UI elements.
    """
    global scr
    print('on stop')
    if scr:
        scr.clean()
        del scr
        scr = None

async def on_start():
    """
    App lifecycle: Called when user enters this app.
    Sets up the main screen and initializes the UI.
    """
    global scr, label
    app_mgr.enter_root_page()
    print('on start')

    # Create and configure main screen
    scr = lv.obj()
    scr.set_size(base.SCR_WIDTH, base.SCR_HEIGHT)

    # Load the LVGL widgets and initialize app
    lv.scr_load(scr)
    await init()

async def on_running_foreground():
    """
    App lifecycle: Called periodically when app is in foreground.
    """
    now = clocktime.now()
    if net.connected() and now != -1:
        # log.debug("@{}".format(now))
        await update_ui(now)
