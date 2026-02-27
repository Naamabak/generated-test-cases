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
Test Case:     TC-CSA-REMOVENODE-NOTFOUND-0001
Requirement:   CSA-REMOVENODE-REQ-NOTFOUND-001

Verify RemoveNode fails with NOT_FOUND if Node Information Entry does not exist for the given NodeID.
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

# --- Test Configuration (set as per your testbed/environment) ---
# These must be provided by the test context/fixture:
# - self.jfda_admin_controller : Controller with admin rights to the JFDA cluster
# - self.jfda_endpoint         : JFDA endpoint, default 1 or as per device config
# - self.datastore_node_id     : Node ID hosting the JFDA cluster (the anchor/admin node)
# - self.nonexistent_nodeids   : List of NodeIDs that are not present in Node Information Entries, e.g. [0xDEAD, 0xBEEF]

JFDA_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
JFDA_ENDPOINT = 1  # Adjust if your JFDA is on a different endpoint
REMOVE_NODE_CMD = getattr(JFDA_CLUSTER.Commands, "RemoveNode", None) if JFDA_CLUSTER else None
NODE_ENTRY_ATTR = getattr(JFDA_CLUSTER.Attributes, "NodeEntries", None) if JFDA_CLUSTER else None

class TC_CSA_REMOVENODE_NOTFOUND_0001(MatterBaseTest):
    """
    Test RemoveNode returns NOT_FOUND if Node Information Entry for NodeID is missing.
    """

    async def get_node_entry(self, dev_ctrl, db_node_id, endpoint, node_id):
        # Query JFDA for NodeEntries, returns True if node_id is present
        asserts.assert_is_not_none(NODE_ENTRY_ATTR, "NodeEntries attribute must exist in JFDA cluster")
        node_entries_resp = await dev_ctrl.ReadAttribute(
            nodeId=db_node_id,
            attributes=[(endpoint, JFDA_CLUSTER, NODE_ENTRY_ATTR)],
        )
        entries = node_entries_resp[endpoint][JFDA_CLUSTER][NODE_ENTRY_ATTR]
        for entry in entries:
            n_id = getattr(entry, "nodeId", entry.get("nodeId", None))
            if n_id == node_id:
                return True
        return False

    @async_test_body
    async def test_remove_node_fails_with_not_found(self):
        # Fixture/Testbed parameters
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        datastore_node_id = getattr(self, "datastore_node_id", self.dut_node_id)
        jfda_ep = getattr(self, "jfda_endpoint", JFDA_ENDPOINT)
        # Should be a list of two (or more) NodeIDs that are known to have no entry
        missing_nodeids = getattr(self, "nonexistent_nodeids", [0xDEAD0001, 0xBEEF0002])

        # Precondition: Assert RemoveNode command/attributes are present
        asserts.assert_is_not_none(REMOVE_NODE_CMD, "RemoveNode command not present in JFDA cluster definitions.")

        for node_id in missing_nodeids:
            # Step 1: Query and confirm Node Information Entry for target NodeID does not exist
            self.print_step(1, f"Check that Node Information Entry for NodeID {hex(node_id)} does NOT exist")
            is_present = await self.get_node_entry(admin_ctrl, datastore_node_id, jfda_ep, node_id)
            asserts.assert_false(is_present,
                f"NodeID {hex(node_id)} unexpectedly present in Node Information Entries for negative RemoveNode test.")

            # Step 2: Issue RemoveNode command for missing NodeID
            self.print_step(2, f"Issue RemoveNode command for missing NodeID {hex(node_id)}, expect NOT_FOUND")
            not_found_err = False
            try:
                await admin_ctrl.SendCommand(
                    nodeId=datastore_node_id,
                    endpoint=jfda_ep,
                    command=REMOVE_NODE_CMD(nodeId=node_id)
                )
            except InteractionModelError as e:
                # Step 3: Capture status code, expect NOT_FOUND
                self.print_step(3, f"RemoveNode for {hex(node_id)} returned status: {e.status}")
                not_found_err = (e.status == Status.NotFound or str(e.status).upper() == "NOT_FOUND")
                asserts.assert_true(
                    not_found_err,
                    f"RemoveNode for {hex(node_id)} returned {e.status} instead of NOT_FOUND"
                )
            except Exception as e:
                asserts.fail(f"RemoveNode for {hex(node_id)} failed with unexpected error: {e}")
            else:
                # Should NOT succeed for missing node
                asserts.fail(f"RemoveNode succeeded unexpectedly for non-existent NodeID {hex(node_id)}; should fail with NOT_FOUND.")

            # Step 4: Confirm Datastore has not changed (no new entry present)
            self.print_step(4, f"Datastore remains unchanged for NodeID {hex(node_id)}")
            still_absent = not await self.get_node_entry(admin_ctrl, datastore_node_id, jfda_ep, node_id)
            asserts.assert_true(still_absent, f"After RemoveNode, NodeID {hex(node_id)} became present in datastore unexpectedly.")

            # (Manual/infra) Step 5: Suggest to check logs/audit - not automatable in this test
            self.print_step(5, f"System/audit logs should show RemoveNode attempt for NodeID {hex(node_id)} with NOT_FOUND result.")

        self.print_step(6, "All RemoveNode attempts for missing NodeIDs fail with NOT_FOUND; Node Information Entries remain unchanged.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions**:
- Save this file as `tests/test_TC_CSA_REMOVENODE_NOTFOUND_0001.py`.
- You may override `self.nonexistent_nodeids` in your test harness/runner to ensure the NodeIDs specified are not present in the Node Information Entries of your JFDA cluster (fabric anchor).
- Adjust cluster and attribute/command references if your integration uses custom names or locations for NodeEntries or RemoveNode.
- This test follows the style, structure, and assertions used in your existing Matter Python tests, and includes step comments for traceability.
- After completion, verify test and system logs for proper status reporting and absence of side effects.