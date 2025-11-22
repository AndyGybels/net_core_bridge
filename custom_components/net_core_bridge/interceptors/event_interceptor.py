import json
from homeassistant.core import EventBus
from ..hacore_pb2 import EventMessage


class EventBusInterceptor:
    """Intercept Home Assistant event bus and forward events to .NET."""

    def __init__(self, hass, grpc_client):
        self.hass = hass
        self.grpc = grpc_client

    def apply(self):
        """Patch hass.bus.async_fire."""
        original_bus = self.hass.bus
        interceptor = self

        class ProxyEventBus(EventBus):
            async def async_fire(
                self2, event_type, event_data=None, origin=None, context=None
            ):
                return await interceptor._handle_event(
                    original_bus, event_type, event_data or {}, origin, context
                )

        self.hass.bus = ProxyEventBus(self.hass)
        self.hass.logger.info("net_core_bridge: EventBus patched.")

    async def _handle_event(
        self, original_bus, event_type, event_data, origin, context
    ):
        evt = EventMessage(
            event_type=event_type,
            entity_id=event_data.get("entity_id", ""),
            json_data=json.dumps(event_data),
            context_id=str(context.id if context else ""),
        )

        try:
            resp = await self.grpc.InterceptEvent(evt)
        except Exception as ex:
            self.hass.logger.error("EventBusInterceptor: gRPC error: %s", ex)
            resp = None

        if resp and resp.handled:
            return  # .NET suppressed event

        return await original_bus.async_fire(event_type, event_data, origin, context)
