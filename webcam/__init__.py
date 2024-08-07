import lvgl as lv
import urequests
import net
import _thread
import time

# App Name
NAME: str = "Webcam"

# App Icon
ICON: str = "A:apps/webcam/resources/icon.png"

# LVGL widgets
scr: lv.obj = None
label: lv.obj = None

# App manager
app_mgr: Any = None
task_running: bool = False
task_running_lock = _thread.allocate_lock()

# Constants
DEFAULT_BG_COLOR = lv.color_hex3(0x000)

# Current image index
webcam_index: int = 0
webcam_name: str = ""
webcam_changed: bool = False

DEBUG: bool = False


def dprint(msg: str) -> None:
    """
    Print a debug message to console, if in debug mode.

    Args:
        msg (str): The message to print
    """
    if DEBUG:
        print(msg)


def load_image_from_url(url: str) -> None:
    """
    Actually load an image from a given URL.

    Args:
        url (str): The URL to load the image from

    Returns:
        LVGL Image description with the respective image.

    Raises:
        Exception, if something went wrong loading the image.
    """
    global task_running

    if url.startswith("http"):
        if net.connected():
            response = None
            if "@" in url and ":" in url:
                # we need to do basic auth
                start = url.index(":") + 3
                end = url.index("@")
                usernamepassword = url[start:end]
                url = url[:start] + url[(end + 1) :]
                if ":" in usernamepassword:
                    sep_index = usernamepassword.index(":")
                    username = usernamepassword[:sep_index]
                    password = usernamepassword[(sep_index + 1) :]
                    dprint(
                        f"Calling {url} with Username '{username}' and given password"
                    )
                    response = urequests.get(url, auth=(username, password))
            else:
                dprint(f"Calling {url} without basic auth")
                response = urequests.get(url)

            status_code = 0
            if response is not None:
                dprint(f"Got image with response {response.status_code}")
                status_code = response.status_code

            if task_running:
                if response is not None and response.status_code == 200:
                    image_description = lv.img_dsc_t(
                        {"data_size": len(response.content), "data": response.content}
                    )

                    response.close()

                    return image_description
                else:
                    if response is None:
                        raise Exception(f"Error URL wrongly formatted")
                    else:
                        response.close()
                        raise Exception(f"Error {status_code} while loading {url}")
            else:
                if response is not None:
                    response.close()
        else:
            raise Exception(f"Wifi not connected")
    else:
        raise Exception(f"Please configure webcams in application settings")


def load_webcam() -> None:
    """
    Task to manage loading the webcam images and displaying them.

    There is especially some error handling in this method.
    """
    global scr, label, webcam_index, task_running, task_running_lock, webcam_changed

    if scr is None:
        scr = lv.obj()
        lv.scr_load(scr)

    scr.set_style_bg_color(DEFAULT_BG_COLOR, lv.PART.MAIN)
    scr.set_style_bg_img_src("A:apps/webcam/resources/bg.png", lv.PART.MAIN)

    app_mgr_config = app_mgr.config()
    webcam_name = app_mgr_config.get(f"name{webcam_index + 1}", "")

    if label is None:
        label = lv.label(scr)
        label.center()
    label.set_text(f"Loading webcam {webcam_index + 1}...\n{webcam_name}")

    # Focus the key operation on the current screen and enable editing mode.
    lv.group_get_default().add_obj(scr)
    lv.group_focus_obj(scr)
    lv.group_get_default().set_editing(True)

    # Listen for keyboard events
    scr.add_event(event_handler, lv.EVENT.ALL, None)

    with task_running_lock:
        time.sleep_ms(800)  # Allow other tasks to run
        try:
            while task_running:
                url = app_mgr_config.get(f"url{webcam_index + 1}", "Unknown")

                try:
                    image_description = load_image_from_url(url)

                    if scr and not webcam_changed:  # can get None, if app was exited
                        label.set_text("")
                        scr.set_style_bg_img_src(image_description, lv.PART.MAIN)
                    webcam_changed = False
                except Exception as error:
                    dprint(f"Error: {error}")
                    if scr:  # can get None, if app was exited
                        label.set_text(str(error))
                        scr.set_style_bg_color(DEFAULT_BG_COLOR, lv.PART.MAIN)
                        time.sleep_ms(500)

                if task_running:
                    time.sleep_ms(100)  # Allow other tasks to run
        except Exception as err:
            print(f"Webcam thread had an exception: {err}")
            raise
    dprint("Webcam thread ended")


def change_webcam(delta: int) -> None:
    """
    Change the webcam.

    Also checks, if the settings have an entry for the new webcam. If not, the next camera is chosen.

    Args:
        delta (int): Get the next (+1) or previous (-1) camera
    """

    global webcam_index, app_mgr, scr, label, webcam_changed

    app_mgr_config = app_mgr.config()
    webcam_changed = True

    while True:
        webcam_index = (webcam_index + delta) % 5

        # Check if URL is valid:
        url = app_mgr_config.get(f"url{webcam_index + 1}", "Unknown")
        webcam_name = app_mgr_config.get(f"name{webcam_index + 1}", "")
        if url.startswith("http") or webcam_index == 0:
            scr.set_style_bg_img_src("A:apps/webcam/resources/bg.png", lv.PART.MAIN)
            label.set_text(f"Loading webcam {webcam_index + 1}...\n{webcam_name}")
            break


def event_handler(event) -> None:
    """
    Code executed when an event is called.

    Note:
    - This can be some paint events as well. Therefore, check the event code!
    - Don't call a method using "await"! Otherwise, the whole function becomes async!

    See https://docs.lvgl.io/master/overview/event.html for possible events.
    """
    global app_mgr
    e_code = event.get_code()

    if e_code == lv.EVENT.KEY:
        e_key = event.get_key()
        dprint(f"Got key {e_key}")
        if e_key == lv.KEY.RIGHT:
            change_webcam(1)
        elif e_key == lv.KEY.LEFT:
            change_webcam(-1)
        # Escape key == EXIT app is handled by the underlying OS
    elif e_code == lv.EVENT.FOCUSED:
        # If not in edit mode, set to edit mode.
        if not lv.group_get_default().get_editing():
            lv.group_get_default().set_editing(True)


async def on_boot(apm: Any) -> None:
    """
    Code executed on boot.
    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    global app_mgr
    app_mgr = apm


async def on_resume() -> None:
    """
    Code executed on resume. Essentially this starts the webcam thread.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    dprint("on resume")
    global task_running, task_running_lock

    if task_running_lock.locked():
        dprint("Waiting for lock to be released / previous thread to fininsh")
        while task_running_lock.locked():
            time.sleep_ms(100)

    dprint("Starting new thread")
    task_running = True
    _thread.start_new_thread(load_webcam, ())


async def on_pause() -> None:
    """
    Code executed on pause. This stops the webcam thread.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    dprint("on pause")
    global task_running
    task_running = False


async def on_stop() -> None:
    """
    Code executed on stop. Make sure, everything is cleaned up nicely.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    dprint("on stop")
    global scr, label, task_running, task_running_lock
    task_running = False
    scr.set_style_bg_img_src("A:apps/webcam/resources/bg.png", lv.PART.MAIN)
    label.set_text("Ending...")

    if task_running_lock.locked():
        dprint("Waiting for lock to be released / previous thread to fininsh")
        while task_running_lock.locked():
            time.sleep_ms(100)

    if scr is not None:
        scr.clean()
        scr.del_async()
        scr = None
        label = None


async def on_start() -> None:
    """
    Code executed on start.

    See https://dock.myvobot.com/developer/guides/app-design/ for clife cycle diagram
    """
    dprint("on start")


def get_settings_json() -> dict:
    """
    App settings.

    The app is configured via the webbrowser. This json helps creating the app settings page.
    See https://dock.myvobot.com/developer/reference/web-page/ for reference
    """
    return {
        "title": "Settings for Webcam app",
        "form": [
            {
                "type": "input",
                "default": "",
                "caption": "URL for webcam 1:",
                "name": "url1",
                "tip": "Images need to have 320x240 pixels resolution. They cannot be scaled.",
                "attributes": {"placeholder": "http://my.domain/webcam.jpg"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "Name for webcam 1",
                "name": "name1",
                "attributes": {"placeholder": "Frontdoor"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "URL for webcam 2:",
                "name": "url2",
                "tip": "Use http://{USERNAME}:{PASSWORD}@my.domain/webcam.jpg for Basic Auth.",
                "attributes": {"placeholder": "http://my.domain/webcam.jpg"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "Name for webcam 2",
                "name": "name2",
                "attributes": {"placeholder": "Frontdoor"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "URL for webcam 3:",
                "name": "url3",
                "tip": "Leave empty, if not used.",
                "attributes": {"placeholder": "http://my.domain/webcam.jpg"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "Name for webcam 3",
                "name": "name3",
                "attributes": {"placeholder": "Frontdoor"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "URL for webcam 4:",
                "name": "url4",
                "tip": "Leave empty, if not used.",
                "attributes": {"placeholder": "http://my.domain/webcam.jpg"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "Name for webcam 4",
                "name": "name4",
                "attributes": {"placeholder": "Frontdoor"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "URL for webcam 5:",
                "name": "url5",
                "tip": "Leave empty, if not used.",
                "attributes": {"placeholder": "http://my.domain/webcam.jpg"},
            },
            {
                "type": "input",
                "default": "",
                "caption": "Name for webcam 5",
                "name": "name5",
                "attributes": {"placeholder": "Frontdoor"},
            },
        ],
    }
