import lvgl as lv

# App Name
NAME = "Photo Album"

# App Icon
ICON = "A:apps/photo_album/resources/icon.png"

# LVGL widgets
scr = None

# Image paths
PHOTO_PATHS = [
    "A:apps/photo_album/resources/1.jpg",
    "A:apps/photo_album/resources/2.jpg",
    "A:apps/photo_album/resources/3.jpg",
    "A:apps/photo_album/resources/4.jpg"
]

# Constants
PHOTO_COUNT = len(PHOTO_PATHS)  # Number of photos
DEFAULT_BG_COLOR = lv.color_hex3(0x000)

# Current image index
photo_index = 0

def load_photo(index):
    global scr
    if scr:
        scr.set_style_bg_img_src(PHOTO_PATHS[index], lv.PART.MAIN)

def change_photo(delta):
    global photo_index
    photo_index = (photo_index + delta) % PHOTO_COUNT
    load_photo(photo_index)

def event_handler(event):
    e_code = event.get_code()
    if e_code == lv.EVENT.KEY:
        e_key = event.get_key()
        if e_key == lv.KEY.RIGHT:
            change_photo(1)
        elif e_key == lv.KEY.LEFT:
            change_photo(-1)
    elif e_code == lv.EVENT.FOCUSED:
        # If not in edit mode, set to edit mode.
        if not lv.group_get_default().get_editing():
            lv.group_get_default().set_editing(True)

async def on_stop():
    print('on stop')
    global scr
    if scr:
        scr.clean()
        scr.del_async()
        scr = None

async def on_start():
    print('on start')
    global scr
    scr = lv.obj()
    lv.scr_load(scr)

    scr.set_style_bg_color(DEFAULT_BG_COLOR, lv.PART.MAIN)
    load_photo(photo_index)  # Load the initial photo

    scr.add_event(event_handler, lv.EVENT.ALL, None)

    # Focus the key operation on the current screen and enable editing mode.
    lv.group_get_default().add_obj(scr)
    lv.group_focus_obj(scr)
    lv.group_get_default().set_editing(True)
