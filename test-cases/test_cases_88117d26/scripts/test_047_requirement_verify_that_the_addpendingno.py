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
Test Case:     TC-CSA-ADDPENDING-CONSTRAINT-0001
Requirement:   CSA-ADDPENDINGNODE-REQ-INVALIDCONSTRAINT-001

Verify AddPendingNode fails with INVALID_CONSTRAINT when a Node Information Entry already exists for the NodeID.
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

# ---- Test Context/Fixture Constants (to be supplied by testbed) ----
# Set these to values required by your environment/testbed
DATASTORE_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
DATASTORE_ENDPOINT = 1  # Change if Datastore is on another endpoint
ADD_PENDING_NODE_CMD = getattr(DATASTORE_CLUSTER.Commands, "AddPendingNode", None) if DATASTORE_CLUSTER else None
NODE_ENTRY_ATTR = getattr(DATASTORE_CLUSTER.Attributes, "NodeEntries", None) if DATASTORE_CLUSTER else None

class TC_CSA_ADDPENDING_CONSTRAINT_0001(MatterBaseTest):
    """
    Verify AddPendingNode fails with INVALID_CONSTRAINT status if a Node Information Entry already exists.
    """

    async def get_node_entries(self, dev_ctrl, ds_node_id):
        # Query all NodeEntries from the Joint Fabric Datastore
        result = await dev_ctrl.ReadAttribute(
            nodeId=ds_node_id,
            attributes=[(DATASTORE_ENDPOINT, DATASTORE_CLUSTER, NODE_ENTRY_ATTR)],
        )
        return result[DATASTORE_ENDPOINT][DATASTORE_CLUSTER][NODE_ENTRY_ATTR]

    def _get_nodeid(self, entry):
        # Extract nodeId from the NodeEntry struct (object or dict)
        if hasattr(entry, "nodeId"):
            return entry.nodeId
        if isinstance(entry, dict):
            return entry.get("nodeId")
        return None

    @async_test_body
    async def test_addpendingnode_fails_if_entry_exists(self):
        # ---- Setup/Fixture: System setup must provide these ----
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        ds_node_id = getattr(self, "datastore_node_id", self.dut_node_id)
        target_node_id = getattr(self, "existing_node_id", None)  # Must already exist in NodeEntries
        asserts.assert_is_not_none(admin_ctrl, "Test requires jfda_admin_controller or self.default_controller.")
        asserts.assert_is_not_none(ds_node_id, "Test requires datastore_node_id (ID of Joint Fabric Datastore node).")
        asserts.assert_is_not_none(target_node_id, "Test requires existing_node_id (NodeID of entry already in datastore).")
        asserts.assert_is_not_none(
            ADD_PENDING_NODE_CMD, "AddPendingNode command not implemented on JointFabricDatastore cluster."
        )
        asserts.assert_is_not_none(
            NODE_ENTRY_ATTR, "NodeEntries attribute not found on JointFabricDatastore cluster."
        )

        # Step 1: Query Datastore to confirm an entry for target_node_id already exists
        self.print_step(1, "Query NodeEntries from Datastore, assert entry already exists for target NodeID.")
        node_entries_before = await self.get_node_entries(admin_ctrl, ds_node_id)
        existing = [entry for entry in node_entries_before if self._get_nodeid(entry) == target_node_id]
        asserts.assert_true(
            len(existing) == 1, f"Expected one Node Information Entry for NodeID {hex(target_node_id)} before test."
        )

        # Step 2: Attempt to issue AddPendingNode with same NodeID, should fail with INVALID_CONSTRAINT
        self.print_step(2, "Issue AddPendingNode command with existing NodeID, expect INVALID_CONSTRAINT status.")
        constraint_error = False
        try:
            await admin_ctrl.SendCommand(
                nodeId=ds_node_id, endpoint=DATASTORE_ENDPOINT,
                command=ADD_PENDING_NODE_CMD(nodeId=target_node_id)
            )
        except InteractionModelError as e:
            self.print_step(3, f"AddPendingNode returned status: {e.status}")
            constraint_error = (e.status == Status.ConstraintError or str(e.status).upper() == "INVALID_CONSTRAINT")
            asserts.assert_true(
                constraint_error,
                f"Expected INVALID_CONSTRAINT/ConstraintError for AddPendingNode with existing entry, got: {e.status}"
            )
        except Exception as e:
            asserts.fail(f"Unexpected error for AddPendingNode with duplicate NodeID: {e}")
        else:
            asserts.fail("AddPendingNode with duplicate NodeID succeeded; expected constraint error.")

        # Step 4: Confirm no duplicate NodeEntry created
        self.print_step(4, "Re-query NodeEntries after command, confirm no duplicate entry was created.")
        node_entries_after = await self.get_node_entries(admin_ctrl, ds_node_id)
        entry_count = sum(1 for entry in node_entries_after if self._get_nodeid(entry) == target_node_id)
        asserts.assert_equal(entry_count, 1, "Duplicate Node Information Entry found after constraint failure; expected only one.")

        # Step 5: Confirm content of existing entry is unchanged (best effort: compare dict/object values)
        self.print_step(5, "Verify that the original entry remains unchanged (compare as best possible).")
        original = existing[0]
        after = [entry for entry in node_entries_after if self._get_nodeid(entry) == target_node_id][0]
        # Compare a set of critical fields; adapt as needed.
        for field in ["nodeId", "commissioningStatus"]:
            val_orig = getattr(original, field, None) if hasattr(original, field) else original.get(field, None)
            val_after = getattr(after, field, None) if hasattr(after, field) else after.get(field, None)
            asserts.assert_equal(
                val_orig, val_after,
                f"Field '{field}' of Node Entry was modified by failed AddPendingNode attempt."
            )

        self.print_step(6, "Review logs/audit (manual or infra integration) to confirm status code and no side effect.")

        self.print_step(7, "Test complete: AddPendingNode correctly fails with INVALID_CONSTRAINT, no duplicates/side effect.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**How to use/adapt:**
- Save as `tests/test_TC_CSA_ADDPENDING_CONSTRAINT_0001.py`.
- Ensure your test runner/fixture provides:
  - `self.jfda_admin_controller` (admin controller)
  - `self.datastore_node_id` (NodeID of your Joint Fabric Datastore cluster/node)
  - `self.existing_node_id` (a NodeID already present in the Datastore before the test)
- All steps are step-annotated, and strong assertions are used for robust failure tracking.
- If your cluster or attributes differ, adapt constant names as appropriate for your implementation.
- Audit/log checks are noted for manual/testbed validation if required.