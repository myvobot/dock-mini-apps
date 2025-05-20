import lvgl as lv

SINGLE_CARD = 1
DUAL_CARD = 2
QUAD_CARD = 4

# Card common style, distinguished by card type
CARD_STYLE = {
    SINGLE_CARD: {
        "sensor_name": { # Sensor name style
            "width": 180,
            "font": lv.font_ascii_bold_28
        },
        "partition": True, # Whether to show the divider line
        "icon": {
            "type": ["battery", "signal"], # Types of icons to display
            "cover": False, # Whether to cover the previous icon
        },
        "elapsed_time": True, # Whether to show elapsed time and measurement difference since last report
        "data": { # Measurement data container style
            "size": (320, 165),
            "align": (lv.ALIGN.TOP_LEFT, 0, 33)
        },
    },
    DUAL_CARD: {
        "sensor_name": {
            "width": 180,
            "font": lv.font_ascii_22
        },
        "partition": False,
        "icon": {
            "type": ["battery", "signal"],
            "cover": False
        },
        "elapsed_time": True,
        "data": {
            "size": (320, 74),
            "align": (lv.ALIGN.TOP_LEFT, 0, 25),
        },
    },
    QUAD_CARD: {
        "sensor_name": {
            "width": 135,
            "font": lv.font_ascii_22
        },
        "partition": False,
        "icon": {
            "type": [],
            "cover": True
        },
        "elapsed_time": False,
        "data": {
            "size": (159, 95),
            "align": (lv.ALIGN.TOP_LEFT, 0, 25),
        },
    }
}

DATA_STYLE = {
    SINGLE_CARD: {
        (("temperature",),): {
            "value_font": [lv.font_numbers_92], # Font for value
            "symbol_font": [lv.font_ascii_22], # Font for symbol
            "value_align": [(lv.ALIGN.CENTER, 0, 0)], # Alignment for value
            "symbol_align": [(lv.ALIGN.OUT_RIGHT_BOTTOM, 0, 5)], # Alignment for symbol
            "placement_mode": [0], # Layout mode for symbol and value, 0: symbol follows value; 1: value follows symbol [valid when symbol exists]
        },
    },
    DUAL_CARD: {
        (("temperature",),): {
            "value_font": [lv.font_numbers_72],
            "symbol_font": [lv.font_ascii_22],
            "value_align": [(lv.ALIGN.CENTER, 0, 5)],
            "symbol_align": [(lv.ALIGN.OUT_RIGHT_BOTTOM, 0, -10)],
            "placement_mode": [0],
        },
    },
    QUAD_CARD: {
        (("temperature",),): {
            "value_font": [lv.font_ascii_bold_48],
            "symbol_font": [lv.font_ascii_22],
            "value_align": [(lv.ALIGN.CENTER, -10, 0)],
            "symbol_align": [(lv.ALIGN.OUT_RIGHT_BOTTOM, 0, 5)],
            "placement_mode": [0],
        },
    }
}
