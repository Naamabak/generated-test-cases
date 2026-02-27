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
Test Case:     TC-CSA-REMOVE-INUSE-0001
Requirements:  CSA-REMOVEKEYSET-REQ-001, CSA-REMOVEGROUP-REQ-001

Verify that attempts to remove KeySets or Groups that are currently in use and not marked as DeletePending
fail with CONSTRAINT_ERROR status code.
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

# ---- Test Configuration (override as needed for your environment/testbed) ----
IN_USE_KEYSET_ID = 0x50      # An example KeySetID for an in-use keyset
IN_USE_GROUP_ID = 0x2222     # An example GroupID for an in-use group
TEST_ENDPOINT = 1            # Example endpoint for where these are applied (customize as needed)

REMOVE_KEYSET_CMD = getattr(Clusters.GroupKeyManagement.Commands, "RemoveKeySet", None)
REMOVE_GROUP_CMD = getattr(Clusters.GroupKeyManagement.Commands, "RemoveGroup", None)

class TC_CSA_REMOVE_INUSE_0001(MatterBaseTest):
    """
    Tests that RemoveKeySet and RemoveGroup return CONSTRAINT_ERROR if called on
    keysets/groups that are in use and not marked as DeletePending.
    """

    async def get_keyset_table(self):
        # Reads KeySet Table
        return await self.read_single_attribute_check_success(
            cluster=Clusters.GroupKeyManagement,
            attribute=Clusters.GroupKeyManagement.Attributes.GroupKeyMap,
            endpoint=TEST_ENDPOINT
        )

    async def get_group_table(self):
        # Reads Groups attribute
        return await self.read_single_attribute_check_success(
            cluster=Clusters.GroupKeyManagement,
            attribute=Clusters.GroupKeyManagement.Attributes.Groups,
            endpoint=TEST_ENDPOINT
        )

    async def remove_keyset(self, keyset_id):
        asserts.assert_is_not_none(REMOVE_KEYSET_CMD, "RemoveKeySet command not implemented in GroupKeyManagement cluster.")
        return await self.default_controller.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=TEST_ENDPOINT,
            command=REMOVE_KEYSET_CMD(GroupKeySetID=keyset_id)
        )

    async def remove_group(self, group_id):
        asserts.assert_is_not_none(REMOVE_GROUP_CMD, "RemoveGroup command not implemented in GroupKeyManagement cluster.")
        return await self.default_controller.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=TEST_ENDPOINT,
            command=REMOVE_GROUP_CMD(GroupID=group_id)
        )

    @async_test_body
    async def test_inuse_remove_keyset_and_group_fail(self):
        # Step 1: Identify a KeySet in use, check state (not DeletePending)
        self.print_step(1, "Check a KeySet is currently in use and not DeletePending.")
        keysets = await self.get_keyset_table()
        keyset_in_use = next((k for k in keysets if getattr(k, "groupKeySetID", None) == IN_USE_KEYSET_ID), None)
        asserts.assert_is_not_none(keyset_in_use, f"KeySetID {IN_USE_KEYSET_ID} must exist for the test.")

        # Try to detect DeletePending (attribute varies per product; commonly `status` or similar)
        delete_pending = getattr(keyset_in_use, "status", None) == "DeletePending"
        asserts.assert_false(delete_pending, "KeySet must not be DeletePending for negative removal test.")

        # Step 2: Attempt to remove the active KeySet
        self.print_step(2, f"Issue RemoveKeySet({IN_USE_KEYSET_ID}) command and expect CONSTRAINT_ERROR.")
        got_constraint_error = False
        try:
            await self.remove_keyset(IN_USE_KEYSET_ID)
        except InteractionModelError as e:
            got_constraint_error = (e.status == Status.ConstraintError)
            asserts.assert_true(
                got_constraint_error,
                f"RemoveKeySet for KeySetID {IN_USE_KEYSET_ID} did not return CONSTRAINT_ERROR. Received: {e.status}"
            )
        except Exception as e:
            asserts.fail(f"Unexpected failure on RemoveKeySet: {e}")
        else:
            asserts.fail("RemoveKeySet for in-use KeySet succeeded unexpectedly; should return CONSTRAINT_ERROR.")

        # Step 3: Read Keyset Table, ensure keyset still present
        keysets_post = await self.get_keyset_table()
        post_exists = any(getattr(ks, "groupKeySetID", None) == IN_USE_KEYSET_ID for ks in keysets_post)
        asserts.assert_true(
            post_exists, "KeySet was removed after RemoveKeySet with in-use; should have been retained."
        )

        # Step 4: Identify a Group in use, check state (not DeletePending)
        self.print_step(3, "Check a Group is currently in use and not DeletePending.")
        groups = await self.get_group_table()
        group_in_use = next((g for g in groups if getattr(g, "groupID", None) == IN_USE_GROUP_ID), None)
        asserts.assert_is_not_none(group_in_use, f"GroupID {IN_USE_GROUP_ID} must exist for the test.")

        delete_pending_group = getattr(group_in_use, "status", None) == "DeletePending"
        asserts.assert_false(delete_pending_group, "Group must not be DeletePending for negative removal test.")

        # Step 5: Attempt to remove the active Group
        self.print_step(4, f"Issue RemoveGroup({IN_USE_GROUP_ID}) command and expect CONSTRAINT_ERROR.")
        got_constraint_error_group = False
        try:
            await self.remove_group(IN_USE_GROUP_ID)
        except InteractionModelError as e:
            got_constraint_error_group = (e.status == Status.ConstraintError)
            asserts.assert_true(
                got_constraint_error_group,
                f"RemoveGroup for GroupID {IN_USE_GROUP_ID} did not return CONSTRAINT_ERROR. Received: {e.status}"
            )
        except Exception as e:
            asserts.fail(f"Unexpected failure on RemoveGroup: {e}")
        else:
            asserts.fail("RemoveGroup for in-use Group succeeded unexpectedly; should return CONSTRAINT_ERROR.")

        # Step 6: Read Group Table, ensure group still present
        groups_post = await self.get_group_table()
        group_exists_post = any(getattr(g, "groupID", None) == IN_USE_GROUP_ID for g in groups_post)
        asserts.assert_true(
            group_exists_post, "Group was removed after RemoveGroup for in-use group; should have been retained."
        )

        self.print_step(5, "Checked RemoveKeySet and RemoveGroup failed with CONSTRAINT_ERROR for in-use objects.")

        # Step 7: (Optional) Suggest log/audit review if test infra supports it.
        self.print_step(6, "Check system/audit logs for constraint failure records (manual/log integration step).")

        self.print_step(7, "All KeySets and Groups remain; in-use removals are properly rejected with CONSTRAINT_ERROR.")

if __name__ == "__main__":
    default_matter_test_main()
```

**Instructions/Usage**:
- Save as `tests/test_TC_CSA_REMOVE_INUSE_0001.py` or similar in your MATTER/CHIP test directory.
- The script uses async/pytest `async_test_body`, robust step-to-code mapping, and detailed assertion messages matching your project's conventions.
- Set `IN_USE_KEYSET_ID` and `IN_USE_GROUP_ID` to known in-use IDs before running.
- The script expects the cluster to raise an `InteractionModelError` with `Status.ConstraintError` for removal attempts of in-use keysets or groups.
- Adjust command/attribute and endpoint IDs as needed for your product/testbed.
- For auditing, additional infra hooks or post-processing log checks may be added as per your certification requirements.