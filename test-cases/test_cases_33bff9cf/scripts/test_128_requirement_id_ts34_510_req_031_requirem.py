```python
# File: tests/test_fumo_alert_uri_points_to_dynamic_fw_object.py

"""
Test Case for:
Requirement ID: TS.34_5.10_REQ_031

Requirement:
For IoT Communications Module initiated updates, the URI in the alert message sent by the module
must point to the dynamic node representing a single firmware update management object (per OMA-TS-DM_FUMO-V1_0 Section 7.1.3).

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_031
- OMA-TS-DM_FUMO-V1_0, Section 7.1.3 & 6.2.1 (Firmware Update Management Object URI requirements)
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest
import re

# --- MOCKS / PLACEHOLDERS (Replace with real FUMO client, server, and tree integration for live/integration tests) ---

class MockFirmwareUpdateMgmtTree:
    """
    Simulates device management tree, containing dynamic nodes for FUMO firmware objects.
    """
    def __init__(self):
        # Example branch structure: <base>/Mgmt/FUMO/3/ - "3" is a dynamic instance/object
        self.fumo_base = "./Mgmt/FUMO"
        self.dynamic_objects = {
            "1": {"state": "none", "version": "v1.0"},
            "3": {"state": "downloaded", "version": "v2.0"},
            "5": {"state": "installing", "version": "v2.1-rc"}
        }

    def get_dynamic_node_uris(self):
        """
        Return the URIs of all the dynamic FUMO firmware update objects in the tree.
        """
        return [f"{self.fumo_base}/{key}/" for key in self.dynamic_objects]

    def node_exists(self, uri):
        """
        Checks if the provided URI points to a valid dynamic firmware object node.
        """
        match = re.match(rf"^{re.escape(self.fumo_base)}/(\d+)/$", uri)
        return match and match.group(1) in self.dynamic_objects

class MockDMServer:
    """
    Simulates the Device Management server (FUMO-capable), receives alert messages and logs their URIs.
    """
    def __init__(self, mgmt_tree):
        self.alerts = []
        self.mgmt_tree = mgmt_tree

    def receive_alert(self, alert_msg):
        # Record alert and check if the URI matches a dynamic firmware object in the device tree
        uri = alert_msg["URI"]
        alert_msg["uri_valid"] = self.mgmt_tree.node_exists(uri)
        self.alerts.append(alert_msg)
        return alert_msg

    def get_last_alert(self):
        if not self.alerts:
            return None
        return self.alerts[-1]

    def clear(self):
        self.alerts = []

class MockIoTCommModuleFUMO:
    """
    Simulates IoT Communications Module OMA DM/FUMO client, able to initiate updates (sends Alerts).
    """
    def __init__(self, mgmt_tree):
        self.mgmt_tree = mgmt_tree
        self.alert_log = []

    def trigger_firmware_update(self, obj_id, dm_server):
        """
        Initiates a self-initiated firmware update, sending a Generic Alert per OMA FUMO v1.0 (Section 7.1.3).
        URI must point to a valid dynamic node.
        """
        # Pick one node to simulate an update, e.g., ./Mgmt/FUMO/3/
        uri = f"{self.mgmt_tree.fumo_base}/{obj_id}/"
        alert_msg = {
            "MsgType": "Alert",
            "AlertCode": "1226",  # GenericAlert OMA code
            "Type": "org.openmobilealliance.dm.firmwareupdate.devicerequest",
            "URI": uri,
            "AdditionalData": {"FirmwareVersion": self.mgmt_tree.dynamic_objects[obj_id]["version"]}
        }
        self.alert_log.append(alert_msg)
        dm_server.receive_alert(alert_msg)
        return alert_msg

    def get_alert_log(self):
        return list(self.alert_log)

    def clear_log(self):
        self.alert_log = []

# --- PYTEST FIXTURES ---
@pytest.fixture
def mgmt_tree():
    return MockFirmwareUpdateMgmtTree()

@pytest.fixture
def dm_server(mgmt_tree):
    return MockDMServer(mgmt_tree)

@pytest.fixture
def module(mgmt_tree):
    return MockIoTCommModuleFUMO(mgmt_tree)

# --- TEST SCRIPT ---

@pytest.mark.parametrize("fw_obj_id", ["1", "3", "5"])
def test_fumo_alert_uri_points_to_dynamic_fw_object(module, dm_server, mgmt_tree, fw_obj_id):
    """
    TS.34_5.10_REQ_031
    - On module-initiated update, alert URI must point to the dynamic node for the single relevant firmware update object.
    - URI must match a subtree like ./Mgmt/FUMO/<Instance>/
    """
    # Step 1: Trigger module-initiated firmware update for object instance (simulate FUMO client scenario)
    alert_msg = module.trigger_firmware_update(fw_obj_id, dm_server)

    # Step 2: DM server receives alert, parse URI, check it matches dynamic node
    received_alert = dm_server.get_last_alert()
    assert received_alert is not None, "No alert received by DM server"

    # Step 3: Extract and inspect URI field
    alert_uri = received_alert["URI"]
    assert isinstance(alert_uri, str) and alert_uri != "", "Alert URI missing or not a string"
    # URI must match ./Mgmt/FUMO/<number>/ per OMA FUMO 7.1.3
    match = re.match(r"^\.?/Mgmt/FUMO/\d+/?$", alert_uri)
    assert match, f"Alert URI '{alert_uri}' does not point to a dynamic FUMO object node"

    # Step 4: Use management tree to verify node exists and is correct
    assert mgmt_tree.node_exists(alert_uri), f"URI '{alert_uri}' does not correspond to a valid firmware node in tree"

    # Step 5: Ensure alert structure contains correct request-type
    assert received_alert.get("Type") == "org.openmobilealliance.dm.firmwareupdate.devicerequest", \
        f"Alert Type field is incorrect: {received_alert.get('Type')}"
    # Additional evidence (FW version, etc.) is optional but should be correct if present
    if "AdditionalData" in received_alert:
        assert "FirmwareVersion" in received_alert["AdditionalData"]

    # Step 6: Repeat for multiple update scenarios, all must pass
    print(f"Module-initiated update alert: {received_alert}")

def test_fumo_alert_uri_points_to_correct_fumo_instances(module, dm_server, mgmt_tree):
    """
    Run a sequence for all FUMO objects, repeat for coverage.
    """
    for obj_id in mgmt_tree.dynamic_objects.keys():
        module.trigger_firmware_update(obj_id, dm_server)
        alert = dm_server.get_last_alert()
        assert alert is not None and mgmt_tree.node_exists(alert["URI"])
    print("All module-initiated update alerts point to correct firmware update objects.")

def test_fumo_alert_uri_missing_or_root_fails(module, dm_server):
    """
    If the alert points to a non-dynamic or root node, test should fail.
    """
    # Simulate an incorrect update request: Using the base FUMO root (not a dynamic instance)
    alert_msg = {
        "MsgType": "Alert",
        "URI": "./Mgmt/FUMO",
        "Type": "org.openmobilealliance.dm.firmwareupdate.devicerequest"
    }
    dm_server.receive_alert(alert_msg)
    # This should not pass requirement (root is not a single dynamic firmware object)
    received_alert = dm_server.get_last_alert()
    uri = received_alert["URI"]
    match = re.match(r"^\.?/Mgmt/FUMO/\d+/?$", uri)
    assert not match, (
        f"Alert URI '{uri}' incorrectly accepted; should not be root/static, must point to a unique dynamic instance"
    )
    print("Alert with root node URI correctly fails requirement TS.34_5.10_REQ_031.")

```
---

**Instructions:**

- Save as `tests/test_fumo_alert_uri_points_to_dynamic_fw_object.py`.
- Replace mocks with your device's FUMO client, management tree, and server for lab or integration.
- All checks directly honor OMA FUMO and TS.34_5.10_REQ_031, including URI pattern, node existence, and alert semantics.
- Run with:
  ```bash
  pytest tests/test_fumo_alert_uri_points_to_dynamic_fw_object.py
  ```
- Audit print/log lines are included for traceability and evidence.