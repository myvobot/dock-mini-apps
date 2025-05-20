import settings
import clocktime
import lvgl as lv
from . import config
from . import ui_style
from . import data_storage
from ... import base as app_base

def show_elapsed_time(parent, live_info, record_info, calibration):
    elapsed_text = ""
    if "temperature" in live_info:
        _offset = calibration.get("temperature", 0)
        last_tm = record_info.get("temperature", 0) + _offset
        curr_tm = live_info.get("temperature", 0) + _offset
        if settings.temp_unit() == 0:
            # Convert Celsius to Fahrenheit
            last_tm = int(config.celsius2Fahrenheit(last_tm / 100) * 100)
            curr_tm = int(config.celsius2Fahrenheit(curr_tm / 100) * 100)

        # Calculate the difference
        value = str(int((curr_tm - last_tm) / 10) / 10)
        elapsed_text += ("" if value.startswith("-") else "+") + f"{value}° "
    elapsed_text += "since last record"

    # Calculate time difference
    diff_time = clocktime.now() - record_info.get("timestamp", 0)
    # If the time difference is illogical, do not display
    if diff_time < 0: return None
    elif diff_time < 60: time_label = "<1m"
    elif diff_time < 3600: time_label = f"{diff_time // 60}m"
    elif diff_time < 86400: time_label = f"{diff_time // 3600}h"
    else: time_label = f"{diff_time // 68400}d"
    elapsed_text += f" {time_label} ago"

    # Display text
    elapsed = lv.label(parent)
    elapsed.set_text(elapsed_text)
    elapsed.align(lv.ALIGN.BOTTOM_RIGHT, 0, -1)
    elapsed.set_style_text_font(lv.font_ascii_18, 0)
    elapsed.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

    return elapsed

def convert_measurement(value, _type, calibration):
    # Convert the value and unit to be displayed according to the data type/configuration
    res = ["N/A", None]
    try:
        if _type == "temperature":
            value = value + calibration.get(_type, 0)
            if settings.temp_unit() == 1:
                res[1] = "°C"
                res[0] = str(int(value / 10) / 10)
            else:
                res[1] = "°F"
                res[0] = str(int(int(config.celsius2Fahrenheit(value/100) * 100) / 10) / 10)
    except Exception as e:
        print(f"convert measurement fail.[{str(e)}]")
    return res

def show_measure(parent, info, calibration, card_type):
    # Display measurement data
    model_code = info.get("dev_model", None)
    _profile = config.getProfile(model_code)
    attach_info = tuple(_profile.get("attr", {}).get("display", {}).get("attachInfo", []))
    if not attach_info: return

    data_style = None
    # Find the corresponding UI style according to the card type and measurement type
    for _attachs, _style in ui_style.DATA_STYLE.get(card_type, {}).items():
        if attach_info in _attachs:
            data_style = _style
            break

    if not data_style: return

    for index, m_type in enumerate(attach_info):
        data_width = data_style.get("value_width", [])
        # Get the converted measurement value
        value, symbol = convert_measurement(info.get(m_type, None), m_type, calibration)

        # Create a hidden label for alarm use
        f_label = lv.label(parent)
        f_label.set_text(m_type)
        f_label.add_state(lv.STATE.USER_1)
        f_label.add_flag(lv.obj.FLAG.HIDDEN)

        # Display measurement value
        v_label = lv.label(parent)
        v_label.set_text(value)
        v_label.set_style_text_font(data_style["value_font"][index], 0)
        if data_width: # If data length is specified
            v_label.set_width(data_width[index])
            v_label.set_style_text_line_space(-13, 0)
            v_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)

        # Display measurement unit
        if symbol:
            s_label = lv.label(parent)
            s_label.set_text(symbol)
            s_label.set_style_text_font(data_style["symbol_font"][index], 0)
            # Placement mode [0: s_label follows v_label; 1: v_label follows s_label]
            placement_mode = data_style.get("placement_mode", None)
            if not placement_mode: placement_mode = 0
            else: placement_mode = placement_mode[index]

            # Adjust layout
            if placement_mode == 1:
                s_label.align(*data_style["symbol_align"][index])
                v_label.align_to(s_label, *data_style["value_align"][index])
            else:
                v_label.align(*data_style["value_align"][index])
                s_label.align_to(v_label, *data_style["symbol_align"][index])

        else: # For measurement types without a symbol, value_align should not be lv.ALIGN.OUT_xxx
            v_label.align(*data_style["value_align"][index])

def show_battery(parent, align_obj, battery, card_style):
    if not parent: return align_obj
    if "battery" not in card_style["icon"]["type"]: return align_obj

    color = lv.color_hex3(0xFFF)
    if battery > 80: _icon = "\uf240"
    elif battery > 60: _icon = "\uf241"
    elif battery > 40: _icon = "\uf242"
    elif battery > 20: _icon = "\uf243"
    else:
        _icon = "\uf244"
        color = lv.color_hex(0xF5411C)
    battery_icon = lv.label(parent)
    battery_icon.set_text(_icon)
    battery_icon.set_style_text_font(lv.font_ascii_18, 0)
    battery_icon.set_style_text_color(color, 0)

    if not card_style["icon"]["cover"]:
        if align_obj is None: battery_icon.align(lv.ALIGN.TOP_RIGHT, -3, -2)
        else: battery_icon.align_to(align_obj, lv.ALIGN.OUT_LEFT_MID, -3, 0)
    else:
        if align_obj is None: battery_icon.align(lv.ALIGN.TOP_RIGHT, 7, 0)
        else:
            align_obj.delete_async()
            battery_icon.align(lv.ALIGN.TOP_RIGHT, 7, 0)

    return battery_icon

def show_probe(parent, align_obj, probe_status, card_style):
    if probe_status != 1:
        probe_icon = lv.label(parent)
        probe_icon.set_text("\ue560")
        probe_icon.set_style_text_font(app_base._customize_font.get("probe_font", lv.font_ascii_22), 0)
        probe_icon.set_style_text_color(lv.color_hex(0xF5411C), 0)
        if not card_style["icon"]["cover"]:
            if align_obj is None: probe_icon.align(lv.ALIGN.TOP_RIGHT, 0, 0)
            else: probe_icon.align_to(align_obj, lv.ALIGN.OUT_LEFT_MID, -7, 0)
        else:
            probe_icon.set_style_text_font(app_base._customize_font.get("probe_font", lv.font_ascii_22), 0)
            if align_obj is None: probe_icon.align(lv.ALIGN.TOP_RIGHT, -7, 0)
            else:
                align_obj.delete_async()
                probe_icon.align(lv.ALIGN.TOP_RIGHT, -7, 0)
        return probe_icon
    return align_obj

def show_signal(parent, align_obj, info, card_style):
    if not parent: return align_obj

    signal_icon = None

    if "signal" in card_style["icon"]["type"]:
        signal = abs(info["rssi"])
        signal_icon = lv.obj(parent)
        signal_icon.set_size(28, 28)
        signal_icon.set_style_radius(0, 0)
        signal_icon.set_style_pad_all(0, 0)
        signal_icon.set_style_border_width(0, 0)
        signal_icon.set_style_bg_opa(lv.OPA._0, 0)
        signal_icon.set_style_bg_color(lv.color_hex3(0x000), 0)

        if signal < 50: grade = 5
        elif signal < 60: grade = 4
        elif signal < 70: grade = 3
        elif signal < 80: grade = 2
        else: grade = 1

        for index in range(5):
            if index < grade:
                line_points = [{"x": index * 4 + 4, "y": 21 - 4 * index}, {"x": index * 4 + 4, "y": 25}]
            else:
                line_points = [{"x": index * 4 + 4, "y": 23}, {"x": index * 4 + 4, "y": 25}]
            line = lv.line(signal_icon)
            line.set_points(line_points, len(line_points))  # Set the points
            line.set_style_line_width(3, 0)
            line.set_style_line_color(lv.color_hex3(0xFFF), 0)

    # If the signal icon is None, return align_obj
    if signal_icon is None: return align_obj

    if not card_style["icon"]["cover"]:
        if align_obj is None: signal_icon.align(lv.ALIGN.TOP_RIGHT, -3, -4)
        else: signal_icon.align_to(align_obj, lv.ALIGN.OUT_LEFT_MID, -3, -4)
    else:
        if align_obj is None: signal_icon.align(lv.ALIGN.TOP_RIGHT, 10, -4)
        else:
            align_obj.del_async()
            signal_icon.align(lv.ALIGN.TOP_RIGHT, 10, -4)

    return signal_icon

async def show_card(parent, s_info, card_type):
    if not parent: return
    card_style = ui_style.CARD_STYLE.get(card_type, None)
    if not card_style: return
    parent.clean()

    # Sensor name [scroll if too long]
    sensor_name = lv.label(parent)
    sensor_name.align(lv.ALIGN.TOP_LEFT, 5, 0)
    sensor_name.set_style_anim_duration(5000, 0)
    sensor_name.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
    sensor_name.set_width(card_style["sensor_name"]["width"])
    sensor_name.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
    sensor_name.set_text(s_info.get("nickname", s_info["sensor_id"][-6:]))
    sensor_name.set_style_text_font(card_style["sensor_name"]["font"], 0)

    # Divider line
    if card_style["partition"]:
        line_points = [{"x": 0, "y": 0}, {"x": 320, "y": 0}]
        line = lv.line(parent)
        line.set_style_line_width(2, 0)
        line.set_points(line_points, len(line_points))
        line.set_style_line_color(lv.color_hex(0xBBBBBB), 0)
        line.align(lv.ALIGN.TOP_LEFT, 0, 35)

    live_info = data_storage.get_live_info(s_info["sensor_id"])
    record_info = data_storage.get_record_info(s_info["sensor_id"])
    calibration = {"temperature": 0, "humidity": 0}

    align_obj = None
    probe_state = live_info.get("probe_state", 1)
    battery = live_info.get("battery_percentage", None)

    if live_info:
        align_obj = show_battery(parent, align_obj, battery, card_style)
        align_obj = show_probe(parent, align_obj, probe_state, card_style)
        show_signal(parent, align_obj, live_info, card_style)

    # Time difference/measurement difference display
    if record_info and card_style["elapsed_time"]:
        show_elapsed_time(parent, live_info, record_info, calibration)

    # Data display
    # Create a container at the end of parent to store measurement controls
    m_obj = lv.obj(parent)
    m_obj.set_style_radius(0, 0)
    m_obj.set_style_pad_all(0, 0)
    m_obj.set_style_border_width(0, 0)
    m_obj.set_style_bg_opa(lv.OPA._0, 0)
    m_obj.set_size(*card_style["data"]["size"])
    m_obj.align(*card_style["data"]["align"])
    m_obj.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

    # If the device is not scanned or the device status is abnormal or the device information is incomplete, display N/A
    if (not live_info) or (probe_state != 1):
        tip_label = lv.label(m_obj)
        tip_label.set_text("N/A")
        tip_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        tip_label.set_style_text_font(lv.font_ascii_bold_48, 0)
        tip_label.set_style_text_line_space(-20, 0)
        tip_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        tip_label.align(lv.ALIGN.CENTER, 0, 5)
    else:
        show_measure(m_obj, live_info, calibration, card_type)
