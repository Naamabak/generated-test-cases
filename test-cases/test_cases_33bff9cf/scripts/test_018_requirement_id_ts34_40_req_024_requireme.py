```python
# File: tests/test_factory_reset.py

"""
Requirement:
    TS.34_4.0_REQ_024
    The IoT Device Application SHOULD support a “reset to factory settings” via remote and local connection.

References:
    - GSMA TS.34 v8.0, Section 4.0, Requirement TS.34_4.0_REQ_024
    - TS.34_4.2_REQ_024 (Embedded Service Layer function)
    - Test checks BOTH remote and local reset to factory settings, and restoration of original state.
"""

import pytest

# ---- MOCK IMPLEMENTATION (Replace the following class with your real device API or SDK connection) ----

class MockIoTDeviceApplication:
    """Simulates an IoT Device with settings, user data, and reset to factory functions."""
    FACTORY_DEFAULTS = {
        "settings": {
            "wifi_ssid": "default-net",
            "timezone": "UTC",
            "app_mode": "basic"
        },
        "user_data": {
            "profile": None,
            "device_name": "IoT Factory",
            "logs": []
        }
    }

    def __init__(self):
        self.reset_to_factory()

    def alter_settings_and_data(self):
        self.settings["wifi_ssid"] = "altered-net"
        self.settings["timezone"] = "Europe/Berlin"
        self.settings["app_mode"] = "advanced"
        self.user_data["profile"] = {"username": "alice", "level": 7}
        self.user_data["device_name"] = "TestDevice01"
        self.user_data["logs"] = ["sample log A", "sample log B"]

    def reset_to_factory(self):
        self.settings = self.FACTORY_DEFAULTS["settings"].copy()
        self.user_data = self.FACTORY_DEFAULTS["user_data"].copy()
        self.status_log = ["reset to factory settings"]

    def reset_remote(self):
        # Simulate OTA or cloud-API triggered reset
        self.reset_to_factory()
        self.status_log.append("remote reset completed")

    def reset_local(self):
        # Simulate physical button/UI/menu driven reset
        self.reset_to_factory()
        self.status_log.append("local reset completed")

    def get_current_state(self):
        return {
            "settings": self.settings.copy(),
            "user_data": self.user_data.copy(),
        }

    def is_factory_default(self):
        return (self.settings == self.FACTORY_DEFAULTS["settings"] and
                self.user_data == self.FACTORY_DEFAULTS["user_data"])

    def get_status_log(self):
        return list(self.status_log)

# ---- FIXTURE ----

@pytest.fixture
def device():
    """Yield a fresh device in factory default state for each test."""
    dev = MockIoTDeviceApplication()
    return dev

# ---- TEST CASE ----

def test_factory_reset_remote_and_local(device):
    """TS.34_4.0_REQ_024: Verify both remote and local factory resets restore device to original state."""

    # Step 1: Alter device state from factory defaults to unique values
    device.alter_settings_and_data()
    state_after_alter = device.get_current_state()
    assert state_after_alter["settings"]["wifi_ssid"] == "altered-net"
    assert state_after_alter["user_data"]["profile"] == {"username": "alice", "level": 7}
    assert not device.is_factory_default()

    # Step 2: Trigger remote factory reset and monitor
    device.reset_remote()
    state_after_remote_reset = device.get_current_state()

    # Step 3: Verify all settings and data have reverted to factory defaults
    assert device.is_factory_default(), "Remote factory reset should restore factory defaults"
    # Confirm log tracks remote reset
    assert "remote reset completed" in device.get_status_log()

    # Step 4: Alter device state again to a different unique non-default state
    device.alter_settings_and_data()
    state_after_alter_2 = device.get_current_state()
    assert state_after_alter_2["settings"]["app_mode"] == "advanced"
    assert not device.is_factory_default()

    # Step 5: Trigger local factory reset and monitor
    device.reset_local()
    state_after_local_reset = device.get_current_state()

    # Step 6: Verify all settings and data have reverted to factory defaults again
    assert device.is_factory_default(), "Local factory reset should restore factory defaults"
    # Confirm log tracks local reset
    assert "local reset completed" in device.get_status_log()

    # Step 7: Confirm all unique data has been erased or overwritten
    for key in device.FACTORY_DEFAULTS["settings"]:
        assert state_after_local_reset["settings"][key] == device.FACTORY_DEFAULTS["settings"][key]

    for key in device.FACTORY_DEFAULTS["user_data"]:
        assert state_after_local_reset["user_data"][key] == device.FACTORY_DEFAULTS["user_data"][key]

    print("Status log:", device.get_status_log())

```

---

**How to use:**
- Save as `tests/test_factory_reset.py`.
- Replace `MockIoTDeviceApplication` with your real device interface (remote/local reset APIs and state query).
- Run with `pytest tests/test_factory_reset.py`.

**Coverage:**
- Performs both remote and local resets.
- Verifies full return to factory defaults.
- Ensures altered data/settings are cleared.
- Ensures distinct logs/confirmations for each reset path.

Let me know if you want this adapted to your real device REST/gRPC/CLI or have a specific SDK!