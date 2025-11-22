from homeassistant.helpers.entity_platform import EntityPlatform
from homeassistant.core import callback

from ..clients.entity_platform_pb2 import (
    PlatformInfo,
    EntityInfo,
    EntitiesAddedRequest,
    EntityAddedRequest,
    EntityRemovedRequest,
    PlatformSetupRequest,
    PlatformResetRequest,
)
from ..clients.entity_platform_pb2_grpc import EntityPlatformInterceptorStub


class EntityPlatformInterceptor:
    """Intercept EntityPlatform lifecycle events and forward to .NET."""

    def __init__(self, hass, grpc_client: EntityPlatformInterceptorStub):
        self.hass = hass
        self.grpc = grpc_client

        self._orig_add = None
        self._orig_setup = None
        self._orig_reset = None
        self._orig_remove_entity = None

    def apply(self):
        """Monkey patch EntityPlatform functions."""

        self._orig_add = EntityPlatform.async_add_entities
        self._orig_setup = EntityPlatform.async_setup
        self._orig_reset = EntityPlatform.async_reset
        self._orig_remove_entity = EntityPlatform.async_remove_entity

        EntityPlatform.async_add_entities = self._patched_add_entities
        EntityPlatform.async_setup = self._patched_setup
        EntityPlatform.async_reset = self._patched_reset
        EntityPlatform.async_remove_entity = self._patched_remove_entity

        self.hass.logger.info("net_core_bridge: EntityPlatform patched.")

    # ---------------------------------------------------------
    # Helper: Build protobuf structures
    # ---------------------------------------------------------

    def _build_platform_info(self, platform: EntityPlatform) -> PlatformInfo:
        return PlatformInfo(
            domain=platform.domain,
            platform_name=platform.platform_name,
            config_entry_id=platform.config_entry.entry_id
            if platform.config_entry
            else "",
        )

    def _build_entity_info(self, entity) -> EntityInfo:
        return EntityInfo(
            entity_id=entity.entity_id or "",
            name=(entity.name or ""),
            domain=entity.platform.domain if entity.platform else "",
            platform=entity.platform.platform_name if entity.platform else "",
            unique_id=entity.unique_id or "",
            should_poll=entity.should_poll,
        )

    # ---------------------------------------------------------
    # PLATFORM SETUP
    # ---------------------------------------------------------

    async def _patched_setup(self, platform, *args, **kwargs):
        """Fire PlatformSetup → .NET"""
        req = PlatformSetupRequest(platform=self._build_platform_info(platform))

        try:
            await self.grpc.PlatformSetup(req)
        except Exception as ex:
            self.hass.logger.error(f"net_core_bridge: PlatformSetup RPC failed: {ex}")

        return await self._orig_setup(platform, *args, **kwargs)

    # ---------------------------------------------------------
    # PLATFORM RESET
    # ---------------------------------------------------------

    async def _patched_reset(self, platform):
        """Fire PlatformReset → .NET"""
        req = PlatformResetRequest(platform=self._build_platform_info(platform))

        try:
            await self.grpc.PlatformReset(req)
        except Exception as ex:
            self.hass.logger.error(f"net_core_bridge: PlatformReset RPC failed: {ex}")

        return await self._orig_reset(platform)

    # ---------------------------------------------------------
    # ADD ENTITIES
    # ---------------------------------------------------------

    async def _patched_add_entities(self, platform, entities, update_before_add=False):
        """Fire EntityAdded / EntitiesAdded → .NET"""

        # Batch RPC
        batch_req = EntitiesAddedRequest(
            platform=self._build_platform_info(platform),
            entities=[self._build_entity_info(e) for e in entities],
        )

        try:
            await self.grpc.EntitiesAdded(batch_req)
        except Exception as ex:
            self.hass.logger.error(f"net_core_bridge: EntitiesAdded RPC failed: {ex}")

        # Per-entity RPC
        for e in entities:
            single_req = EntityAddedRequest(
                platform=self._build_platform_info(platform),
                entity=self._build_entity_info(e),
            )
            try:
                await self.grpc.EntityAdded(single_req)
            except Exception as ex:
                self.hass.logger.error(
                    f"net_core_bridge: EntityAdded RPC failed for {e.entity_id}: {ex}"
                )

        return await self._orig_add(platform, entities, update_before_add)

    # ---------------------------------------------------------
    # REMOVE ENTITY
    # ---------------------------------------------------------

    async def _patched_remove_entity(self, platform, entity_id: str):
        """Fire EntityRemoved → .NET."""
        req = EntityRemovedRequest(
            platform=self._build_platform_info(platform),
            entity_id=entity_id,
        )

        try:
            await self.grpc.EntityRemoved(req)
        except Exception as ex:
            self.hass.logger.error(
                f"net_core_bridge: EntityRemoved RPC failed for {entity_id}: {ex}"
            )

        return await self._orig_remove_entity(platform, entity_id)
