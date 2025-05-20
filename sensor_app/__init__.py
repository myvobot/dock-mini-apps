from . import base
from . import routes

NAME = "Sensor App"
CAN_BE_AUTO_SWITCHED = True  # Indicates if the app can be auto-switched

def get_settings_json():
    return {
        "form": [{
            "type": "customPage",
            "html_file": "asset/html/home.html",
            "routes": routes.get_routes(),
        }]
    }

async def on_start():
    """Initialize the screen and load the UI when the app starts."""
    await base.on_start()

async def on_stop():
    """Clean up the screen and leave the app when it stops."""
    await base.on_stop()

async def on_boot(apm):
    """Initialize the app manager on boot."""
    routes.init(apm)
    await base.on_boot(apm)

async def on_running_foreground():
    """
    Handle actions when the app is running in the foreground.
    """
    await base.on_running_foreground()
