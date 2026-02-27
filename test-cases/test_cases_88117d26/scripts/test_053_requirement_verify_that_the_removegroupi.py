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
Test Case:     TC-CSA-GRP-REMOVEGROUPID-NOTFOUND-0001
Requirement:   CSA-REMOVEGROUPIDFROMENDPOINT-REQ-NOTFOUND-001

Verify RemoveGroupIDFromEndpointForNode fails with NOT_FOUND if
no Endpoint Information Entry exists for the given NodeID and EndpointID.
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

# --- Testbed/test context configuration (override as needed for your environment) ---
GROUP_KEY_MGMT_CLUSTER = Clusters.GroupKeyManagement
# Typically this is the relevant command for group membership removal
REMOVE_GROUP_CMD = getattr(GROUP_KEY_MGMT_CLUSTER.Commands, "RemoveGroupIDFromEndpointForNode", None)
GROUPS_ATTR = getattr(GROUP_KEY_MGMT_CLUSTER.Attributes, "Groups", None)

class TC_CSA_GRP_REMOVEGROUPID_NOTFOUND_0001(MatterBaseTest):
    """
    Test RemoveGroupIDFromEndpointForNode returns NOT_FOUND if endpoint entry does not exist (NodeID+EndpointID pair).
    """

    async def check_endpoint_group_entry(self, endpoint, group_id):
        """
        Checks if a group entry exists for (endpoint, group_id).
        Returns True if present, otherwise False.
        """
        result = await self.read_single_attribute_check_success(
            cluster=GROUP_KEY_MGMT_CLUSTER,
            attribute=GROUPS_ATTR,
            endpoint=endpoint
        )
        group_ids = [g.groupID for g in result] if result else []
        return group_id in group_ids

    @async_test_body
    async def test_removegroupidfromendpointfornode_returns_notfound(self):
        """
        Steps:
        1. Ensure test NodeID+EndpointID has no entry for the group (precondition).
        2. Issue RemoveGroupIDFromEndpointForNode (for NodeID/EndpointID/group_id with missing entry).
        3. Verify NOT_FOUND is returned.
        4. Optionally, repeat for an additional (NodeID, EndpointID) that doesn't exist.
        5. Confirm no changes or deletions in Node/Datastore and review logs if available.
        """
        # ---- Testbed/configuration variables (override in CI or set via test harness) ----
        node_id = getattr(self, "test_node_id", self.dut_node_id)
        endpoint_id = getattr(self, "test_endpoint_id", 99)         # Choose a non-existent/applicable endpoint for test
        test_group_id = getattr(self, "test_group_id", 0x9999)      # Group ID for test, should not exist on endpoint
        alt_node_id = getattr(self, "alt_test_node_id", node_id + 1)
        alt_endpoint_id = getattr(self, "alt_test_endpoint_id", endpoint_id + 1)

        assert REMOVE_GROUP_CMD is not None, "Testbed: RemoveGroupIDFromEndpointForNode command must be defined."
        assert GROUPS_ATTR is not None, "Testbed: GROUPS_ATTR must be set on GroupKeyManagement cluster."

        # -- Step 1: Confirm no group entry for (NodeID, EndpointID) --
        self.print_step(1, f"Check no entry exists for NodeID {hex(node_id)}, EndpointID {endpoint_id}, GroupID {hex(test_group_id)}")
        entry_exists = await self.check_endpoint_group_entry(endpoint_id, test_group_id)
        asserts.assert_false(
            entry_exists,
            f"Precondition failed: Group {hex(test_group_id)} is already assigned to endpoint {endpoint_id}."
        )

        # -- Step 2: Issue RemoveGroupIDFromEndpointForNode (expect NOT_FOUND) --
        self.print_step(2, f"Issue RemoveGroupIDFromEndpointForNode for non-existent entry (NodeID={hex(node_id)}, EndpointID={endpoint_id})")
        with pytest.raises(InteractionModelError) as excinfo:
            await self.default_controller.SendCommand(
                nodeId=node_id,
                endpoint=endpoint_id,
                command=REMOVE_GROUP_CMD(GroupID=test_group_id, Endpoint=endpoint_id)
            )
        exc: InteractionModelError = excinfo.value
        self.print_step(3, f"Received error status: {exc.status}")
        asserts.assert_equal(
            exc.status, Status.NotFound,
            f"Expected NOT_FOUND, got {exc.status} for RemoveGroupIDFromEndpointForNode (NodeID={hex(node_id)}, EndpointID={endpoint_id})"
        )

        # -- Step 4: (Optional) Repeat with another (NodeID, EndpointID) combo --
        self.print_step(4, f"Repeat with different NodeID ({hex(alt_node_id)}) and EndpointID ({alt_endpoint_id})")
        with pytest.raises(InteractionModelError) as excinfo2:
            await self.default_controller.SendCommand(
                nodeId=alt_node_id,
                endpoint=alt_endpoint_id,
                command=REMOVE_GROUP_CMD(GroupID=test_group_id, Endpoint=alt_endpoint_id)
            )
        exc2: InteractionModelError = excinfo2.value
        asserts.assert_equal(
            exc2.status, Status.NotFound,
            f"Expected NOT_FOUND, got {exc2.status} for RemoveGroupIDFromEndpointForNode (NodeID={hex(alt_node_id)}, EndpointID={alt_endpoint_id})"
        )

        # -- Step 5: Confirm endpoint group entries unchanged and no side effects --
        self.print_step(5, "Verify endpoint group and Node configuration are unchanged.")
        still_no_entry = not await self.check_endpoint_group_entry(endpoint_id, test_group_id)
        asserts.assert_true(still_no_entry, "Unexpected entry was created or modified in endpoint group entries.")
        still_no_entry2 = not await self.check_endpoint_group_entry(alt_endpoint_id, test_group_id)
        asserts.assert_true(still_no_entry2, "Unexpected entry was created/modified for alternative endpoint/group.")

        self.print_step(6, "Test complete: RemoveGroupIDFromEndpointForNode returns NOT_FOUND when endpoint entry does not exist, and system state is unchanged.")

if __name__ == "__main__":
    default_matter_test_main()
```
**Instructions to Use or Adapt:**
- Save as `tests/test_TC_CSA_GRP_REMOVEGROUPID_NOTFOUND_0001.py` (or similar).
- Override `test_node_id`, `test_endpoint_id`, `test_group_id`, etc., in your test runner to ensure tested NodeID+EndpointID/GroupID tuples do **not** exist.
- Make sure the command/attribute mappings in your Matter Python stack match those used in this script.
- All step comments, error assertions, and compliance checks match your project’s style and certification protocol.