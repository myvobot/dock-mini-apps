import settings
import clocktime
import lvgl as lv
from . import config
from . import data_storage

_title = None
_parent = None
_sensor_id = None
_cur_details = {}

def sync_details_info(info):
    # Get the model code from the device info
    model_code = info.get("dev_model", None)
    profile = config.getProfile(model_code)
    live_info = data_storage.get_live_info(_sensor_id)

    details_info = {}
    details_info["title"] = info.get("nickname", "")
    details_info["options"] = []
    details_info["options"].append(["SN", _sensor_id])
    details_info["options"].append(["Model", profile.get("model", "-")])
    details_info["options"].append(["Probe", lv.SYMBOL.OK if live_info.get("probe_state", 1) == 1 else lv.SYMBOL.CLOSE])
    details_info["options"].append(["Battery", f"{live_info.get('battery_percentage', '-')}%"])
    details_info["options"].append(["Signal", f"{live_info.get("rssi", "-")} dBm"])
    details_info["options"].append(["Product", info.get("product_name", "-")])

    epoch = live_info.get("timestamp", None)
    if epoch is None:
        lastseen = "-/-/- -:-"
    else:
        tm = clocktime.datetime(epoch)
        # Decide whether to display 12-hour or 24-hour time based on settings
        if not settings.hour24():
            if tm[3] < 12:
                hour = str(tm[3])
                time_tip = ""
            elif tm[3] == 12:
                hour = str(tm[3])
                time_tip = " PM"
            else:
                hour = str(tm[3] - 12)
                time_tip = " PM"
        else:
            time_tip = ""
            hour = f"{tm[3]:02d}"
        minute = f"{tm[4]:02d}"
        lastseen = "%s/%s/%d %s:%s%s" % (f"{tm[1]:02d}", f"{tm[2]:02d}", tm[0], hour, minute, time_tip)
    details_info["options"].append(["LastSeen", lastseen])

    return details_info

def show_one_data(parent, last_obj, name, content, is_last=False):
    # Display a single row of sensor detail (name and value)
    title_label = lv.label(parent)
    title_label.set_text(name + ":")
    title_label.set_style_text_font(lv.font_ascii_18, 0)
    if last_obj:
        title_label.align_to(last_obj, lv.ALIGN.OUT_BOTTOM_LEFT, 10, 6)
    else:
        title_label.align(lv.ALIGN.TOP_LEFT, 10, 6)
    title_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

    content_label = lv.label(parent)
    content_label.set_text(content)
    content_label.set_style_text_font(lv.font_ascii_18, 0)
    if last_obj:
        content_label.align_to(last_obj, lv.ALIGN.OUT_BOTTOM_RIGHT, -10, 6)
    else:
        content_label.align(lv.ALIGN.TOP_RIGHT, -10, 6)
    content_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

    # Draw a separator line unless this is the last data row
    if is_last: return title_label
    else:
        line_points = [{"x": 0, "y": 0}, {"x": 320, "y": 0}]
        line = lv.line(parent)
        line.set_points(line_points, len(line_points))  # Set the points
        line.align_to(title_label, lv.ALIGN.OUT_BOTTOM_LEFT, -10, 6)
        line.set_style_line_width(2, 0)
        line.set_style_line_color(lv.color_hex(0xBBBBBB), 0)
        return line

def update_details(sensor_info):
    global _cur_details
    tmp_details = sync_details_info(sensor_info)
    # Update only the changed fields in the UI
    for index, data in enumerate(_cur_details["options"]):
        if _cur_details["options"][index][1] == tmp_details["options"][index][1]: continue
        obj = _parent.get_child((index + 1) * 3)
        last_obj = _parent.get_child((index + 1) * 3 - 2) if (index + 1) * 3 - 2 >= 0 else None
        obj.set_text(tmp_details["options"][index][1])
        if last_obj is None: obj.align(lv.ALIGN.TOP_RIGHT, -10, 6)
        else: obj.align_to(last_obj, lv.ALIGN.OUT_BOTTOM_RIGHT, -10, 6)

    _cur_details = tmp_details

def show_details(parent, sensor_info):
    global _parent, _sensor_id, _title, _cur_details
    _parent = parent
    _sensor_id = sensor_info.get("sensor_id", None)

    _cur_details = sync_details_info(sensor_info)

    if _parent: _parent.clean()
    try:
        # Create the title label
        _title = lv.label(parent)
        _title.set_text(_cur_details["title"])
        _title.set_width(300)
        _title.set_style_text_font(lv.font_ascii_bold_28, 0)
        _title.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        _title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        _title.align(lv.ALIGN.TOP_LEFT, 10, 1)

        # Draw a separator line under the title
        line_points = [{"x": 0, "y": 0}, {"x": 320, "y": 0}]
        line = lv.line(parent)
        line.set_points(line_points, len(line_points))  # Set the points
        line.align_to(_title, lv.ALIGN.OUT_BOTTOM_LEFT, -10, 3)
        line.set_style_line_width(2, 0)
        line.set_style_line_color(lv.color_hex(0xBBBBBB), 0)

        last_obj = line
        last_index = len(_cur_details["options"]) - 1
        # Display each sensor detail row
        for index, data in enumerate(_cur_details["options"]):
            last_obj = show_one_data(_parent, last_obj, data[0], data[1], index == last_index)

    except Exception as e:
        print(f"show_details error: {str(e)}")
