from .self_test import run_bridge_self_test
from .bridge import NetCoreBridge


async def async_setup(hass, config):
    bridge = NetCoreBridge(hass)

    # Delay a bit so channel connects
    hass.async_create_task(_run_test(hass, bridge))

    return True


async def _run_test(hass, bridge):
    await hass.async_add_executor_job(lambda: time.sleep(1))
    await run_bridge_self_test(hass, bridge.channel)
