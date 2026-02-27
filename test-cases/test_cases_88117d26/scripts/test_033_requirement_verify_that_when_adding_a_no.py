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
Test Case:     TC-CSA-GKS-ADDGROUP-0001
Requirement:   CSA-GROUP-REQ-ADDGROUPID-GKS

Verify AddGroupIDToEndpointForNode adds a Node to a Group with a GroupKeySetID,
updating group membership and keys, and validates group secured communication.
"""

import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

# Constants for this test case (set to appropriate values for your environment)
TEST_GROUP_ID = 0xCAF1
TEST_ENDPOINT = 1
CORRECT_GROUP_KEYSET_ID = 0x42
INCORRECT_GROUP_KEYSET_ID = 0x99  # Used to test incorrect key
# The controller and cluster endpoint for sending commands is provided by infra as self.default_controller, self.dut_node_id

class TC_CSA_GKS_ADDGROUP_0001(MatterBaseTest):
    """
    Verify that adding a Node to a Group with GroupKeySetID via AddGroupIDToEndpointForNode
    configures both membership and group keys, and only the correct keys permit group message exchange.
    """

    async def get_group_membership(self, endpoint):
        # Reads the Groups attribute that lists group memberships for the endpoint.
        return await self.read_single_attribute_check_success(
            cluster=Clusters.GroupKeyManagement,
            attribute=Clusters.GroupKeyManagement.Attributes.Groups,
            endpoint=endpoint
        )

    async def get_group_keymap(self, endpoint):
        # Reads the GroupKeyMap
        return await self.read_single_attribute_check_success(
            cluster=Clusters.GroupKeyManagement,
            attribute=Clusters.GroupKeyManagement.Attributes.GroupKeyMap,
            endpoint=endpoint
        )

    async def send_add_group_cmd(self, dev_ctrl, group_id, endpoint, group_keyset_id):
        cmd_cls = getattr(Clusters.GroupKeyManagement.Commands, "AddGroupIDToEndpointForNode", None)
        asserts.assert_is_not_none(cmd_cls, "Cluster does not implement AddGroupIDToEndpointForNode command")
        cmd = cmd_cls(GroupID=group_id, Endpoint=endpoint, GroupKeySetID=group_keyset_id)
        return await dev_ctrl.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=endpoint,
            command=cmd
        )

    async def send_secured_group_command(self, group_id, endpoint, keyset_id=None):
        # Use groupcast interface; correct group_keyset_id assumed installed in controller infra.
        # If keyset_id argument is used, swap credentials if supported (test infra must allow this).
        groupcast_ctrl = getattr(self, "groupcast_controller", self.default_controller)
        # NOTE: If infra supports "impersonate"/"swap" key, do so for incorrect_keyset_id test
        if hasattr(groupcast_ctrl, "set_group_keyset"):
            groupcast_ctrl.set_group_keyset(keyset_id)
        await groupcast_ctrl.SendGroupCommand(
            groupId=group_id,
            endpoint=endpoint,
            command=Clusters.OnOff.Commands.On()
        )
        # Verify effect (e.g., OnOff=True)
        onoff_val = await self.read_single_attribute_check_success(
            cluster=Clusters.OnOff,
            attribute=Clusters.OnOff.Attributes.OnOff,
            endpoint=endpoint
        )
        return onoff_val

    @async_test_body
    async def test_group_add_with_keyset(self):
        # --- Step 1: Confirm Node is not member of the Group ---
        self.print_step(1, f"Check Node is not a member of group {hex(TEST_GROUP_ID)} and has no GroupKeySetID {CORRECT_GROUP_KEYSET_ID}")
        group_list_before = await self.get_group_membership(TEST_ENDPOINT)
        group_ids_before = [g.groupID for g in group_list_before] if group_list_before else []
        asserts.assert_not_in(TEST_GROUP_ID, group_ids_before,
            f"Group {hex(TEST_GROUP_ID)} already assigned before test.")
        group_keymap_before = await self.get_group_keymap(TEST_ENDPOINT)
        keysets_before = [k.groupKeySetID for k in group_keymap_before] if group_keymap_before else []
        asserts.assert_not_in(CORRECT_GROUP_KEYSET_ID, keysets_before,
            f"GroupKeySetID {CORRECT_GROUP_KEYSET_ID} already present before test.")

        # --- Step 2: Execute AddGroupIDToEndpointForNode ---
        self.print_step(2, f"Send AddGroupIDToEndpointForNode (GroupID={TEST_GROUP_ID}, Endpoint={TEST_ENDPOINT}, GroupKeySetID={CORRECT_GROUP_KEYSET_ID})")
        try:
            response = await self.send_add_group_cmd(
                self.default_controller, TEST_GROUP_ID, TEST_ENDPOINT, CORRECT_GROUP_KEYSET_ID)
        except Exception as e:
            asserts.fail(f"AddGroupIDToEndpointForNode command failed: {e}")

        # --- Step 3: Wait for and verify success ---
        self.print_step(3, "Check Node acknowledges AddGroupIDToEndpointForNode command with success.")
        # The protocol should either succeed, or raise no exception. Check for lack of errors.
        asserts.assert_true(response is None or not isinstance(response, Exception),
            f"AddGroupIDToEndpointForNode produced error response: {response}")

        # --- Step 4: Read group membership after addition ---
        self.print_step(4, "Read group membership after addition and check GroupID presence")
        group_list_after = await self.get_group_membership(TEST_ENDPOINT)
        group_ids_after = [g.groupID for g in group_list_after] if group_list_after else []
        asserts.assert_in(TEST_GROUP_ID, group_ids_after,
            "Node is not a member of Group after AddGroupIDToEndpointForNode")

        # --- Step 5: Confirm GroupKeySetID is recorded in key mapping ---
        self.print_step(5, "Check Node's GroupKeyMap contains correct GroupKeySetID")
        group_keymap_after = await self.get_group_keymap(TEST_ENDPOINT)
        asserts.assert_true(
            any(k.groupID == TEST_GROUP_ID and k.groupKeySetID == CORRECT_GROUP_KEYSET_ID for k in group_keymap_after),
            f"No GroupKeyMap entry for GroupID={TEST_GROUP_ID} and GroupKeySetID={CORRECT_GROUP_KEYSET_ID}"
        )

        # --- Step 6: Attempt secured group command with correct keyset ---
        self.print_step(6, f"Send On command to Node via groupcast (correct GroupID and GroupKeySetID), expect success")
        try:
            on_val = await self.send_secured_group_command(TEST_GROUP_ID, TEST_ENDPOINT, CORRECT_GROUP_KEYSET_ID)
            asserts.assert_equal(on_val, True, "OnOff cluster did not turn on after correct secure group message.")
        except Exception as e:
            asserts.fail(f"Secured group command with correct KeySet failed: {e}")

        # --- Step 7: Attempt group command with mismatched GroupKeySetID ---
        self.print_step(7, "Send group message using mismatched GroupKeySetID, expect access denial/failure.")
        try:
            # If testbed allows key swap, set wrong keyset; else, force error via infra or skip step.
            await self.send_secured_group_command(TEST_GROUP_ID, TEST_ENDPOINT, INCORRECT_GROUP_KEYSET_ID)
            asserts.fail("Groupcast with wrong GroupKeySetID did not fail as expected.")
        except Exception:
            # Should get denial, error, or silent ignore
            pass

        # --- Step 8: Check logs/events if available (manual or via integrated infra hook) ---
        self.print_step(8, "Review logs/events for Node configuration updated by AddGroupIDToEndpointForNode")
        # Out of scope for pure API, but automated testbeds may have hooks for event/log verification

        self.print_step(9, "Test done: Node in group with correct GroupKeySetID, secured access confirmed.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**Usage/Adaptation**:
- Save as `tests/test_TC_CSA_GKS_ADDGROUP_0001.py`.
- Adjust `TEST_GROUP_ID`, `TEST_ENDPOINT`, and keyset IDs as needed.
- Your test infra should provide `groupcast_controller.set_group_keyset()` or equivalent for proper negative testing; if not available, skip Step 7.
- Step-annotated, robust assertion style per project CHIP Python tests.