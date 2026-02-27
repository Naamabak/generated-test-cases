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
TC-CSA-REMOVEADMIN-0001

Requirement: CSA-REMOVEADMIN-REQ-001

Verify that RemoveAdmin command fails with NOT_FOUND status code
if the entry for the given NodeID does not exist.
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

# Replace with real Admin cluster and attributes according to your implementation
ADMIN_CLUSTER = getattr(Clusters, "Admin", None)
ADMINLIST_ATTR = getattr(ADMIN_CLUSTER.Attributes, "AdminList", None) if ADMIN_CLUSTER else None
REMOVE_ADMIN_CMD = getattr(ADMIN_CLUSTER.Commands, "RemoveAdmin", None) if ADMIN_CLUSTER else None

class TC_CSA_REMOVEADMIN_0001(MatterBaseTest):
    """
    Test RemoveAdmin for missing NodeID returns NOT_FOUND and does not change admin list.
    """

    def get_admin_list(self):
        return self.read_single_attribute_check_success(
            cluster=ADMIN_CLUSTER,
            attribute=ADMINLIST_ATTR,
            endpoint=0
        )

    async def send_remove_admin(self, dev_ctrl, node_id):
        asserts.assert_is_not_none(REMOVE_ADMIN_CMD, "Admin cluster does not implement RemoveAdmin command.")
        return await dev_ctrl.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=0,
            command=REMOVE_ADMIN_CMD(NodeID=node_id)
        )

    @async_test_body
    async def test_removeadmin_with_nonexistent_nodeid(self):
        # Step 1: Read admin list and select NodeIDs not present
        self.print_step(1, "Query AdminList to find missing NodeIDs.")
        admin_list = await self.get_admin_list()
        asserts.assert_is_instance(admin_list, list, "AdminList must be a list of entries (dict or object).")
        existing_node_ids = set(
            getattr(entry, "nodeId", entry.get("nodeId", None)) for entry in admin_list
        )

        # Pick two arbitrary NodeIDs that are not in the list (use high numbers for uniqueness)
        NONEXISTENT_NODEIDS = [0xDEADBEEF, 0xFEEDBEEF]
        for nodeid in NONEXISTENT_NODEIDS:
            asserts.assert_not_in(nodeid, existing_node_ids, f"NodeID 0x{nodeid:08X} unexpectedly found in AdminList.")

        # Store adminlist to compare after test
        admin_list_before = list(admin_list)

        # Step 2: Issue RemoveAdmin for both missing NodeIDs
        for idx, nodeid in enumerate(NONEXISTENT_NODEIDS):
            self.print_step(idx+2, f"Issue RemoveAdmin for non-existent NodeID 0x{nodeid:08X}.")
            with pytest.raises(InteractionModelError) as excinfo:
                await self.send_remove_admin(self.default_controller, nodeid)
            exc: InteractionModelError = excinfo.value
            self.print_step(idx+3, f"Got error status: {exc.status}")
            asserts.assert_equal(
                exc.status, Status.NotFound,
                f"Expected NOT_FOUND status, got {exc.status} for NodeID 0x{nodeid:08X}"
            )

        # Step 3: Re-query AdminList and confirm it hasn't changed
        self.print_step(4, "Verify AdminList remains unchanged after RemoveAdmin attempts.")
        admin_list_after = await self.get_admin_list()
        assert len(admin_list_after) == len(admin_list_before), "AdminList size changed after RemoveAdmin."
        after_ids = sorted(getattr(e, "nodeId", e.get("nodeId", None)) for e in admin_list_after)
        before_ids = sorted(getattr(e, "nodeId", e.get("nodeId", None)) for e in admin_list_before)
        asserts.assert_equal(after_ids, before_ids, "AdminList entries changed after RemoveAdmin with missing NodeID.")

        self.print_step(5, "All removals for missing admins failed with NOT_FOUND; admin table unchanged.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions/Notes**
- Place as `tests/test_TC_CSA_REMOVEADMIN_0001.py` or a similar location in your test suite.
- Adjust `ADMIN_CLUSTER`, `ADMINLIST_ATTR`, and `REMOVE_ADMIN_CMD` to match your actual implementation if needed.
- The test dynamically checks for NodeIDs that are *not* in the admin list and verifies removal fails as required.
- All steps, logging, and assertions use conventions matching other MatterBaseTest-based scripts in the project.
- If the testbed provides admin API or cluster with a different command/attribute name, update those references.