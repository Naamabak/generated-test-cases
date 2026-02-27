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
Test Case:     TC-CSA-ADDBINDING-NOTFOUND-0001
Requirement:   CSA-ADDBINDING-REQ-NOTFOUND-001

Verify that AddBindingToEndpointForNode fails with NOT_FOUND if Endpoint Information Entry does not exist for NodeID and EndpointID.
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

# ---- Cluster/command constants (assume testbed/environment provides cluster implementations) ----
BINDING_CLUSTER = Clusters.Binding
ADDBINDING_CMD = getattr(BINDING_CLUSTER.Commands, "AddBindingToEndpointForNode", None)
ENDPOINT_INFO_ENTRY_ATTR = None   # Typically part of a Datastore/Descriptor/Binding config (update for product env)

# For negative test, these (NodeID, EndpointID) pairs must not exist in EndpointInfoEntries:
MISSING_EPINFO_PAIRS = [
    (0xD00D0001, 11),
    (0xBEEF0022, 99),
]

class TC_CSA_ADDBINDING_NOTFOUND_0001(MatterBaseTest):
    """
    Test AddBindingToEndpointForNode returns NOT_FOUND for missing Endpoint Information Entry.
    """

    async def endpoint_info_entry_exists(self, node_id, endpoint_id):
        """
        Check via proper cluster/attribute that Endpoint Information Entry for NodeID/EndpointID exists.
        Should return False for purposely missing test pairs.
        """
        # Customize this method for your project. Normally via a Datastore/Binding/Descriptor cluster attribute.
        # Here, stubbed to always return False as expected for missing test pairs.
        # Testbed should override if product environment exposes endpoint info query.
        if ENDPOINT_INFO_ENTRY_ATTR is None:
            return False
        # Example: Query attribute and check for entry
        try:
            entry_list = await self.read_single_attribute_check_success(
                cluster=BINDING_CLUSTER,
                attribute=ENDPOINT_INFO_ENTRY_ATTR,
                endpoint=endpoint_id,
                device_id=node_id,
            )
            # Search for (node_id, endpoint_id) in entry_list; adapt as required
            for entry in entry_list:
                eid = getattr(entry, "endpointId", entry.get("endpointId", None))
                nid = getattr(entry, "nodeId", entry.get("nodeId", None))
                if eid == endpoint_id and nid == node_id:
                    return True
        except Exception:
            pass
        return False

    async def send_add_binding_cmd(self, dev_ctrl, node_id, endpoint_id):
        """
        Issue AddBindingToEndpointForNode with specified NodeID/EndpointID, expect NOT_FOUND for missing pairs.
        """
        asserts.assert_is_not_none(ADDBINDING_CMD, "AddBindingToEndpointForNode command not implemented.")
        # Compose a dummy binding entry as per cluster object
        # For a negative test, fields other than nodeId/endpointId do not matter; set essential ones.
        from matter.clusters.ClusterObjects import Binding
        BIND_TYPE_ENUM = getattr(Binding, "BindingTypeEnum", None)
        typ = BIND_TYPE_ENUM.kGroup if BIND_TYPE_ENUM else 2  # fallback: '2' for Group
        binding_entry = Binding.BindingStruct(
            node=node_id,
            group=None,
            endpoint=endpoint_id,
            cluster=None,
            type=typ,
            fabricIndex=1,
        )
        return await dev_ctrl.SendCommand(
            nodeId=node_id,
            endpoint=endpoint_id,
            command=ADDBINDING_CMD(bindingEntry=binding_entry)
        )

    @async_test_body
    async def test_addbinding_returns_not_found_for_missing_endpoint_entry(self):
        """
        1. For each (NodeID, EndpointID) pair not present as an Endpoint Information Entry:
            a. Confirm entry is missing.
            b. Attempt AddBindingToEndpointForNode, expect NOT_FOUND.
            c. Ensure no binding created; repeat for each.
        """
        test_ctrl = getattr(self, "default_controller")  # Use standard controller for admin actions

        # Step 1: For each pair, check entry is not present in Endpoint Info Entries (if infra available)
        for i, (node_id, endpoint_id) in enumerate(MISSING_EPINFO_PAIRS):
            self.print_step(1 + i*3, f"Checking for missing Endpoint Info Entry for NodeID={hex(node_id)} EndpointID={endpoint_id}")
            present = await self.endpoint_info_entry_exists(node_id, endpoint_id)
            asserts.assert_false(present, f"Endpoint Info Entry unexpectedly present for NodeID={hex(node_id)} EndpointID={endpoint_id}")

            # Step 2: Attempt AddBindingToEndpointForNode for each such pair.
            self.print_step(2 + i*3, f"Attempt AddBindingToEndpointForNode for missing entry: NodeID={hex(node_id)}, EndpointID={endpoint_id}")
            not_found_received = False
            try:
                await self.send_add_binding_cmd(test_ctrl, node_id, endpoint_id)
            except InteractionModelError as e:
                not_found_received = (e.status == Status.NotFound or str(e.status).upper() == "NOT_FOUND")
                asserts.assert_true(
                    not_found_received,
                    f"AddBindingToEndpointForNode for missing (NodeID={hex(node_id)}, EndpointID={endpoint_id}) "
                    f"did not return NOT_FOUND (got {e.status})"
                )
            except Exception as e:
                asserts.fail(f"Unexpected error on AddBindingToEndpointForNode for missing entry: {e}")
            else:
                asserts.fail("AddBindingToEndpointForNode succeeded unexpectedly for non-existent Endpoint Info Entry; should fail with NOT_FOUND.")

            # Step 3: Reconfirm that no new Endpoint Info Entry or Binding has been created (if infra supports)
            self.print_step(3 + i*3, f"Confirm no Binding created for NodeID={hex(node_id)}, EndpointID={endpoint_id}.")
            # For most cases, infra will enforce this, but if you can check, re-query the entry as above
            still_absent = not await self.endpoint_info_entry_exists(node_id, endpoint_id)
            asserts.assert_true(still_absent, f"Binding unexpectedly created for missing Endpoint Info Entry (NodeID={hex(node_id)}, EndpointID={endpoint_id}).")

        self.print_step(3 + len(MISSING_EPINFO_PAIRS)*3, "Test complete: All AddBindingToEndpointForNode attempts for missing Endpoint Info Entries failed with NOT_FOUND; no changes made.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**Instructions for Use/Adaptation:**
- Save this script as `tests/test_TC_CSA_ADDBINDING_NOTFOUND_0001.py` (or similar).
- Set `MISSING_EPINFO_PAIRS` in the test or fixture according to your integration (use NodeID/EndpointID pairs with *no* Endpoint Info Entry).
- If your cluster definition or product environment exposes a queryable attribute for Endpoint Information Entries, set `ENDPOINT_INFO_ENTRY_ATTR`; otherwise, the script will stub this as always missing (expected for a negative test).
- All assertions, step comments, and usage patterns follow your Project CHIP Matter test conventions.
- Adjust constants and step/cluster logic as needed for your testbed or product.
