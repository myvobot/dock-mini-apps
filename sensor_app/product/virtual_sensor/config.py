# Virtual sensor models
_WINDOW_MODEL = 0x00        # Windows virtual sensor model code
_LINUX_MODEL = 0x01         # Linux virtual sensor model code
_MAC_MODEL = 0x02           # Mac virtual sensor model code

# Maximum number of historical measurements allowed to be stored
_MAX_HISTORY_MEASUREMENTS = 50 # Maximum history records

# Tuple of all model codes
_MODEL_CODE = (_WINDOW_MODEL, _LINUX_MODEL, _MAC_MODEL)

_PROFILE = {
    _WINDOW_MODEL: {
        "model": "Window Sensor",
        "name": "Virtual Temperature Sensor",
        "attr": {"display": {"attachInfo": ["temperature"]}}
    },
    _LINUX_MODEL: {
        "model": "Linux Sensor",
        "name": "Virtual Temperature Sensor",
        "attr": {"display": {"attachInfo": ["temperature"]}}
    },
    _MAC_MODEL: {
        "model": "Mac Sensor",
        "name": "Virtual Temperature Sensor",
        "attr": {"display": {"attachInfo": ["temperature"]}}
    }
}

def createFolder(p):
    # Create a folder if it does not exist
    try:
        import os
        os.mkdir(p)
    except OSError:
        pass

def remove(fileOrFolder):
    # Remove a file or folder, return True if successful, otherwise False
    try:
        import os
        os.remove(fileOrFolder)
        return True
    except:
        return False

def celsius2Fahrenheit(c):
    # Convert Celsius to Fahrenheit
    return c * 9 / 5 + 32

def getProfile(model):
    # Get the profile configuration for a given model code
    return _PROFILE.get(model, {})

def get_sensor_models():
    # Get a list of all available sensor models and their codes
    result = []
    for model_code in _MODEL_CODE:
        model_name = _PROFILE.get(model_code, {}).get("model", None)
        if model_name is None: continue
        result.append({model_name: model_code})
    return result
