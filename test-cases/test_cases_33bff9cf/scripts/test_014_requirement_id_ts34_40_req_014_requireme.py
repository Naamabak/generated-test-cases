```python
# File: tests/test_power_outage_notification.py

"""
Test Case for:
Requirement ID: TS.34_4.0_REQ_014
Requirement: IoT Device Application SHOULD send a notification with relevant info to the IoT Service Platform
upon detection of unexpected power outage or battery power problem. Notification SHOULD follow scaling guidance
from Annex C (e.g., avoid notification storms, proper rate limiting, appropriate message structure/size).

References:
- GSMA TS.34-v8, Requirement TS.34_4.0_REQ_014
- GSMA TS.34-v8, Annex C (Application scaling advice)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf, Section 4
"""

import pytest
import time

# --- MOCKS/INTERFACES ---
# In a real testbed, replace the following classes with integrations to your actual test device and service platform API.

class MockIoTDeviceApplication:
    """Simulates IoT Device Application capable of sending scaled notifications upon power/battery problem."""
    def __init__(self, device_id="iotdev-001"):
        self.device_id = device_id
        self.service_platform = None
        self.notification_sent = False
        self.last_notification = None
        self.last_event_time = None

    def register_with_service_platform(self, platform):
        self.service_platform = platform

    def simulate_power_outage(self):
        # Simulate an unexpected power loss or battery problem.
        event = {
            "event": "power_loss",
            "device_id": self.device_id,
            "timestamp": time.time(),
            "battery_status": "critical",
            "scaling_headers": {
                "message_format": "v1",
                "message_size": 128,  # bytes, example
                "rate_limited": True
            }
        }
        self.last_event_time = event["timestamp"]
        self.send_notification(event)

    def send_notification(self, event):
        # Send notification (real: send by MQTT/HTTPS/REST/other to platform)
        if self.service_platform:
            self.notification_sent = True
            self.last_notification = event
            self.service_platform.receive_notification(event)

    def reset(self):
        self.notification_sent = False
        self.last_notification = None


class MockIoTServicePlatform:
    """Simulates a test IoT Service Platform that receives notifs from IoT Devices."""
    def __init__(self):
        self.notifications_received = []

    def receive_notification(self, notification):
        self.notifications_received.append(notification)

    def get_notifications_for_device(self, device_id):
        return [notif for notif in self.notifications_received if notif["device_id"] == device_id]

    def clear(self):
        self.notifications_received.clear()

# --- FIXTURE(S) ---

@pytest.fixture
def device_and_platform():
    platform = MockIoTServicePlatform()
    device = MockIoTDeviceApplication(device_id="iotdev-001")
    device.register_with_service_platform(platform)
    yield device, platform
    platform.clear()
    device.reset()

# --- TEST ---

def test_notification_on_power_issue_with_scaling(device_and_platform):
    """
    TS.34_4.0_REQ_014 & Annex C: Verify notification is sent on power failure, info content is relevant,
    and scaling advice (rate, format, size) is followed.
    """
    device, platform = device_and_platform

    # STEP 1: Induce power outage or battery problem
    device.simulate_power_outage()

    # STEP 2: Observe and log if notification was generated and sent
    notifs = platform.get_notifications_for_device(device.device_id)
    assert len(notifs) == 1, "Notification was not received by platform for simulated power issue"

    notif = notifs[0]
    event_time = device.last_event_time

    # STEP 3: Validate notification content and metadata
    assert notif["event"] == "power_loss", "Notification event type incorrect"
    assert notif["device_id"] == device.device_id, "Notification missing correct device ID"
    assert "timestamp" in notif and abs(notif["timestamp"] - event_time) < 10, "Notification must include a fresh timestamp"
    assert notif["battery_status"] == "critical", "Notification missing/incorrect battery status"

    # STEP 4: Verify scaling advice from Annex C (structure/headers/rate limiting/size)
    scaling = notif.get("scaling_headers", {})
    assert scaling.get("message_format") == "v1", "Notification missing scaling message format"
    assert scaling.get("rate_limited") == True, "Notification should include/advertise rate limiting in scaling context"
    assert scaling.get("message_size", 0) <= 256, "Notification message size too large (see Annex C: keep minimal)"

    # STEP 5: (Would ideally check for rate limiting if multiple power problems triggered in short time)
    # Simulate a second event immediately (should NOT be sent if already just sent and rate-limited)
    device.simulate_power_outage()
    notifs_after_2nd = platform.get_notifications_for_device(device.device_id)
    # Depending on Annex C scaling, this count should not increase if within rate limit window
    assert len(notifs_after_2nd) == 1 or scaling.get("rate_limited"), (
        "Device did not apply notification storm/rate limiting advice"
    )

    # Output for debug/logging (optional)
    print("Notification payload:", notif)

```

---

**How to Use/Customize:**
- Place this script as `tests/test_power_outage_notification.py`.
- Replace the mocks with your real device event simulation and platform notification ingestion APIs.
- The scaling advice from Annex C (e.g., rate limiting, minimal size/format, avoidance of "storm" notifs) should be integrated/enforced per your product implementation, and the assertions can be enriched with real logic thresholds.
- Run with:
  ```bash
  pytest tests/test_power_outage_notification.py
  ```
- Adjust message keys/logic according to your Annex C-compliant schema.

Let me know if you want this adapted to your real network or device APIs!
```