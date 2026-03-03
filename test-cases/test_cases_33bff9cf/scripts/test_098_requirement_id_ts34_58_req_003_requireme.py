```python
# File: tests/test_comm_module_factory_reset.py

"""
Test Case for:
Requirement ID : TS.34_5.8_REQ_003

Requirement:
The IoT Communications Module SHOULD support a “reset to factory settings” via remote and local connection.

References:
- GSMA TS.34 v8.0, Section 5.8, Requirement TS.34_5.8_REQ_003
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- Related: TS.34_4.0_REQ_024, TS.34_4.2_REQ_024
"""

import pytest

# --- MOCK/PLACEHOLDER CLASS (replace with your real module/device/SDK integration) ---
class MockIoTCommModule:
    """
    Simulates an IoT Communications Module with configurable state and reset-to-factory operations.
    """
    FACTORY_DEFAULTS = {
        "settings": {
            "apn": "default.apn",
            "report_interval": 60,
            "mode": "production",
        },
        "user_data": {
            "custom_profile": None,
            "device_name": "GSMA IoT Module",
            "logs": [],
        }
    }

    def __init__(self):
        self.reset_to_factory()

    def alter_settings_and_data(self):
        self.settings['apn'] = "custom.iot"
        self.settings['report_interval'] = 120
        self.settings['mode'] = "debug"
        self.user_data['custom_profile'] = {"sim": "test", "level": 99}
        self.user_data['device_name'] = "QA-Device"
        self.user_data['logs'] = ["log1", "log2"]

    def reset_to_factory(self):
        self.settings = self.FACTORY_DEFAULTS['settings'].copy()
        self.user_data = self.FACTORY_DEFAULTS['user_data'].copy()
        self.status_log = ["reset to factory settings"]

    def remote_factory_reset(self):
        # Simulate remote/OTA reset (e.g., via management platform/command)
        self.reset_to_factory()
        self.status_log.append("remote reset completed")

    def local_factory_reset(self):
        # Simulate local reset (e.g., physical button, serial, or UI)
        self.reset_to_factory()
        self.status_log.append("local reset completed")

    def get_state(self):
        return {
            "settings": self.settings.copy(),
            "user_data": self.user_data.copy()
        }

    def is_factory_default_state(self):
        return self.settings == self.FACTORY_DEFAULTS["settings"] and self.user_data == self.FACTORY_DEFAULTS["user_data"]

    def get_status_log(self):
        return list(self.status_log)

# --- FIXTURE ---
@pytest.fixture
def comm_module():
    """Yield a fresh module in factory state for each test."""
    mod = MockIoTCommModule()
    return mod

# --- TEST SCRIPT ---
def test_factory_reset_remote_and_local(comm_module):
    """
    TS.34_5.8_REQ_003: Test both remote and local factory reset operations.
    """

    # Step 1: Alter configuration/data from factory defaults
    comm_module.alter_settings_and_data()
    state = comm_module.get_state()
    assert state["settings"]["apn"] == "custom.iot"
    assert state["user_data"]["custom_profile"]["level"] == 99
    assert not comm_module.is_factory_default_state()

    # Step 2: Perform remote factory reset
    comm_module.remote_factory_reset()
    state_after_remote = comm_module.get_state()
    assert comm_module.is_factory_default_state(), "Remote reset failed to restore factory default"
    assert "remote reset completed" in comm_module.get_status_log()

    # Step 3: Alter settings/data again
    comm_module.alter_settings_and_data()
    state2 = comm_module.get_state()
    assert state2["settings"]["mode"] == "debug"
    assert not comm_module.is_factory_default_state()

    # Step 4: Perform local factory reset
    comm_module.local_factory_reset()
    state_after_local = comm_module.get_state()
    assert comm_module.is_factory_default_state(), "Local reset failed to restore factory default"
    assert "local reset completed" in comm_module.get_status_log()

    # Step 5: Confirm all unique data is erased/overwritten
    for key in comm_module.FACTORY_DEFAULTS["settings"]:
        assert state_after_local["settings"][key] == comm_module.FACTORY_DEFAULTS["settings"][key]
    for key in comm_module.FACTORY_DEFAULTS["user_data"]:
        assert state_after_local["user_data"][key] == comm_module.FACTORY_DEFAULTS["user_data"][key]

    # Step 6: Check logs/status
    logs = comm_module.get_status_log()
    assert "reset to factory settings" in logs
    assert "remote reset completed" in logs
    assert "local reset completed" in logs

    # Output for human audit/debug
    print("Status log:", logs)
    print("Final state after local reset:", state_after_local)

```

---

**How to use/adapt:**
- Place as `tests/test_comm_module_factory_reset.py`.
- Replace the mock class with your real device/module API (integration with OTA or local interfaces).
- Run with:
  ```bash
  pytest tests/test_comm_module_factory_reset.py
  ```
- This script asserts all pass/fail criteria, result logging, and full factory reset coverage for both remote and local triggers, as required by GSMA TS.34_5.8_REQ_003.