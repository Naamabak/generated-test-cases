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
Test Case:     TC-CSA-UPDATEENDPOINT-NOTFOUND-0001
Requirement:   CSA-UPDATEENDPOINT-REQ-NOTFOUND-001

Verify that UpdateEndpointForNode fails with NOT_FOUND if an Endpoint Information Entry
does not exist for the given NodeID and EndpointID.
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

# These must be overridden/provided via the test harness/environment:
# - self.jfda_admin_controller      : Admin controller/session for JFDA
# - self.jfda_endpoint              : JFDA endpoint (default 1)
# - self.datastore_node_id          : NodeID of the JFDA/Joint Fabric Datastore server
# - self.existing_node_id           : NodeID present in the JFDA system
# - self.nonexistent_endpoint_ids   : List of EndpointIDs *NOT PRESENT* for the node (e.g. [101, 102])

JFDA_CLUSTER = getattr(Clusters, "JointFabricDatastore", None)
JFDA_ENDPOINT = 1  # Default, override as needed
UPDATE_ENDPOINT_CMD = getattr(JFDA_CLUSTER.Commands, "UpdateEndpointForNode", None) if JFDA_CLUSTER else None
ENDPOINT_ENTRY_ATTR = getattr(JFDA_CLUSTER.Attributes, "EndpointEntries", None) if JFDA_CLUSTER else None

class TC_CSA_UPDATEENDPOINT_NOTFOUND_0001(MatterBaseTest):
    """
    Test UpdateEndpointForNode returns NOT_FOUND if Endpoint Information Entry does not exist for NodeID/EndpointID.
    """

    async def get_endpoint_entries(self, dev_ctrl, ds_node_id, node_id):
        """
        Query all EndpointEntries for the given NodeID in the Datastore.
        Returns a list of entries (or empty list, if none).
        """
        asserts.assert_is_not_none(ENDPOINT_ENTRY_ATTR, "EndpointEntries attribute not available in JFDA cluster.")
        resp = await dev_ctrl.ReadAttribute(
            nodeId=ds_node_id,
            attributes=[(JFDA_ENDPOINT, JFDA_CLUSTER, ENDPOINT_ENTRY_ATTR)]
        )
        endpoint_entries = resp[JFDA_ENDPOINT][JFDA_CLUSTER][ENDPOINT_ENTRY_ATTR]
        # Each entry should be for a specific NodeID and EndpointID; filter for NodeID just in case.
        return [e for e in endpoint_entries if getattr(e, "nodeId", e.get("nodeId", None)) == node_id]

    def get_entry_endpoint_ids(self, entries):
        """Extracts EndpointIDs from EndpointEntries."""
        return [getattr(e, "endpointId", e.get("endpointId", None)) for e in entries]

    @async_test_body
    async def test_update_endpoint_for_node_not_found(self):
        # --- Setup/Fixture references (override via testbed/run args as needed)
        admin_ctrl = getattr(self, "jfda_admin_controller", self.default_controller)
        ds_node_id = getattr(self, "datastore_node_id", self.dut_node_id)
        jfda_ep = getattr(self, "jfda_endpoint", JFDA_ENDPOINT)
        existing_node_id = getattr(self, "existing_node_id", None)
        nonexistent_endpoint_ids = getattr(self, "nonexistent_endpoint_ids", [101, 102])

        asserts.assert_is_not_none(admin_ctrl, "Admin controller required (jfda_admin_controller).")
        asserts.assert_is_not_none(JFDA_CLUSTER, "JointFabricDatastore cluster not found in current SDK.")
        asserts.assert_is_not_none(UPDATE_ENDPOINT_CMD, "UpdateEndpointForNode command not found on JFDA cluster.")
        asserts.assert_is_not_none(existing_node_id, "Must set existing_node_id (known NodeID for the test).")
        asserts.assert_true(len(nonexistent_endpoint_ids) > 0, "Must provide at least one nonexistent EndpointID.")

        # --- Step 1: Query EndpointEntries for NodeID and confirm EndpointID to be tested does NOT exist
        self.print_step(1, f"Check EndpointEntries for NodeID {hex(existing_node_id)} -- must not include test EndpointIDs.")
        endpoint_entries = await self.get_endpoint_entries(admin_ctrl, ds_node_id, existing_node_id)
        endpointids_existing = self.get_entry_endpoint_ids(endpoint_entries)
        # Check all test (nonexistent) EndpointIDs
        for ep_id in nonexistent_endpoint_ids:
            asserts.assert_not_in(ep_id, endpointids_existing,
                                  f"EndpointID {ep_id} unexpectedly present in EndpointEntries for NodeID {hex(existing_node_id)}!")

        # --- Steps 2-3: Attempt UpdateEndpointForNode for each missing EndpointID, expect NOT_FOUND
        for idx, ep_id in enumerate(nonexistent_endpoint_ids):
            self.print_step(2, f"Issue UpdateEndpointForNode (NodeID={hex(existing_node_id)}, EndpointID={ep_id}); expect NOT_FOUND.")
            got_not_found = False
            try:
                # Dummy update payload -- fill fields as needed by your cluster definition
                await admin_ctrl.SendCommand(
                    nodeId=ds_node_id,
                    endpoint=jfda_ep,
                    command=UPDATE_ENDPOINT_CMD(
                        nodeId=existing_node_id,
                        endpointId=ep_id,
                        # Provide minimal dummy update data; adjust fields if needed
                        friendlyName=f"Test-EP{ep_id}"
                    )
                )
            except InteractionModelError as e:
                got_not_found = (e.status == Status.NotFound or str(e.status).upper() == "NOT_FOUND")
                asserts.assert_true(
                    got_not_found, f"Expected NOT_FOUND, got {e.status} for NodeID={hex(existing_node_id)} EndpointID={ep_id}"
                )
            except Exception as e:
                asserts.fail(f"Unexpected exception issuing UpdateEndpointForNode: {e}")
            else:
                asserts.fail(f"UpdateEndpointForNode unexpectedly succeeded for missing EndpointID {ep_id}; should fail.")

            # --- Step 3/4: Optionally repeat for another NodeID (not present in Datastore)
            # Optionally, can use another_node_id if supported in your environment

        # --- Step 4: Confirm EndpointEntries for NodeID remain unchanged; no new Endpoint was created
        self.print_step(3, "Verify the Datastore's EndpointEntries remain unchanged for tested NodeID.")
        endpoint_entries_after = await self.get_endpoint_entries(admin_ctrl, ds_node_id, existing_node_id)
        endpointids_after = self.get_entry_endpoint_ids(endpoint_entries_after)
        for ep_id in nonexistent_endpoint_ids:
            asserts.assert_not_in(ep_id, endpointids_after,
                                  f"UpdateEndpointForNode for EndpointID {ep_id} (non-existent) should not add an entry!")

        self.print_step(4, "All failures correctly issued NOT_FOUND; Datastore state is unchanged; test complete.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**Instructions:**
- Save as `tests/test_TC_CSA_UPDATEENDPOINT_NOTFOUND_0001.py`.
- Provide appropriate values for `existing_node_id` and `nonexistent_endpoint_ids` in your testbed/environment.
- Adjust attribute/command names as needed for your JFDA cluster definition.
- Script uses step-by-step print annotations and strong assertions, matching your project conventions.
- No state change is tolerated; only NOT_FOUND status is accepted for the tested negative cases.