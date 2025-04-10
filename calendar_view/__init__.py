import asyncio
import clocktime
import lvgl as lv
import peripherals

NAME = "Calendar View"
CAN_BE_AUTO_SWITCHED = True  # Indicates if the app can be auto-switched

_INVALID_TIME = -1  # Invalid time
_MAX_YEAR_DIFF = 5  # Maximum year difference
_SCR_WIDTH, _SCR_HEIGHT = peripherals.screen.screen_resolution  # Get the screen size from peripherals
_MON_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]  # Month abbreviations

_scr = None  # Initialize screen variable
_app_mgr = None  # Initialize app manager variable
_cur_date = None  # Current date
_disp_date = None  # Display date
_is_cur_month = True  # Flag to track if current month is displayed

def get_settings_json():
    return {
        "category": "Lifestyle",
        "form": [{
            "type": "radio",
            "default": "Sun",
            "caption": "First Day of the Week",
            "name": "week_start_day",
            "tip": "Select the day to start the week for the calendar display.",
            "options":[("Monday", "Mon"), ("Sunday", "Sun")],
        }]
    }

def check_current_time():
    """
    Checks if the current time is valid.
    Returns True if valid, otherwise shows an error and exits the app.
    """
    if clocktime.now() != _INVALID_TIME: return True

    _app_mgr.error( \
        "Invalid Time", \
        "The current time is invalid.\nPlease wait until the time is valid before entering the app.", \
        confirm=False, cb=lambda res: asyncio.create_task(_app_mgr.exit()))
    return False

def _draw_event_cb(e):
    """
    Callback for drawing events in the calendar.
    Handles custom styling for calendar items.
    """
    obj = e.get_target_obj()
    draw_task = e.get_draw_task()
    dsc = lv.draw_dsc_base_t.__cast__(draw_task.get_draw_dsc())
    # When the button matrix draws the buttons...
    if dsc.part != lv.PART.ITEMS: return
    if dsc.id1 < 7: return

    _label_dsc = draw_task.get_label_dsc()
    label_draw_dsc = lv.draw_label_dsc_t.__cast__(_label_dsc)

    if obj.has_button_ctrl(dsc.id1, lv.buttonmatrix.CTRL.CUSTOM_1):
        _fill_dsc = draw_task.get_fill_dsc()
        if not _fill_dsc: return

        # Modify the current date style
        draw_fill_dsc = lv.draw_fill_dsc_t.__cast__(_fill_dsc)
        draw_fill_dsc.init()
        draw_fill_dsc.radius = 5
        draw_fill_dsc.opa = lv.OPA._100
        draw_fill_dsc.color = lv.color_hex(0x0BB4ED)
    elif obj.has_button_ctrl(dsc.id1, lv.buttonmatrix.CTRL.DISABLED) and _label_dsc:
        # Adjust the style of dates that are not the current month
        label_draw_dsc.color = lv.color_hex(0x505050)

def event_handler(e):
    e_code = e.get_code()
    if e_code == lv.EVENT.KEY:
        global _disp_date, _is_cur_month
        date = _disp_date.copy()
        e_key = e.get_key()
        if e_key == lv.KEY.LEFT:
            # Show the previous month
            if date[1] > 1:
                date[1] -= 1
            else:
                date[1] = 12
                date[0] -= 1

        elif e_key == lv.KEY.RIGHT:
            # Show the next month
            if date[1] < 12:
                date[1] += 1
            else:
                date[1] = 1
                date[0] += 1

        # If the year difference is greater than _MAX_YEAR_DIFF, do not update the date
        if abs(date[0] - _cur_date[0]) > _MAX_YEAR_DIFF: return

        # If the date is the same as the current date, update the today's date
        if date[:2] == list(_cur_date[:2]):
            _scr.get_child(2).set_today_date(*date[:3])

        # Set and display the current date
        _scr.get_child(2).set_showed_date(*date[:2])
        _scr.get_child(0).set_text(f"{_MON_ABBR[date[1] - 1]}, {date[0]}")
        _disp_date = date

        if date[:3] == list(_cur_date[:3]):
            _is_cur_month = True
        else:
            _is_cur_month = False

    elif e_code == lv.EVENT.FOCUSED:
        lv_group = lv.group_get_default()
        if lv_group.get_focused() != e.get_target_obj(): return
        # If the group is not in edit mode, set it to edit mode
        if not lv_group.get_editing(): lv_group.set_editing(True)

async def create_calendar_view():
    """
    Creates and initializes the calendar view UI.
    Sets up the date label, divider line, and calendar widget.
    """
    global _scr, _cur_date, _disp_date, _is_cur_month

    # Clean the screen if it exists
    if _scr: _scr.clean()

    # Get the start day of the week from the settings
    if not _app_mgr: start_day = "Sun"
    else: start_day = _app_mgr.config().get("week_start_day", "Sun")
    lv.calendar.set_week_starts_monday(start_day == "Mon")

    # Set the current date and display date
    _cur_date = clocktime.datetime()
    _disp_date = list(_cur_date)

    # Create and align the date label
    date_label = lv.label(_scr)
    date_label.align(lv.ALIGN.TOP_MID, 0, 2)
    date_label.set_style_text_font(lv.font_ascii_22, lv.PART.MAIN)
    date_label.set_text(f"{_MON_ABBR[_cur_date[1] - 1]}, {_cur_date[0]}")
    date_label.set_style_text_color(lv.color_hex(0x0BB4ED), lv.PART.MAIN)

    # Create and align the divider line
    points = [{"x":3, "y":65}, {"x":_SCR_WIDTH - 3, "y":65}]
    divider = lv.line(_scr)
    divider.set_points(points, len(points))

    # Create and align the calendar widget
    cal = lv.calendar(_scr)
    cal.align(lv.ALIGN.BOTTOM_MID, 0, 0)
    cal.set_size(_SCR_WIDTH, _SCR_HEIGHT - 30)
    cal.set_style_border_width(0, lv.PART.MAIN)
    cal.set_style_bg_opa(lv.OPA._0, lv.PART.MAIN)
    cal.add_flag(lv.obj.FLAG.SEND_DRAW_TASK_EVENTS)
    cal.add_event_cb(event_handler, lv.EVENT.ALL, None)
    cal.get_btnmatrix().set_style_border_width(0, lv.PART.ITEMS)
    cal.get_btnmatrix().set_style_text_font(lv.font_ascii_22, 0)
    cal.get_btnmatrix().add_event_cb(_draw_event_cb, lv.EVENT.DRAW_TASK_ADDED, None)

    # Set the today's date and the displayed date
    cal.set_today_date(*_cur_date[:3])
    cal.set_showed_date(*_cur_date[:2])
    _is_cur_month = True

    # Remove the group from the calendar button matrix
    lv.group_remove_obj(cal.get_btnmatrix())

async def on_start():
    """Initialize the screen and load the UI when the app starts."""
    global _scr
    if not _scr:
        _scr = lv.obj()
        _scr.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
        _app_mgr.enter_root_page()
        lv.screen_load(_scr)

    # Check if the current time is valid
    if not check_current_time(): return

    # Create the calendar view
    await create_calendar_view()

async def on_stop():
    """Clean up the screen and leave the app when it stops."""
    global _scr
    if _scr:
        _scr.clean()
        _scr.delete_async()
        _scr = None
        _app_mgr.leave_root_page()

async def on_boot(apm):
    """Initialize the app manager on boot."""
    global _app_mgr
    _app_mgr = apm

async def on_running_foreground():
    """
    Handle actions when the app is running in the foreground.
    Updates the calendar if the date has changed.
    """
    global _cur_date, _disp_date, _is_cur_month
    if not _scr: return
    if _scr.get_child_count() < 3: return

    date = clocktime.datetime()
    # If the date is the same as the current date, do not update the date
    if _cur_date[:3] == date[:3]: return

    # If the year difference is greater than _MAX_YEAR_DIFF + 1, update the date
    if abs(date[0] - _cur_date[0]) > _MAX_YEAR_DIFF + 1:
        _disp_date = list(date)
        _is_cur_month = True

    # If the current month is displayed, update the date label and calendar
    if _is_cur_month:
        if _cur_date[:2] != date[:2]:
            _scr.get_child(0).set_text(f"{_MON_ABBR[date[1] - 1]}, {date[0]}")

        _scr.get_child(2).set_today_date(*date[:3])
        _scr.get_child(2).set_showed_date(*date[:2])

    _cur_date = date
