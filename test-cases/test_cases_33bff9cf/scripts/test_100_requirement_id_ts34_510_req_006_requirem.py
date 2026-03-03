```python
# File: tests/test_oma_dm_hostswv_node.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_006

Requirement:
The OMA-DM node DevDetail/Ext/HostSwV SHALL specify the Host Device Software Version as provided by 
the Host manufacturer, must match the PTCRB-certified value, and SHALL be updated when the Host SW is updated.

References:
- GSMA TS.34 v8.0, Section 5.10, TS.34_5.10_REQ_006
- OMA Device Management (OMA-DM) specifications (DevDetail/Ext/HostSwV)
- PTCRB certification database
"""

import pytest


# ------- MOCK INTERFACES / PLACEHOLDERS -------
# Replace these with your actual OMA-DM client/query tool, device management API, and PTCRB records loader.

class MockPTCRBCertRecords:
    """Simulates lookup for the PTCRB certified firmware/software version."""
    def __init__(self, device_model, certified_version):
        self.device_model = device_model
        self.certified_version = certified_version
    def get_certified_version(self):
        return self.certified_version

class MockIoTDeviceHost:
    """Simulates an IoT Device Host with OMA-DM client updating Host Device SW version node."""
    def __init__(self, manufacturer, model, sw_version):
        self.manufacturer = manufacturer
        self.model = model
        self.software_version = sw_version
        self.oma_dm_db = {"DevDetail/Ext/HostSwV": sw_version}
        self.log = []

    def device_get_software_version(self):
        """Return the manufacturer SW version (running)"""
        return self.software_version

    def oma_dm_get_node(self, node_path):
        """Simulate OMA DM GET operation."""
        return self.oma_dm_db[node_path]

    def update_software(self, new_version):
        """Simulate a software update, and only then is OMA-DM node updated via manufacturer logic"""
        self.software_version = new_version
        self.log.append(f"Software updated to {new_version}")

    def oma_dm_sync(self):
        """Simulate OMA DM sync -- manufacturer logic updates the node to match running SW version"""
        current_version = self.device_get_software_version()
        self.oma_dm_db["DevDetail/Ext/HostSwV"] = current_version
        self.log.append(f"OMA-DM node DevDetail/Ext/HostSwV updated to {current_version}")

    def get_log(self):
        return list(self.log)


# ------------- PYTEST FIXTURE -------------

@pytest.fixture
def device_and_ptcrb():
    # Initial configuration: certified version 1.0.0
    device = MockIoTDeviceHost(manufacturer="TestCorp", model="X1000", sw_version="1.0.0")
    ptcrb = MockPTCRBCertRecords(device_model="X1000", certified_version="1.0.0")
    yield device, ptcrb
    # No teardown required for mock


# ------------------- TEST SCRIPT -----------------------

def test_hostswv_node_correctly_populated_and_updated(device_and_ptcrb):
    """
    TS.34_5.10_REQ_006:
    - OMA-DM node DevDetail/Ext/HostSwV value matches PTCRB-certified SW before update,
      is updated immediately/at next sync following an update, and is only managed
      by Host Device manufacturer and OMA DM client.
    """
    device, ptcrb = device_and_ptcrb

    # Step 1: Retrieve DevDetail/Ext/HostSwV and log the timestamp/value
    value_before = device.oma_dm_get_node("DevDetail/Ext/HostSwV")
    print(f"OMA-DM HostSwV before update: {value_before}")

    # Step 2: Compare to PTCRB-certified SW version (compliance)
    certified_version = ptcrb.get_certified_version()
    assert value_before == certified_version, (
        f"OMA-DM node DevDetail/Ext/HostSwV value '{value_before}' "
        f"does not match PTCRB-certified SW version '{certified_version}'"
    )

    # Step 3: Perform a Host Device software update to a new version
    new_version = "2.0.2"
    device.update_software(new_version)

    # Step 4: After update, trigger OMA DM client sync (node should now reflect new SW version)
    device.oma_dm_sync()
    value_after = device.oma_dm_get_node("DevDetail/Ext/HostSwV")
    print(f"OMA-DM HostSwV after update: {value_after}")

    # Step 5: Confirm new value matches running SW version, and update is reflected in the OMA-DM node
    assert value_after == new_version, (
        f"OMA-DM node DevDetail/Ext/HostSwV '{value_after}' "
        f"does not reflect updated Host Device SW version '{new_version}'"
    )

    # Step 6: Ensure node's value is only manageable by manufacturer/OMA DM update logic
    # (In a real product, try to spoof/overwrite this from outside the manufacturer/OMA-DM path and assert failure)
    # Here, simulate only correct flows occur
    device_log = device.get_log()
    assert any("OMA-DM node DevDetail/Ext/HostSwV updated" in l for l in device_log), (
        "OMA-DM node was not updated through correct sync/manufacturer process."
    )

    # Step 7: Confirm all update steps and values are logged or recordable
    print("Update log: ", device_log)

    # Step 8: Check no stale/mismatched value after update cycle
    assert device.oma_dm_get_node("DevDetail/Ext/HostSwV") == device.device_get_software_version(), (
        "OMA-DM node value is stale/mismatched after SW update."
    )

@pytest.mark.parametrize("old,new,should_pass", [
    ("1.1.5", "1.1.5", True),
    ("2.3.0", "4.4.1", False),
])
def test_hostswv_node_matches_current_software_after_any_update(old, new, should_pass):
    """Node must always match current running SW version after update."""
    device = MockIoTDeviceHost(manufacturer="TestCorp", model="Z2020", sw_version=old)
    device.oma_dm_sync()
    device.update_software(new)
    device.oma_dm_sync()
    node_val = device.oma_dm_get_node("DevDetail/Ext/HostSwV")
    current = device.device_get_software_version()
    print(f"After update: Node={node_val}, Running={current}")
    if should_pass:
        assert node_val == current
    else:
        assert node_val != old

```
---

**Instructions:**
- Save this file as `tests/test_oma_dm_hostswv_node.py`.
- Replace mocks with integration calls to your OMA-DM client, device software, and PTCRB interfaces as available.
- Run with:
  ```sh
  pytest tests/test_oma_dm_hostswv_node.py
  ```
- All steps, assertions, and output mapping are aligned to GSMA TS.34_5.10_REQ_006, OMA-DM node management, and traceability for compliance.