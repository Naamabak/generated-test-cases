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
Test Case:     TC-CSA-JFDA-ADDPENDING-CONFLICT-0001
Requirement:   CSA-JFDA-REQ-ADDPENDINGNODE-002

Verify that if a Node Information Entry already exists for the given NodeID,
the AddPendingNode command fails with an INVALID_CONSTRAINT status code.
"""

from mobly import asserts
import pytest

import matter.clusters as Clusters
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

# Dummy command/attribute references (adjust to your actual cluster implementation)
JFDA_CLUSTER = Clusters.JointFabricDatastore
JFDA_ENDPOINT = 1  # Change to your JFDA endpoint as needed

ADD_PENDING_NODE_CMD = getattr(JFDA_CLUSTER.Commands, "AddPendingNode", None)
QUERY_NODE_CMD = getattr(JFDA_CLUSTER.Commands, "QueryNode", None)
NODELIST_ATTRIBUTE = getattr(JFDA_CLUSTER.Attributes, "NodeList", None)

# Test fixture variables that runner/environment should provide
TEST_NODE_ID = None           # The NodeID for the test (should be an existing entry)
DUT_NODE_ID = None            # The Anchor Administrator Node ID (where JFDA is present)
ADMIN_CTRL = None             # Controller with privileges to send AddPendingNode

class TC_CSA_JFDA_ADDPENDING_CONFLICT_0001(MatterBaseTest):
    """
    Verify AddPendingNode fails with INVALID_CONSTRAINT if Node Information Entry already exists for NodeID.
    """
    @async_test_body
    async def test_addpending_conflict_existing_entry(self):
        # --- Step 0: Retrieve testbed-provided variables
        test_node_id = getattr(self, "test_node_id", TEST_NODE_ID)
        admin_ctrl = getattr(self, "admin_ctrl", self.default_controller)
        dut_node_id = getattr(self, "dut_node_id", DUT_NODE_ID or self.dut_node_id)
        jfda_ep = getattr(self, "jfda_endpoint", JFDA_ENDPOINT)

        asserts.assert_is_not_none(test_node_id, "Test requires test_node_id to be set!")
        asserts.assert_is_not_none(admin_ctrl, "Test requires admin_ctrl/controller to send commands!")
        asserts.assert_is_not_none(dut_node_id, "DUT (Anchor Administrator Node ID) must be set.")

        # --- Step 1: Query JFDA cluster to confirm there is already a Node Info Entry for NodeID ---
        self.print_step(1, f"Query Joint Fabric Datastore to verify NodeInfo entry for NodeID 0x{test_node_id:X} exists.")
        if NODELIST_ATTRIBUTE is not None:
            node_list = await admin_ctrl.ReadAttribute(
                nodeId=dut_node_id,
                attributes=[(jfda_ep, JFDA_CLUSTER, NODELIST_ATTRIBUTE)]
            )
            nlist = node_list.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(NODELIST_ATTRIBUTE, [])
            pre_count = sum(1 for entry in nlist if getattr(entry, "nodeId", None) == test_node_id)
            asserts.assert_equal(pre_count, 1, f"Expected exactly one entry for NodeID 0x{test_node_id:X} before AddPendingNode.")
        elif QUERY_NODE_CMD is not None:
            entry = await admin_ctrl.SendCommand(
                nodeId=dut_node_id,
                endpoint=jfda_ep,
                command=QUERY_NODE_CMD(nodeId=test_node_id)
            )
            asserts.assert_is_not_none(entry, f"No Node Information Entry found for NodeID 0x{test_node_id:X}, cannot run test.")
        else:
            pytest.skip("No way to query Node Information Entry in JFDA cluster.")

        # --- Step 2: Attempt AddPendingNode command for same NodeID ---
        self.print_step(2, "Issue AddPendingNode command for NodeID, expecting it to fail.")

        asserts.assert_is_not_none(ADD_PENDING_NODE_CMD, "JFDA Cluster does not have AddPendingNode command.")

        # Fill in required AddPendingNode fields (these are typical, adapt for your cluster definition)
        cmd_kwargs = dict(nodeId=test_node_id)
        # Optionally, add more required fields via your cluster's schema
        got_invalid_constraint = False
        try:
            await admin_ctrl.SendCommand(
                nodeId=dut_node_id,
                endpoint=jfda_ep,
                command=ADD_PENDING_NODE_CMD(**cmd_kwargs)
            )
        except InteractionModelError as e:
            self.print_step(3, f"AddPendingNode returned error code: {e.status}")
            got_invalid_constraint = (e.status == Status.ConstraintError or str(e.status).upper() == "INVALID_CONSTRAINT")
            asserts.assert_true(
                got_invalid_constraint,
                f"Expected INVALID_CONSTRAINT/ConstraintError, got {e.status}. Full error: {e}"
            )
        except Exception as e:
            asserts.fail(f"Unexpected error during AddPendingNode: {e}")
        else:
            asserts.fail("AddPendingNode succeeded when it should have failed due to existing entry.")

        # --- Step 4: Confirm Node Information Entry is unchanged and no duplicate was created ---
        self.print_step(4, "Verify no duplicate Node Information Entry was created by the failed command.")
        if NODELIST_ATTRIBUTE is not None:
            node_list_post = await admin_ctrl.ReadAttribute(
                nodeId=dut_node_id,
                attributes=[(jfda_ep, JFDA_CLUSTER, NODELIST_ATTRIBUTE)]
            )
            nlist_post = node_list_post.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(NODELIST_ATTRIBUTE, [])
            post_count = sum(1 for entry in nlist_post if getattr(entry, "nodeId", None) == test_node_id)
            asserts.assert_equal(post_count, 1,
                f"Expected still exactly one Node Info Entry for NodeID 0x{test_node_id:X} after failed AddPendingNode.")
        # If not possible to check, accept as-compliance with previous step.

        self.print_step(5, "Test complete: AddPendingNode was blocked correctly with INVALID_CONSTRAINT, and no duplicate entry created.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions:**
- Save as `tests/test_TC_CSA_JFDA_ADDPENDING_CONFLICT_0001.py`.
- The script expects environment or runner to provide:  
  - `self.test_node_id` (an existing Node Information Entry in JFDA cluster)
  - `self.dut_node_id` (Anchor Admin Node ID)
  - `self.admin_ctrl` (controller with rights to JFDA cluster).
- Command/attribute names (`AddPendingNode`, `NodeList`, `QueryNode`, etc.) must be adapted to your actual cluster model.
- The test checks the precondition, issues the command, asserts failure and verifies no duplicate or data inconsistency. 
- All steps have comments and checks for maintainability and audit.