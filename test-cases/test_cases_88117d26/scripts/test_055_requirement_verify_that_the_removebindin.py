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
Test Case:     TC-CSA-REMOVEBINDING-NOTFOUND-0001
Requirement:   CSA-REMOVEBINDING-REQ-NOTFOUND-001

Verify RemoveBindingFromEndpointForNode fails with NOT_FOUND if no Endpoint Information Entry exists for the NodeID+EndpointID.
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

# TEST CONFIGURATION -- override in testbench/harness as needed
BINDING_CLUSTER = Clusters.Binding
REMOVE_BINDING_CMD = getattr(BINDING_CLUSTER.Commands, "RemoveBindingFromEndpointForNode", None)
ENDPOINT_INFO_ENTRY_ATTR = getattr(BINDING_CLUSTER.Attributes, "Binding", None)

class TC_CSA_REMOVEBINDING_NOTFOUND_0001(MatterBaseTest):
    """
    Test RemoveBindingFromEndpointForNode fails with NOT_FOUND if Endpoint Information Entry does not exist.
    """

    async def get_endpoint_entries(self, dev_ctrl, node_id, endpoint):
        """
        Returns True if a Binding entry exists for (node_id, endpoint), False otherwise.
        For this test, we expect no entry to be present.
        """
        if ENDPOINT_INFO_ENTRY_ATTR is None:
            pytest.skip("Binding cluster does not expose Binding attribute for info entry query.")

        result = await dev_ctrl.ReadAttribute(
            nodeId=node_id,
            attributes=[(endpoint, BINDING_CLUSTER, ENDPOINT_INFO_ENTRY_ATTR)]
        )
        entries = result.get(endpoint, {}).get(BINDING_CLUSTER, {}).get(ENDPOINT_INFO_ENTRY_ATTR, [])
        # Each binding entry struct should have a 'node', 'endpoint', and possibly other fields
        found = False
        for entry in entries:
            n_id = getattr(entry, "node", entry.get("node", None))
            ep_id = getattr(entry, "endpoint", entry.get("endpoint", None))
            # Both must match exactly
            if n_id == node_id and ep_id == endpoint:
                found = True
        return found

    @async_test_body
    async def test_removebinding_notfound_for_missing_endpoint_entry(self):
        # Set from fixture/env
        dev_ctrl = getattr(self, "binding_controller", self.default_controller)
        dut_node_id = getattr(self, "dut_node_id", self.dut_node_id)
        # Set (NodeID, EndpointID) pairs that are NOT present in Endpoint Info Entry
        TEST_CASES = getattr(self, "notfound_binding_cases", [
            (0xDABBADF, 2),
            (0xFADE123, 3)
        ])

        asserts.assert_is_not_none(REMOVE_BINDING_CMD, "RemoveBindingFromEndpointForNode command is not implemented in Binding cluster.")

        for idx, (target_node_id, target_endpoint_id) in enumerate(TEST_CASES):
            # Step 1: Confirm that no Endpoint Information Entry exists for this (NodeID, EndpointID)
            self.print_step(1, f"Check that Binding entry for NodeID={hex(target_node_id)}, Endpoint={target_endpoint_id} does NOT exist.")
            entry_exists = await self.get_endpoint_entries(dev_ctrl, target_node_id, target_endpoint_id)
            asserts.assert_false(
                entry_exists,
                f"Found Binding entry unexpectedly for NodeID={hex(target_node_id)}, Endpoint={target_endpoint_id}. Necessary pre-condition failed."
            )

            # Step 2: Attempt RemoveBindingFromEndpointForNode for (NodeID, EndpointID).
            self.print_step(2, f"Issue RemoveBindingFromEndpointForNode for NodeID={hex(target_node_id)}, Endpoint={target_endpoint_id}; expect NOT_FOUND.")
            try:
                await dev_ctrl.SendCommand(
                    nodeId=dut_node_id,
                    endpoint=target_endpoint_id,
                    command=REMOVE_BINDING_CMD(NodeID=target_node_id, EndpointID=target_endpoint_id)
                )
            except InteractionModelError as e:
                self.print_step(3, f"RemoveBindingFromEndpointForNode returned error status: {e.status}")
                is_not_found = (e.status == Status.NotFound or str(e.status).upper() == "NOT_FOUND")
                asserts.assert_true(
                    is_not_found,
                    f"Expected NOT_FOUND, got {e.status} for RemoveBindingFromEndpointForNode (NodeID={hex(target_node_id)}, Endpoint={target_endpoint_id})"
                )
            except Exception as ex:
                asserts.fail(f"Got unexpected error on RemoveBindingFromEndpointForNode: {ex}")
            else:
                asserts.fail(
                    f"RemoveBindingFromEndpointForNode unexpectedly succeeded for (NodeID={hex(target_node_id)}, Endpoint={target_endpoint_id}); should fail with NOT_FOUND."
                )

            # Step 3: Confirm system state is unchanged (no new entries created)
            self.print_step(4, "Verify no Endpoint Information Entry was created/changed for the test combination.")
            entry_still_absent = not await self.get_endpoint_entries(dev_ctrl, target_node_id, target_endpoint_id)
            asserts.assert_true(entry_still_absent, f"Binding entry for test case NodeID={hex(target_node_id)}, Endpoint={target_endpoint_id} unexpectedly appeared after test.")

            # (Manual/infra): Step 4: Recommend checking system/audit logs for proper record of these failures
            self.print_step(5, f"System/logs should show RemoveBindingFromEndpointForNode for NodeID={hex(target_node_id)}, Endpoint={target_endpoint_id} with NOT_FOUND.")

        self.print_step(6, "Completed: RemoveBindingFromEndpointForNode fails with NOT_FOUND for missing entries; state remains unchanged.")

if __name__ == "__main__":
    default_matter_test_main()
```

**Usage/Notes:**
- Save as `tests/test_TC_CSA_REMOVEBINDING_NOTFOUND_0001.py` (or as fits your test structure).
- Optionally, pass or override `self.notfound_binding_cases` with a list of (NodeID, EndpointID) pairs certain to have no Binding entry for the test.
- The test queries both before and after the RemoveBindingFromEndpointForNode command, asserts NOT_FOUND each time, and checks that no new Binding entry is created.
- Attribute and command references match your test/cluster model; adapt as required.
- All steps include comments and strong assertions for clear result reporting.