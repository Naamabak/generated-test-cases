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
Test Case:     TC-CSA-UPDATENODE-0001
Requirement:   CSA-UPDATENODE-REQ-001

Verify UpdateNode fails with NOT_FOUND if no Node Information Entry exists for NodeID.
"""

from mobly import asserts
import pytest

import matter.clusters as Clusters
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

import logging
log = logging.getLogger(__name__)

# --- Test configuration (to be set via test harness/environment) ---
DATASTORE_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
DATASTORE_ENDPOINT = 1  # Use actual endpoint for Joint Fabric Datastore in your environment
UPDATE_NODE_CMD = getattr(DATASTORE_CLUSTER.Commands, "UpdateNode", None) if DATASTORE_CLUSTER else None
NODE_ENTRIES_ATTR = getattr(DATASTORE_CLUSTER.Attributes, "NodeEntries", None) if DATASTORE_CLUSTER else None

NON_EXISTENT_NODE_IDS = [
    0xDEADBEEF1,  # Must not exist in the datastore for the test
    0xFEEDFACE2,  # Must not exist in the datastore for the second attempt
]

class TC_CSA_UPDATENODE_0001(MatterBaseTest):
    """
    Test that UpdateNode returns NOT_FOUND if no Node Information Entry for NodeID exists.
    """

    async def get_node_entries(self, admin_ctrl, datastore_node_id, endpoint):
        asserts.assert_is_not_none(
            NODE_ENTRIES_ATTR, "NodeEntries attribute not found in JFDA cluster objects."
        )
        node_entries_resp = await admin_ctrl.ReadAttribute(
            nodeId=datastore_node_id,
            attributes=[(endpoint, DATASTORE_CLUSTER, NODE_ENTRIES_ATTR)],
        )
        return node_entries_resp[endpoint][DATASTORE_CLUSTER][NODE_ENTRIES_ATTR]

    async def send_updatenode(self, admin_ctrl, datastore_node_id, endpoint, node_id_to_update):
        """
        Attempt to issue UpdateNode for the provided node ID.
        Provide a dummy update payload as required by your cluster model.
        """
        asserts.assert_is_not_none(UPDATE_NODE_CMD, "UpdateNode command is not implemented in cluster model.")
        # You may need to adapt the command args per your cluster definition. Here, only nodeId is changed.
        # Example: UpdateNode(nodeId=..., friendlyName='UpdateAttempt')
        try:
            result = await admin_ctrl.SendCommand(
                nodeId=datastore_node_id,
                endpoint=endpoint,
                command=UPDATE_NODE_CMD(nodeId=node_id_to_update, friendlyName="TestUpdate"),
            )
            return result
        except InteractionModelError as e:
            return e

    @async_test_body
    async def test_update_node_on_nonexistent_entry_fails_with_not_found(self):
        """
        Step 1: Confirm target NodeIDs do not exist in the datastore
        Step 2: Issue UpdateNode for each; expect NOT_FOUND each time
        Step 3: Verify no Node Information Entry is created/changed in datastore
        """
        # Test ·infra/fixtures:
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        datastore_node_id = getattr(self, "datastore_node_id", self.dut_node_id)
        endpoint = getattr(self, "jfda_endpoint", DATASTORE_ENDPOINT)

        asserts.assert_is_not_none(admin_ctrl, "Admin controller for JFDA cluster required.")
        asserts.assert_is_not_none(DATASTORE_CLUSTER, "JointFabricDatastore cluster is not available.")

        # Step 1: Confirm NodeIDs are NOT present in NodeEntries
        self.print_step(1, "Query NodeEntries, ensure target NodeIDs do not exist.")
        node_entries = await self.get_node_entries(admin_ctrl, datastore_node_id, endpoint)
        entries_ids = [getattr(entry, "nodeId", entry.get("nodeId", None)) for entry in node_entries]

        for node_id in NON_EXISTENT_NODE_IDS:
            asserts.assert_not_in(node_id, entries_ids, f"Test NodeID 0x{node_id:X} already exists in NodeEntries!")

        # Step 2: Attempt UpdateNode for each missing NodeID, expect NOT_FOUND
        for i, node_id in enumerate(NON_EXISTENT_NODE_IDS):
            self.print_step(2 + i, f"Attempt UpdateNode for missing NodeID 0x{node_id:X}; expect NOT_FOUND.")
            result = await self.send_updatenode(admin_ctrl, datastore_node_id, endpoint, node_id)
            if isinstance(result, InteractionModelError):
                asserts.assert_equal(
                    result.status, Status.NotFound,
                    f"Expected NOT_FOUND status for UpdateNode on NodeID 0x{node_id:X}, got {result.status}"
                )
            else:
                asserts.fail(f"UpdateNode({hex(node_id)}) did not return InteractionModelError; got: {result}")

        # Step 3: Ensure NodeEntries list is unchanged and still does not include the test NodeIDs
        self.print_step(4, "Re-query NodeEntries and verify no new entries created for missing NodeIDs.")
        node_entries_after = await self.get_node_entries(admin_ctrl, datastore_node_id, endpoint)
        after_ids = [getattr(entry, "nodeId", entry.get("nodeId", None)) for entry in node_entries_after]

        for node_id in NON_EXISTENT_NODE_IDS:
            asserts.assert_not_in(
                node_id, after_ids,
                f"Node Information Entry for non-existent NodeID 0x{node_id:X} was created by UpdateNode (should not be present)"
            )

        self.print_step(5, "Test complete: UpdateNode fails with NOT_FOUND for non-existent NodeIDs, no entries created.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**Instructions to Use/Adapt:**

- Save as `tests/test_TC_CSA_UPDATENODE_0001.py` in your test directory.
- Set/override `NON_EXISTENT_NODE_IDS` to use NodeIDs not present in NodeEntries on your Datastore.
- Ensure `jfda_admin_controller`, `datastore_node_id`, and cluster endpoint are set appropriately per your test setup.
- All steps are annotated, and status/error checks use project standard idioms.
- No actual NodeEntries should be created as a result of this test; only NOT_FOUND status is a correct response.