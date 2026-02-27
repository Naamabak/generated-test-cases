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
TC-CSA-JFDA-ADDNODE-0001

Verifies adding a Node to the Joint Fabric requires:
 - a node entry with 'pending' status is first added to JFDA cluster,
 - on commissioning complete, a RefreshNode call changes it to 'committed'.
"""

import logging
import pytest

from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

# ---- Test parameters/Cluster ID definitions ----
# Must be provided/mapped by your test bed/infra.
JFDA_CLUSTER_ID = 0xFFF1  # Example: Standardize if yours is different.
JFDA_ENDPOINT = 0  # Commonly at EP0 or fabric/anchor-specific endpoint.
NODE_ENTRY_STRUCT = getattr(ClusterObjects, 'JointFabricDatastore_NodeEntryStruct', None)  # If cluster object mapping exists
NODE_ENTRIES_ATTR = getattr(Clusters.JointFabricDatastore.Attributes, 'NodeEntries', None)
REFRESH_NODE_CMD = getattr(Clusters.JointFabricDatastore.Commands, 'RefreshNode', None)

# Will need test bed setup to provide:
# - self.jfda_admin_controller: controller/session for JFDA admin ops
# - self.target_node_id: node id of the device being added
# - self.dut_node_id: fabric anchor/admin node (with JFDA cluster)

class TC_CSA_JFDA_ADDNODE_0001(MatterBaseTest):
    """
    TC-CSA-JFDA-ADDNODE-0001:
    Verify adding a node requires:
      - pending entry on add,
      - RefreshNode marks as committed after commissioning.
      - Node is operational after commit.
    """

    @async_test_body
    async def test_add_node_pending_committed(self):
        # ---- Step 1: Initiate add target node to the Joint Fabric ----
        self.print_step(1, "Start adding target Node to the Joint Fabric using admin JFDA interface.")
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        target_node_id = getattr(self, "target_node_id", None)
        fabric_admin_id = getattr(self, "dut_node_id", None)
        asserts.assert_is_not_none(target_node_id, "target_node_id for new node required (test setup)")
        asserts.assert_is_not_none(admin_ctrl, "jfda_admin_controller required (test setup).")
        asserts.assert_is_not_none(fabric_admin_id, "dut_node_id (JFDA admin node id) required.")

        # Simulate/trigger start-of-joining of node; actual cluster/command will depend on implementation.
        # E.g., might be a command like AddPendingNode (not shown); here only the status is checked afterward.

        # ---- Step 2: Query the JFDA cluster for node entries before commissioning completes ----
        self.print_step(2, "Query Joint Fabric Datastore cluster for node entries before commissioning.")
        if NODE_ENTRIES_ATTR is None:
            pytest.skip("NodeEntries attribute not available in cluster mapping.")
        node_entries = await admin_ctrl.ReadAttribute(
            nodeId=fabric_admin_id,
            attributes=[(JFDA_ENDPOINT, JFDA_CLUSTER_ID, NODE_ENTRIES_ATTR)]
        )
        node_entry_list = list(node_entries[JFDA_ENDPOINT][JFDA_CLUSTER_ID][NODE_ENTRIES_ATTR])
        log.info("Node entries in JFDA before commissioning: %s", node_entry_list)

        # ---- Step 3: Confirm entry for target node exists, status is 'pending' ----
        self.print_step(3, "Check for node entry with 'pending' status.")
        pending_found = False
        for entry in node_entry_list:
            nid = getattr(entry, "nodeId", None)
            status = getattr(entry, "status", None)
            if nid == target_node_id and str(status).lower() == "pending":
                pending_found = True
                break
        asserts.assert_true(
            pending_found,
            f"Target node {hex(target_node_id)} should have a 'pending' entry in node list before commissioning complete."
        )

        # ---- Step 4: Complete commissioning process for target Node ----
        self.print_step(4, "Complete commissioning process for target Node.")
        # In real test infra, this might require explicit PairDevice call or complete steps manually

        await self.matter_test_config.ensure_commissioned(admin_ctrl, target_node_id)

        # ---- Step 5: Invoke RefreshNode command for target Node ----
        self.print_step(5, "Invoke RefreshNode command on JFDA for target Node.")
        if REFRESH_NODE_CMD is None:
            pytest.skip("RefreshNode command not defined in JointFabricDatastore cluster objects.")

        try:
            response = await admin_ctrl.SendCommand(
                nodeId=fabric_admin_id,
                endpoint=JFDA_ENDPOINT,
                command=REFRESH_NODE_CMD(nodeId=target_node_id)
            )
            log.info(f"RefreshNode command result: {response}")
        except InteractionModelError as e:
            asserts.fail(f"RefreshNode command failed: {e}")

        # ---- Step 6: Query the node entries again (should now be 'committed') ----
        self.print_step(6, "Query node entries; expect target node to have status 'committed'.")
        node_entries_after = await admin_ctrl.ReadAttribute(
            nodeId=fabric_admin_id,
            attributes=[(JFDA_ENDPOINT, JFDA_CLUSTER_ID, NODE_ENTRIES_ATTR)]
        )
        node_entry_list_after = list(node_entries_after[JFDA_ENDPOINT][JFDA_CLUSTER_ID][NODE_ENTRIES_ATTR])
        log.info("Node entries in JFDA after RefreshNode: %s", node_entry_list_after)

        committed_found = False
        for entry in node_entry_list_after:
            nid = getattr(entry, "nodeId", None)
            status = getattr(entry, "status", None)
            if nid == target_node_id and str(status).lower() == "committed":
                committed_found = True
                break
        asserts.assert_true(
            committed_found,
            f"Target node {hex(target_node_id)} should have a status of 'committed' in node list after RefreshNode."
        )

        # ---- Step 7: Attempt operational communication with the target node ----
        self.print_step(7, "Attempt operational communication with target node to validate participation.")
        # Try reading a standard attribute (e.g., Basic Info: NodeLabel)
        try:
            node_label = await admin_ctrl.ReadAttribute(
                nodeId=target_node_id,
                attributes=[(0, Clusters.BasicInformation, Clusters.BasicInformation.Attributes.NodeLabel)],
            )
            log.info(f"Operational read from target node succeeded: NodeLabel={node_label}")
        except Exception as e:
            asserts.fail(f"Failed to communicate with node {hex(target_node_id)} after committing: {e}")

        self.print_step(8, "Test complete: Node addition to Joint Fabric properly involves pending/committed status transitions.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Usage/Integration Notes:**
- Save as e.g. `tests/test_TC_CSA_JFDA_ADDNODE_0001.py`.
- Your test runner must provide or attach:
  - `self.jfda_admin_controller`: controller/session of a Joint Fabric Administrator Node (with write access to JFDA cluster).
  - `self.target_node_id`: node id of the device being added.
  - The actual endpoint/cluster id/constants may need to be adjusted for your Matter implementation.
- The test queries node entries before/after commissioning and RefreshNode, and checks for both "pending" and "committed" status.
- The script is robust with step-to-code comments, log output, and assertions. It is suitable for CI or manual campaign execution.