import net
import asyncio
import clocktime
import lvgl as lv
import peripherals
from micropython import const
from .service import get_stock_detials

NAME = "Stock View" # App name
CAN_BE_AUTO_SWITCHED = True # Whether the App supports auto-switching in carousel mode

_MENU_ITEM_FOCUSED = lv.color_hex3(0x022) # Background color when a widget is focused
_MENU_ITEM_DEFOCUSED = lv.color_hex3(0x000) # Background color when a widget is unfocused
_STOCK_UPDATE_INTERVAL = const(900) # Time interval for updating stock information (in seconds)
_SCR_WIDTH, _SCR_HEIGHT = peripherals.screen.screen_resolution  # Get the screen size from peripherals
_ITEM_WIDTH, _ITEM_HEIGHT = (_SCR_WIDTH, const(60)) # Size of a single stock information item

_NO_SUBUNIT_CURRENCIES = ["JPY", "KRW", "VND", "CLP"] # Currencies that don't commonly use subunits (cents)
_THREE_DECIMAL_CURRENCIES = ["KWD", "BHD", "OMR", "IQD", "JOD", "TND", "LYD"] # Currencies with three decimal places
_DEFAULT_STOCK_SYMBOLS = ["MSFT:NASDAQ", "TSLA:NASDAQ", "NVDA:NASDAQ", "AAPL:NASDAQ", "GOOG:NASDAQ"] # Default stock configuration
_CURRENCY_SYMBOLS= {
        "USD": "$",   # US Dollar
        "EUR": "€",   # Euro
        "GBP": "£",   # British Pound
        "JPY": "¥",   # Japanese Yen
        "INR": "₹",   # Indian Rupee
        "KRW": "₩",   # South Korean Won
        "RUB": "₽",   # Russian Ruble
        "TRY": "₺",   # Turkish Lira
        "NGN": "₦",   # Nigerian Naira
        "THB": "THB",   # Thai Baht
        "VND": "₫",   # Vietnamese Dong
        "PLN": "zł",   # Polish Zloty
        "BRL": "R$",  # Brazilian Real
        "ILS": "₪",   # Israeli New Shekel
        "AUD": "A$",  # Australian Dollar
        "CAD": "C$",  # Canadian Dollar
        "SGD": "S$",  # Singapore Dollar
        "CHF": "CHF", # Swiss Franc
        # ... Add more as needed
    }

_scr = None  # Initialize screen variable
_app_mgr = None  # Initialize app manager variable
_stock_count = 0 # Number of stock information items currently displayed
_last_updated = 0 # Timestamp of the last stock information update
_stock_detials = [] # Current stock information for multiple stocks
_stock_symbols = _DEFAULT_STOCK_SYMBOLS # Current stock configuration

def get_settings_json():
    return {
        "category": "Finance",
        "form": [{
            "type": "input",
            "default": ",".join(_DEFAULT_STOCK_SYMBOLS),
            "caption": "Stocks Symbols",
            "name": "stocks",
            "validation": ":,\w+",
            "attributes": {"maxLength": 60, "placeholder": "e.g., AAPL:NASDAQ"},
            "tip": "For multiple stocks, use commas, like 'AAPL:NASDAQ,GOOGL:NASDAQ'.",
            "hint": {
                "url": "https://google.com/finance/",
                "label": "Click here to search for stock codes."
            }
        }]
    }

def _load_config():
    # Load application configuration
    global _stock_symbols, _last_updated, _stock_detials
    stock_cfg = _app_mgr.config()
    symbols = stock_cfg.get("stocks", None)
    if symbols:
        # Check if configuration has changed; if so, need to refresh stock information
        temp_symbols = [x.strip() for x in symbols.strip(",").split(",") ]
        if _stock_symbols != temp_symbols:
            _last_updated = 0
            _stock_detials = []
            _stock_symbols = temp_symbols
        print(f"{NAME}: {_stock_symbols}")
        return True
    elif symbols == "":
        # Stock configuration is empty, prompt user to configure
        _stock_symbols = []
        _stock_detials = []
        _app_mgr.error(
            "Stocks View App Not Configured",
            "Please go to the application settings to configure stock information.",
            confirm = "OK", cancel=False, cb=lambda res: asyncio.create_task(_app_mgr.exit()))
        return False
    else:
        # First load? Save default configuration
        stock_cfg["stocks"] = ",".join(_DEFAULT_STOCK_SYMBOLS)
        _app_mgr.config(stock_cfg)
        return True

async def display_single_stock(parent, price_info):
    # Display information for a single stock
    if ('symbol' not in price_info) or (price_info['symbol'] is None): return None

    # Create container
    menu_cont = lv.menu_cont(parent)
    menu_cont.set_size(_ITEM_WIDTH, _ITEM_HEIGHT)
    menu_cont.set_style_pad_all(0, lv.PART.MAIN)

    cont = lv.obj(menu_cont)
    cont.set_style_radius(0, lv.PART.MAIN)
    cont.remove_flag(lv.obj.FLAG.SCROLLABLE)
    cont.set_size(_ITEM_WIDTH, _ITEM_HEIGHT)
    cont.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
    cont.set_style_border_side(lv.BORDER_SIDE.BOTTOM, lv.PART.MAIN)
    cont.set_style_border_color(lv.color_hex3(0xFFF), lv.PART.MAIN)

    # Display symbol
    symbol = lv.label(cont)
    symbol.set_text(price_info["symbol"])
    symbol.set_width(_ITEM_WIDTH // 3 + 5)
    symbol.align(lv.ALIGN.TOP_LEFT, -8, -12)
    symbol.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
    symbol.set_style_text_font(lv.font_ascii_22, lv.PART.MAIN)
    symbol.set_style_text_align(lv.TEXT_ALIGN.LEFT, lv.PART.MAIN)
    symbol.set_style_text_color(lv.color_hex(0x0BB4ED), lv.PART.MAIN)

    # Display short name
    short_name = lv.label(cont)
    short_name.set_text(price_info["shortName"])
    short_name.align(lv.ALIGN.TOP_RIGHT, 5, -12)
    short_name.set_width((_ITEM_WIDTH // 3) * 2 - 15)
    short_name.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
    short_name.set_style_text_font(lv.font_ascii_18, lv.PART.MAIN)
    short_name.set_style_text_align(lv.TEXT_ALIGN.RIGHT, lv.PART.MAIN)
    short_name.set_style_text_color(lv.color_hex(0x888888), lv.PART.MAIN)

    curr_price = price_info["currentPrice"]
    prev_close = price_info["previousClose"]
    if curr_price is not None and prev_close != 0:
        # Choose currency symbol to display
        if price_info["currency"] is None:
            currency = _CURRENCY_SYMBOLS["USD"]
        elif price_info["currency"].upper() in _CURRENCY_SYMBOLS:
            currency = _CURRENCY_SYMBOLS[price_info["currency"].upper()]
        elif price_info["currency"] == "Unknown":
            currency = ""
        else:
            currency = price_info["currency"]

        diff_amount = curr_price - prev_close
        color = 0xA50E0E if diff_amount < 0 else 0x137333
        bgcolor = 0xFCE8E6 if diff_amount < 0 else 0xE6f4EA
        arrow = lv.SYMBOL.DOWN if diff_amount < 0 else lv.SYMBOL.UP
        prefix = "-" + currency if diff_amount < 0 else "+" + currency

        if diff_amount == 0: _prefix = ""
        if diff_amount < 0: diff_amount = -diff_amount

        # Determine how many decimal places to display
        if price_info["currency"] in _NO_SUBUNIT_CURRENCIES:
            amount_number = "{:.0f}".format(round(curr_price, 0))
            diff_amount_number = "{:.0f}".format(round(diff_amount, 0))
        elif price_info["currency"] in _THREE_DECIMAL_CURRENCIES:
            amount_number = "{:.3f}".format(round(curr_price, 3))
            diff_amount_number = "{:.3f}".format(round(diff_amount, 3))
        else:
            amount_number = "{:.2f}".format(round(curr_price, 2))
            diff_amount_number = "{:.2f}".format(round(diff_amount, 2))

        amount_text = currency + amount_number
        diff_amount_text = prefix + diff_amount_number

        amount = lv.label(cont)
        amount.set_text(amount_text)
        amount.set_width(_ITEM_WIDTH // 3 + 5)
        amount.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        amount.set_style_text_font(lv.font_ascii_bold_22, 0)
        amount.set_style_text_color(lv.color_hex(0xFFFE66), 0)
        amount.align(lv.ALIGN.BOTTOM_LEFT, -12, 10)

        diff_amount = lv.label(cont)
        diff_amount.set_text(amount_text)
        diff_amount.set_width(_ITEM_WIDTH // 3 - 10)
        diff_amount.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        diff_amount.set_style_text_font(lv.font_ascii_bold_22, 0)
        diff_amount.set_text(diff_amount_text)
        diff_amount.set_style_text_color(lv.color_hex(color), 0)
        diff_amount.align(lv.ALIGN.BOTTOM_LEFT, 100, 10)

        ratio_obj = lv.obj(cont)
        ratio_obj.set_style_bg_color(lv.color_hex(bgcolor), 0)
        ratio_obj.set_size(110, 32)
        ratio_obj.set_style_pad_all(0, 0)
        ratio_obj.set_style_border_width(0, 0)
        ratio_obj.align(lv.ALIGN.BOTTOM_RIGHT, 10, 10)

        diff_ratio =  100 * (curr_price - prev_close) / prev_close
        if diff_ratio < 0: diff_ratio = -diff_ratio
        diff_ratio_label = lv.label(ratio_obj)
        diff_ratio_label.set_text("{:.2f}%".format(round(diff_ratio, 2)))
        diff_ratio_label.set_style_text_font(lv.font_ascii_bold_22, 0)
        diff_ratio_label.set_style_text_color(lv.color_hex(color), 0)
        diff_ratio_label.align(lv.ALIGN.CENTER, 10, 0)

        if prefix == "": arrow= " "
        arrow_text = lv.label(ratio_obj)
        arrow_text.set_text(arrow)
        arrow_text.set_style_text_color(lv.color_hex(color), 0)
        arrow_text.align_to(diff_ratio_label, lv.ALIGN.OUT_LEFT_MID, -4, 0)

    else:
        # No price information obtained, indicate data source not available
        tip_label = lv.label(cont)
        tip_label.set_text("Stock information not found.")
        tip_label.set_width(_ITEM_WIDTH)
        tip_label.align(lv.ALIGN.BOTTOM_MID, 0, 10)
        tip_label.set_long_mode(lv.label.LONG.SCROLL_CIRCULAR)
        tip_label.set_style_text_font(lv.font_ascii_18, lv.PART.MAIN)
        tip_label.set_style_text_align(lv.TEXT_ALIGN.CENTER, lv.PART.MAIN)
        tip_label.set_style_text_color(lv.color_hex(0x888888), lv.PART.MAIN)

    return menu_cont

def menu_cont_event_handler(e):
    # Widget event callback for implementing widget switching
    global _stock_count
    e_code = e.get_code()
    target = e.get_target_obj()
    lv_group = lv.group_get_default()

    if lv_group.get_focused() == target and lv_group.get_editing():
        lv_group.set_editing(False)

    if e_code == lv.EVENT.FOCUSED:
        target.scroll_to_view(lv.ANIM.OFF)
        if _stock_count > 4: target.get_child(0).set_style_bg_color(_MENU_ITEM_FOCUSED, 0)

    elif e_code == lv.EVENT.DEFOCUSED:
        if _stock_count > 4: target.get_child(0).set_style_bg_color(_MENU_ITEM_DEFOCUSED, 0)
    elif e_code == lv.EVENT.DELETE:
        # FIXME: When a widget is deleted, lv.EVENT.DELETE is triggered first, then lv.EVENT.DEFOCUSED,
        # causing an error when setting background color [widget already deleted]
        _stock_count = 0

async def display_multiple_stocks():
    global _stock_count

    if not _scr: return
    _scr.clean()

    # Create a menu object
    menu = lv.menu(_scr)
    menu.set_size(_SCR_WIDTH, _SCR_HEIGHT)
    menu.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
    menu.center()

    # Create a main page
    main_page = lv.menu_page(menu, None)
    # remove the scroll bar
    main_page.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

    for price_info in _stock_detials:
        # Try to render stock information
        try:
            menu_cont = await display_single_stock(main_page, price_info)
            if not menu_cont: continue
            menu_cont.add_event_cb(menu_cont_event_handler, lv.EVENT.ALL, None)
            lv.group_get_default().add_obj(menu_cont)
            _stock_count += 1
        except Exception as e:
            pass

    if _stock_count > 0:
        # For the last stock information widget, no need to add an underline
        main_page.get_child(-1).get_child(0).set_style_border_width(0, lv.PART.MAIN)
        menu.set_page(main_page)
        # Focus on the first stock information
        lv.group_focus_obj(main_page.get_child(0))
    else:
        # No stock information? Display "No Data" message
        _scr.clean()
        tip_label = lv.label(_scr)
        tip_label.set_text("Not Data...")
        tip_label.set_style_text_font(lv.font_ascii_18, lv.PART.MAIN)
        tip_label.set_style_text_color(lv.color_hex(0xA7A7A7), lv.PART.MAIN)
        tip_label.center()

async def on_start():
    global _scr
    if not _scr:
        _scr = lv.obj()
        _scr.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)
        _app_mgr.enter_root_page()
        lv.screen_load(_scr)

    # Check if network is connected
    if not net.connected():
        _app_mgr.error(
            "Network Not Connected",
            "Please wait for the network to be fully connected before accessing the app.",
            confirm = False, cb=lambda res: asyncio.create_task(_app_mgr.exit()))
        return

    # Load App configuration
    if not _load_config(): return

    # Display "Loading stock information" message
    loading_label = lv.label(_scr)
    loading_label.set_text("Fetching Stocks...")
    loading_label.align(lv.ALIGN.BOTTOM_MID, 0, -20)
    loading_label.set_style_text_font(lv.font_ascii_22, lv.PART.MAIN)
    loading_label.set_style_text_color(lv.color_hex3(0xFFF), lv.PART.MAIN)

    # If stock information already exists, display it directly
    if _stock_detials: await display_multiple_stocks()

async def on_stop():
    """Clean up the screen and leave the app when it stops."""
    global _scr
    if _scr:
        _scr.clean()
        _scr.delete_async()
        _scr = None
        _app_mgr.leave_root_page()

async def on_boot(apm):
    global _app_mgr
    _app_mgr = apm

async def on_running_foreground():
    """
    Handle actions when the app is running in the foreground.
    """
    global _last_updated, _stock_detials
    # When no stock information is displayed, no need to update
    if _scr.get_child_count() < 1: return

    now = clocktime.now()
    # No need to update if network not connected / time not synchronized / no stock configuration
    if not net.connected() or now < 0 or not _stock_symbols: return
    # No need to update if time interval not reached
    if now - _last_updated < _STOCK_UPDATE_INTERVAL: return

    # Time interval reached, fetch stock information again
    _stock_detials = await get_stock_detials(_stock_symbols)
    # Redraw stock information
    await display_multiple_stocks()
    _last_updated = now
