from homeassistant.helpers.entity_platform import EntityPlatform


class EntityPlatformInterceptor:
    """Intercept EntityPlatform lifecycle events."""

    def __init__(self, hass, grpc_client):
        self.hass = hass
        self.grpc = grpc_client

        self._orig_add = None
        self._orig_setup = None
        self._orig_reset = None

    def apply(self):
        self._orig_add = EntityPlatform.async_add_entities
        self._orig_setup = EntityPlatform.async_setup
        self._orig_reset = EntityPlatform.async_reset

        EntityPlatform.async_add_entities = self._patched_add_entities
        EntityPlatform.async_setup = self._patched_setup
        EntityPlatform.async_reset = self._patched_reset

        self.hass.logger.info("net_core_bridge: EntityPlatform patched.")

    async def _patched_add_entities(self, platform, entities, update_before_add=False):
        self.hass.logger.info(
            f"net_core_bridge: Adding {len(entities)} entities → "
            f"{platform.domain}.{platform.platform_name}"
        )

        # TODO: Send to .NET via self.grpc ...
        return await self._orig_add(platform, entities, update_before_add)

    async def _patched_setup(self, platform, *args, **kwargs):
        self.hass.logger.info(
            f"net_core_bridge: Platform setup → {platform.domain}.{platform.platform_name}"
        )
        return await self._orig_setup(platform, *args, **kwargs)

    async def _patched_reset(self, platform):
        self.hass.logger.info(
            f"net_core_bridge: Platform reset → {platform.domain}.{platform.platform_name}"
        )
        return await self._orig_reset(platform)
