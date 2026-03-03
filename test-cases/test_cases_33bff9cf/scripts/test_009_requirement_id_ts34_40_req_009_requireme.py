```python
# File: tests/test_network_adaptation.py

"""
Test Case for:
Requirement ID: TS.34_4.0_REQ_009
Requirement: The IoT Device Application SHOULD be capable of adapting to changes in mobile network type and data speed at any given time.
Reference: GSMA TS.34-v8, Section 4.0, TS.34_4.0_REQ_009

This test models/simulates the IoT Device Application's adaptation strategies under different RAT/mobile network types and data speeds.
Replace the 'MockIoTDeviceApp' and state transitions with the actual device interface or API calls for real-world/integration tests.
"""

import pytest

# Mock representation for demonstration. Replace with actual APIs or device control modules in live/lab execution.
class MockIoTDeviceApp:
    SUPPORTED_NETWORKS = [
        {"rat": "LTE", "speed": "high"},
        {"rat": "3G", "speed": "medium"},
        {"rat": "2G", "speed": "low"},
        {"rat": "LTE-M", "speed": "medium"},
        {"rat": "NB-IoT", "speed": "low"},
    ]
    
    def __init__(self):
        self.current_network = None
        self.adaptation_log = []
        self.running = False

    def power_on(self):
        self.running = True
        # Start on LTE by default
        self.current_network = {"rat": "LTE", "speed": "high"}
        self.log_adaptation("Initial LTE connection established (high speed).")

    def force_network_change(self, network_type):
        """
        Simulate/force a handover to a different RAT type and speed.
        """
        net_config = next((n for n in self.SUPPORTED_NETWORKS if n['rat'] == network_type), None)
        if net_config:
            self.current_network = net_config
            self.adapt_to_network(net_config)
        else:
            raise Exception(f"Unsupported RAT requested: {network_type}")

    def adapt_to_network(self, net_config):
        """Application should adapt logic based on new network condition."""
        rat = net_config["rat"]
        speed = net_config["speed"]
        # Log what adaptation (mocked example)
        if speed == "high":
            self.log_adaptation(f"Switched to {rat}: Normal/best-effort mode. Standard protocol, normal transmission frequency.")
        elif speed == "medium":
            self.log_adaptation(f"Switched to {rat}: Moderately efficient mode. May reduce payload size or batch messages.")
        else:  # low speed
            self.log_adaptation(f"Switched to {rat}: High-efficiency mode. Adapts by using compressed payloads, decreasing transmission frequency, and batching messages.")
        # Simulate communication attempt
        self.log_communication(rat, speed)

    def log_adaptation(self, msg):
        self.adaptation_log.append({"event": "adaptation", "msg": msg})

    def log_communication(self, rat, speed):
        # Log/record communication event for monitoring
        self.adaptation_log.append({"event": "communication", "msg": f"Sent data over {rat} ({speed} speed)."})

    def get_adaptation_events(self):
        return [entry for entry in self.adaptation_log if entry["event"] == "adaptation"]

    def get_communication_events(self):
        return [entry for entry in self.adaptation_log if entry["event"] == "communication"]

    def reset(self):
        self.adaptation_log = []
        self.running = False
        self.current_network = None

@pytest.fixture
def iot_device_app():
    """Fixture for a fresh/mock IoT Device Application."""
    app = MockIoTDeviceApp()
    yield app
    app.reset()

@pytest.mark.parametrize("rat_type,speed,efficiency_expected", [
    ("LTE", "high", "Normal/best-effort mode"),
    ("3G", "medium", "Moderately efficient mode"),
    ("LTE-M", "medium", "Moderately efficient mode"),
    ("2G", "low", "High-efficiency mode"),
    ("NB-IoT", "low", "High-efficiency mode"),
])
def test_device_adapts_to_network_changes(iot_device_app, rat_type, speed, efficiency_expected):
    """
    Test that the IoT Device Application observes and adapts to all provided RAT/network speed changes,
    and applies application-side adaptations as required by TS.34_4.0_REQ_009.
    """
    # Step 1: Power on device (assume LTE start)
    iot_device_app.power_on()
    # Step 2: Force network environment to given RAT
    iot_device_app.force_network_change(rat_type)
    # Step 3: Monitor adaptation log
    adapts = iot_device_app.get_adaptation_events()
    found_msg = any(efficiency_expected in entry["msg"] for entry in adapts)
    assert found_msg, f"App did not perform expected adaptation for {rat_type} ({speed}). Log: {adapts}"
    # Step 4: Communication log must show device continues operation (i.e., no failure or disconnect).
    communications = iot_device_app.get_communication_events()
    assert len(communications) > 0
    # Step 5: For low/medium speed, adaptation should not just downgrade but actively adjust logic (e.g., batching/compression).
    if speed in ["low", "medium"]:
        found_keywords = any(
            ("batch" in entry["msg"].lower() or 
             "compressed" in entry["msg"].lower() or 
             "reduce" in entry["msg"].lower() or
             "decreas" in entry["msg"].lower())
            for entry in adapts
        )
        assert found_keywords, f"Adaptation for slow RAT {rat_type} does not reflect payload/timing adjustments. Log: {adapts}"

def test_device_cycles_all_supported_rats(iot_device_app):
    """Test the IoT Device Application can adapt and operate continuously through all supported RAT switches."""
    # Step 1: Initial power on
    iot_device_app.power_on()
    all_rats = [net['rat'] for net in MockIoTDeviceApp.SUPPORTED_NETWORKS]
    for rat in all_rats:
        iot_device_app.force_network_change(rat)
        # Should always be able to send data and adapt without error
        communications = iot_device_app.get_communication_events()
        assert len(communications) >= 1
        adapts = iot_device_app.get_adaptation_events()
        # There should be at least one adaptation event for each network change
        assert len(adapts) >= 1
    # Optional: Print adaptation log for human review/debug
    print("Adaptation Log:", iot_device_app.adaptation_log)
```

---

**Instructions:**
- Save as `tests/test_network_adaptation.py`.
- Replace the `MockIoTDeviceApp` with your device’s real interface and logs for real-world runs.
- Run with:  
  ```
  pytest tests/test_network_adaptation.py
  ```

**Coverage:**  
- Powers on and cycles through multiple RAT/network types.
- Checks adaptation (e.g., switching to efficient/batched/compressed modes under low/slow networks).
- Ensures communication continues reliably throughout changes.
- Each step’s adaptation can be expanded to check for device-specific protocol, batching, data compression, or scheduling changes according to device/app API.

Let me know if you want this scaffolding against your actual device APIs!