import json
from homeassistant.core import StateMachine
from ..state_interceptor_pb2 import StateWriteRequest


class StateMachineInterceptor:
    """Intercept state writes (the most important HA hook)."""

    def __init__(self, hass, grpc_client):
        self.hass = hass
        self.grpc = grpc_client
        self._orig_async_set = None

    def apply(self):
        if self._orig_async_set:
            return

        self._orig_async_set = StateMachine.async_set

        async def patched_async_set(
            sm_self, entity_id, new_state, attributes=None, force=False, context=None
        ):
            attrs = attributes or {}

            req = StateWriteRequest(
                entity_id=entity_id,
                state=str(new_state),
                attributes_json=json.dumps(attrs),
                context_id=str(context.id if context else ""),
            )

            try:
                resp = await self.grpc.InterceptStateWrite(req)
            except Exception as ex:
                self.hass.logger.error("StateMachineInterceptor: gRPC error: %s", ex)
                resp = None

            # Does .NET want to block this?
            if resp and resp.handled:
                return

            # Override state?
            if resp and resp.override_state:
                new_state = resp.override_state

            # Override attributes?
            if resp and resp.override_attributes_json:
                attributes = json.loads(resp.override_attributes_json)

            # Continue normal flow
            return await self._orig_async_set(
                sm_self, entity_id, new_state, attributes, force, context
            )

        # monkey patch
        StateMachine.async_set = patched_async_set
        self.hass.logger.info("net_core_bridge: StateMachine.async_set patched.")
