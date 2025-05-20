# Module: BLE scan utility functions

import aioble
import asyncio

# Flag to indicate whether scanning is enabled
_scan_enable = False

# Flag to indicate whether the scan task has finished
_is_scan_finished = True

# Mapping from GAP name to its callback: { gap_name: callback_func }
_gap_name_callbacks = {}

async def scan_ble_devices(duration_ms=60000,
                           interval_ms=30,
                           window_ms=30,
                           active=True,
                           filter_dup=True,
                           loop_count=-1):
    """
    Perform BLE scan with the given parameters.
    Invoke registered callbacks when a matching device is found.
    """
    global _is_scan_finished
    # If a previous scan is still running, skip starting a new one
    if not _is_scan_finished: return
    _is_scan_finished = False

    # Continue scanning until loop_count expires or scanning is disabled
    while loop_count < 0 or loop_count > 0:
        try:
            # Enter scanning context manager
            async with aioble.scan(
                duration_ms=duration_ms,
                interval_us=interval_ms * 1000,
                window_us=window_ms * 1000,
                active=active, filter_dup=filter_dup) as scanner:

                # Iterate over scan results
                async for result in scanner:
                    # If user requested to stop, cancel this scanner
                    if not _scan_enable:
                        await scanner.cancel()
                        break

                    name = result.name()
                    # Only process results that have a registered callback
                    if name not in list(_gap_name_callbacks.keys()): continue
                    # Invoke the callback with (address, rssi, adv_data)
                    _gap_name_callbacks[name](result.device.addr, result.rssi, result.adv_data)

            # If loop_count is positive, decrement it
            if loop_count > 0: loop_count -= 1
            # If scanning is disabled, break out of the loop
            elif not _scan_enable: break
        except Exception as e:
            # Log exception and continue retrying
            print(f"Error in BLE scan task: {str(e)}")

        # Brief pause before the next scan iteration
        await asyncio.sleep(1)

    # Mark scan task as finished
    _is_scan_finished = True

async def start_scan(duration_ms=60000, loop_count=-1):
    """
    Enable scanning and launch the BLE scan task.
    """
    global _scan_enable
    _scan_enable = True

    # Only start a new task if previous scan has finished
    if _is_scan_finished: asyncio.create_task(scan_ble_devices(duration_ms=duration_ms, loop_count=loop_count))

    # Wait until the scan task actually begins
    while _is_scan_finished: await asyncio.sleep_ms(100)

async def stop_scan():
    """
    Disable scanning and wait for the current scan task to complete.
    """
    global _scan_enable
    _scan_enable = False

    await wait_scan_complete()

async def wait_scan_complete():
    """
    Busy-wait until the scan task signals that it has finished.
    """
    while not _is_scan_finished: await asyncio.sleep_ms(100)

def set_gap_name_callbacks(gap_name_callbacks):
    """
    Replace current GAP name → callback mapping with the provided one.
    """
    global _gap_name_callbacks
    _gap_name_callbacks = gap_name_callbacks
