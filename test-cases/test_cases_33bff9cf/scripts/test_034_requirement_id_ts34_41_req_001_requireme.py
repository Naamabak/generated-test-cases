```python
# File: tests/test_embedded_service_layer_network_quality.py

"""
Test Case for:
Requirement ID: TS.34_4.1_REQ_001
Requirement: If data speed and latency are critical, the IoT Device Application SHOULD be able to retrieve mobile network speed and connection quality
information from the IoT Embedded Service Layer, in order to request appropriate quality of content from the IoT Service Platform.

References:
- GSMA TS.34 v8.0, Section 4.1, TS.34_4.1_REQ_001
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- Related: TS.34_4.0_REQ_010 (continuous monitoring for content quality adjustment)
"""

import pytest

# --- MOCK REPRESENTATION (Replace with integrations to device API/SDK and the real Embedded Service Layer as needed) ---

class MockEmbeddedServiceLayer:
    """Simulates the IoT Embedded Service Layer reporting network quality info."""
    def __init__(self):
        # Default: Excellent link
        self.current_metrics = {
            "speed_kbps": 8000,      # kbps
            "latency_ms": 50,        # ms
            "packet_loss_pct": 0.1   # percent
        }

    def set_network_conditions(self, speed_kbps, latency_ms, packet_loss_pct):
        self.current_metrics = {
            "speed_kbps": speed_kbps,
            "latency_ms": latency_ms,
            "packet_loss_pct": packet_loss_pct
        }

    def get_network_metrics(self):
        """What the Device Application can query."""
        return dict(self.current_metrics)

class MockIoTDeviceApplication:
    """Simulates the device application that queries the Embedded Service Layer and chooses content quality."""
    def __init__(self, embedded_service_layer):
        self.embedded_service_layer = embedded_service_layer
        self.request_log = []   # List of (network_metrics, requested_quality)
        
    def operate(self):
        """In a real device: would operate in main/service loop."""
        pass

    def retrieve_and_select_quality(self):
        """Queries the Embedded Service Layer and selects appropriate content quality for the Service Platform request."""
        metrics = self.embedded_service_layer.get_network_metrics()  # (step 3)
        # Decision logic: map metrics to content quality
        if metrics['speed_kbps'] > 3000 and metrics['latency_ms'] < 100 and metrics['packet_loss_pct'] <= 1:
            quality = 'high'
        elif metrics['speed_kbps'] > 1000 and metrics['latency_ms'] < 250 and metrics['packet_loss_pct'] <= 5:
            quality = 'medium'
        else:
            quality = 'low'
        self.request_content_from_platform(quality, metrics)

    def request_content_from_platform(self, quality, metrics):
        # Log the parameters for verification (step 4)
        # In a real app: would send a real request to the IoT Service Platform
        self.request_log.append({
            "network_metrics": metrics,
            "quality": quality
        })

    def get_request_log(self):
        return list(self.request_log)


# --- FIXTURES ---

@pytest.fixture
def embedded_service_layer():
    return MockEmbeddedServiceLayer()

@pytest.fixture
def iot_device_app(embedded_service_layer):
    return MockIoTDeviceApplication(embedded_service_layer)

# --- TEST CASES ---

@pytest.mark.parametrize("sim_name,metrics,expected_quality", [
    ("excellent", {"speed_kbps": 5500, "latency_ms": 60,  "packet_loss_pct": 0.2}, "high"),
    ("moderate",  {"speed_kbps": 1800, "latency_ms": 180, "packet_loss_pct": 3.0}, "medium"),
    ("poor",      {"speed_kbps": 450,  "latency_ms": 700, "packet_loss_pct": 10.0}, "low"),
])
def test_embedded_service_layer_quality_selection(iot_device_app, embedded_service_layer, sim_name, metrics, expected_quality):
    """
    TS.34_4.1_REQ_001: Verify device app:
        (a) retrieves network info from Embedded Service Layer,
        (b) requests content from platform at the quality matching metrics,
        (c) logs/outputs confirm correct adaptation for network change scenarios.
    """
    # Steps 1-2: Start in normal operation, then simulate network variability.
    embedded_service_layer.set_network_conditions(**metrics)

    # Step 3: Monitor if application queries the service layer (implicit in retrieve_and_select_quality())
    iot_device_app.retrieve_and_select_quality()

    # Step 4: Check the quality value used in the request to the Service Platform
    log = iot_device_app.get_request_log()
    assert log, "No content request made to IoT Service Platform"
    last_entry = log[-1]
    # (a) Confirm network metrics retrieved match simulated values
    assert last_entry['network_metrics'] == metrics, \
        f"Device app did not retrieve correct network metrics from Embedded Service Layer (expected {metrics}, got {last_entry['network_metrics']})"
    # (b) Content request must reflect correct quality selection
    assert last_entry['quality'] == expected_quality, \
        f"Device app did not select correct quality: expected {expected_quality}, got {last_entry['quality']}"
    
    # (c) Optionally, log output for test/debug
    print(f"[{sim_name}] metrics={metrics}, app_selected_quality={last_entry['quality']}")

def test_various_network_quality_cycles(iot_device_app, embedded_service_layer):
    """
    Further validates the application for at least three different network scenarios (step 5).
    """
    scenarios = [
        {"speed_kbps": 7500, "latency_ms": 80,  "packet_loss_pct": 0.3},  # high
        {"speed_kbps": 1500, "latency_ms": 210, "packet_loss_pct": 4.0},  # medium
        {"speed_kbps": 600,  "latency_ms": 500, "packet_loss_pct": 7.5},  # low
    ]

    expected = ['high', 'medium', 'low']

    for i, metrics in enumerate(scenarios):
        embedded_service_layer.set_network_conditions(**metrics)
        iot_device_app.retrieve_and_select_quality()
        last_entry = iot_device_app.get_request_log()[-1]
        assert last_entry['network_metrics'] == metrics
        assert last_entry['quality'] == expected[i], f"Cycle {i+1}: Expected {expected[i]}, got {last_entry['quality']}"

    print("All network conditions tested, correct adaptation logged for each scenario.")

```

---

**How to Use/Customize:**
- Place as `tests/test_embedded_service_layer_network_quality.py`.
- Replace mocks with real device SDK, Embedded Service Layer APIs, and actual content request hooks in integration/lab tests.
- Run with:
  ```
  pytest tests/test_embedded_service_layer_network_quality.py
  ```
- Coverage:
  - Verifies retrieval of network quality metrics from Embedded Service Layer
  - Checks that request to platform reflects metrics in quality selection
  - Covers at least three different network quality scenarios
  - Asserts all pass/fail criteria from GSMA TS.34_4.1_REQ_001

Let me know if you need integration with your actual device API, test lab, or Embedded Service Layer!