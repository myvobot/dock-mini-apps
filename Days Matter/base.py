import utime
import clocktime
import peripherals
from micropython import const

REFRESH_INTERVAL = const(300)
SECONDS_FROM_1970_TO_2000 = const(946684800)
SCR_WIDTH = peripherals.screen.screen_resolution[0]
SCR_HEIGHT = peripherals.screen.screen_resolution[1]

PRESET_TARGET_ITEM = {
    "new_year": {
        "name": "New Year",
        "time_tuple": [0, 1, 1, 24, 0, 0, 0, 0]
    },
    "halloween": {
        "name": "Halloween",
        "time_tuple": [0, 10, 31, 24, 0, 0, 0, 0]
    },
    "christmas": {
        "name": "Christmas",
        "time_tuple": [0, 12, 25, 24, 0, 0, 0, 0]
    },
    "brazil_independence_day": {
        "name": "Independence Day (Brazil)",
        "time_tuple": [0, 9, 7, 24, 0, 0, 0, 0]
    },
    "italy_republic_day": {
        "name": "Republic Day (Italy)",
        "time_tuple": [0, 6, 2, 24, 0, 0, 0, 0]
    },
    "mexico_independence_day": {
        "name": "Independence Day (Mexico)",
        "time_tuple": [0, 9, 16, 24, 0, 0, 0, 0]
    },
    "national_day_china": {
        "name": "National Day (China)",
        "time_tuple": [0, 10, 1, 24, 0, 0, 0, 0]
    },
    "canada_day": {
        "name": "Canada Day",
        "time_tuple": [0, 7, 1, 24, 0, 0, 0, 0]
    },
    "german_unity_day": {
        "name": "German Unity Day",
        "time_tuple": [0, 10, 3, 24, 0, 0, 0, 0]
    },
    "independence_day_usa": {
        "name": "Independence Day (USA)",
        "time_tuple": [0, 7, 4, 24, 0, 0, 0, 0]
    },
    "australia_day": {
        "name": "Australia Day",
        "time_tuple": [0, 1, 26, 24, 0, 0, 0, 0]
    },
    "bastille_day": {
        "name": "Bastille Day",
        "time_tuple": [0, 7, 14, 24, 0, 0, 0, 0]
    },
    "boxing_day": {
        "name": "Boxing Day",
        "time_tuple": [0, 12, 26, 24, 0, 0, 0, 0]
    },
}

PRESET_TARGET_LIST = [
    ["new_year",PRESET_TARGET_ITEM["new_year"]["name"]],
    ["christmas",PRESET_TARGET_ITEM["christmas"]["name"]],
    ["halloween",PRESET_TARGET_ITEM["halloween"]["name"]],
    ["brazil_independence_day",PRESET_TARGET_ITEM["brazil_independence_day"]["name"]],
    ["national_day_china",PRESET_TARGET_ITEM["national_day_china"]["name"]],
    ["bastille_day",PRESET_TARGET_ITEM["bastille_day"]["name"]],
    ["boxing_day",PRESET_TARGET_ITEM["boxing_day"]["name"]],
    ["canada_day",PRESET_TARGET_ITEM["canada_day"]["name"]],
    ["german_unity_day",PRESET_TARGET_ITEM["german_unity_day"]["name"]],
    ["independence_day_usa",PRESET_TARGET_ITEM["independence_day_usa"]["name"]],
    ["mexico_independence_day",PRESET_TARGET_ITEM["mexico_independence_day"]["name"]],
    ["australia_day",PRESET_TARGET_ITEM["australia_day"]["name"]],
    ["italy_republic_day",PRESET_TARGET_ITEM["italy_republic_day"]["name"]],
]

def time_tuple_to_timestamp(time_tuple):
    """Convert time tuple to timestamp"""
    return utime.mktime(time_tuple) + SECONDS_FROM_1970_TO_2000

def is_leap_year(year):
    """Check if the given year is a leap year"""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def get_days_in_month(year, month):
    """Get the number of days in the specified year and month"""
    if month in [4, 6, 9, 11]:
        return 30
    elif month == 2:
        if is_leap_year(year): return 29
        return 28
    else:
        return 31

def get_next_leap_year(year):
    """Get the next leap year after the given year"""
    year += 1
    while not is_leap_year(year):
        year += 1
    return year

def adjust_date(time_tuple, year_repeat):
    """Adjust date to handle special month day counts"""
    year, month, day = time_tuple[0], time_tuple[1], time_tuple[2]

    if year_repeat and month == 2 and day == 29:
        # If it's yearly repeat and not a leap year
        if not is_leap_year(year):
            # Find the next leap year
            next_leap = get_next_leap_year(year)
            time_tuple[0] = next_leap
            return time_tuple
    days_in_month = get_days_in_month(year, month)

    # If current date exceeds the number of days in the month
    while day > days_in_month:
        month += 1
        if month > 12:
            month = 1
            year += 1
        days_in_month = get_days_in_month(year, month)

    time_tuple[0], time_tuple[1] = year, month
    return time_tuple

def get_days_remaining(time_tuple):
    """Get the number of days remaining until the target time"""
    # time_tuple = (year, month, day, hour, minute, second, weekday, yearday)
    local_time = clocktime.datetime()
    now = time_tuple_to_timestamp(local_time)
    if time_tuple[0] == 0 or time_tuple[1] == 0:
        # If year or month is 0, use current year and month
        time_tuple[0] = local_time[0]
        if time_tuple[1] == 0:
            time_tuple[1] = local_time[1]
            if now - time_tuple_to_timestamp(time_tuple) > 86400:
                # If the day is greater than current day, add one month
                time_tuple[1] += 1
                if time_tuple[1] > 12:
                    time_tuple[1] = 1
                    time_tuple[0] += 1
                # Adjust the date
            time_tuple = adjust_date(time_tuple, False)
        else:
            if now - time_tuple_to_timestamp(time_tuple) > 86400:
                # If the day is greater than current day, add one year
                time_tuple[0] += 1
            # Adjust the date
            time_tuple = adjust_date(time_tuple, True)

    timestamp = time_tuple_to_timestamp(time_tuple)

    days_remaining = (timestamp - now) // 86400
    return days_remaining, time_tuple

def updata_days_remaining(days_list):
    """Update the remaining days for all events in the list and sort them"""
    for days in days_list:
        days["days_remaining"], days["show_time_tuple"] = get_days_remaining(days["time_tuple"].copy())
    # Sort by days_remaining
    days_list.sort(key=lambda x: x["days_remaining"])
    print(days_list)
    return days_list

def get_event_time(event_name, target_day, target_day_repeat):
    """Create an event object from event name, target day, and repeat settings"""
    if event_name and target_day:
        try:
            # Check if the date contains exactly two "-" characters
            if target_day.count("-") != 2:
                print(f"Invalid date format: {target_day}, expected format: YYYY-MM-DD")
                return {}

            target_day_str = target_day.split("-")
            # Check if there are exactly 3 parts after splitting
            if len(target_day_str) != 3:
                print(f"Invalid date format: {target_day}, expected format: YYYY-MM-DD")
                return {}

            # Convert to integers and validate date validity
            year = int(target_day_str[0])
            month = int(target_day_str[1])
            day = int(target_day_str[2])

            # Validate month
            if month < 1 or month > 12:
                print(f"Invalid month: {month}, should be between 1 and 12")
                return {}

            # Get the number of days in the month
            days_in_month = get_days_in_month(year, month)

            # Validate day
            if day < 1 or day > days_in_month:
                print(f"Invalid day: {day}, should be between 1 and {days_in_month} for month {month}")
                return {}

            # Set target time based on repeat settings
            if target_day_repeat == "0":
                target_time = [year, month, day, 24, 0, 0, 0, 0]
            elif target_day_repeat == "1":
                target_time = [0, month, day, 24, 0, 0, 0, 0]
            elif target_day_repeat == "2":
                target_time = [0, 0, day, 24, 0, 0, 0, 0]
            else:
                target_time = [year, month, day, 24, 0, 0, 0, 0]

            return {"name": event_name, "time_tuple": target_time, "show_time_tuple": []}

        except (ValueError, IndexError) as e:
            print(f"Error parsing date {target_day}: {str(e)}")
            return {}
    return {}
