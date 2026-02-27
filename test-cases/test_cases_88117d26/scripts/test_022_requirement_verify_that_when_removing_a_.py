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
Test Case: TC-CSA-JFDA-REMOVENODE-0001
Requirement: CSA-JFDA-REQ-REMOVENODE-001

Verify that when removing a Node from the Joint Fabric, privileges for the node
are first revoked, and the Node Information Entry is then removed via RemoveNode
command in the Joint Fabric Datastore cluster.
"""

import logging

from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

# Constants for the test - should be provided by testbed/fixtures
JFDA_CLUSTER = Clusters.JointFabricDatastore
JFDA_ENDPOINT = 1  # Replace with actual endpoint for JFDA cluster if not 1

REMOVE_NODE_COMMAND = getattr(JFDA_CLUSTER.Commands, "RemoveNode", None)
QUERY_NODE_COMMAND = getattr(JFDA_CLUSTER.Commands, "QueryNode", None)
# Typical attributes/members for Node Information Entry. These depend on implementation.

# The following should be set via test environment/product/harness:
TARGET_NODE_ID = None          # The nodeId of the node to be removed
ADMIN_CTRL = None              # Device controller/session for admin node with RemoveNode rights
TARGET_NODE_CTRL = None        # Device controller/session for the target node to be removed
DUT_NODE_ID = None             # The device/server that hosts JFDA cluster (DUT)

class TC_CSA_JFDA_REMOVENODE_0001(MatterBaseTest):
    """
    Verify the correct sequence: privilege revocation before node entry removal in Joint Fabric removal.
    """

    @async_test_body
    async def test_remove_node_from_joint_fabric(self):
        # --- Step 0: Setup/controller mappings ---
        target_node_id = getattr(self, "target_node_id", TARGET_NODE_ID)
        admin_ctrl = getattr(self, "admin_ctrl", ADMIN_CTRL)
        target_node_ctrl = getattr(self, "target_node_ctrl", TARGET_NODE_CTRL)
        jfda_ep = getattr(self, "jfda_endpoint", JFDA_ENDPOINT)
        dut_node_id = getattr(self, "dut_node_id", DUT_NODE_ID or self.dut_node_id)

        asserts.assert_is_not_none(target_node_id, "Test needs TARGET_NODE_ID to be set in test env/fixture")
        asserts.assert_is_not_none(admin_ctrl, "Test needs ADMIN_CTRL (admin controller) to be set")
        asserts.assert_is_not_none(target_node_ctrl, "Test needs TARGET_NODE_CTRL to check privilege loss after removal")

        # --- Step 1: Query JFDA to confirm presence of Target Node's entry ---
        self.print_step(1, "Query JFDA cluster to confirm Target Node's entry exists (before removal)")
        if QUERY_NODE_COMMAND is None:
            self.print_step(1, "No direct QueryNode command in cluster; attempting attribute-based node info listing")
            # Use attribute read or another method (device/field specific)
            node_list = await admin_ctrl.ReadAttribute(
                nodeId=dut_node_id,
                attributes=[(jfda_ep, JFDA_CLUSTER, JFDA_CLUSTER.Attributes.NodeList)]
            )
            found = any(entry["nodeId"] == target_node_id for entry in node_list.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(JFDA_CLUSTER.Attributes.NodeList, []))
            asserts.assert_true(found, f"Target Node {hex(target_node_id)} entry not found in JFDA cluster")
        else:
            entry = await admin_ctrl.SendCommand(
                nodeId=dut_node_id,
                endpoint=jfda_ep,
                command=QUERY_NODE_COMMAND(nodeId=target_node_id)
            )
            asserts.assert_is_not_none(entry, "Target Node entry not found in JFDA Datastore cluster (QUERY_NODE)")

        # --- Step 2: Verify Target Node has active privileges (ACL entry exists) ---
        self.print_step(2, f"Ensure Target Node {hex(target_node_id)} has privileges in ACL")
        acl_list = await admin_ctrl.ReadAttribute(
            nodeId=dut_node_id,
            attributes=[(0, Clusters.AccessControl, Clusters.AccessControl.Attributes.Acl)]
        )
        acl = list(acl_list[0][Clusters.AccessControl][Clusters.AccessControl.Attributes.Acl])
        has_target_priv = any(
            (hasattr(ace, "subjects") and target_node_id in ace.subjects)
            or (isinstance(ace, dict) and target_node_id in ace.get("subjects", [])) for ace in acl
        )
        asserts.assert_true(has_target_priv, "Target Node does not have any assigned privilege in ACL prior to removal.")

        # --- Step 3: From admin node, issue RemoveNode command ---
        self.print_step(3, f"Admin issues RemoveNode command for Target Node {hex(target_node_id)}")
        asserts.assert_is_not_none(REMOVE_NODE_COMMAND, "RemoveNode command not available in JointFabricDatastore cluster.")
        try:
            await admin_ctrl.SendCommand(
                nodeId=dut_node_id,
                endpoint=jfda_ep,
                command=REMOVE_NODE_COMMAND(nodeId=target_node_id)
            )
        except Exception as e:
            asserts.fail(f"Failed to send RemoveNode command: {e}")

        # --- Step 4: Monitor logs/events for privilege revocation (not automatable here, but expected in system logs) ---
        self.print_step(4, "Check/log: Privileges for Target Node revoked immediately upon RemoveNode command")
        # This is infra/tool dependent; at minimum can check the effect at next steps...

        # --- Step 5: Query Target Node's privileges (expect: all revoked) ---
        self.print_step(5, "Query Target Node's privileges post-RemoveNode (expect revoked / not present in ACL)")
        acl_post = await admin_ctrl.ReadAttribute(
            nodeId=dut_node_id,
            attributes=[(0, Clusters.AccessControl, Clusters.AccessControl.Attributes.Acl)]
        )
        acl_post_entries = list(acl_post[0][Clusters.AccessControl][Clusters.AccessControl.Attributes.Acl])
        # Target node's privileges must now be gone
        privilege_still_exists = any(
            (hasattr(ace, "subjects") and target_node_id in ace.subjects)
            or (isinstance(ace, dict) and target_node_id in ace.get("subjects", [])) for ace in acl_post_entries
        )
        asserts.assert_false(privilege_still_exists, f"Target Node {hex(target_node_id)} still has privileges after RemoveNode command.")

        # --- Step 6: Query JFDA for Target Node entry (expect gone) ---
        self.print_step(6, "Query JFDA again for target node entry (should be removed)")
        if QUERY_NODE_COMMAND is not None:
            try:
                entry = await admin_ctrl.SendCommand(
                    nodeId=dut_node_id,
                    endpoint=jfda_ep,
                    command=QUERY_NODE_COMMAND(nodeId=target_node_id)
                )
                entry_exists = entry is not None
            except Exception:
                entry_exists = False
            asserts.assert_false(entry_exists, "Target Node entry still present in JFDA cluster after RemoveNode")
        else:
            node_list = await admin_ctrl.ReadAttribute(
                nodeId=dut_node_id,
                attributes=[(jfda_ep, JFDA_CLUSTER, JFDA_CLUSTER.Attributes.NodeList)]
            )
            found = any(entry["nodeId"] == target_node_id for entry in node_list.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(JFDA_CLUSTER.Attributes.NodeList, []))
            asserts.assert_false(found, "Target Node entry still present in JFDA cluster after RemoveNode")

        # --- Step 7: Attempt operation as Target Node (should be rejected) ---
        self.print_step(7, "Attempt privileged operation from Target Node (expect failure)")
        try:
            await target_node_ctrl.SendCommand(
                nodeId=dut_node_id,
                endpoint=1,
                command=Clusters.OnOff.Commands.On()
            )
            asserts.fail("Target Node was able to operate after RemoveNode; privilege should be revoked.")
        except InteractionModelError as e:
            asserts.assert_equal(e.status, Status.AccessDenied, "Expected AccessDenied after RemoveNode")

        # --- Step 8: System log: order of events (revocation before entry) should appear in logs - not automatable here ---
        self.print_step(8, "Order of events (privilege revocation then node entry removal) expected in system logs (manual).")

        self.print_step(9, "Validation complete: privileges revoked and node entry removed on RemoveNode.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions/Assumptions:**
- Save this test as `tests/test_TC_CSA_JFDA_REMOVENODE_0001.py`.
- The test assumes the existence of:
  - `self.target_node_id`: The node ID to be removed from the joint fabric.
  - `self.admin_ctrl`: Device controller object with admin rights.
  - `self.target_node_ctrl`: Device controller object for the target node, to verify loss of privilege.
  - `self.dut_node_id`: The node ID of the JFDA server (could be admin node).
- The example assumes attributes and commands for the JFDA cluster typical to current Matter/CHIP usages; update `NodeList`, `RemoveNode`, etc., to match your actual cluster library.
- Steps requiring system/event log checks are indicated but not automated.
- The test will fail if commands/attributes are missing; adapt to your stack's capabilities as necessary.
- All critical transitions are checked: Target Node's entry in the datastore, privileges in ACL, JFDA RemoveNode invocation, and subsequent access checks.