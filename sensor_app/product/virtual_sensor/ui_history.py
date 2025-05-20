import asyncio
import settings
import clocktime
import lvgl as lv
from . import config
from . import data_storage
from micropython import const

_PTS_DO_SHIFT_ONLY = 50 # If the number of points exceeds N, only shift the chart, do not redraw
_LV_CHART_POINT_NONE = 0x7fffffff
_ENABLE_SHOW_ATTACH = ["temperature"] # Allowed measurement data types to display

_p_cnt = 0 # Total number of points in the current chart
_p_index = 0 # The position where a new point is inserted in the current chart
_ser1 = None # Series 1 of the chart
_chart = None
_cursor = None
_parent = None
_major_cnt = 4
_sensor_id = None
_attach_info = () # Measurement data types corresponding to the sensor
_x_axis_text = [] # Save X-axis text
_history_data = {}
_curr_attach = None # Currently displayed data type [temperature/humidity, etc.]
_time_gap_limit = 900 # If the time interval exceeds 900s, insert an empty coordinate point

def get_date_time_string(epoch, time):
    time_text = []
    for i in range(_major_cnt):
        tm = clocktime.datetime(epoch + i * time)
        month = tm[1]
        day = "0" + str(tm[2]) if tm[2] < 10 else str(tm[2])
        hour= "0" + str(tm[3]) if tm[3] < 10 else str(tm[3])
        minute = "0" + str(tm[4]) if tm[4] < 10 else str(tm[4])
        s = "%s:%s" % (hour, minute)
        time_text.append(s)
    return time_text

def data_calibration(data, calibration):
    # Data calibration
    for key, values in data.items():
        # Skip calibration for measure_id
        if key in ["measure_id"]: continue
        for index, value in enumerate(values):
            # For temperature type, need to add calibration value
            if key in ["temperature"]:
                if isinstance(value, int):
                    data[key][index] = value + calibration.get(key, 0)
    return data

def get_history_data(sensor_id):
    # Convert historical data to the format required by the UI
    res = {}
    for s_id, measurements in data_storage.get_sensor_history_data(sensor_id).items():
        prev_timestamp = None
        for measurement in measurements:
            if not res: res = {key: [] for key in measurement}
            timestamp = measurement['timestamp']
            if prev_timestamp is not None and timestamp - prev_timestamp > _time_gap_limit:
                # If the interval from the previous timestamp is too long, insert empty coordinate points
                num_insertions = (timestamp - prev_timestamp) // _time_gap_limit  # Calculate the number of timestamps to insert
                if num_insertions > _PTS_DO_SHIFT_ONLY:
                    # If the number of points to insert exceeds _PTS_DO_SHIFT_ONLY, clear previous data
                    prev_timestamp = timestamp
                    res = {key: [] for key in measurement}
                else:
                    # Append coordinate points
                    for i in range(num_insertions):
                        new_timestamp = prev_timestamp + _time_gap_limit
                        for key in measurement: res[key].append(new_timestamp if key == "timestamp" else None)
                        prev_timestamp = new_timestamp
            # Insert the current coordinate point
            for key, value in measurement.items(): res[key].append(int(value))
            prev_timestamp = timestamp

    for key in list(res.keys()):
        # For measure_id, only keep the last one
        if key == "measure_id": res[key] = res[key][-1]
        # For data that is not timestamp/allowed to display, there is no need to save its history
        elif key not in ["timestamp"] + _ENABLE_SHOW_ATTACH: del res[key]

    return res

def minmax():
    value_list = [x for x in _history_data.get(_curr_attach, []) if isinstance(x, int)]
    v_min = min(value_list) if value_list else 0
    v_max = max(value_list) if value_list else 0

    if _curr_attach == "temperature" and settings.temp_unit() == 0:
        # Convert Celsius to Fahrenheit (for Y axis)
        v_min = int(config.celsius2Fahrenheit(v_min/100)*100)
        v_max = int(config.celsius2Fahrenheit(v_max/100)*100)

    v_min = (v_min // 200) * 200 - 100
    v_max = (v_max // 200 + 1) * 200 + 100

    return v_min, v_max

def get_y_axis_text():
    v_min = 0
    v_max = 1
    value_text = []

    if _curr_attach in ["temperature"]:
        v_min, v_max = minmax()
        v_avg = (v_min + v_max) // 2
        v_unit = "°"
        value_text = [f"{int(v_min // 100)}{v_unit} ", "", f"{int(v_avg // 100)}{v_unit} ", f"", f"{int(v_max // 100)}{v_unit} "]
        # Check if the average value between min and avg is an integer, if so, display it
        if ((v_min + v_avg) / 2) % 100 == 0:
            value_text[1] = f"{int(((v_min + v_avg) / 2) // 100)}{v_unit} "
            # If the text is the same as min/avg, do not display
            if value_text[1] in (value_text[0], value_text[2]): value_text[1] = ""

        if ((v_max + v_avg) / 2) % 100 == 0:
            value_text[3] = f"{int(((v_max + v_avg) / 2) // 100)}{v_unit} "
            # If the text is the same as max/avg, do not display
            if value_text[3] in (value_text[4], value_text[2]): value_text[3] = ""

    else: value_text = [""] * 5

    return value_text, v_min, v_max

def get_chart_style():
    if _curr_attach == "temperature":
        return "Temperature History", lv.PALETTE.RED
    else:
        return "", lv.PALETTE.BLUE

def refresh_history(sensor_id, calibration=None, refresh_all=False):
    global _p_index, _history_data, _sensor_id, _x_axis_text, _major_cnt
    if (_sensor_id != sensor_id): return
    if calibration is None: calibration = {"temperature": 0, "humidity": 0}

    _history_data = data_calibration(get_history_data(_sensor_id), calibration)
    point_cnt = len(_history_data.get("timestamp", []))
    if not _chart or not _ser1: # Chart is not drawn
        # If there are at least 2 data points, try to draw the chart
        if point_cnt >=2: asyncio.create_task(show_chart())
        return

    # If major_cnt changes, update the X axis scale
    if _major_cnt != min(point_cnt, 4):
        _major_cnt = min(point_cnt, 4)
        tick_count = _major_cnt * 2 - 1 if _major_cnt > 1 else 2
        _parent.get_child(-2).set_total_tick_count(tick_count)

    at = _history_data.get("timestamp",[])
    time = abs(at[0] - at[-1])
    # Update X axis text
    _x_axis_text = get_date_time_string(at[0], int(time/(_major_cnt-1)))
    _parent.get_child(-2).set_text_src(_x_axis_text)

    # If the number of points has exceeded the maximum, just shift
    if _p_cnt >= _PTS_DO_SHIFT_ONLY and not refresh_all:
        val = _history_data[_curr_attach][-1] + calibration.get(_curr_attach, 0)
        if _curr_attach == "temperature" and settings.temp_unit() == 0:
            val = int(config.celsius2Fahrenheit(val/100)*100)

        _chart.set_next_value(_ser1, val)
        # Update Y axis text
        value_text, v_min, v_max = get_y_axis_text()
        _parent.get_child(-1).set_text_src(value_text)
        _chart.set_range(lv.chart.AXIS.PRIMARY_Y, v_min, v_max)

        _p_index += 1
        if _p_index >= _p_cnt: _p_index = 0

    # If there are still few points, reload the entire chart each time new data is received
    else: load_chart_data()

def load_chart_data():
    global _p_index, _p_cnt, _x_axis_text
    if _chart and _ser1:
        at = _history_data.get("timestamp",[])
        samples = _history_data.get(_curr_attach, [])
        if len(at) and _parent.get_child(-2) and _parent.get_child(-1):
            time = abs(at[0] - at[-1])
            # Update X axis text
            _x_axis_text = get_date_time_string(at[0], int(time/(_major_cnt-1)))
            # If the chart control exists, the X/Y axis scale controls also exist
            _parent.get_child(-2).set_text_src(_x_axis_text)

            # Update Y axis text
            value_text, v_min, v_max = get_y_axis_text()
            _parent.get_child(-1).set_text_src(value_text)
            _chart.set_range(lv.chart.AXIS.PRIMARY_Y, v_min, v_max)

            label, color = get_chart_style()
            _chart.set_series_color(_ser1, lv.palette_main(color))

        _p_index = 0
        _p_cnt = len(samples)
        if _p_cnt == 0:
            _p_cnt = 1
            samples = [0,]
        _chart.set_point_count(_p_cnt)
        if (_curr_attach == "temperature") and (settings.temp_unit() == 0):
            # Convert Celsius to Fahrenheit (for each point)
            for i,v in enumerate(samples):
                if isinstance(v, int):
                    samples[i] = int(config.celsius2Fahrenheit(v/100)*100)

        samples = [x if x is not None else _LV_CHART_POINT_NONE for x in samples]
        _chart.set_ext_y_array(_ser1, samples)

async def show_chart():
    global _chart, _ser1, _cursor, _major_cnt
    last_id = -1

    def _shifted_id(id):
        # The id position of the extracted array does not correspond to the data (because set_next_value can insert new values at any time)
        # So, use _p_index to find the new index in the array, and extract the uint16 value
        new_id = _p_index + id
        if new_id >= _p_cnt: new_id = new_id - _p_cnt
        return new_id

    def event_cb(e):
        nonlocal last_id
        code = e.get_code()
        _chart = e.get_target_obj()

        if code == lv.EVENT.VALUE_CHANGED:
            # _chart.invalidate()
            id = _chart.get_pressed_point()
            if id != _LV_CHART_POINT_NONE:
                last_id = _shifted_id(id)
                p0 = lv.point_t()
                _chart.get_point_pos_by_id(_ser1, id, p0)
                p1 = lv.point_t()
                _chart.get_point_pos_by_id(_ser1, last_id, p1)
                p = lv.point_t() # When new data is inserted, you cannot simply take the data point corresponding to id
                p.x = p0.x # The index in the view (id) corresponds to the X axis
                p.y = p1.y # After shift adjustment (last_id), the extracted Y value is valid
                # _chart.set_cursor_point(_cursor, _ser1, last_id)
                _chart.set_cursor_pos(_cursor, p) # Set the coordinate directly, not to a certain id, so that the cursor position is correct (actually a bug in lvgl)
        elif code == lv.EVENT.REFR_EXT_DRAW_SIZE: pass # e.set_ext_draw_size(20)

    try:
        if _parent: _parent.clean()
        label, color = get_chart_style()

        # Title
        title = lv.label(_parent)
        title.set_text(label)
        title.set_style_text_font(lv.font_ascii_bold_28, 0)
        title.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
        title.align(lv.ALIGN.TOP_LEFT, 10, 1)

        # Separator line
        line_points = [{"x": 0, "y": 0}, {"x": 320, "y": 0}]
        line = lv.line(_parent)
        line.set_points(line_points, len(line_points))  # Set the points
        line.align(lv.ALIGN.TOP_LEFT, 0, 35)
        line.set_style_line_width(2, 0)
        line.set_style_line_color(lv.color_hex(0xBBBBBB), 0)

        cnt = len(_history_data.get("timestamp",[]))
        if cnt < 2:
            # Prompt: no historical data yet
            tip = lv.label(_parent)
            tip.set_text("No historical data yet. ")
            tip.set_style_text_font(lv.font_ascii_18, 0)
            tip.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
            tip.align(lv.ALIGN.CENTER, 0, 0)
            return tip

        elif cnt < 4: _major_cnt = cnt
        else: _major_cnt = 4

        chart_size = (255, 175)
        _chart = lv.chart(_parent)
        _chart.set_size(*chart_size)
        _chart.align(lv.ALIGN.CENTER, 20, 10)
        _chart.set_div_line_count(5, 0)
        _chart.set_type(lv.chart.TYPE.LINE)
        _chart.set_style_bg_opa(lv.OPA.TRANSP, lv.PART.MAIN)
        _chart.set_style_radius(0, lv.PART.MAIN)
        _chart.set_style_border_width(0, lv.PART.MAIN)
        _chart.set_style_text_color(lv.color_hex(0x111111), lv.PART.MAIN | lv.STATE.DEFAULT)
        _chart.set_style_text_font(lv.font_ascii_14, 0)
        _chart.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)

        # In lvgl v9.1, chart does not have set_axis_tick function, need to use scale control to display
        scale_x = lv.scale(_parent)
        scale_x.set_size(chart_size[0] - 30, 25)
        scale_x.set_mode(lv.scale.MODE.HORIZONTAL_BOTTOM)
        # Set main/secondary tick lines to transparent
        scale_x.set_style_line_opa(lv.OPA._0, lv.PART.MAIN)
        scale_x.set_style_line_opa(lv.OPA._0, lv.PART.ITEMS)
        # Main tick width is 1, text is font_ascii_14
        scale_x.set_style_line_width(1, lv.PART.INDICATOR)
        scale_x.set_style_text_font(lv.font_ascii_14, 0)
        # Set range
        tick_count = _major_cnt * 2 - 1 if _major_cnt > 1 else 2
        scale_x.set_total_tick_count(tick_count)
        scale_x.set_major_tick_every(2)
        scale_x.set_text_src([""] * _major_cnt)
        scale_x.align_to(_chart, lv.ALIGN.OUT_BOTTOM_MID, 0, -3)

        scale_y = lv.scale(_parent)
        scale_y.set_size(25, chart_size[1] - 16)
        scale_y.set_mode(lv.scale.MODE.VERTICAL_LEFT)
        scale_y.align_to(_chart, lv.ALIGN.OUT_LEFT_MID, -3, 0)
        # Set main line to transparent
        scale_y.set_style_line_opa(lv.OPA._0, lv.PART.MAIN)
        # Main/secondary tick width is 1
        scale_y.set_style_length(10, lv.PART.INDICATOR)
        scale_y.set_style_line_width(1, lv.PART.ITEMS)
        scale_y.set_style_line_width(1, lv.PART.INDICATOR)
        scale_y.set_style_text_font(lv.font_ascii_14, 0)
        # Set range
        scale_y.set_total_tick_count(9)
        scale_y.set_major_tick_every(2)
        scale_y.set_text_src([""] * 5)

        _chart.add_event_cb(event_cb, lv.EVENT.ALL, None)
        _chart.refresh_ext_draw_size()

        _cursor = _chart.add_cursor(lv.palette_main(lv.PALETTE.GREEN), lv.DIR.LEFT| lv.DIR.BOTTOM)

        # Do not display points on the data
        _chart.set_style_size(0, 0, lv.PART.INDICATOR)
        _ser1 = _chart.add_series(lv.palette_main(color), lv.chart.AXIS.PRIMARY_Y)
        await asyncio.sleep_ms(100)
        load_chart_data()
        return title
    except Exception as e:
        print(f"show_chart error: {str(e)}")
        return _parent

def show_history(parent, sensor_id, model_code, calibration=None):
    # return: None - No measurement type available for display; True - There is a measurement type available for display
    global _parent, _sensor_id, _history_data, _attach_info, _curr_attach
    if calibration is None: calibration = {"temperature": 0}
    if _sensor_id == sensor_id and _curr_attach is not None:
        # If the sensor is the same as last time and curr_attach is not empty,
        # then switch to the next measurement type for history display
        new_attach = None
        for attach in _ENABLE_SHOW_ATTACH[_ENABLE_SHOW_ATTACH.index(_curr_attach) + 1:]:
            if attach in _attach_info:
                new_attach = attach
                break

        if new_attach is None: return None
        _curr_attach = new_attach
        # If history data has already been obtained, no need to get it again
    else:
        if model_code is None: model_code = data_storage.get_live_info(sensor_id).get("dev_model", None)
        if model_code is None: model_code = data_storage.get_record_info(sensor_id).get("dev_model", None)
        _profile = config.getProfile(model_code)
        _attach_info = tuple(_profile.get("attr", {}).get("display", {}).get("attachInfo", []))

        _curr_attach = None
        # Check if the sensor's measurement data type can be displayed
        for attach in _ENABLE_SHOW_ATTACH:
            if attach in _attach_info:
                _curr_attach = attach
                break
        # If there is no type that can display historical data, return None
        if _curr_attach is None: return None

        _history_data = data_calibration(get_history_data(sensor_id), calibration)

    _parent = parent
    _sensor_id = sensor_id
    asyncio.create_task(show_chart())
    return True

async def reset_history_info():
    # Reset current parameters
    global _curr_attach, _chart, _parent, _history_data, _sensor_id, _attach_info
    _curr_attach = None
    _chart = None
    _parent = None
    _history_data = {}
    _sensor_id = None
    _curr_attach = None # Currently displayed data type [temperature/humidity, etc.]
    _attach_info = () # Measurement data types corresponding to the sensor
