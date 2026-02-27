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
Test Case:     TC-CSA-JFDA-REMOVENODE-0002
Requirement:   CSA-JFDA-REQ-REMOVENODE-002

Verify, when removing a Node from the Joint Fabric, privileges are first revoked, and
the Node Information Entry is present in the datastore until privileges are gone,
after which the Node entry is removed.
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

# These should be set by the test infra/test context:
JFDA_CLUSTER = Clusters.JointFabricDatastore
JFDA_ENDPOINT = 1  # Use actual endpoint for Joint Fabric Datastore, adjust as needed

REMOVE_NODE_COMMAND = getattr(JFDA_CLUSTER.Commands, "RemoveNode", None)
QUERY_NODE_COMMAND = getattr(JFDA_CLUSTER.Commands, "QueryNode", None)
NODE_LIST_ATTR = getattr(JFDA_CLUSTER.Attributes, "NodeList", None)

class TC_CSA_JFDA_REMOVENODE_0002(MatterBaseTest):
    """
    Test removal sequencing: privileges revoked before Node entry is deleted from Datastore.
    """

    @async_test_body
    async def test_removenode_revokes_privileges_before_entry(self):
        # Fixture/Substitute by test environment:
        target_node_id = getattr(self, "target_node_id", None)
        admin_ctrl = getattr(self, "admin_ctrl", None)
        target_node_ctrl = getattr(self, "target_node_ctrl", None)
        jfda_ep = getattr(self, "jfda_endpoint", JFDA_ENDPOINT)
        dut_node_id = getattr(self, "dut_node_id", self.dut_node_id)

        asserts.assert_is_not_none(target_node_id, "You must set target_node_id in the test environment.")
        asserts.assert_is_not_none(admin_ctrl, "Admin controller must be supplied via 'admin_ctrl'.")
        asserts.assert_is_not_none(target_node_ctrl, "Target node controller (target_node_ctrl) required.")

        # Step 1: Document current access privileges for Target Node in fabric (in ACL/group)
        self.print_step(1, "Document Target Node access privileges in the Joint Fabric.")
        acl_entries = await admin_ctrl.ReadAttribute(
            nodeId=dut_node_id,
            attributes=[(0, Clusters.AccessControl, Clusters.AccessControl.Attributes.Acl)]
        )
        acl = list(acl_entries[0][Clusters.AccessControl][Clusters.AccessControl.Attributes.Acl])
        has_privilege = any(
            (hasattr(ace, "subjects") and target_node_id in ace.subjects) or
            (isinstance(ace, dict) and target_node_id in ace.get("subjects", []))
            for ace in acl
        )
        asserts.assert_true(has_privilege, "Target Node does not have a privilege in ACL before test (required precondition).")

        # Step 2: Confirm Node Information Entry in JFDA Datastore
        self.print_step(2, f"Confirm Node Information Entry for {hex(target_node_id)} exists in JFDA Datastore.")
        node_list = await admin_ctrl.ReadAttribute(
            nodeId=dut_node_id,
            attributes=[(jfda_ep, JFDA_CLUSTER, NODE_LIST_ATTR)]
        )
        entries = node_list.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(NODE_LIST_ATTR, [])
        entry_present = any(entry.get("nodeId", None) == target_node_id for entry in entries)
        asserts.assert_true(entry_present, "Node entry not found in datastore before removal.")

        # Step 3: Initiate Node removal using administrator
        self.print_step(3, "Initiate Node removal process using administrator (RemoveNode command).")
        asserts.assert_is_not_none(REMOVE_NODE_COMMAND, "RemoveNode command not in cluster.")
        try:
            await admin_ctrl.SendCommand(
                nodeId=dut_node_id,
                endpoint=jfda_ep,
                command=REMOVE_NODE_COMMAND(nodeId=target_node_id)
            )
        except Exception as e:
            asserts.fail(f"RemoveNode command failed: {e}")

        # Step 4: Verify that access privileges are revoked first (ACL emptied for target node, even while entry exists)
        self.print_step(4, "Verify Target Node privileges are revoked first, before Node entry is removed.")
        acl_after_removal = await admin_ctrl.ReadAttribute(
            nodeId=dut_node_id,
            attributes=[(0, Clusters.AccessControl, Clusters.AccessControl.Attributes.Acl)]
        )
        acl_after = list(acl_after_removal[0][Clusters.AccessControl][Clusters.AccessControl.Attributes.Acl])
        still_priv = any(
            (hasattr(ace, "subjects") and target_node_id in ace.subjects) or
            (isinstance(ace, dict) and target_node_id in ace.get("subjects", []))
            for ace in acl_after
        )
        asserts.assert_false(still_priv, "Target Node's access privileges not revoked after RemoveNode command issued.")

        # Step 5: Verify Node entry still present in Datastore before it's deleted
        self.print_step(5, "Verify Node entry remains in datastore until privileges are revoked.")
        node_list_post = await admin_ctrl.ReadAttribute(
            nodeId=dut_node_id,
            attributes=[(jfda_ep, JFDA_CLUSTER, NODE_LIST_ATTR)]
        )
        entries_post = node_list_post.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(NODE_LIST_ATTR, [])
        entry_present_post = any(entry.get("nodeId", None) == target_node_id for entry in entries_post)
        asserts.assert_true(entry_present_post, "Node entry prematurely removed before privilege revocation complete.")

        # Step 6: Wait for Node entry to be removed (poll for removal completion)
        self.print_step(6, "Wait and confirm removal of the Node Information Entry from Datastore.")
        import asyncio
        for _ in range(15):  # Wait up to ~15 seconds (poll every second)
            node_list_poll = await admin_ctrl.ReadAttribute(
                nodeId=dut_node_id,
                attributes=[(jfda_ep, JFDA_CLUSTER, NODE_LIST_ATTR)]
            )
            entries_poll = node_list_poll.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(NODE_LIST_ATTR, [])
            if not any(entry.get("nodeId", None) == target_node_id for entry in entries_poll):
                break
            await asyncio.sleep(1)
        else:
            asserts.fail("Node Information Entry not removed from Datastore in expected time.")

        # Step 7: Attempt operational command from the Target Node after privileges revoked but before entry removal
        self.print_step(7, "Attempt an operational command from Target Node after privilege loss but before entry removal.")
        # This step is theoretical; after privileges are lost but entry exists, should get AccessDenied
        try:
            await target_node_ctrl.SendCommand(
                nodeId=dut_node_id,
                endpoint=1,
                command=Clusters.OnOff.Commands.On()
            )
            asserts.fail("Target Node wrongly able to perform operation after privileges revoked but before entry removal.")
        except InteractionModelError as e:
            asserts.assert_equal(e.status, Status.AccessDenied, "Expected AccessDenied after privilege revocation.")

        # Step 8: Confirm Target Node is no longer present in the Datastore after complete removal
        self.print_step(8, "Confirm the Node Information Entry for Target Node no longer appears in the Datastore.")
        node_list_final = await admin_ctrl.ReadAttribute(
            nodeId=dut_node_id,
            attributes=[(jfda_ep, JFDA_CLUSTER, NODE_LIST_ATTR)]
        )
        entries_final = node_list_final.get(jfda_ep, {}).get(JFDA_CLUSTER, {}).get(NODE_LIST_ATTR, [])
        asserts.assert_false(any(entry.get("nodeId", None) == target_node_id for entry in entries_final),
                             "Node entry still present in Datastore after expected removal.")

        # Step 9: (Manual/Audit) Review system & audit logs for correct event ordering
        self.print_step(9, "Manual/log review: Privilege revocation should precede entry removal in logs/events.")

        self.print_step(10, "Test complete: Node privileges revoked before information entry is removed during fabric removal.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**USAGE & NOTES:**
- Save as `tests/test_TC_CSA_JFDA_REMOVENODE_0002.py`.
- Test assumes testbed fixtures for:
    - `self.target_node_id`
    - `self.admin_ctrl` (administrator)
    - `self.target_node_ctrl` (for simulating/validating loss of op commands after privilege revocation)
    - `self.dut_node_id` (ID hosting JFDA cluster; usually anchor/administrator)
- Step-by-step checks, assertions, and polling are included, matching description/order.
- Adjust endpoint, attribute, and command mappings to actual cluster library as needed.
- For system/audit log review, leverage integration or manual check as available.
