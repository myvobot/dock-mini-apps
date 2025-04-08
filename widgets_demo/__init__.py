import lvgl as lv
import peripherals

NAME = "Widgets Demo"
CAN_BE_AUTO_SWITCHED = True  # Indicates if the app can be auto-switched
_SCR_WIDTH = peripherals.screen.screen_resolution[0]  # Get the screen width from peripherals

_scr = None  # Initialize screen variable
_app_mgr = None  # Initialize app manager variable

async def show_ui():
    """Display the user interface elements on the screen."""
    if not _scr: return  # Ensure the screen is initialized

    # Clear the current content displayed on the screen
    _scr.clean()
    lv.group_get_default().set_editing(False)  # Disable editing mode for the default group

    # Initialize style for the container
    _container_style = lv.style_t()
    _container_style.init()  # Initialize the style
    _container_style.set_pad_all(0)  # Set padding to 0
    _container_style.set_border_width(0)  # Set border width to 0
    _container_style.set_bg_color(lv.color_hex3(0x000))  # Set background color to black

    # Create a container for the slider
    _sl_container = lv.obj(_scr)
    _sl_container.set_size(_SCR_WIDTH, 40)  # Set size of the container
    _sl_container.align(lv.ALIGN.TOP_LEFT, 0, 5)  # Align the container to the top left
    _sl_container.add_style(_container_style, lv.PART.MAIN)  # Add style to the container

    # Create a label for the slider
    _sl_label = lv.label(_sl_container)
    _sl_label.set_text("Slider")  # Set label text
    _sl_label.align(lv.ALIGN.LEFT_MID, 10, 0)  # Align the label

    # Create the slider
    _sl = lv.slider(_sl_container)
    _sl.set_size(_SCR_WIDTH // 2, 10)  # Set size of the slider
    _sl.align_to(_sl_label, lv.ALIGN.OUT_RIGHT_MID, 50, 0)  # Align the slider to the right of the label

    # Create a dropdown container
    _dw_container = lv.obj(_scr)
    _dw_container.set_size(_SCR_WIDTH, 50)  # Set size of the dropdown container
    _dw_container.align_to(_sl_container, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 0)  # Align below the slider container
    _dw_container.add_style(_container_style, lv.PART.MAIN)  # Add style to the dropdown container

    # Create a label for the dropdown
    _dw_label = lv.label(_dw_container)
    _dw_label.set_text("Dropdown")  # Set label text
    _dw_label.align(lv.ALIGN.LEFT_MID, 10, 0)  # Align the label

    # Create the dropdown
    _dw1 = lv.dropdown(_dw_container)
    _dw1.set_size(_SCR_WIDTH // 2, 40)  # Set size of the dropdown
    _dw1.set_options_static("\n".join(["Option 1", "Option 2", "Option 3"]))  # Set options for the dropdown
    _dw1.align_to(_dw_label, lv.ALIGN.OUT_RIGHT_MID, 10, 0)  # Align the dropdown to the right of the label

    # Create a switch container
    _sw_container = lv.obj(_scr)
    _sw_container.set_size(_SCR_WIDTH, 50)  # Set size of the switch container
    _sw_container.align_to(_dw_container, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 0)  # Align below the dropdown container
    _sw_container.add_style(_container_style, lv.PART.MAIN)  # Add style to the switch container

    # Create a label for the switch
    _sw_label = lv.label(_sw_container)
    _sw_label.set_text("Switch")  # Set label text
    _sw_label.align(lv.ALIGN.LEFT_MID, 10, 0)  # Align the label

    # Create the switch
    _sw = lv.switch(_sw_container)
    _sw.align_to(_sw_label, lv.ALIGN.OUT_RIGHT_MID, 40, 0)  # Align the switch to the right of the label

    # Create a checkbox container
    _cb_container = lv.obj(_scr)
    _cb_container.set_size(_SCR_WIDTH, 50)  # Set size of the checkbox container
    _cb_container.align_to(_sw_container, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 0)  # Align below the switch container
    _cb_container.add_style(_container_style, lv.PART.MAIN)  # Add style to the checkbox container

    # Create the checkbox
    _cb = lv.checkbox(_cb_container)
    _cb.set_text("Checkbox")  # Set checkbox text
    _cb.align(lv.ALIGN.LEFT_MID, 10, 0)  # Align the checkbox

    # Create a button
    _btn = lv.button(_scr)
    _btn.set_size(100, 40)  # Set size of the button
    _btn.align_to(_cb_container, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)  # Align below the checkbox container
    _btn_label = lv.label(_btn)  # Create a label for the button
    _btn_label.set_text("Enter")  # Set button label text
    _btn_label.align(lv.ALIGN.CENTER, 0, 1)  # Center the button label

async def on_start():
    """Initialize the screen and load the UI when the app starts."""
    global _scr
    if not _scr:
        _scr = lv.obj()  # Create a new screen object
        _scr.set_style_bg_color(lv.color_hex3(0x000), lv.PART.MAIN)  # Set background color to black
        _app_mgr.enter_root_page()  # Enter the root page of the app manager
        lv.screen_load(_scr)  # Load the screen

    await show_ui()  # Show the user interface

async def on_stop():
    """Clean up the screen and leave the app when it stops."""
    global _scr
    if _scr:
        _scr.clean()  # Clean the screen
        _scr.delete_async()  # Delete the screen asynchronously
        _scr = None  # Reset the screen variable
        _app_mgr.leave_root_page()  # Leave the root page of the app manager

async def on_boot(apm):
    """Initialize the app manager on boot."""
    global _app_mgr
    _app_mgr = apm  # Set the app manager

async def on_running_foreground():
    """Handle actions when the app is running in the foreground."""
    pass  # Currently no actions needed