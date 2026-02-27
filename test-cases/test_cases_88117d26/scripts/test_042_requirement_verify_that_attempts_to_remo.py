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
Test Case:     TC-CSA-GKS-REMOVEIPK-0001
Requirement:   CSA-GROUP-REQ-REMOVEKEYSET-IPK

Verify that attempts to remove the IPK (GroupKeySetID of 0) using the RemoveKeySet
command fails with a CONSTRAINT_ERROR status code and the IPK remains present.
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

GROUP_KEYSET_ID_IPK = 0
GROUPKEYMAN_CLUSTER = Clusters.GroupKeyManagement
REMOVE_KEYSET_CMD = getattr(GROUPKEYMAN_CLUSTER.Commands, "RemoveKeySet", None)
GROUP_KEYSET_TABLE_ATTR = getattr(GROUPKEYMAN_CLUSTER.Attributes, "GroupKeyMap", None)

class TC_CSA_GKS_REMOVEIPK_0001(MatterBaseTest):
    """
    Test that RemoveKeySet(GroupKeySetID=0 [IPK]) fails with CONSTRAINT_ERROR and does not remove IPK.
    """

    async def get_group_keymap(self):
        # Query group key store (GroupKeyMap) from the Node
        # Returns: list of keyset entries present (may be struct objects or dicts)
        result = await self.read_single_attribute_check_success(
            cluster=GROUPKEYMAN_CLUSTER,
            attribute=GROUPKEYMAN_CLUSTER.Attributes.GroupKeyMap,
            endpoint=0
        )
        return result

    async def send_remove_keyset(self, group_keyset_id):
        # Attempt to remove a keyset from the Node (command)
        asserts.assert_is_not_none(REMOVE_KEYSET_CMD, "RemoveKeySet command not in cluster model.")
        return await self.default_controller.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=0,
            command=REMOVE_KEYSET_CMD(GroupKeySetID=group_keyset_id)
        )

    @async_test_body
    async def test_remove_ipk_with_constraint_error(self):
        # Step 1: Query Node to confirm presence of GroupKeySetID 0 (the IPK)
        self.print_step(1, "Query Node for GroupKeySetID 0 (IPK) in group key store.")
        keymap = await self.get_group_keymap()
        ipk_present_before = any(
            (getattr(entry, 'groupKeySetID', getattr(entry, 'groupKeySetId', -1)) == GROUP_KEYSET_ID_IPK) for entry in keymap
        )
        asserts.assert_true(ipk_present_before, "GroupKeySetID 0 (IPK) not present before test; setup error.")

        # Step 2: Attempt to remove the IPK using RemoveKeySet(GroupKeySetID=0)
        self.print_step(2, "Issue RemoveKeySet command with GroupKeySetID=0 (IPK), expect failure.")
        constraint_error_received = False
        try:
            await self.send_remove_keyset(GROUP_KEYSET_ID_IPK)
        except InteractionModelError as e:
            self.print_step(3, f"Node replied with status code: {e.status}")
            constraint_error_received = (e.status == Status.ConstraintError or str(e.status).upper() == "CONSTRAINT_ERROR")
            asserts.assert_true(
                constraint_error_received,
                f"Expected CONSTRAINT_ERROR, got {e.status} ({e})"
            )
        except Exception as e:
            asserts.fail(f"Unexpected error when issuing RemoveKeySet: {e}")
        else:
            asserts.fail("RemoveKeySet command for IPK unexpectedly succeeded; should fail with CONSTRAINT_ERROR.")

        # Step 4: Confirm IPK is still present in the group key store, unchanged
        self.print_step(4, "Query Node group key store after RemoveKeySet to confirm IPK is still present.")
        keymap_after = await self.get_group_keymap()
        ipk_present_after = any(
            (getattr(entry, 'groupKeySetID', getattr(entry, 'groupKeySetId', -1)) == GROUP_KEYSET_ID_IPK) for entry in keymap_after
        )
        asserts.assert_true(ipk_present_after, "IPK (GroupKeySetID=0) has been removed! It must remain present as per spec.")

        self.print_step(5, "Test complete: RemoveKeySet of IPK correctly rejected with CONSTRAINT_ERROR and no removal occurred.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**Instructions/Notes:**
- Save as `tests/test_TC_CSA_GKS_REMOVEIPK_0001.py`.
- The script matches the `MatterBaseTest` style, using `async_test_body`, step-to-code mappings, and robust assertions.
- If your project represents GroupKeySetID fields as `groupKeySetId` (vs. `groupKeySetID`), the script will check both properties for compatibility.
- The test ensures the IPK is present before and after, attempts removal, expects a constraint violation, and confirms no actual removal.
- If you have additional teardown or CI needs, add fixture cleanup to restore the group key environment if necessary.