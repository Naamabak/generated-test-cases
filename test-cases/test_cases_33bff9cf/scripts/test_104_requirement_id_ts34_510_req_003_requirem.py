```python
# File: tests/test_oma_dm_host_reporting_nodes.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_003

Requirement:
The IoT Communications Module SHALL support IoT Device Host Reporting in the Device Detail Management Object,
including four extension nodes:
  - DevDetail/Ext/HostMan   (Manufacturer)
  - DevDetail/Ext/HostMod   (Model)
  - DevDetail/Ext/HostSwV   (Software Version)
  - DevDetail/Ext/HostDevId (Unique ID)
Each SHALL match the corresponding value in the PTCRB or GCF certification (requirement IDR4).
All nodes must be accessible via OMA DM GET.

References:
- GSMA TS.34 v8.0, Section 5.10, Requirement TS.34_5.10_REQ_003–007
- OMA DM specification
- PTCRB/GCF certification documentation for device submission (requirement IDR4)
"""

import pytest

# --- MOCK CLASSES / PLACEHOLDERS ---
# Replace these mocks with integration to your real OMA DM client/server, and actual PTCRB/GCF records loader.

class MockCertificationDoc:
    """
    Simulates the official PTCRB or GCF certification record/document, required for cross-checking.
    In a real test, this would be loaded from the certification doc or database.
    """
    def __init__(self, manufacturer, model, sw_version, unique_id):
        self.manufacturer = manufacturer
        self.model = model
        self.sw_version = sw_version
        self.unique_id = unique_id

    def get_values(self):
        return {
            "DevDetail/Ext/HostMan": self.manufacturer,
            "DevDetail/Ext/HostMod": self.model,
            "DevDetail/Ext/HostSwV": self.sw_version,
            "DevDetail/Ext/HostDevId": self.unique_id,
        }

class MockOMADMClient:
    """
    Simulates an IoT Device Host with OMA DM client exposing custom extension nodes for host details.
    """
    def __init__(self):
        # Initialize the OMA DM management tree with default values (to be set by manufacturer)
        self.management_tree = {
            "DevDetail/Ext/HostMan": "TestCorp",
            "DevDetail/Ext/HostMod": "ModelX1",
            "DevDetail/Ext/HostSwV": "1.0.0",
            "DevDetail/Ext/HostDevId": "TEST-DEV-12345"
        }
        self.log = []
    
    def oma_dm_get(self, node_path):
        """
        Simulate OMA DM GET request for specified node.
        """
        if node_path not in self.management_tree:
            raise KeyError(f"Node {node_path} not found in OMA DM tree")
        value = self.management_tree[node_path]
        self.log.append(f"GET {node_path} -> '{value}'")
        return value

    def oma_dm_set(self, node_path, value):
        """
        Simulate OMA DM SET for node values (e.g., after device update or correction).
        Normally, these nodes should only be populated by manufacturer logic/process.
        """
        self.management_tree[node_path] = value
        self.log.append(f"SET {node_path} = '{value}'")

    def sync_with_host_updates(self, updated_values):
        """
        Simulate manufacturer process to update nodes after local device change.
        """
        for node, value in updated_values.items():
            self.oma_dm_set(node, value)

    def get_log(self):
        return self.log[:]

# --- TEST FIXTURES ---

@pytest.fixture
def cert_doc():
    # Simulate loading values from PTCRB or GCF certification record (requirement IDR4)
    # You would replace these values with the ones from your actual certificate submission.
    return MockCertificationDoc(
        manufacturer="TestCorp",
        model="ModelX1",
        sw_version="1.0.0",
        unique_id="TEST-DEV-12345"
    )

@pytest.fixture
def oma_dm_client():
    # In a live test, hook to your real OMA DM client/device with GET/SET node APIs.
    return MockOMADMClient()

# --- TEST SCRIPT ---

def test_oma_dm_host_reporting_nodes(cert_doc, oma_dm_client):
    """
    TS.34_5.10_REQ_003 (and TS.34_5.10_REQ_004 ... TS.34_5.10_REQ_007):

    - All four custom nodes exist as extension items in Management Object.
    - Each node is accessible via OMA DM GET.
    - Each node's value matches PTCRB/GCF certified submission.
    - Updating the device host value and process is reflected in nodes after trigger/sync.
    """
    # Step 1: Perform OMA DM GET queries for each node
    required_nodes = [
        "DevDetail/Ext/HostMan",
        "DevDetail/Ext/HostMod",
        "DevDetail/Ext/HostSwV",
        "DevDetail/Ext/HostDevId",
    ]
    certified_values = cert_doc.get_values()

    queried_values = {}
    for node in required_nodes:
        # Step 2: Record string value returned by each node (GET operation)
        value = oma_dm_client.oma_dm_get(node)
        queried_values[node] = value

    # Step 3: Each returned value matches the corresponding certified value
    for node in required_nodes:
        expected = certified_values[node]
        actual = queried_values[node]
        assert actual == expected, f"Node {node} value '{actual}' does not match certification '{expected}'"

    # Step 4: Try updating a host value, update the node (simulate manufacturer sync after change)
    updated_cert_doc = MockCertificationDoc(
        manufacturer="TestCorp",
        model="ModelX1",
        sw_version="2.0.0",       # <-- New version installed
        unique_id="TEST-DEV-12345"
    )
    updated_values = updated_cert_doc.get_values()
    oma_dm_client.sync_with_host_updates(updated_values)  # Simulate update after upgrade

    # Confirm node value matches the new certified value
    value_after_update = oma_dm_client.oma_dm_get("DevDetail/Ext/HostSwV")
    assert value_after_update == "2.0.0", \
        f"HostSwV node not updated after software upgrade, got '{value_after_update}'"

    # Step 5: Confirm all nodes are accessible for GET operation and up-to-date
    for node in required_nodes:
        value = oma_dm_client.oma_dm_get(node)
        expected = updated_values[node]
        assert value == expected, \
            f"Updated node value {node}='{value}' does not match new certified '{expected}'"

    # Step 6: Output for traceability/audit
    print("Queried node values pre-update:", queried_values)
    print("Queried node values post-update:", {n: oma_dm_client.oma_dm_get(n) for n in required_nodes})
    print("OMA DM operation log:", oma_dm_client.get_log())

```
---

**Instructions:**
- Save as `tests/test_oma_dm_host_reporting_nodes.py`.
- Integrate with your real device APIs, OMA DM client/server for live testing.
- Update `cert_doc` fixture according to PTCRB/GCF records and device under test.
- Run with:
  ```bash
  pytest tests/test_oma_dm_host_reporting_nodes.py
  ```
- The test directly asserts all four extension nodes, their values, OMA DM GET accessibility, and node updating/reflection.
- All logs/outputs are suitable for audit/certification traceability.