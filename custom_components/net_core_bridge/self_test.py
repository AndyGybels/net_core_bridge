import time
import grpc

from .clients.event_interceptor_pb2_grpc import EventInterceptorStub
from .clients.event_interceptor_pb2 import EventMessage

from .clients.state_interceptor_pb2_grpc import StateInterceptorStub
from .clients.state_interceptor_pb2 import StateWriteRequest

from .clients.entity_platform_pb2_grpc import EntityPlatformInterceptorStub
from .clients.entity_platform_pb2 import PlatformSetupRequest, PlatformInfo


async def run_bridge_self_test(hass, channel):
    """Verify that all .NET gRPC services are reachable and responding."""

    hass.logger.info("net_core_bridge: Running self-test…")

    results = {}

    # ---------------------------------------------------------
    # Channel health check
    # ---------------------------------------------------------
    state = await channel.check_connectivity_state(False)
    results["channel_state"] = str(state)

    if state.name == "SHUTDOWN":
        hass.logger.error("net_core_bridge SELF-TEST FAILED: gRPC channel SHUTDOWN")
        return results

    # ---------------------------------------------------------
    # EVENT INTERCEPTOR TEST
    # ---------------------------------------------------------
    try:
        event_stub = EventInterceptorStub(channel)
        start = time.perf_counter()

        resp = await event_stub.InterceptEvent(
            EventMessage(
                event_type="net_core_bridge.self_test",
                entity_id="",
                json_data="{}",
                context_id="",
            )
        )

        latency = (time.perf_counter() - start) * 1000
        results["event_interceptor"] = {
            "ok": True,
            "latency_ms": latency,
            "response": resp.handled,
        }

    except Exception as ex:
        hass.logger.error("net_core_bridge SELF-TEST: EventInterceptor FAILED: %s", ex)
        results["event_interceptor"] = {"ok": False, "error": str(ex)}

    # ---------------------------------------------------------
    # STATE INTERCEPTOR TEST
    # ---------------------------------------------------------
    try:
        state_stub = StateInterceptorStub(channel)
        start = time.perf_counter()

        resp = await state_stub.InterceptStateWrite(
            StateWriteRequest(
                entity_id="self_test.entity",
                state="online",
                attributes_json="{}",
                context_id="",
            )
        )

        latency = (time.perf_counter() - start) * 1000
        results["state_interceptor"] = {
            "ok": True,
            "latency_ms": latency,
            "response": {
                "handled": resp.handled,
                "override_state": resp.override_state,
            },
        }

    except Exception as ex:
        hass.logger.error("net_core_bridge SELF-TEST: StateInterceptor FAILED: %s", ex)
        results["state_interceptor"] = {"ok": False, "error": str(ex)}

    # ---------------------------------------------------------
    # ENTITY PLATFORM INTERCEPTOR TEST
    # ---------------------------------------------------------
    try:
        ep_stub = EntityPlatformInterceptorStub(channel)
        start = time.perf_counter()

        resp = await ep_stub.PlatformSetup(
            PlatformSetupRequest(
                platform=PlatformInfo(
                    domain="self_test",
                    platform_name="self_test_platform",
                    config_entry_id="",
                )
            )
        )

        latency = (time.perf_counter() - start) * 1000
        results["entity_platform_interceptor"] = {
            "ok": True,
            "latency_ms": latency,
            "response": resp.ok,
        }

    except Exception as ex:
        hass.logger.error(
            "net_core_bridge SELF-TEST: EntityPlatformInterceptor FAILED: %s", ex
        )
        results["entity_platform_interceptor"] = {"ok": False, "error": str(ex)}

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------
    hass.logger.info("net_core_bridge SELF-TEST RESULTS:")
    for key, r in results.items():
        hass.logger.info(f"  {key}: {r}")

    return results
