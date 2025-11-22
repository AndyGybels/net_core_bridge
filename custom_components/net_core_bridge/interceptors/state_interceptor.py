import json
from homeassistant.core import StateMachine

from ..clients.state_interceptor_pb2 import StateWriteRequest
from ..clients.state_interceptor_pb2_grpc import StateInterceptorStub


class StateMachineInterceptor:
    """Intercept Home Assistant state writes and forward them to .NET."""

    def __init__(self, hass, grpc_client: StateInterceptorStub):
        self.hass = hass
        self.grpc = grpc_client
        self._orig_async_set = None

    def apply(self):
        """Patch StateMachine.async_set once."""
        if self._orig_async_set is not None:
            return  # already patched

        self._orig_async_set = StateMachine.async_set
        interceptor = self

        async def patched_async_set(
            sm_self,
            entity_id,
            new_state,
            attributes=None,
            force=False,
            context=None,
        ):
            attrs = attributes or {}

            # Build protobuf request
            req = StateWriteRequest(
                entity_id=entity_id,
                state=str(new_state),
                attributes_json=json.dumps(attrs),
                context_id=str(context.id if context else ""),
            )

            resp = None
            try:
                resp = await interceptor.grpc.InterceptStateWrite(req)
            except Exception as ex:
                interceptor.hass.logger.error(
                    "StateMachineInterceptor: gRPC error: %s", ex
                )

            # If .NET vetoes the change → do NOT update HA state
            if resp and resp.handled:
                return None

            # If .NET wants to override the state value
            if resp and resp.override_state:
                new_state = resp.override_state

            # If .NET wants to override attributes
            if resp and resp.override_attributes_json:
                try:
                    attributes = json.loads(resp.override_attributes_json)
                except Exception:
                    interceptor.hass.logger.error(
                        "StateMachineInterceptor: Invalid override_attributes_json"
                    )

            # Continue normal HA state write
            return await interceptor._orig_async_set(
                sm_self, entity_id, new_state, attributes, force, context
            )

        # Monkey patch StateMachine.async_set
        StateMachine.async_set = patched_async_set
        self.hass.logger.info("net_core_bridge: StateMachine.async_set patched.")
