import json
import picoweb
import settings
import clocktime
from . import base
from . import product

_app_mgr = None # Application manager instance
_product_registry = None # Mapping of product name to its model

def get_selected_sensors():
    """
    Retrieve a list of selected sensors with display info.
    Returns a list of dicts: {
        model, lastSeen, nickname, sensorId, brand
    }
    """
    sensor_list = []
    config = _app_mgr.config()
    selected_configs = config.get("selected", [])

    for sensor in selected_configs:
        p_model = _product_registry.get(sensor["product_name"], {})
        if not p_model: continue

        # Get human-readable model name if available
        model_name = "-"
        if hasattr(p_model, "get_profile"):
            model_name = p_model.get_profile(sensor["dev_model"]).get("model", "-")

        # Try live data timestamp first, then record info
        timestamp = None
        if hasattr(p_model, "get_sensor_data"):
            timestamp = p_model.get_sensor_data(sensor["sensor_id"]).get("timestamp", None)
        if timestamp is None and hasattr(p_model, "get_record_info"):
            timestamp = p_model.get_record_info(sensor["sensor_id"]).get("timestamp", None)

        # Format last seen time or use placeholder
        if timestamp is None:
            last_seen = "-/-/- -:-"
        else:
            tm = clocktime.datetime(timestamp)
            # Decide whether to use 12-hour format based on settings
            if not settings.hour24():
                if tm[3] < 12:
                    hour = str(tm[3])
                    time_tip = ""
                elif tm[3] == 12:
                    hour = str(tm[3])
                    time_tip = " PM"
                else:
                    hour = str(tm[3] - 12)
                    time_tip = " PM"
            else:
                time_tip = ""
                hour = f"{tm[3]:02d}"
            minute = f"{tm[4]:02d}"
            last_seen = "%s/%s/%d %s:%s%s" % (f"{tm[1]:02d}", f"{tm[2]:02d}", tm[0], hour, minute, time_tip) #"10/03/2024 15:59"

        sensor_list.append({
            "model": model_name,
            "lastSeen": last_seen,
            "nickname": sensor["nickname"],
            "sensorId": sensor["sensor_id"],
            "brand": sensor["product_name"],
        })

    return sensor_list

async def get_max_selectable(req, resp):
    """
    GET /sensor_app/get_max_selectable
    Return the maximum number of sensors that can be selected.
    """
    res = {"code": "403"}
    if req.method == "GET":
        res["code"] = "200"
        res["maxSelectable"] = base._MAX_SELECTABLE
    await picoweb.start_response(resp, status=res["code"], content_type="application/json")
    await resp.awrite(json.dumps(res))

async def card_view(req, resp):
    """
    POST /sensor_app/card_view
        - Set the number of display cards ("displayCount") in app configuration.
    GET /sensor_app/card_view
        - Retrieve the current display card count ("displayCount") from config.
    """
    res = {"code": "403"}
    config = _app_mgr.config()

    if req.method == "POST":
        await req.read_json_data()
        if "displayCount" not in req.form:
            res["code"] = "422"
            res["msg"] = "displayCount is required"
        else:
            if config.get("display_mode", None) != req.form["displayCount"]:
                config["display_mode"] = req.form["displayCount"]
                _app_mgr.config(config)
            res = {"code": "200"}
    elif req.method == "GET":
        res = {"code": "200", "displayCount": config.get("display_mode", 1)}

    await picoweb.start_response(resp, status=res["code"], content_type="application/json")
    await resp.awrite(json.dumps(res))

async def clear_cache(req, resp):
    """
    POST /sensor_app/clear_cache
        - Clear the cache for a given sensor ("sensorId") if it exists in selected list.
    """
    res = {"code": "403"}
    config = _app_mgr.config()

    if req.method == "POST":
        await req.read_json_data()
        if "sensorId" not in req.form:
            res["code"] = "422"
            res["msg"] = "sensorId is required"
        else:
            selected_sensor = config.get("selected", [])
            sensor_ids = [dev["sensor_id"] for dev in selected_sensor]
            if req.form["sensorId"] in sensor_ids:
                sensor =selected_sensor[sensor_ids.index(req.form["sensorId"])]
                p_model = _product_registry.get(sensor["product_name"], None)
                if p_model and hasattr(p_model, "clear_cache"):
                    p_model.clear_cache(sensor["sensor_id"])
                res["code"] = "200"
                res["msg"] = "cache cleared"
            else:
                res["code"] = "404"
                res["msg"] = "sensorId not found"

    await picoweb.start_response(resp, status=res["code"], content_type="application/json")
    await resp.awrite(json.dumps(res))

async def delete_sensor(req, resp):
    """
    DELETE /sensor_app/delete_sensor
        - Remove a sensor ("sensorId") from selected list and delete its data via product model.
    """
    res = {"code": "403"}
    config = _app_mgr.config()

    if req.method == "DELETE":
        await req.read_json_data()
        if "sensorId" not in req.form:
            res["code"] = "422"
            res["msg"] = "sensorId is required"
        else:
            selected_sensor = config.get("selected", [])
            sensor_ids = [dev["sensor_id"] for dev in selected_sensor]
            if req.form["sensorId"] in sensor_ids:
                del_sensor =selected_sensor.pop(sensor_ids.index(req.form["sensorId"]))
                p_model = _product_registry.get(del_sensor["product_name"], None)
                if p_model and hasattr(p_model, "delete_sensor_data"):
                    p_model.delete_sensor_data(del_sensor["sensor_id"])

                config["selected"] = selected_sensor
                _app_mgr.config(config)
                res = {"code": "200"}
            else:
                res["code"] = "404"
                res["msg"] = "sensorId not found"

    await picoweb.start_response(resp, status=res["code"], content_type="application/json")
    await resp.awrite(json.dumps(res))

async def get_sensors(req, resp):
    """
    GET /sensor_app/get_sensors
        - Return the list of currently selected sensors with display info.
    """
    res = {"code": "403"}
    if req.method == "GET":
        res["code"] = "200"
        res["sensors"] = get_selected_sensors()

    await picoweb.start_response(resp, content_type="application/json")
    await resp.awrite(json.dumps(res))

async def nickname(req, resp):
    """
    PUT /sensor_app/nickname
        - Update the nickname of a selected sensor ("sensorId") in app configuration.
    """
    res = {"code": "403"}
    config = _app_mgr.config()

    if req.method == "PUT":
        await req.read_json_data()
        if "sensorId" not in req.form or "nickname" not in req.form:
            res["code"] = "422"
            res["msg"] = "sensorId and nickname are required"
        else:
            selected_sensor = config.get("selected", [])
            for sensor in selected_sensor:
                if sensor["sensor_id"] != req.form["sensorId"]: continue
                sensor["nickname"] = req.form["nickname"]

            config["selected"] = selected_sensor
            _app_mgr.config(config)
            res = {"code": "200"}

    await picoweb.start_response(resp, status=res["code"], content_type="application/json")
    await resp.awrite(json.dumps(res))


async def ble_scan(req, resp):
    """
    POST /sensor_app/ble_scan
        - Perform a BLE scan for nearby sensors given "productName" and "modelId".
    """
    res = {"code": "403"}

    if req.method == "POST":
        res = {"code": "200"}
        await req.read_json_data()
        if "productName" not in req.form or "modelId" not in req.form:
            res["code"] = "422"
            res["msg"] = "productName and modelId are required"
        else:
            res["sensors"] = await base.search_nearby_sensors(req.form["productName"], req.form["modelId"])
    await picoweb.start_response(resp, status=res["code"], content_type="application/json")
    await resp.awrite(json.dumps(res))

async def add_sensors(req, resp):
    """
    POST /sensor_app/add_sensors
        - Add one or more sensors ("sensorIds") to the selected list under given product/model.
    """
    res = {"code": "403"}
    config = _app_mgr.config()

    if req.method == "POST":
        res = {"code": "200"}
        await req.read_json_data()
        data = req.form
        if "productName" not in data or "modelId" not in data or "sensorIds" not in data:
            res["code"] = "422"
            res["msg"] = "productName and modelId and sensorIds are required"
        else:
            selected_sensor = config.get("selected", [])
            sensor_ids = [dev["sensor_id"] for dev in selected_sensor]
            for sensor_id in data["sensorIds"]:
                if sensor_id in sensor_ids: continue
                selected_sensor.append({
                    "sensor_id": sensor_id,
                    "nickname": sensor_id[-6:],
                    "dev_model": data["modelId"],
                    "product_name": data["productName"]})

            config["selected"] = selected_sensor
            _app_mgr.config(config)
            res["code"] = "200"

    await picoweb.start_response(resp, status=res["code"], content_type="application/json")
    await resp.awrite(json.dumps(res))

async def get_product_info(req, resp):
    """
    GET /sensor_app/get_product_info
        - Return mapping of each product name to its supported sensor models.
    """
    if req.method != "GET":
        await picoweb.start_response(resp, status="403", content_type="application/json")
        return

    p_info = {}
    for p_name, p_model in _product_registry.items():
        if hasattr(p_model, "get_sensor_models"):
            p_info[p_name] = p_model.get_sensor_models()
        else:
            p_info[p_name] = []

    await picoweb.start_response(resp, content_type="application/json")
    await resp.awrite(json.dumps(p_info))

def get_routes():
    return [
        ("/sensor_app/get_max_selectable", get_max_selectable),
        ("/sensor_app/delete_sensor", delete_sensor),
        ("/sensor_app/get_sensors", get_sensors),
        ("/sensor_app/clear_cache", clear_cache),
        ("/sensor_app/card_view", card_view),
        ("/sensor_app/nickname", nickname),
        ("/sensor_app/ble_scan", ble_scan),
        ("/sensor_app/add_sensors", add_sensors),
        ("/sensor_app/get_product_info", get_product_info),
    ]

def init(apm):
    global _app_mgr, _product_registry
    _app_mgr = apm
    _product_registry = product.get_product_registry()
