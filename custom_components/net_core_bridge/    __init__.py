from .bridge import NetCoreBridge


async def async_setup(hass, config):
    hass.data["net_core_bridge"] = NetCoreBridge(hass)
    hass.logger.info("net_core_bridge: unified bridge initialized.")
    return True
