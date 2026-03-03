```python
# File: tests/test_service_platform_trigger_on_device_attachment.py

"""
Test Case for:
Requirement ID : TS.34_6.0_REQ_004

Requirement:
The IoT Service Platform SHOULD be aware of the IoT Device’s state and only send ‘wake up’ triggers when the IoT Device is known to be attached to the mobile network.

References:
- GSMA TS.34 v8.0, Section 6.0, TS.34_6.0_REQ_004
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCKS / PLACEHOLDER CLASSES FOR DEMONSTRATION ---
# In a live environment, replace/migrate these to actual service platform/device APIs.

class MockIoTDevice:
    """Simulates an IoT Device attachment state and reporting to the Service Platform."""
    def __init__(self, device_id, platform):
        self.device_id = device_id
        self.attached = True  # default begins as attached
        self.platform = platform
        self.logs = []

    def set_attachment_state(self, attached: bool):
        """Simulates attach/detach action and notifies the platform."""
        self.attached = attached
        self.logs.append(f"Device attachment state set to: {'ATTACHED' if attached else 'DETACHED'}")
        self.platform.update_device_state(self.device_id, "attached" if attached else "detached")

    def get_logs(self):
        return list(self.logs)

class MockServicePlatform:
    """Simulates IoT Service Platform trigger logic gated by device attachment state."""
    def __init__(self):
        self.device_states = {}     # device_id -> "attached" or "detached"
        self.sent_triggers = []     # [(device_id, time_or_tag)]
        self.logs = []

    def register_device(self, device_id):
        self.device_states[device_id] = "attached"
        self.logs.append(f"Device {device_id} registered as ATTACHED (by default)")

    def update_device_state(self, device_id, state):
        self.device_states[device_id] = state
        self.logs.append(f"Device {device_id} state updated to: {state.upper()}")

    def send_wake_up_trigger(self, device_id, tag=None):
        """Sends a trigger only if device is attached."""
        state = self.device_states.get(device_id, "detached")
        if state == "attached":
            self.sent_triggers.append((device_id, tag or f"trigger-{len(self.sent_triggers)+1}"))
            self.logs.append(f"Wake up trigger SENT to {device_id}, tag={tag}")
            return True
        else:
            self.logs.append(f"Wake up trigger NOT sent to {device_id}, device is DETACHED")
            return False

    def get_sent_triggers(self, device_id=None):
        if device_id:
            return [tag for dev, tag in self.sent_triggers if dev == device_id]
        return list(self.sent_triggers)
    
    def get_logs(self):
        return list(self.logs)

# --- PYTEST FIXTURE ---

@pytest.fixture
def platform_and_device():
    platform = MockServicePlatform()
    device = MockIoTDevice("iot001", platform)
    platform.register_device(device.device_id)
    return platform, device

# --- TEST SCRIPT ---

def test_triggers_only_sent_when_device_attached(platform_and_device):
    """
    TS.34_6.0_REQ_004 core validation: platform must send triggers only when device is ATTACHED.
    """
    platform, device = platform_and_device

    # Step 1: Device starts attached; trigger is sent
    assert device.attached is True
    trigger_1 = platform.send_wake_up_trigger(device.device_id, tag="cycle1-attached")
    assert trigger_1, "Trigger should be sent when device is ATTACHED"
    assert platform.get_sent_triggers(device.device_id)[-1] == "cycle1-attached"

    # Step 2: Device detaches from network
    device.set_attachment_state(False)
    assert device.attached is False

    # Step 3: Attempt trigger when device is detached (should NOT send)
    trigger_2 = platform.send_wake_up_trigger(device.device_id, tag="cycle1-detached")
    assert not trigger_2, "Trigger should NOT be sent when device is DETACHED"
    triggers = platform.get_sent_triggers(device.device_id)
    assert "cycle1-detached" not in triggers

    # Step 4: Logs confirm: no trigger sent in detached state
    platform_logs = platform.get_logs()
    assert any("NOT sent" in log for log in platform_logs), "No log for blocked trigger in detached state"

    # Step 5: Reattach device, ensure state is updated and triggers can be sent again
    device.set_attachment_state(True)
    assert device.attached is True

    trigger_3 = platform.send_wake_up_trigger(device.device_id, tag="cycle1-reattached")
    assert trigger_3, "Trigger should be sent after device is reattached"
    assert "cycle1-reattached" in platform.get_sent_triggers(device.device_id)

    # Step 6: Repeat steps 2-5 for another cycle to confirm consistency
    for cycle in range(2, 4):
        device.set_attachment_state(False)
        trig = platform.send_wake_up_trigger(device.device_id, tag=f"cycle{cycle}-detached")
        assert not trig
        device.set_attachment_state(True)
        trig = platform.send_wake_up_trigger(device.device_id, tag=f"cycle{cycle}-reattached")
        assert trig

    # Step 7: Print logs for audit/compliance evidence
    print("Device Logs:", device.get_logs())
    print("Platform Logs:", platform.get_logs())
    print("Sent Triggers:", platform.get_sent_triggers(device.device_id))

    # Step 8: (Optional) Simulate another device for broad test
    other = MockIoTDevice("iot002", platform)
    platform.register_device(other.device_id)
    other.set_attachment_state(False)
    assert not platform.send_wake_up_trigger(other.device_id, tag="other-detached")
    other.set_attachment_state(True)
    assert platform.send_wake_up_trigger(other.device_id, tag="other-attached")

```
---

**Instructions:**

- Save as `tests/test_service_platform_trigger_on_device_attachment.py`.
- Integrate the mocks here with your actual platform/device APIs/logs as appropriate for your environment.
- This test cycles through attach/detach states, asserts correct trigger-sending logic, and checks logs/outputs per GSMA TS.34_6.0_REQ_004.
- Run with:
  ```bash
  pytest tests/test_service_platform_trigger_on_device_attachment.py
  ```
- Adjust or expand for production integration or more realistic state reporting as required.

Let me know if you need this adapted for real APIs, with networked device simulation, or log parser hooks!