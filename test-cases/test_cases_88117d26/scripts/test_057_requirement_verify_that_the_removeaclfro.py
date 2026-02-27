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
Test Case:    TC-CSA-REMOVEACL-NOTFOUND-0001
Requirement:  CSA-REMOVEACLFROMNODE-REQ-NOTFOUND-001

Verify RemoveACLFromNode fails with NOT_FOUND
if there is no Node Information Entry for the NodeID.
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

# --- Testbed/cluster constants; check/update as needed for your environment ---
JFDA_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
JFDA_ENDPOINT = 1  # Set as correct for your environment/cluster mapping
REMOVEACL_CMD = getattr(JFDA_CLUSTER.Commands, "RemoveACLFromNode", None) if JFDA_CLUSTER else None
NODE_ENTRIES_ATTR = getattr(JFDA_CLUSTER.Attributes, "NodeEntries", None) if JFDA_CLUSTER else None

class TC_CSA_REMOVEACL_NOTFOUND_0001(MatterBaseTest):
    """
    Test: RemoveACLFromNode returns NOT_FOUND if Node Information Entry does not exist.
    """

    async def node_entry_exists(self, dev_ctrl, ds_node_id, node_id):
        """Check if Node Information Entry exists for node_id."""
        asserts.assert_is_not_none(NODE_ENTRIES_ATTR, "NodeEntries attribute not found in JFDA cluster")
        resp = await dev_ctrl.ReadAttribute(
            nodeId=ds_node_id,
            attributes=[(JFDA_ENDPOINT, JFDA_CLUSTER, NODE_ENTRIES_ATTR)],
        )
        entries = resp[JFDA_ENDPOINT][JFDA_CLUSTER][NODE_ENTRIES_ATTR]
        for entry in entries:
            nid = getattr(entry, "nodeId", entry.get("nodeId", None))
            if nid == node_id:
                return True
        return False

    @async_test_body
    async def test_removeaclfromnode_returns_notfound_for_missing_node(self):
        # ---- Fixture/provided by product environment or override in test runner ----
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        ds_node_id = getattr(self, "datastore_node_id", self.dut_node_id)
        # Set these as two NodeIDs that are NOT present in the Node Information Entries:
        TEST_NODEIDS = getattr(self, "missing_nodeids", [0xCAFE1234, 0xDEAD5555])

        asserts.assert_is_not_none(admin_ctrl, "Need admin controller for JFDA admin commands")
        asserts.assert_is_not_none(JFDA_CLUSTER, "JointFabricDatastore cluster not found in SDK")
        asserts.assert_is_not_none(REMOVEACL_CMD, "RemoveACLFromNode command not found in cluster definition")

        for idx, nodeid in enumerate(TEST_NODEIDS):
            # Step 1: Confirm Node Information Entry does not exist
            self.print_step(idx*4+1, f"Check missing Node Information Entry for NodeID {hex(nodeid)}")
            entry_exists = await self.node_entry_exists(admin_ctrl, ds_node_id, nodeid)
            asserts.assert_false(entry_exists,
                f"Test precondition failure: NodeID {hex(nodeid)} already in Node Information Entries"
            )

            # Step 2: Issue RemoveACLFromNode for the missing NodeID; expect NOT_FOUND
            self.print_step(idx*4+2, f"Issue RemoveACLFromNode(NodeID={hex(nodeid)}); expect NOT_FOUND")
            did_get_notfound = False
            try:
                await admin_ctrl.SendCommand(
                    nodeId=ds_node_id,
                    endpoint=JFDA_ENDPOINT,
                    command=REMOVEACL_CMD(nodeId=nodeid)
                )
            except InteractionModelError as e:
                self.print_step(idx*4+3, f"RemoveACLFromNode command returned error: {e.status}")
                did_get_notfound = (e.status == Status.NotFound or str(e.status).upper() == "NOT_FOUND")
                asserts.assert_true(did_get_notfound,
                    f"Expected NOT_FOUND for RemoveACLFromNode({hex(nodeid)}), got {e.status}"
                )
            except Exception as ex:
                asserts.fail(f"Unexpected error for RemoveACLFromNode({hex(nodeid)}): {ex}")
            else:
                asserts.fail(f"RemoveACLFromNode({hex(nodeid)}) succeeded unexpectedly; should fail with NOT_FOUND.")

            # Step 3: (Optional) Re-confirm that no Node Information Entry appears after attempt
            self.print_step(idx*4+4, f"Check Node Information Entry for NodeID {hex(nodeid)} still does NOT exist after attempt")
            still_absent = not await self.node_entry_exists(admin_ctrl, ds_node_id, nodeid)
            asserts.assert_true(still_absent,
                f"NodeID {hex(nodeid)} unexpectedly present after failed RemoveACLFromNode (should remain absent)"
            )

        self.print_step(
            1 + len(TEST_NODEIDS)*4,
            "All RemoveACLFromNode attempts for missing NodeIDs returned NOT_FOUND, Datastore unchanged."
        )

if __name__ == "__main__":
    default_matter_test_main()
```
---

**How to use / adapt:**

- Place as `tests/test_TC_CSA_REMOVEACL_NOTFOUND_0001.py` or in your test directory structure.
- Override/provide `self.missing_nodeids` in your test runner with guaranteed-to-be-absent NodeIDs.
- If `NodeEntries` attribute or `RemoveACLFromNode` command is implemented with different names in your codebase, update their usage accordingly.
- All steps and assertions are labeled for clarity, matching project conventions. The script asserts precondition, negative operation, negative outcome (NOT_FOUND returned), and that no node entries are created or altered as a result of the operations.
- For log/audit checks, integrate with infra or run post-test log reviews as required for compliance/certification.