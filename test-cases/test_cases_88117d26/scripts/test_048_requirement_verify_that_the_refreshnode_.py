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
Test Case:     TC-CSA-REFRESHNODE-0003
Requirement:   CSA-REFRESHNODE-REQ-003

Verify that the RefreshNode command fails with a NOT_FOUND status code
if a Node Information Entry does not exist for the given NodeID.
"""

from mobly import asserts
import pytest
import logging

import matter.clusters as Clusters
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

# Cluster and command/attribute constants; update as needed for your specific SDK/environment
JFDA_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
JFDA_ENDPOINT = 1  # Common default for the JFDA cluster
REFRESHNODE_COMMAND = getattr(JFDA_CLUSTER.Commands, "RefreshNode", None) if JFDA_CLUSTER else None
NODE_ENTRY_ATTR = getattr(JFDA_CLUSTER.Attributes, "NodeEntries", None) if JFDA_CLUSTER else None

class TC_CSA_REFRESHNODE_0003(MatterBaseTest):
    """
    Test that RefreshNode returns NOT_FOUND when targeting a NodeID that does not exist in JFDA NodeEntries.
    """

    async def get_node_entry(self, dev_ctrl, datastore_node_id, endpoint, node_id):
        """Return node entry from NodeEntries attribute for node_id, or None if absent."""
        if NODE_ENTRY_ATTR is None:
            pytest.skip("NodeEntries attribute not found in JFDA cluster objects")
        
        node_entries_resp = await dev_ctrl.ReadAttribute(
            nodeId=datastore_node_id,
            attributes=[(endpoint, JFDA_CLUSTER, NODE_ENTRY_ATTR)],
        )
        entries = node_entries_resp[endpoint][JFDA_CLUSTER][NODE_ENTRY_ATTR]
        for entry in entries:
            nid = getattr(entry, "nodeId", entry.get("nodeId", None))
            if nid == node_id:
                return entry
        return None

    @async_test_body
    async def test_refreshnode_not_found_for_missing_node_entry(self):
        # ---- Retrieve testbench/fixture parameters ----
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        datastore_node_id = getattr(self, "datastore_node_id", self.dut_node_id)  # JFDA node ID (e.g., anchor/administrator)
        jfda_ep = getattr(self, "jfda_endpoint", JFDA_ENDPOINT)
        # TEST_NODE_IDS must be absent from NodeEntries
        TEST_NODE_IDS = getattr(self, "missing_node_ids", [0xBADC0DE, 0xDEFACED])  # Supply via infra if possible

        asserts.assert_is_not_none(JFDA_CLUSTER, "JFDA cluster not found in SDK.")
        asserts.assert_is_not_none(REFRESHNODE_COMMAND, "RefreshNode command not found in JFDA cluster.")
        asserts.assert_true(len(TEST_NODE_IDS) > 0, "At least one absent NodeID must be set for this test.")

        # Step 1: Confirm NodeIDs not present in NodeEntries
        self.print_step(1, "Query Joint Fabric Datastore for missing NodeIDs before testing RefreshNode.")
        for node_id in TEST_NODE_IDS:
            entry = await self.get_node_entry(admin_ctrl, datastore_node_id, jfda_ep, node_id)
            asserts.assert_is_none(entry, f"Precondition failed: NodeID {hex(node_id)} unexpectedly present in NodeEntries.")

        # Step 2: Issue RefreshNode command for each non-existent NodeID
        for node_id in TEST_NODE_IDS:
            self.print_step(2, f"Issuing RefreshNode command for missing NodeID {hex(node_id)}.")

            not_found_error = False
            try:
                await admin_ctrl.SendCommand(
                    nodeId=datastore_node_id,
                    endpoint=jfda_ep,
                    command=REFRESHNODE_COMMAND(nodeId=node_id)
                )
            except InteractionModelError as e:
                not_found_error = (e.status == Status.NotFound or str(e.status).upper() == "NOT_FOUND")
                asserts.assert_true(not_found_error, f"Expected NOT_FOUND status for missing NodeID {hex(node_id)}, got {e.status}.")
                log.info(f"RefreshNode({hex(node_id)}) returned NOT_FOUND as expected.")
            except Exception as e:
                asserts.fail(f"Unexpected exception for missing NodeID {hex(node_id)}: {e}")
            else:
                asserts.fail(f"RefreshNode unexpectedly succeeded for missing NodeID {hex(node_id)}; should fail with NOT_FOUND.")

        # Step 3: Optionally verify Datastore unchanged, no entries were created/removed.
        self.print_step(3, "Verify Datastore unchanged, no Node Information Entry created or deleted.")
        current_entries_resp = await admin_ctrl.ReadAttribute(
            nodeId=datastore_node_id,
            attributes=[(jfda_ep, JFDA_CLUSTER, NODE_ENTRY_ATTR)],
        )
        entry_ids = [
            getattr(e, "nodeId", e.get("nodeId", None))
            for e in current_entries_resp[jfda_ep][JFDA_CLUSTER][NODE_ENTRY_ATTR]
        ]
        for node_id in TEST_NODE_IDS:
            asserts.assert_not_in(node_id, entry_ids, f"Missing NodeID {hex(node_id)} should stay absent in NodeEntries post-RefreshNode.")

        self.print_step(4, "Test complete: RefreshNode for missing NodeIDs properly returns NOT_FOUND and makes no changes.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Usage/Integration Notes:**
- Save this script as `tests/test_TC_CSA_REFRESHNODE_0003.py`.
- This script expects your testbed/infra to provide (or allows you to override at runtime):
  - `self.jfda_admin_controller`: The admin controller object/session for the JFDA cluster.
  - `self.datastore_node_id`: The JFDA server node ID.
  - `self.jfda_endpoint`: The endpoint for the JFDA cluster (default 1).
  - `self.missing_node_ids`: List of NodeIDs not present in JFDA; if not provided, uses default dummy values.
- The script verifies that the RefreshNode command fails with `NOT_FOUND` for each specified non-existent NodeID, as per the spec.
- All step-to-code mapping, assertion, and logging are in line with your project's idioms for API/pytesting Matter tests.
- No changes are made to the Datastore and system state remains ready for further testing.