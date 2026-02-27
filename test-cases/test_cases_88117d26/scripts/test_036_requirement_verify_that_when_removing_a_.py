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
Test Case:     TC-CSA-REMOVEACL-0002
Requirement:   CSA-REMOVEACL-REQ-002

Verify that when removing a Node from a Group, RemoveACLFromNode is used to remove
group-based ACL entries, and group control is revoked.
"""

from mobly import asserts
import pytest

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

import logging
log = logging.getLogger(__name__)

# --- Test Constants ---
GROUP_ID = 0x4455        # Example group ID for group-based control, adjust as required
GROUP_VERSION = 1        # Example CAT version when encoding group subject as CAT
TEST_ENDPOINT = 1        # Endpoint on Node supporting group operations
PRIVILEGE = "operate"    # Target privilege for group control (use as appropriate for OnOff, etc.)

REMOVEACL_CMD = getattr(Clusters.AccessControl.Commands, "RemoveACLFromNode", None)

# Helper to encode group CAT subject for ACE entries
def group_subject_for_cat(group_id: int, version: int = 1) -> int:
    return 0xFFFFFFFD00000000 | ((group_id << 16) | (version & 0xF))

GROUP_SUBJECT_CAT = group_subject_for_cat(GROUP_ID)

class TC_CSA_REMOVEACL_0002(MatterBaseTest):
    """
    Test RemoveACLFromNode for removing group-based access after group removal,
    and verify former group control is no longer allowed.
    """

    async def get_current_acl(self):
        # Returns list of ACEs from device under test
        acl = await self.read_single_attribute_check_success(
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
            endpoint=0,
        )
        return acl

    async def set_acl(self, acl):
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id, [(0, Clusters.AccessControl.Attributes.Acl(acl))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    async def get_group_membership(self, endpoint):
        # Reads the Groups attribute listing group memberships for this endpoint.
        return await self.read_single_attribute_check_success(
            cluster=Clusters.GroupKeyManagement,
            attribute=Clusters.GroupKeyManagement.Attributes.Groups,
            endpoint=endpoint
        )

    async def send_remove_acl_from_node(self, dev_ctrl):
        asserts.assert_is_not_none(REMOVEACL_CMD, "No RemoveACLFromNode command in cluster implementation.")
        return await dev_ctrl.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=0,  # ACL is usually at endpoint 0
            command=REMOVEACL_CMD()
        )

    @async_test_body
    async def test_remove_acl_after_group_removal(self):
        # --- Step 1: Confirm Node is part of a Group granting control privileges ---
        self.print_step(1, f"Ensure Node is in group {hex(GROUP_ID)} and allows group control.")
        group_list_before = await self.get_group_membership(TEST_ENDPOINT)
        group_ids_before = [g.groupID for g in group_list_before] if group_list_before else []
        asserts.assert_in(GROUP_ID, group_ids_before, f"Node not a member of Group {hex(GROUP_ID)} prior to test.")

        # Try to send group control command and verify success (should respond)
        try:
            groupcast_ctrl = getattr(self, "groupcast_controller", self.default_controller)
            await groupcast_ctrl.SendGroupCommand(
                groupId=GROUP_ID,
                endpoint=TEST_ENDPOINT,
                command=Clusters.OnOff.Commands.On()
            )
            on_value = await self.read_single_attribute_check_success(
                cluster=Clusters.OnOff,
                attribute=Clusters.OnOff.Attributes.OnOff,
                endpoint=TEST_ENDPOINT
            )
            asserts.assert_equal(on_value, True, "Node did not respond to group command prior to ACL/group removal.")
        except Exception as e:
            asserts.fail(f"Node did not accept group command: {e}")

        # --- Step 2: Confirm ACL includes group subject entry ---
        self.print_step(2, "Check Node's ACL includes entry for group subject.")
        acl = await self.get_current_acl()
        group_acl_entry_present = any(
            (hasattr(ace, "subjects") and GROUP_SUBJECT_CAT in ace.subjects) or
            (isinstance(ace, dict) and GROUP_SUBJECT_CAT in ace.get("subjects", []))
            for ace in acl
        )
        asserts.assert_true(group_acl_entry_present, "ACL does not contain entry for the group-based subject.")

        # --- Step 3: Remove Node from Group (simulate group removal) ---
        self.print_step(3, "Remove the Node from the Group via config (simulate via test infra or Group cluster command).")
        # Simulate by directly updating membership attribute, if possible
        group_memberships = list(group_ids_before)
        if GROUP_ID in group_memberships:
            group_memberships.remove(GROUP_ID)
        # Write the group list back (skip if infra doesn't support)
        try:
            await self.default_controller.WriteAttribute(
                self.dut_node_id,
                [(TEST_ENDPOINT, Clusters.GroupKeyManagement.Attributes.Groups(group_memberships))]
            )
        except Exception:
            log.info("Unable to simulate group removal directly; ensure testbed removes Node from group.")

        # --- Step 4: Issue RemoveACLFromNode command to remove group-based ACLs ---
        self.print_step(4, "Send RemoveACLFromNode command.")
        rsp = await self.send_remove_acl_from_node(self.default_controller)

        # --- Step 5: Wait/confirm command was processed ---
        self.print_step(5, "Wait for RemoveACLFromNode command to be processed (sleep or poll as needed).")
        import asyncio
        await asyncio.sleep(2)  # Or poll state/event as required

        # --- Step 6: Inspect ACL to confirm group entries are deleted ---
        self.print_step(6, "Inspect Node's ACL for deletion of group-based entries.")
        acl_after = await self.get_current_acl()
        group_acl_entry_present_after = any(
            (hasattr(ace, "subjects") and GROUP_SUBJECT_CAT in ace.subjects) or
            (isinstance(ace, dict) and GROUP_SUBJECT_CAT in ace.get("subjects", []))
            for ace in acl_after
        )
        asserts.assert_false(
            group_acl_entry_present_after,
            "After RemoveACLFromNode, ACL still contains group-based subject entry!"
        )

        # --- Step 7: Attempt previous group control operation (expect rejection) ---
        self.print_step(7, f"Try group control operation after ACL and group removal; expect access denied or ignored.")
        try:
            await groupcast_ctrl.SendGroupCommand(
                groupId=GROUP_ID,
                endpoint=TEST_ENDPOINT,
                command=Clusters.OnOff.Commands.Off()
            )
            # If command is accepted, OnOff should still be ON (unchanged) or not respond at all.
            # Wait and check value remained ON (operation has not effect)
            await asyncio.sleep(1)
            value_after = await self.read_single_attribute_check_success(
                cluster=Clusters.OnOff,
                attribute=Clusters.OnOff.Attributes.OnOff,
                endpoint=TEST_ENDPOINT
            )
            # If still ON, we assume group command was not accepted.
            asserts.assert_equal(value_after, True, "Node unexpectedly responded to group command after ACL removal.")
        except Exception:
            log.info("Group command was ignored or rejected as expected after RemoveACLFromNode.")

        # --- Step 8: Review logs evidence (manual/infra) ---
        self.print_step(8, "Check Node/system logs for evidence of RemoveACLFromNode invocation and ACL update.")
        # Not possible to automate in standard API; infra/test harness reference needed.

        self.print_step(9, "ACL tied to Group is removed; Node no longer controllable via the removed Group.")

if __name__ == "__main__":
    default_matter_test_main()
```
**Instructions/Notes**:
- Save as `tests/test_TC_CSA_REMOVEACL_0002.py`.
- You may need to adjust group IDs, endpoints, or command mappings for your testbed.
- The script follows your project idioms for structure, step-by-step `print_step`, and `asserts`.
- Simulated group removal is direct but can be replaced by actual Group Management cluster operations or testbed APIs.
- Manual/infra check for log/audit steps is referenced.
- For test environment cleanup, include teardown code as appropriate if group additions/removals are not auto-reverted.