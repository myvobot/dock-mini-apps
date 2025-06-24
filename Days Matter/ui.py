import lvgl as lv
from . import base

app_mgr = None

async def show_days_matter(parent, name, days, time_tuple, handle_event_cb):
    """
    Display detailed view for a single date event.

    Args:
        parent: Parent container
        name: Event name
        days: Days remaining/elapsed
        time_tuple: Date tuple
        handle_event_cb: Event handler callback
    """
    if parent: parent.clean()
    app_mgr.leave_root_page()

    # Determine display style based on whether event is past or future
    if days < 0:
        # Past event - orange theme
        name_obj_color = lv.color_hex(0xFF8C00)
        time_tuple_text = f'Start Date: {time_tuple[0]}-{time_tuple[1]}-{time_tuple[2]}'
        tip_text = f"It has been {abs(days)} days since the {name} started."
        days = abs(days)
    else:
        # Future event or today - blue theme
        name_obj_color = lv.color_hex(0x1E90FF)
        time_tuple_text = f'Target Day: {time_tuple[0]}-{time_tuple[1]}-{time_tuple[2]}'
        if days == 0:
            tip_text = f"Today is {name}."
        else:
            tip_text = f"There are {abs(days)} days left until {name}."

    # Main container setup
    container = lv.obj(parent)
    container.set_style_radius(0, 0)
    container.set_style_pad_all(0, 0)
    container.set_style_border_width(0, 0)
    container.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    container.set_size(base.SCR_WIDTH, base.SCR_HEIGHT)
    container.set_style_bg_color(lv.color_hex3(0xFFFFFF), 0)
    container.add_event_cb(handle_event_cb, lv.EVENT.ALL, None)

    name_obj = lv.obj(container)
    name_obj.set_style_radius(0, 0)
    name_obj.set_style_pad_all(0, 0)
    name_obj.set_style_border_width(0, 0)
    name_obj.set_size(base.SCR_WIDTH, 40)
    name_obj.set_style_bg_color(name_obj_color, 0)
    name_obj.align(lv.ALIGN.TOP_MID, 0, 0)

    name_label = lv.label(name_obj)
    name_label.set_text(name)
    name_label.set_size(base.SCR_WIDTH, 40)
    name_label.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
    name_label.set_style_text_font(lv.font_ascii_bold_28, 0)
    name_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    name_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
    name_label.align(lv.ALIGN.CENTER, 0, 0)

    tip_label = lv.label(container)
    tip_label.set_text(tip_text)
    tip_label.set_size(base.SCR_WIDTH, 40)
    tip_label.set_style_text_font(lv.font_ascii_14, 0)
    tip_label.set_style_text_color(lv.color_hex(0xC0C0C0), 0)
    tip_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    tip_label.align_to(name_obj, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)

    if days == 0:
        days_text = "Today"
    else:
        days_text = f'{days}'
    days_label = lv.label(container)
    days_label.set_text(days_text)
    if days_text == "Today":
        days_label.set_style_text_font(lv.font_ascii_bold_48, 0)
    else:
        days_label.set_style_text_font(lv.font_numbers_92, 0)
    days_label.set_style_text_color(lv.color_hex(0x303030), 0)
    days_label.align(lv.ALIGN.CENTER, 0, 15)

    # Date information at bottom
    time_tuple_label = lv.label(container)
    time_tuple_label.set_text(time_tuple_text)
    time_tuple_label.set_style_text_font(lv.font_ascii_18, 0)
    time_tuple_label.set_style_text_color(lv.color_hex(0xC0C0C0), 0)
    time_tuple_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
    time_tuple_label.align(lv.ALIGN.BOTTOM_MID, 0, -10)

    # Focus on the sub-page
    lv.group_get_default().add_obj(container)
    lv.group_get_default().set_editing(True)

async def _show_one_days(parent, days_info, handle_event_cb):
    """
    Create a single day item in the list view.

    Args:
        parent: Parent container
        days_info: Dictionary containing day information
        handle_event_cb: Event handler callback

    Returns:
        Button object representing the day item
    """
    # Main button container for the day item
    tasks_btn = lv.button(parent)
    tasks_btn.set_size(base.SCR_WIDTH, 40)
    tasks_btn.set_style_border_width(0, 0)
    tasks_btn.set_style_radius(0, 0)
    tasks_btn.remove_style(None, lv.STATE.PRESSED)
    tasks_btn.remove_style(None, lv.STATE.FOCUS_KEY)
    tasks_btn.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
    tasks_btn.add_event_cb(handle_event_cb, lv.EVENT.ALL, None)

    # Event name label
    lv_label = lv.label(tasks_btn)
    lv_label.set_text(days_info["name"])
    lv_label.set_style_text_font(lv.font_ascii_18, 0)
    lv_label.set_style_text_color(lv.color_hex(0x000000), lv.PART.MAIN)
    lv_label.align_to(tasks_btn, lv.ALIGN.LEFT_MID, 0, 0)
    lv_label.set_size(200, 40)
    lv_label.set_long_mode(lv.label.LONG.DOT)

    # Determine display style and colors based on days remaining
    if days_info["days_remaining"] < 0:
        # Past event - orange theme
        days_text = f"{abs(days_info['days_remaining'])}"
        days_color = lv.color_hex(0xFFA500)
        days_text_color = lv.color_hex(0xFF8C00)
        days_text_width = 65
    elif days_info['days_remaining'] == 0:
        # Today - blue theme with special text
        days_text = "Today"
        days_color = lv.color_hex(0x00A5FF)
        days_text_color = lv.color_hex(0x008CFF)
        days_text_width = 125
    else:
        # Future event - blue theme
        days_text = f"{days_info['days_remaining']}"
        days_color = lv.color_hex(0x00A5FF)
        days_text_color = lv.color_hex(0x008CFF)
        days_text_width = 65

    # Create "Days" suffix label for numeric days
    days_text_obj = None
    if days_text != "Today":
        days_text_obj = lv.obj(tasks_btn)
        days_text_obj.set_size(60, 40)
        days_text_obj.set_style_bg_color(days_text_color, 0)
        days_text_obj.set_style_radius(0, 0)
        days_text_obj.set_style_border_width(0, 0)
        days_text_obj.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
        days_text_obj.align(lv.ALIGN.RIGHT_MID, 13, 0)

        days_text_label = lv.label(days_text_obj)
        days_text_label.set_text("Day" if abs(days_info['days_remaining']) == 1 else "Days")
        days_text_label.set_style_text_font(lv.font_ascii_22, 0)
        days_text_label.set_style_text_color(lv.color_hex(0x000000), 0)
        days_text_label.align(lv.ALIGN.CENTER, 0, 0)

    # Days number display
    days_obj = lv.obj(tasks_btn)
    days_obj.set_size(days_text_width, 40)
    days_obj.set_style_bg_color(days_color, 0)
    days_obj.set_style_radius(0, 0)
    days_obj.set_style_border_width(0, 0)
    days_obj.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    if days_text_obj:
        days_obj.align_to(days_text_obj, lv.ALIGN.OUT_LEFT_MID, 0, 0)
    else:
        days_obj.align(lv.ALIGN.RIGHT_MID, 13, 0)

    days_label = lv.label(days_obj)
    days_label.set_text(days_text)
    days_label.set_style_text_font(lv.font_ascii_bold_22, 0)
    days_label.set_style_text_color(lv.color_hex(0x000000), 0)
    days_label.align(lv.ALIGN.CENTER, 0, 0)

    return tasks_btn

async def show_days_list(parent, last_index, days_list, handle_event_cb):
    """
    Display the main list view of all day events.

    Args:
        parent: Parent container
        last_index: Previously selected item index
        days_list: List of day event dictionaries
        handle_event_cb: Event handler callback
    """
    if not parent: return
    parent.clean()
    app_mgr.enter_root_page()

    # Set list background color
    parent.set_style_bg_color(lv.color_hex(0xEFEFEF), 0)

    # Create header with title
    title_obj = lv.obj(parent)
    title_obj.set_size(base.SCR_WIDTH, 39)
    title_obj.set_style_radius(0, 0)
    title_obj.set_style_border_width(0, 0)
    title_obj.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
    title_obj.set_style_bg_color(lv.color_hex(0x1E90FF), 0)
    title_obj.align(lv.ALIGN.TOP_LEFT, 0, 0)

    # Title text
    title = lv.label(title_obj)
    title.set_text("Days Matter")
    title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
    title.set_style_text_font(lv.font_ascii_bold_28, 0)
    title.align(lv.ALIGN.CENTER, 0, -2)

    # Header separator line
    line_points = [{"x": 0, "y": 0}, {"x": base.SCR_WIDTH, "y": 0}]
    line = lv.line(parent)
    line.set_style_line_color(lv.color_hex(0x000000), 0)
    line.set_points(line_points, len(line_points))  # Set the points
    line.align(lv.ALIGN.TOP_LEFT, 0, 39)

    # Create container to store data, otherwise when focusing on later data,
    # the exit App prompt UI will shift upward
    list_container = lv.obj(parent)
    list_container.remove_style(None, 0)
    list_container.set_size(base.SCR_WIDTH, base.SCR_HEIGHT - 40)
    list_container.remove_style(None, lv.PART.SCROLLBAR)
    list_container.set_style_bg_color(lv.color_hex3(0xFFFFFF), 0)
    list_container.align(lv.ALIGN.TOP_LEFT, 0, 40)

    _algin_target = parent

    # Show empty state message if no events
    if days_list == []:
        tips_label = lv.label(parent)
        tips_label.set_text("No news for today.")
        tips_label.set_style_text_font(lv.font_ascii_18, 0)
        tips_label.align_to(line, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 5)

    # Create list items and separators
    for index, days_info in enumerate(days_list):
        day_obj = await _show_one_days(list_container, days_info, handle_event_cb)
        lv.group_get_default().add_obj(day_obj)

        # Select alignment target
        if index == 0: day_obj.align(lv.ALIGN.TOP_LEFT, 0, 0)
        else: day_obj.align_to(_algin_target, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 0)

        # Update alignment target for next item
        _algin_target = day_obj

        # Add separator line between items
        if index != len(days_list):
            line_points = [{"x": 0, "y": 0}, {"x": base.SCR_WIDTH, "y": 0}]
            line = lv.line(day_obj)
            line.set_style_line_width(1, 0)
            line.set_points(line_points, len(line_points))  # Set the points
            line.set_style_line_color(lv.color_hex(0x000000), lv.PART.MAIN)
            line.align(lv.ALIGN.BOTTOM_LEFT, -12, 7)

    # Set focus and selection
    lv.group_get_default().set_editing(False)
    if last_index > len(days_list) - 1:
        last_index = 0
    lv.group_focus_obj(list_container.get_child(last_index))
    list_container.get_child(last_index).scroll_to_view(lv.ANIM.OFF)
    list_container.get_child(last_index).set_style_bg_color(lv.color_hex(0xCBCBCB), 0)

async def show_error_msg(parent, msg):
    """
    Display error message in the center of the screen.

    Args:
        parent: Parent container
        msg: Error message text
    """
    if not parent: return
    parent.clean()
    title = lv.label(parent)
    title.set_text(msg)
    title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
    title.set_style_text_font(lv.font_ascii_bold_28, 0)
    title.align(lv.ALIGN.CENTER, 0, 0)

async def on_boot(apm):
    global app_mgr
    app_mgr = apm
