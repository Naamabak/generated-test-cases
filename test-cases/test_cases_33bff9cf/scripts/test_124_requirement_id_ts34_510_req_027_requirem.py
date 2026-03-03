```python
# File: tests/test_oma_dm_default_apn_add_replace.py

"""
Test Case for:
Requirement ID : TS.34_5.10_REQ_027

Requirement:
- If the management node for the default APN is absent, the device SHOULD support OMA DM ADD to create the node
- Subsequent OMA DM REPLACE updates update the default APN node value and take immediate effect.
- All changes must be remotely verifiable via OMA DM, APN queries, logs, or live config checks.

References:
- GSMA TS.34 v8.0, Section 5.10, TS.34_5.10_REQ_027 (page 37)
- OMA Device Management (DM) v1.2/v1.3 ADD/REPLACE semantics
"""

import pytest

# --- MOCKS / PLACEHOLDER IMPLEMENTATION (replace with real DM client/server integration) ---

DEFAULT_APN_PATH = "./Network/APN/Default"

class MockOmaDmClient:
    """
    Simulates an OMA DM client on the IoT Communications Module, with simple APN mgmt node logic.
    """
    def __init__(self):
        self.management_tree = {}  # e.g., {"./Network/APN/Default": {"APN": "internet"}}
        self.current_apn = None
        self.log = []

    def query_node_exists(self, path):
        """Return True if node exists in the management tree."""
        return path in self.management_tree

    def oma_dm_replace(self, path, apn_value):
        """
        Simulates an OMA DM REPLACE command for the default APN node.
        - Succeeds if node present; fails if absent.
        - Updates the APN value and takes effect immediately.
        """
        if self.query_node_exists(path):
            self.management_tree[path]["APN"] = apn_value
            self.current_apn = apn_value
            self.log.append(f"REPLACE command: APN node at {path} updated to '{apn_value}'")
            return True
        self.log.append(f"REPLACE command: Failed (node {path} not found)")
        return False

    def oma_dm_add(self, path, apn_value):
        """
        Simulates an OMA DM ADD command to create the default APN node.
        - If already exists, ADD is ignored/denied.
        """
        if self.query_node_exists(path):
            self.log.append(f"ADD command: Node {path} already exists; not adding duplicate.")
            return False
        self.management_tree[path] = {"APN": apn_value}
        self.current_apn = apn_value
        self.log.append(f"ADD command: Created APN node at {path} with '{apn_value}'")
        return True

    def query_apn_value(self):
        """Return current APN in use (simulates network config check)."""
        return self.current_apn

    def reset(self):
        self.management_tree = {}
        self.current_apn = None
        self.log = []

    def power_cycle(self):
        # Simulate device/network power cycle (should retain mgmt tree and APN unless factory reset)
        self.log.append("Device power cycled (APN nodes persist)")

    def factory_reset(self):
        # Factory reset wipes all config
        self.management_tree = {}
        self.current_apn = None
        self.log.append("Factory reset: Management tree wiped")

    def get_log(self):
        return list(self.log)

# --- FIXTURE ---

@pytest.fixture
def dm_client():
    client = MockOmaDmClient()
    yield client
    client.reset()

# --- TEST SCRIPT ---

def test_add_then_replace_default_apn(dm_client):
    """TS.34_5.10_REQ_027: Covers ADD-then-REPLACE flow for default APN management node."""

    # Step 1: Query for the APN management node (should not exist)
    node_exists = dm_client.query_node_exists(DEFAULT_APN_PATH)
    assert not node_exists, "Default APN node should NOT exist at test setup"

    # Step 2: Try REPLACE on missing node (should fail)
    result = dm_client.oma_dm_replace(DEFAULT_APN_PATH, "apn1.operator.net")
    assert not result, "REPLACE should fail when node absent"
    log = dm_client.get_log()
    assert "Failed" in log[-1], "Expected failure log on REPLACE with absent node"

    # Step 3: Send ADD command to create the APN node with new APN
    add_result = dm_client.oma_dm_add(DEFAULT_APN_PATH, "apn1.operator.net")
    assert add_result, "ADD command should create APN node"

    # Step 4: Confirm node exists, APN value set
    node_exists = dm_client.query_node_exists(DEFAULT_APN_PATH)
    assert node_exists, "Default APN node was not created after ADD"
    apn_val = dm_client.management_tree[DEFAULT_APN_PATH]["APN"]
    assert apn_val == "apn1.operator.net"
    assert dm_client.query_apn_value() == "apn1.operator.net"

    # Step 5: Send REPLACE to change APN value (test update)
    replace_result = dm_client.oma_dm_replace(DEFAULT_APN_PATH, "apn2.operator.biz")
    assert replace_result, "REPLACE command should succeed on node created by ADD"
    apn_val_post = dm_client.management_tree[DEFAULT_APN_PATH]["APN"]
    assert apn_val_post == "apn2.operator.biz"
    assert dm_client.query_apn_value() == "apn2.operator.biz"

    # Step 6: Confirm no manual interaction required (simulate: nothing in log)
    assert not any("user" in entry.lower() for entry in dm_client.get_log()), \
        "Manual/user interaction should not be required for APN updates"

    # Step 7: Power cycle, nodes/APN should persist
    dm_client.power_cycle()
    node_exists_post_cycle = dm_client.query_node_exists(DEFAULT_APN_PATH)
    apn_val_post_cycle = dm_client.query_apn_value()
    assert node_exists_post_cycle, "APN node not present after power cycle"
    assert apn_val_post_cycle == "apn2.operator.biz", "APN value should persist after power cycle"

    # Step 8: Factory reset wipes APN/node
    dm_client.factory_reset()
    assert not dm_client.query_node_exists(DEFAULT_APN_PATH), \
        "Factory reset should clear APN management node"
    assert dm_client.query_apn_value() is None

    # Step 9: Re-create to confirm the cycle can be repeated
    assert dm_client.oma_dm_add(DEFAULT_APN_PATH, "apn3.final.io")

    # Step 10: Add duplicate node (should not create), REPLACE again
    assert not dm_client.oma_dm_add(DEFAULT_APN_PATH, "new_apn_should_be_ignored")
    assert dm_client.oma_dm_replace(DEFAULT_APN_PATH, "apn_updated_again")
    assert dm_client.query_apn_value() == "apn_updated_again"

    # Step 11: Output logs for traceability
    print("--- OMA DM ADD/REPLACE APN Node Log ---")
    for entry in dm_client.get_log():
        print(entry)

@pytest.mark.parametrize("cycle", range(2))
def test_default_apn_persistence_and_update(dm_client, cycle):
    """Repeat test to ensure persistence and correct update across test cycles."""
    dm_client.factory_reset()
    new_apn = f"apn.test{cycle}.net"
    dm_client.oma_dm_add(DEFAULT_APN_PATH, new_apn)
    assert dm_client.query_apn_value() == new_apn
    changed_apn = f"apn.changed{cycle}.org"
    dm_client.oma_dm_replace(DEFAULT_APN_PATH, changed_apn)
    assert dm_client.query_apn_value() == changed_apn
    dm_client.power_cycle()
    assert dm_client.query_apn_value() == changed_apn

```
---

**How to use/adapt:**
- Save as `tests/test_oma_dm_default_apn_add_replace.py`
- Replace MockOmaDmClient logic with your device OMA DM client API/testbed integration.
- Run with:
  ```bash
  pytest tests/test_oma_dm_default_apn_add_replace.py
  ```
- Script covers ADD/REPLACE management node semantics, proper updating, APN/network setting check, and persistence per TS.34_5.10_REQ_027.