```python
# File: tests/test_generic_alert_fumo_device_initiated_update.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_028

Requirement:
For IoT Communications Module-initiated updates, the module SHALL use the Generic Alert format
(OMA FUMO, OMA-TS-DM_FUMO-V1_0 Section 7.1.1) for the update request sent to the server.

References:
- GSMA TS.34-v8, Section 5.10, TS.34_5.10_REQ_028
- OMA-TS-DM_FUMO-V1_0, Section 7.1.1
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCKS / PLACEHOLDERS (replace with actual device/DM-server/testbed integration for real-world validation) ---

GENERIC_ALERT_TYPE = "org.openmobilealliance.dm.firmwareupdate.devicerequest"

class MockDeviceManagementServer:
    """
    Simulates a Device Management server that records received Generic Alert messages for update initiation.
    """
    def __init__(self):
        self.received_alerts = []

    def receive_generic_alert(self, alert):
        self.received_alerts.append(alert)

    def get_last_alert(self):
        return self.received_alerts[-1] if self.received_alerts else None

    def clear(self):
        self.received_alerts = []

class MockIoTCommModule:
    """
    Simulates an IoT Communications Module capable of device-initiated FUMO updates.
    When an update is requested, it uses the OMA DM Generic Alert format to notify the DM server.
    """
    def __init__(self, device_id="MOD12345"):
        self.device_id = device_id
        self.event_log = []
        self.sent_messages = []

    def trigger_device_initiated_update(self, dm_server):
        """
        Simulates a scenario in which the module self-initiates an update, and sends a Generic Alert to the DM server.
        """
        # Construct the alert as required by OMA FUMO Section 7.1.1
        alert_msg = {
            "MsgType": "Alert",
            "AlertCode": "1226",  # OMA Generic Alert code (per FUMO spec)
            "correlator": None,  # If used, per protocol
            "Type": GENERIC_ALERT_TYPE,
            "Data": None,        # Data field may be used to provide update parameters, version, etc. (optional)
            "Source": f"./FUMO", # Example LocURI, may be more specific in real product
            "Format": "chr"
        }
        self.event_log.append("Device-initiated update: sending Generic Alert for FUMO")
        self.sent_messages.append(alert_msg)
        dm_server.receive_generic_alert(alert_msg)

    def get_log(self):
        return list(self.event_log)

    def get_last_sent_message(self):
        return self.sent_messages[-1] if self.sent_messages else None

    def clear(self):
        self.event_log.clear()
        self.sent_messages.clear()

# --- TEST FIXTURES ---
@pytest.fixture
def env():
    dm_server = MockDeviceManagementServer()
    device = MockIoTCommModule()
    yield dm_server, device
    dm_server.clear()
    device.clear()

# --- TEST SCRIPT ---

def validate_generic_alert_format(alert):
    """
    Helper: Validate format/content of Generic Alert per OMA FUMO.
    """
    required_keys = {"MsgType", "AlertCode", "Type", "Format", "Source"}
    assert alert["MsgType"] == "Alert"
    assert alert["AlertCode"] == "1226", "Alert Code must be '1226' for Generic Alert (OMA DM spec Section 6.7, FUMO Section 7.1.1)"
    assert required_keys.issubset(alert), f"Generic Alert missing required fields: expected {required_keys}, got {alert.keys()}"
    assert alert["Type"] == GENERIC_ALERT_TYPE, f"Type must be '{GENERIC_ALERT_TYPE}'"
    assert alert["Format"] == "chr"
    assert alert["Source"].startswith("./FUMO")
    # Data may be None or a string, check if present
    assert "Data" in alert

@pytest.mark.parametrize("scenario", [
    "firmware_update_available",
    "forced_security_patch",
])
def test_device_initiated_update_uses_generic_alert(env, scenario):
    """
    TS.34_5.10_REQ_028:
    Every device-initiated update must send a properly-formatted Generic Alert as the first message to the DM server,
    with correct alert-type per OMA FUMO Section 7.1.1.
    """
    dm_server, device = env

    # Step 1: Trigger a device-initiated update (simulate for two distinct scenarios)
    device.trigger_device_initiated_update(dm_server)

    # Step 2: Monitor outgoing messages to DM server
    alert = dm_server.get_last_alert()
    assert alert, "No Generic Alert message was sent to DM server on device-initiated update!"

    # Step 3: Check that the first message is a Generic Alert with correct alert-type
    validate_generic_alert_format(alert)

    # Step 4: Log evidence for both test and audit
    print(f"[Device-Initiated Update: {scenario}] Generic Alert message: {alert}")

    # Step 5: Ensure repeated device-initiated updates also send correct format
    device.trigger_device_initiated_update(dm_server)
    new_alert = dm_server.get_last_alert()
    assert new_alert, "No Generic Alert sent on repeated update request!"
    validate_generic_alert_format(new_alert)

def test_no_alternative_message_format_is_used(env):
    """
    Ensures that update requests do NOT use proprietary or non-compliant message types.
    """
    dm_server, device = env
    device.trigger_device_initiated_update(dm_server)
    alert = dm_server.get_last_alert()
    assert alert
    other_types = ["UpdateRequest", "ProprietaryAlert", "MOD_UPDATE"]
    for other_type in other_types:
        assert alert.get("Type") != other_type, f"Disallowed or proprietary alert/message type used: {other_type}"
    print("No alternative/proprietary alert format detected for update request.")

def test_alert_format_and_type_strictly_enforced(env):
    """
    Negative: Test will fail if Alert is not formatted per OMA FUMO.
    """
    dm_server, device = env
    device.trigger_device_initiated_update(dm_server)
    alert = dm_server.get_last_alert()
    # Break compliance: change alert type to something else and verify the validation fails.
    alert_bad = dict(alert)
    alert_bad["Type"] = "incorrect.type"
    with pytest.raises(AssertionError):
        validate_generic_alert_format(alert_bad)
```

---

**How to use:**

- Save as `tests/test_generic_alert_fumo_device_initiated_update.py`
- Plug into your pytest test runner (or CI).
- Replace mocks with integration/lab hooks for your real IoT module's firmware/FUMO/OMADM implementation and DM server capture.
- Run with:
  ```bash
  pytest tests/test_generic_alert_fumo_device_initiated_update.py
  ```
- The assertions and helper validate the update request is always sent as a Generic Alert with the correct alert-type for OMA FUMO as per TS.34_5.10_REQ_028 and OMA FUMO Section 7.1.1.

Let me know if you need adaptation for direct packet capture or XML schema validation!