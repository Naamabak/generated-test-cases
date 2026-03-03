```python
# File: tests/test_oma_dm_default_apn_and_modifiedtimestamp.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_025

Requirement:
The IoT Communications Module SHALL include the module default APN in the response to the OMA DM GET (device details).
The response SHALL include an Extra node for each setting containing the ModifiedTimeStamp in UTC (if changed); if not present, the setting is factory default.

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_025
- OMA Device Management specification (GET command, Extra node definitions)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf (page 36)
"""

import pytest
from datetime import datetime, timezone
import re

# --- MOCK CLASSES / PLACEHOLDER IMPLEMENTATION ---
# Replace with actual OMA DM client/server, device interface, and parser as needed

def is_valid_utc_string(val):
    # Basic ISO 8601 (UTC) timestamp check (YYYY-MM-DDTHH:MM:SSZ or with milliseconds)
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
    return bool(re.fullmatch(pattern, val))

class MockDMExtraNode:
    """Represents an 'Extra' node containing optional ModifiedTimeStamp field."""
    def __init__(self, modified=None):
        self.extra = {}
        if modified is not None:
            # Value must be a UTC-formatted string (e.g., ISO 8601 Zulu time)
            self.extra["ModifiedTimeStamp"] = modified

    def get(self, key):
        return self.extra.get(key, None)

    def keys(self):
        return self.extra.keys()

    def as_dict(self):
        return dict(self.extra)

class MockAPNSetting:
    """Represents the APN setting and its extra node."""
    def __init__(self, default_apn="factory.apn", modified=False, mod_time=None):
        self.value = default_apn
        if modified and mod_time:
            self.extra = MockDMExtraNode(modified=mod_time)
        else:
            self.extra = MockDMExtraNode()

    def update_apn(self, new_apn, mod_time):
        self.value = new_apn
        self.extra = MockDMExtraNode(modified=mod_time)

    def reset_to_factory(self, apn):
        self.value = apn
        self.extra = MockDMExtraNode()

    def get_value(self):
        return self.value

    def get_extra(self):
        return self.extra

class MockIoTCommModuleOMADMClient:
    """
    Simulates an OMA DM client on the module, handling GET command for device details,
    including APN setting and Extra nodes.
    """
    def __init__(self):
        self.default_apn = "factory.apn"
        # Assume module starts in factory state
        self.apn_setting = MockAPNSetting(default_apn=self.default_apn)
        self.logs = []

    def oma_dm_get_device_details(self):
        # Simulate OMA DM GET for device details—returning APN and its Extra node
        device_details = {
            "apn": self.apn_setting.get_value(),
            "Extra": self.apn_setting.get_extra().as_dict()
        }
        self.logs.append(f"GET DeviceDetails: {device_details}")
        return device_details

    def modify_apn(self, new_apn):
        now_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.apn_setting.update_apn(new_apn, mod_time=now_utc)
        self.logs.append(f"APN modified: {new_apn}, ModifiedTimeStamp: {now_utc}")

    def reset_apn_to_factory(self):
        self.apn_setting.reset_to_factory(self.default_apn)
        self.logs.append("APN reset to factory default.")

    def get_logs(self):
        return list(self.logs)

# --- PYTEST FIXTURE ---
@pytest.fixture
def comm_module():
    return MockIoTCommModuleOMADMClient()

# --- TEST SCRIPT ---
def test_default_apn_and_modifiedtimestamp_behavior(comm_module):
    """
    TS.34_5.10_REQ_025: Verifies default APN, Extra node, and ModifiedTimeStamp field behavior per requirements.
    """
    # Step 1: GET device details in factory state
    response = comm_module.oma_dm_get_device_details()
    assert "apn" in response, "APN missing from device details"
    assert response["apn"] == "factory.apn", "Default APN is missing/incorrect"
    assert "Extra" in response and isinstance(response["Extra"], dict), "Extra node missing or not a dictionary"

    # Step 2: Check ModifiedTimeStamp is absent (factory default, never changed)
    extra = response["Extra"]
    assert "ModifiedTimeStamp" not in extra, (
        "ModifiedTimeStamp present for factory APN, but should be absent"
    )

    # Step 3: Modify the APN and check for ModifiedTimeStamp in Extra node
    comm_module.modify_apn("custom.apn")
    response2 = comm_module.oma_dm_get_device_details()
    assert response2["apn"] == "custom.apn", "Modified APN value not present in response"
    extra2 = response2["Extra"]
    assert "ModifiedTimeStamp" in extra2, "ModifiedTimeStamp missing after APN was changed"
    ts = extra2["ModifiedTimeStamp"]
    assert is_valid_utc_string(ts), f"ModifiedTimeStamp is not valid UTC: {ts}"

    # Step 4: Reset APN to factory and confirm ModifiedTimeStamp absent again
    comm_module.reset_apn_to_factory()
    response3 = comm_module.oma_dm_get_device_details()
    assert response3["apn"] == "factory.apn"
    extra3 = response3["Extra"]
    assert "ModifiedTimeStamp" not in extra3, "ModifiedTimeStamp present after APN restored to factory"

    # Step 5: (Repeat) Modify APN again, then GET to confirm timestamp is updated
    comm_module.modify_apn("another.apn")
    response4 = comm_module.oma_dm_get_device_details()
    ts2 = response4["Extra"]["ModifiedTimeStamp"]
    assert is_valid_utc_string(ts2)
    # (Optional: Ensure new timestamp is different, i.e., a real update.)
    assert ts2 != ts, f"Timestamp did not update after APN was changed again: {ts2}"

    # Step 6: Output response/logs for evidence
    print("Response (Factory):", response)
    print("Response (Modified):", response2)
    print("Response (Reset to factory):", response3)
    print("Response (Modified again):", response4)
    print("Log:", comm_module.get_logs())

    # All asserts above directly correspond to the requirement's pass criteria.

```
**How to use/adapt:**
- Save as `tests/test_oma_dm_default_apn_and_modifiedtimestamp.py`
- Replace mocks with real OMA DM client/server/device interfaces (and actual DM responses/parsing)
- Run:
  ```bash
  pytest tests/test_oma_dm_default_apn_and_modifiedtimestamp.py
  ```
- The test covers initial (factory), modified, and re-factory (reset) APN conditions, and verifies Extra/ModifiedTimeStamp logic, UTC format, and DM response structure per GSMA TS.34_5.10_REQ_025.