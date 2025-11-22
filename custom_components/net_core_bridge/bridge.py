import sys
import grpc
from homeassistant.core import HomeAssistant

# Correct gRPC client imports based on your proto filenames
from .clients.event_interceptor_pb2_grpc import EventInterceptorStub
from .clients.state_interceptor_pb2_grpc import StateInterceptorStub
from .clients.entity_platform_pb2_grpc import EntityPlatformInterceptorStub

# Interceptors
from .interceptors.event_interceptor import EventBusInterceptor
from .interceptors.entity_platform_interceptor import EntityPlatformInterceptor
from .interceptors.state_interceptor import StateMachineInterceptor


class NetCoreBridge:
    """Main orchestrator for all .NET↔HA communication."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass

        # gRPC clients
        self.channel = None
        self.event_client = None
        self.state_client = None
        self.entity_platform_client = None

        self._init_grpc()

        # Apply interceptors
        EventBusInterceptor(hass, self.event_client).apply()
        EntityPlatformInterceptor(hass, self.entity_platform_client).apply()
        StateMachineInterceptor(hass, self.state_client).apply()

        hass.logger.info("net_core_bridge: All interceptors initialized.")

    # ---------------------------------------------------------
    # Transport: UDS (macOS/Linux) or TCP (Windows)
    # ---------------------------------------------------------
    def _init_grpc(self):
        if sys.platform.startswith("win"):
            target = "localhost:50051"
        else:
            target = "unix:/tmp/homeassistant_core.sock"

        self.channel = grpc.aio.insecure_channel(target)

        # Instantiate the stubs
        self.event_client = EventInterceptorStub(self.channel)
        self.state_client = StateInterceptorStub(self.channel)
        self.entity_platform_client = EntityPlatformInterceptorStub(self.channel)

        self.hass.logger.info(f"net_core_bridge: gRPC target = {target}")
