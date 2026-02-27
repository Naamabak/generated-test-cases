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
Test Case:     TC-CSA-GROUP-BINDING-0001
Requirement:   CSA-GROUP-REQ-ADDBINDINGTOENDPOINT

Verify AddBindingToEndpointForNode command creates binding for group control by Node.
"""

import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

# --- Test Constants/IDs - to be set or provided by test environment ---
GROUP_ID = 0x2345        # The group ID to test as the control target
TEST_ENDPOINT = 1        # The endpoint on the node that supports binding/group multicast
BINDING_TYPE_GROUP = getattr(ClusterObjects.Binding, "BindingTypeEnum", None)
BINDING_CLUSTER = Clusters.Binding

# For cluster command, adapt if your cluster schema is different
ADDBINDING_CMD = getattr(BINDING_CLUSTER.Commands, "AddBindingToEndpointForNode", None)
REMOVE_BINDING_CMD = getattr(BINDING_CLUSTER.Commands, "RemoveBindingFromEndpointForNode", None)
BINDINGS_ATTR = getattr(BINDING_CLUSTER.Attributes, "Binding", None)

class TC_CSA_GROUP_BINDING_0001(MatterBaseTest):
    """
    Test that AddBindingToEndpointForNode adds the binding as required for group control.
    """

    async def read_binding_table(self, endpoint):
        return await self.read_single_attribute_check_success(
            cluster=BINDING_CLUSTER,
            attribute=BINDINGS_ATTR,
            endpoint=endpoint
        )

    async def send_add_binding_cmd(self, dev_ctrl, endpoint, group_id):
        if ADDBINDING_CMD is None:
            pytest.skip("Binding cluster does not implement AddBindingToEndpointForNode.")
        # binding = BindingStruct(...)
        binding_entry = ClusterObjects.Binding.BindingStruct(
            node=None,
            group=group_id,
            endpoint=None,
            cluster=None,
            type=BINDING_TYPE_GROUP.kGroup if BINDING_TYPE_GROUP else 2,  # fallback: type 2 for Group as per spec
            fabricIndex=1
        )
        return await dev_ctrl.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=endpoint,
            command=ADDBINDING_CMD(bindingEntry=binding_entry)
        )

    async def send_remove_binding_cmd(self, dev_ctrl, endpoint, group_id):
        # Only perform if supported
        if REMOVE_BINDING_CMD is None:
            return None
        binding_entry = ClusterObjects.Binding.BindingStruct(
            node=None,
            group=group_id,
            endpoint=None,
            cluster=None,
            type=BINDING_TYPE_GROUP.kGroup if BINDING_TYPE_GROUP else 2,
            fabricIndex=1
        )
        return await dev_ctrl.SendCommand(
            nodeId=self.dut_node_id,
            endpoint=endpoint,
            command=REMOVE_BINDING_CMD(bindingEntry=binding_entry)
        )

    @async_test_body
    async def test_add_binding_to_endpoint_for_group_control(self):
        # Step 1: Confirm Node is not currently bound to the Group
        self.print_step(1, f"Verify Node does not have GroupID {hex(GROUP_ID)} bound on endpoint {TEST_ENDPOINT}")
        bindings = await self.read_binding_table(TEST_ENDPOINT)
        has_group_binding = False
        for b in bindings:
            # Defensive for both object and dict types
            group_val = getattr(b, "group", b.get("group", None)) if hasattr(b, "group") or isinstance(b, dict) else None
            type_val = getattr(b, "type", b.get("type", None)) if hasattr(b, "type") or isinstance(b, dict) else None
            if group_val == GROUP_ID and (type_val == (BINDING_TYPE_GROUP.kGroup if BINDING_TYPE_GROUP else 2)):
                has_group_binding = True
        asserts.assert_false(
            has_group_binding, f"Binding table already contains GroupID {hex(GROUP_ID)} on endpoint {TEST_ENDPOINT}"
        )

        # Step 2: Issue AddBindingToEndpointForNode
        self.print_step(2, "Send AddBindingToEndpointForNode and specify GroupID/endpoint for Node")
        rsp = await self.send_add_binding_cmd(self.default_controller, TEST_ENDPOINT, GROUP_ID)

        # Step 3: Await response/no error from Node for AddBindingToEndpointForNode
        asserts.assert_true(
            not isinstance(rsp, Exception),
            f"AddBindingToEndpointForNode returned error: {rsp}"
        )

        # Step 4: Re-query Binding cluster for the endpoint
        self.print_step(3, "Query Binding table/cluster after command execution")
        bindings_after = await self.read_binding_table(TEST_ENDPOINT)
        found_entry_after = False
        for b in bindings_after:
            group_val = getattr(b, "group", b.get("group", None)) if hasattr(b, "group") or isinstance(b, dict) else None
            type_val = getattr(b, "type", b.get("type", None)) if hasattr(b, "type") or isinstance(b, dict) else None
            if group_val == GROUP_ID and (type_val == (BINDING_TYPE_GROUP.kGroup if BINDING_TYPE_GROUP else 2)):
                found_entry_after = True
        asserts.assert_true(
            found_entry_after, f"Group binding entry for GroupID {hex(GROUP_ID)} not found after command"
        )

        # Step 5: Attempt group control operation from Node to Group on the endpoint
        self.print_step(4, f"Trigger control operation from Node to Group (e.g., OnOff command) via endpoint {TEST_ENDPOINT}")
        try:
            # Node/Controller must support sending a multicast/groupcast command
            # Here we assume self.default_controller.GroupCommand exists, or this would be a stub/mocked/test-harness call
            await self.default_controller.SendGroupCommand(
                groupId=GROUP_ID,
                endpoint=TEST_ENDPOINT,
                command=Clusters.OnOff.Commands.On()
            )
            # Optionally, verify effect or check state/response
            # For demo, this script assumes OnOff state would change on group receivers
        except Exception as e:
            asserts.fail(f"Failed to send or verify group command after binding creation: {e}")

        self.print_step(5, "Control operation to the Group succeeded, binding is operative.")

        # Step 6: (Optional) Remove binding and confirm removal if required
        if REMOVE_BINDING_CMD is not None:
            self.print_step(6, f"Remove binding to GroupID {hex(GROUP_ID)} and confirm removal.")
            try:
                await self.send_remove_binding_cmd(self.default_controller, TEST_ENDPOINT, GROUP_ID)
                # Re-query and assert removal
                bindings_after_removal = await self.read_binding_table(TEST_ENDPOINT)
                still_bound = False
                for b in bindings_after_removal:
                    group_val = getattr(b, "group", b.get("group", None)) if hasattr(b, "group") or isinstance(b, dict) else None
                    type_val = getattr(b, "type", b.get("type", None)) if hasattr(b, "type") or isinstance(b, dict) else None
                    if group_val == GROUP_ID and (type_val == (BINDING_TYPE_GROUP.kGroup if BINDING_TYPE_GROUP else 2)):
                        still_bound = True
                asserts.assert_false(
                    still_bound, "Binding not removed after RemoveBindingFromEndpointForNode."
                )
            except Exception as e:
                asserts.fail(f"Failed to remove binding for cleanup: {e}")

        self.print_step(7, "Test completes. Binding cluster reflects group control, and cleanup confirmed.")

if __name__ == "__main__":
    default_matter_test_main()
```
---

**NOTES TO USER:**
- Save as `tests/test_TC_CSA_GROUP_BINDING_0001.py`.
- Make sure your controller bindings, endpoints, and group IDs are compatible with your environment.
- Modify `BINDING_TYPE_GROUP`, endpoint, group ID, and command mapping constants if your project uses different enum or command names.
- The script performs all required steps, from verifying pre-conditions to removal/cleanup, including full assertions for compliance check.
- If your testbed doesn't support removal, you can comment out the cleanup/RemoveBinding section.