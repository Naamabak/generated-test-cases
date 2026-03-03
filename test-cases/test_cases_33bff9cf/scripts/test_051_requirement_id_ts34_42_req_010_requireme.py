```python
# File: tests/test_embedded_service_layer_network_adaptation_content_quality.py

"""
Test Case for:
Requirement ID : TS.34_4.2_REQ_010

Requirement:
- If data speed and latency is critical to the IoT Service, the IoT Embedded Service Layer SHOULD constantly monitor
  mobile network speed and connection quality to request the appropriate quality of content from the IoT Service Platform.

References:
- GSMA TS.34 v8.0, Section 4.2, Requirement TS.34_4.2_REQ_010
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- Related: TS.34_4.1_REQ_001 for adaptation pattern
"""

import pytest

# --- MOCK IMPLEMENTATION (replace with real integration/test harness as needed) ---

class MockEmbeddedServiceLayer:
    """
    Simulates the ESL which frequently/continuously monitors network QoS and chooses content quality.
    """
    def __init__(self):
        self.network_log = []           # keeps a log of all network quality readings
        self.content_requests_log = []  # keeps a log of all quality/content requests made to the platform

    def monitor_network(self, throughput_kbps, latency_ms, packet_loss_pct):
        """ Simulate a monitoring sample (should be run frequently/continuously) """
        network = {
            "throughput_kbps": throughput_kbps,
            "latency_ms": latency_ms,
            "packet_loss_pct": packet_loss_pct
        }
        self.network_log.append(network)
        return network

    def select_content_quality(self, network):
        """
        Use the network measurements to select the appropriate service platform content quality.
        This is a stand-in for a more elaborate policy; typically implemented similar to below.
        """
        t = network["throughput_kbps"]
        l = network["latency_ms"]
        pl = network["packet_loss_pct"]

        if t >= 4000 and l < 75 and pl < 1.0:
            return "high"
        elif t >= 1500 and l < 200 and pl < 3.0:
            return "medium"
        else:
            return "low"

    def request_content(self, measured_quality, network_snapshot):
        """ Log a content request to the IoT Service Platform, including QoS decision """
        request = {
            "requested_quality": measured_quality,
            "network": dict(network_snapshot)
        }
        self.content_requests_log.append(request)

    def monitor_and_request_content(self, throughput_kbps, latency_ms, packet_loss_pct):
        """
        Simulate ESL's cycle: monitor, choose, and request.
        """
        network = self.monitor_network(throughput_kbps, latency_ms, packet_loss_pct)
        quality = self.select_content_quality(network)
        self.request_content(quality, network)

    def get_network_log(self):
        return list(self.network_log)

    def get_content_requests_log(self):
        return list(self.content_requests_log)

    def reset(self):
        self.network_log = []
        self.content_requests_log = []

# --- FIXTURE ---

@pytest.fixture
def esl():
    esl_instance = MockEmbeddedServiceLayer()
    yield esl_instance
    esl_instance.reset()

# --- TEST CASE ---

@pytest.mark.parametrize(
    "scenario,throughput,latency,loss,expected_quality",
    [
        ("excellent", 6000, 40, 0.1, "high"),
        ("good",      3000, 120, 1.8, "medium"),
        ("moderate",  1800, 180, 2.2, "medium"),
        ("congested", 700,  350, 8,   "low"),
        ("bad",       300,  900, 13,  "low"),
    ]
)
def test_esl_network_quality_content_adaptation(esl, scenario, throughput, latency, loss, expected_quality):
    """
    TS.34_4.2_REQ_010:
    - The ESL monitors network quality and chooses an appropriate content quality.
    - Content requests reflect real-time measured network status.
    """
    # Step 1–2: Simulate network variation for one test cycle
    esl.monitor_and_request_content(throughput, latency, loss)

    # Step 3-4: Logs show frequent monitoring of network, and request for content quality
    network_log = esl.get_network_log()
    content_requests_log = esl.get_content_requests_log()

    assert len(network_log) == 1, f"ESL should log every network quality sample (found {len(network_log)})"
    assert len(content_requests_log) == 1, f"ESL should produce a content request for each cycle (found {len(content_requests_log)})"

    # Step 5: Requested content quality must match expected per scenario/network measurement
    latest_request = content_requests_log[-1]
    assert latest_request["requested_quality"] == expected_quality, (
        f"Expected content quality '{expected_quality}' but got '{latest_request['requested_quality']}' "
        f"for network={network_log[-1]}"
    )
    # Confirm logged entry includes network state
    assert "network" in latest_request and latest_request["network"] == network_log[-1]

    # Output for reporting/debug
    print(f"Scenario [{scenario}]: {network_log[-1]} -> requested: {latest_request['requested_quality']}")


def test_esl_adapts_across_multiple_network_states(esl):
    """
    Repeat for several network transitions (as per test instruction) to verify consistent, reactive behavior.
    """
    scenarios = [
        (8000, 40, 0.1, "high"),
        (2000, 180, 2.2, "medium"),
        (600,  350, 6.5, "low"),
        (4500, 50, 0.0, "high"),
        (1600, 180, 2.0, "medium"),
    ]

    for (thr, lat, loss, exp_q) in scenarios:
        esl.monitor_and_request_content(thr, lat, loss)
        req = esl.get_content_requests_log()[-1]
        assert req["requested_quality"] == exp_q, (
            f"Cycle: {thr}/{lat}/{loss} expected '{exp_q}', got '{req['requested_quality']}'."
        )
    print("Network adaptation sequence:", esl.get_content_requests_log())

```
---

**How to use/adapt:**
- Save as `tests/test_embedded_service_layer_network_adaptation_content_quality.py`
- Replace/mock integration points for actual device/service layer network monitoring and platform communication.
- Add/extend as required for hardware/lab/CI.
- Run with:
  ```
  pytest tests/test_embedded_service_layer_network_adaptation_content_quality.py
  ```

**Coverage:**
- Continuous network metric assessment.
- Real-time content quality adaptation per measured network state.
- Verification over multiple changing network scenarios with explicit logs.
