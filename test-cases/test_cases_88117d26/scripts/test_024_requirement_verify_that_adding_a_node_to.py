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
Test Case:     TC-CSA-GROUP-0001
Requirement:   CSA-GROUP-REQ-ADDGROUPID

Verify that AddGroupIDToEndpointForNode updates Node's group membership and key.
"""

from mobly import asserts
import pytest

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

GROUP_ID = 0x1234       # Example Group ID for test
GROUP_KEYSET_ID = 0x71  # Example KeySet ID (use infra-supplied if needed)
TEST_ENDPOINT = 1       # Ensure this endpoint is group-configurable on the Node

class TC_CSA_GROUP_0001(MatterBaseTest):
    """
    TC-CSA-GROUP-0001:
    Verify AddGroupIDToEndpointForNode updates the Node with correct group membership/config.
    """

    async def read_group_membership(self, endpoint):
        return await self.read_single_attribute_check_success(
            cluster=Clusters.GroupKeyManagement,
            attribute=Clusters.GroupKeyManagement.Attributes.Groups,
            endpoint=endpoint
        )

    async def read_group_keymap(self, endpoint):
        return await self.read_single_attribute_check_success(
            cluster=Clusters.GroupKeyManagement,
            attribute=Clusters.GroupKeyManagement.Attributes.GroupKeyMap,
            endpoint=endpoint
        )

    async def send_add_group_cmd(self, dev_ctrl, endpoint, group_id, group_keyset_id):
        # GroupKeyManagement cluster: AddGroupIDToEndpointForNode is likely a custom command
        # Use the actual Matter command when available (e.g., KeySetWrite → Group addition in practice)
        cmd = getattr(Clusters.GroupKeyManagement.Commands, "AddGroupIDToEndpointForNode", None)
        if cmd is None:
            pytest.skip("Cluster does not implement AddGroupIDToEndpointForNode command")
        try:
            return await dev_ctrl.SendCommand(
                nodeId=self.dut_node_id,
                endpoint=endpoint,
                command=cmd(GroupID=group_id, Endpoint=endpoint, GroupKeySetID=group_keyset_id)
            )
        except InteractionModelError as e:
            return e

    @async_test_body
    async def test_add_group_id_to_endpoint(self):
        # Step 1: Confirm Group is NOT present for the endpoint
        self.print_step(1, f"Verify GroupID 0x{GROUP_ID:04X} is not present for Endpoint {TEST_ENDPOINT}")
        group_list_before = await self.read_group_membership(TEST_ENDPOINT)
        pre_groups = [g.groupID for g in group_list_before] if group_list_before else []
        asserts.assert_not_in(GROUP_ID, pre_groups,
                              "GroupID already assigned before test; must not be present pre-command.")

        # Step 2: Send AddGroupIDToEndpointForNode
        self.print_step(2, f"Send AddGroupIDToEndpointForNode (GroupID={GROUP_ID}, KeySetID={GROUP_KEYSET_ID}, Ep={TEST_ENDPOINT})")
        rsp = await self.send_add_group_cmd(self.default_controller, TEST_ENDPOINT, GROUP_ID, GROUP_KEYSET_ID)

        # Step 3: Wait for/validate response (should not error)
        self.print_step(3, "Check Node acknowledges the AddGroupIDToEndpointForNode command")
        asserts.assert_true(
            not isinstance(rsp, Exception),
            f"Command returned an error: {rsp}"
        )

        # Step 4: Read membership again
        self.print_step(4, "Read group membership after command; ensure group is now present")
        group_list_after = await self.read_group_membership(TEST_ENDPOINT)
        post_groups = [g.groupID for g in group_list_after] if group_list_after else []

        # Step 5: Verify GroupID now listed
        asserts.assert_in(GROUP_ID, post_groups,
                          f"GroupID 0x{GROUP_ID:04X} missing in group membership after addition.")

        # Step 6: Verify the group key mapping is present for the endpoint and group
        self.print_step(5, "Verify Node has correct group key mapping for the Group ID")
        group_keymap_after = await self.read_group_keymap(TEST_ENDPOINT)
        keymaps = [k for k in group_keymap_after if k.groupID == GROUP_ID]
        asserts.assert_true(len(keymaps) > 0, "No GroupKeyMap entry found for GroupID after addition")
        for m in keymaps:
            asserts.assert_equal(
                m.groupKeySetID, GROUP_KEYSET_ID,
                f"GroupKeySetID incorrect for GroupID {GROUP_ID} (expected {GROUP_KEYSET_ID}, got {m.groupKeySetID})"
            )

        # Step 7: Send group command and check Node response (For an On/Off cluster, as example)
        # Use controller's Groupcast method if testbed provides.
        self.print_step(6, f"Send On command to the Node via groupcast (GroupID={GROUP_ID}) and verify response.")
        try:
            groupcast_ctrl = getattr(self, "groupcast_controller", self.default_controller)
            await groupcast_ctrl.SendGroupCommand(
                groupId=GROUP_ID,
                endpoint=TEST_ENDPOINT,
                command=Clusters.OnOff.Commands.On()
            )
            # To confirm delivery, optionally read state back or substrate event
            on_value = await self.read_single_attribute_check_success(
                cluster=Clusters.OnOff,
                attribute=Clusters.OnOff.Attributes.OnOff,
                endpoint=TEST_ENDPOINT,
            )
            asserts.assert_equal(
                on_value, True,
                "Node did not turn on after group On command; group membership or key may be incorrect."
            )
        except Exception as e:
            asserts.fail(f"Failed to send/observe group command: {e}")

        self.print_step(7, "Test complete: Node is now member of Group with valid key and responds to group comms.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**How to Use / Adapt:**
- Save as `tests/test_TC_CSA_GROUP_0001.py`.
- Adjust `GROUP_ID`, `GROUP_KEYSET_ID`, and `TEST_ENDPOINT` values as appropriate for your testbed/environment.
- The script assumes the `AddGroupIDToEndpointForNode` command and `Groupcast` capability exist in your controller API; adjust these as needed.
- The script preserves the style, assertions, and idioms of your existing tests.
- If groupcast is not directly available, verify group membership via attribute readback.
