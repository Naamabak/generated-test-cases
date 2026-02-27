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
Test Case:     TC-CSA-ADDGROUPID-NOTFOUND-0001
Requirement:   CSA-ADDGROUPID-REQ-NOTFOUND-001

Verify AddGroupIDToEndpointForNode fails with NOT_FOUND if no Endpoint Information Entry
exists for the target NodeID and EndpointID in the datastore.
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

# ---- Testbed/cluster/command constants (update to match your environment!) ----
JFDA_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
JFDA_ENDPOINT = 1  # Default endpoint; override if needed
ADD_GROUP_CMD = getattr(JFDA_CLUSTER.Commands, "AddGroupIDToEndpointForNode", None) if JFDA_CLUSTER else None
EP_ENTRY_ATTR = getattr(JFDA_CLUSTER.Attributes, "EndpointEntries", None) if JFDA_CLUSTER else None

class TC_CSA_ADDGROUPID_NOTFOUND_0001(MatterBaseTest):
    """
    Test AddGroupIDToEndpointForNode returns NOT_FOUND if no Endpoint Information Entry
    exists for the given NodeID + EndpointID.
    """

    async def get_endpoint_entry(self, dev_ctrl, ds_node_id, node_id, endpoint_id):
        """
        Search the JFDA EndpointEntries list for an entry that matches node_id and endpoint_id.
        Returns True if exists, False otherwise.
        """
        asserts.assert_is_not_none(EP_ENTRY_ATTR, "Attribute EndpointEntries missing in JFDA cluster")
        resp = await dev_ctrl.ReadAttribute(
            nodeId=ds_node_id,
            attributes=[(JFDA_ENDPOINT, JFDA_CLUSTER, EP_ENTRY_ATTR)],
        )
        entries = resp[JFDA_ENDPOINT][JFDA_CLUSTER][EP_ENTRY_ATTR]
        for entry in entries:
            nid = getattr(entry, "nodeId", entry.get("nodeId", None))
            eid = getattr(entry, "endpointId", entry.get("endpointId", None))
            if nid == node_id and eid == endpoint_id:
                return True
        return False

    @async_test_body
    async def test_addgroupidtoendpointfornode_not_found(self):
        # --- Setup testbed fixtures and target node/endpoint IDs ---
        ds_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        ds_node_id = getattr(self, "datastore_node_id", self.dut_node_id)
        # These examples should be overridden/provied by your testbed as not present in Endpoint Information Entries
        TEST_NODE_EPS = [
            (0xBADBAD01, 20),
            (0xFAFADEAD, 30)
        ]

        asserts.assert_is_not_none(ADD_GROUP_CMD, "AddGroupIDToEndpointForNode command not found in JFDA cluster")
        asserts.assert_is_not_none(ds_ctrl, "Admin controller required for JFDA admin ops")

        # Step 1: Query the datastore to ensure NodeID+EndpointID entry does not exist
        for idx, (nodeid, ep) in enumerate(TEST_NODE_EPS):
            self.print_step(idx*4+1, f"Check no Endpoint Information Entry exists for NodeID {hex(nodeid)}, EndpointID {ep}")
            exists = await self.get_endpoint_entry(ds_ctrl, ds_node_id, nodeid, ep)
            asserts.assert_false(exists,
                f"Endpoint Information Entry unexpectedly exists for NodeID={hex(nodeid)}, EndpointID={ep}")

            # Step 2: Attempt AddGroupIDToEndpointForNode with missing entry
            self.print_step(idx*4+2, f"Issue AddGroupIDToEndpointForNode(NodeID={hex(nodeid)}, EndpointID={ep}); expect NOT_FOUND")
            try:
                await ds_ctrl.SendCommand(
                    nodeId=ds_node_id,
                    endpoint=JFDA_ENDPOINT,
                    command=ADD_GROUP_CMD(NodeID=nodeid, EndpointID=ep, GroupID=0x1001, GroupKeySetID=0xA0)
                )
            except InteractionModelError as e:
                self.print_step(idx*4+3, f"AddGroupIDToEndpointForNode returned error: {e.status}")
                asserts.assert_equal(
                    e.status, Status.NotFound,
                    f"Expected NOT_FOUND status but got {e.status} for NodeID={hex(nodeid)}, EndpointID={ep}"
                )
            except Exception as e:
                asserts.fail(f"Unexpected error for AddGroupIDToEndpointForNode: {e}")
            else:
                asserts.fail("AddGroupIDToEndpointForNode unexpectedly succeeded for absent endpoint entry; should return NOT_FOUND.")

            # Step 5: Check datastore remains unchanged (no new entry was created)
            self.print_step(idx*4+4, "Verify Endpoint Information Entry is still absent after failed command.")
            still_absent = not await self.get_endpoint_entry(ds_ctrl, ds_node_id, nodeid, ep)
            asserts.assert_true(still_absent,
                f"Endpoint Information Entry for NodeID={hex(nodeid)}, EndpointID={ep} appeared after NOT_FOUND; should remain absent.")

        self.print_step((len(TEST_NODE_EPS)*4)+1,
            "All AddGroupIDToEndpointForNode attempts for missing entries failed with NOT_FOUND; no changes made.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**Instructions for Usage/Integration:**
- Save as `tests/test_TC_CSA_ADDGROUPID_NOTFOUND_0001.py`.
- The script expects your testbed to provide:
    - `self.jfda_admin_controller` (`self.default_controller` by default)
    - `self.datastore_node_id` (the JFDA/Datastore node ID)
    - Two or more NodeID/EndpointID pairs known to be *absent* in the Endpoint Information Entries (override `TEST_NODE_EPS`).
- All steps follow project conventions: robust assertion, print_step annotation, and "no-state-change" validation.
- Update attribute/command names/values if your JFDA or Group cluster integration differs.
- No state should be modified as a result of these negative operations.