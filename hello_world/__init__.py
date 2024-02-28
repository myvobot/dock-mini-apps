import lvgl as lv

# Name of the App
NAME = "Hello World"

# Initialize LVGL objects
scr = lv.obj()
label = None
counter = 0

async def on_running_foreground():
    """Called when the app is active, approximately every 200ms."""
    global counter
    counter += 1
    # Update the text of the label widget.
    label.set_text(f'{NAME} {counter}')

async def on_stop():
    scr.clean()

async def on_start():
    global label
    # Create and initialize LVGL widgets
    label = lv.label(scr)
    label.set_text(NAME)
    lv.scr_load(scr)
