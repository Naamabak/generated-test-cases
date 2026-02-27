```python
#
#    Copyright (c) 2025 Project CHIP Authors
#    All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

"""
Test Case:     TC-CSA-ADDACL-NOTFOUND-0001
Requirement:   CSA-ADDACL-REQ-NOTFOUND-001

Verify that AddACLToNode fails with NOT_FOUND if a Node Information Entry does not exist for the NodeID.
"""

import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

import logging
log = logging.getLogger(__name__)

# ---- Testbed/cluster/command constants (update to match your environment!) ----
JFDA_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
JFDA_ENDPOINT = 1  # Typically endpoint 1, change as needed
ADDACL_CMD = getattr(JFDA_CLUSTER.Commands, "AddACLToNode", None) if JFDA_CLUSTER else None
NODE_ENTRY_ATTR = getattr(JFDA_CLUSTER.Attributes, "NodeEntries", None) if JFDA_CLUSTER else None

class TC_CSA_ADDACL_NOTFOUND_0001(MatterBaseTest):
    """
    Test AddACLToNode returns NOT_FOUND if a Node Information Entry does not exist for NodeID.
    """

    async def get_node_entries(self, dev_ctrl, ds_node_id):
        """
        Query all NodeEntries from the Joint Fabric Datastore
        :return: list of node entry structs or dicts
        """
        asserts.assert_is_not_none(NODE_ENTRY_ATTR, "NodeEntries attribute missing in JointFabricDatastore cluster")
        resp = await dev_ctrl.ReadAttribute(
            nodeId=ds_node_id,
            attributes=[(JFDA_ENDPOINT, JFDA_CLUSTER, NODE_ENTRY_ATTR)]
        )
        return resp[JFDA_ENDPOINT][JFDA_CLUSTER][NODE_ENTRY_ATTR]

    def _get_nodeid(self, entry):
        if hasattr(entry, "nodeId"):
            return entry.nodeId
        if isinstance(entry, dict):
            return entry.get("nodeId")
        return None

    @async_test_body
    async def test_addacltonode_notfound_if_entry_missing(self):
        # --- Setup/Fixture: testbed must provide these or override as needed
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        ds_node_id = getattr(self, "datastore_node_id", self.dut_node_id)
        # List of NodeIDs NOT present in the datastore (should NOT exist as NodeEntries)
        missing_node_ids = getattr(self, "missing_node_ids", [0xFACED001, 0xDEADD002]) # Example dummy values, override as needed

        asserts.assert_is_not_none(admin_ctrl, "Test requires admin controller")
        asserts.assert_is_not_none(JFDA_CLUSTER, "JointFabricDatastore cluster missing")
        asserts.assert_is_not_none(ADDACL_CMD, "AddACLToNode command not found on JFDA cluster")
        asserts.assert_is_not_none(NODE_ENTRY_ATTR, "NodeEntries attribute missing in JFDA cluster")

        for idx, node_id in enumerate(missing_node_ids):
            # Step 1: Query the Joint Fabric Datastore, confirm Node Information Entry is absent
            self.print_step(idx * 4 + 1, f"Confirm Node Information Entry for NodeID {hex(node_id)} is not present in datastore")
            node_entries = await self.get_node_entries(admin_ctrl, ds_node_id)
            present = any(self._get_nodeid(entry) == node_id for entry in node_entries)
            asserts.assert_false(
                present,
                f"NodeID {hex(node_id)} unexpectedly present in NodeEntries for NOT_FOUND AddACLToNode test"
            )

            # Step 2: Attempt to execute AddACLToNode (should fail with NOT_FOUND)
            self.print_step(idx * 4 + 2, f"Issue AddACLToNode for non-existent NodeID {hex(node_id)} (expect NOT_FOUND)")
            try:
                # Provide correct command arguments as per your cluster model (minimum: NodeID and ACL config)
                # For negative test, the ACL value itself can be dummy - no side effects are expected
                dummy_acl = []  # Empty or example ACL list (structure does not matter for negative NOT_FOUND case)
                await admin_ctrl.SendCommand(
                    nodeId=ds_node_id,
                    endpoint=JFDA_ENDPOINT,
                    command=ADDACL_CMD(nodeId=node_id, aclConfig=dummy_acl)
                )
            except InteractionModelError as e:
                self.print_step(idx * 4 + 3, f"AddACLToNode returned status: {e.status}")
                not_found = (e.status == Status.NotFound or str(e.status).upper() == "NOT_FOUND")
                asserts.assert_true(
                    not_found,
                    f"Expected NOT_FOUND error for AddACLToNode (NodeID={hex(node_id)}), got {e.status}"
                )
            except Exception as ex:
                asserts.fail(f"Unexpected exception for AddACLToNode (NodeID={hex(node_id)}): {ex}")
            else:
                asserts.fail(f"AddACLToNode succeeded for missing NodeID {hex(node_id)}; should fail with NOT_FOUND.")

            # Step 3: Confirm NodeEntries are unchanged for the node
            self.print_step(idx * 4 + 4, f"Re-check NodeEntries after failed AddACLToNode to ensure NodeID {hex(node_id)} is still absent")
            node_entries_after = await self.get_node_entries(admin_ctrl, ds_node_id)
            still_absent = all(self._get_nodeid(entry) != node_id for entry in node_entries_after)
            asserts.assert_true(
                still_absent,
                f"Node Information Entry for NodeID {hex(node_id)} was created after failed AddACLToNode attempt!"
            )
            # (Optionally: audit log check, manual or via infra)

        self.print_step(len(missing_node_ids)*4+1, "Test complete: All AddACLToNode attempts for missing NodeIDs failed with NOT_FOUND and no changes to NodeEntries.")

if __name__ == "__main__":
    default_matter_test_main()
```
---
**Instructions for Use:**
- Save as `tests/test_TC_CSA_ADDACL_NOTFOUND_0001.py`.
- Set/override `missing_node_ids` in your testbed to specify NodeIDs known NOT to exist as NodeEntries in your fabric's Joint Fabric Datastore.
- If your AddACLToNode command signature requires different fields, adapt the arguments.
- All logic for absent NodeIDs, NOT_FOUND status assertions, state checks, and stepped tracing is present, following connectedhomeip’s test idioms.