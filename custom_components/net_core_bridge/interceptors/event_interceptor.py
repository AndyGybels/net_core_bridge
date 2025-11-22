import json
from homeassistant.core import EventBus

from ..clients.event_interceptor_pb2 import EventMessage
from ..clients.event_interceptor_pb2_grpc import EventInterceptorStub


class EventBusInterceptor:
    """Intercept Home Assistant event bus and forward events to .NET."""

    def __init__(self, hass, grpc_client: EventInterceptorStub):
        self.hass = hass
        self.grpc = grpc_client

    def apply(self):
        """Monkey patch hass.bus.async_fire to route through .NET first."""
        original_bus = self.hass.bus
        interceptor = self

        class ProxyEventBus(EventBus):
            async def async_fire(
                self2, event_type, event_data=None, origin=None, context=None
            ):
                return await interceptor._handle_event(
                    original_bus,
                    event_type,
                    event_data or {},
                    origin,
                    context,
                )

        # Replace the event bus
        self.hass.bus = ProxyEventBus(self.hass)
        self.hass.logger.info("net_core_bridge: EventBus patched.")

    # ---------------------------------------------------------
    # CORE EVENT HANDLER
    # ---------------------------------------------------------
    async def _handle_event(
        self, original_bus, event_type, event_data, origin, context
    ):
        """Forward event to .NET before letting Home Assistant process it."""

        evt = EventMessage(
            event_type=event_type,
            entity_id=event_data.get("entity_id", ""),
            json_data=json.dumps(event_data),
            context_id=str(context.id if context else ""),
        )

        resp = None
        try:
            resp = await self.grpc.InterceptEvent(evt)
        except Exception as ex:
            self.hass.logger.error("EventBusInterceptor: gRPC error: %s", ex)

        # If .NET wants to suppress the event, stop here.
        if resp and resp.handled:
            return None

        # Otherwise continue with the real event bus
        return await original_bus.async_fire(
            event_type,
            event_data,
            origin,
            context,
        )
