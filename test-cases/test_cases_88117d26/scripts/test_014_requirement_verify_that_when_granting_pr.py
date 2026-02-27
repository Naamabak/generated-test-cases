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

from mobly import asserts
import pytest

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

# --- TEST PARAMETERS (test infrastructure is expected to provide these) ---

# CAT for the group to be tested
TEST_CAT_ID = 0x002A          # Example CAT identifier (change as appropriate)
TEST_CAT_VERSION = 1          # Example CAT version

# Construct the CAT subject value (per spec: high bits mask | CAT ID << 16 | CAT version)
def cat_subject(cat_id: int, cat_ver: int) -> int:
    # Per spec, CATs for Access Control use "CASE Authenticated Tag" format: 0xFFFFFFFD00000000 | (cat_id << 16) | cat_ver
    return 0xFFFFFFFD00000000 | (cat_id << 16) | cat_ver

CAT_BASED_SUBJECT = cat_subject(TEST_CAT_ID, TEST_CAT_VERSION)

# These should be provided or mapped by the test runner:
GROUPED_NODES = []       # List of node IDs with matching CAT/value
NON_GROUPED_NODES = []   # List of node IDs with non-matching CAT/value

# The identity (controller) representing a member of the CAT group (right CAT/version)
# The identity (controller) for a client not in the group (wrong CAT/version)
# These should be provided by test harness and mapped to correct credentials
GROUP_MEMBER_CONTROLLER = None        # e.g., self.cat_group_controller 
NON_GROUP_MEMBER_CONTROLLER = None    # e.g., self.non_cat_group_controller

# Target for privilege operation (e.g. OnOff)
PRIVILEGED_ENDPOINT = 1
PRIVILEGED_CLUSTER = Clusters.OnOff
PRIVILEGED_COMMAND = Clusters.OnOff.Commands.On()     # Example: On command

class TC_CSA_CAT_0001(MatterBaseTest):
    """
    TC-CSA-CAT-0001:
    Verify that when granting privileges to a group using a CAT-based subject, only Nodes with the matching
    CAT identifier value and version receive the privilege.
    """

    async def get_current_acl(self, node_id):
        """Read the Access Control List from the specified Node."""
        return await self.read_single_attribute_check_success(
            device_id=node_id,
            endpoint=0,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
        )

    async def set_acl(self, node_id, acl):
        """Write the given ACL list to the specified Node."""
        result = await self.default_controller.WriteAttribute(
            node_id,
            [(0, Clusters.AccessControl.Attributes.Acl(acl))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    def make_cat_group_ace(self, cat_subject, privilege="operate", endpoint=PRIVILEGED_ENDPOINT):
        """Create ACE granting <privilege> to CAT subject group for specific endpoint."""
        priv_enum = getattr(ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum, f'k{privilege.capitalize()}')
        return ClusterObjects.AccessControl.AccessControlEntryStruct(
            fabricIndex=1,  # This may need to be set per-fabric for your environment
            privilege=priv_enum,
            authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase,
            subjects=[cat_subject],
            targets=[ClusterObjects.AccessControl.TargetStruct(endpoint=endpoint)],
        )

    async def restore_acl(self, node_id, acl):
        """Restore pre-test ACL on a Node."""
        try:
            await self.set_acl(node_id, acl)
        except Exception:
            pass

    @pytest.fixture(autouse=True, scope="class")
    async def setup_and_teardown(self, request):
        """
        Save and restore ACLs for all nodes touched in this test.
        Expects GROUPED_NODES and NON_GROUPED_NODES filled externally.
        """
        self.pre_test_acls = {}
        nodes_to_test = getattr(self, "nodes_to_test", GROUPED_NODES + NON_GROUPED_NODES)
        for nid in nodes_to_test:
            self.pre_test_acls[nid] = await self.get_current_acl(nid)
        yield
        for nid, acl in self.pre_test_acls.items():
            await self.restore_acl(nid, acl)

    @async_test_body
    async def test_cat_based_ace_enforcement(self):
        # --- Step 1: Identify CAT identifier value and version (already set above) ---
        self.print_step(1, f"Testing privilege enforcement for CAT subject: {hex(CAT_BASED_SUBJECT)}")

        nodes_to_test = getattr(self, "nodes_to_test", GROUPED_NODES + NON_GROUPED_NODES)

        # --- Step 2: Create CAT-based ACE on each Node ---
        self.print_step(2, "Configure CAT-based ACE on each test node")
        for node_id in nodes_to_test:
            acl = list(self.pre_test_acls[node_id])
            ace = self.make_cat_group_ace(CAT_BASED_SUBJECT)
            acl.append(ace)
            await self.set_acl(node_id, acl)

        # --- Step 3: Attempt operation as an in-group client (has CAT/version) ---
        self.print_step(3, "Attempt operation from group member on all nodes (should be allowed on matching CAT/version)")
        group_ctrl = getattr(self, "cat_group_controller", GROUP_MEMBER_CONTROLLER)
        if not group_ctrl:
            pytest.skip("Test requires 'cat_group_controller' with CAT identity matching CAT_BASED_SUBJECT")

        nodes_granted = []
        nodes_denied_in_group = []
        for node_id in nodes_to_test:
            try:
                await group_ctrl.SendCommand(
                    nodeId=node_id,
                    endpoint=PRIVILEGED_ENDPOINT,
                    command=PRIVILEGED_COMMAND,
                )
                nodes_granted.append(node_id)
            except InteractionModelError as e:
                nodes_denied_in_group.append((node_id, e.status))
            except Exception:
                nodes_denied_in_group.append((node_id, "Exception"))

        # --- Step 4: Attempt operation as out-of-group client (wrong CAT/version) ---
        self.print_step(4, "Attempt operation from NOT-in-group client on all nodes (should be denied everywhere)")
        non_group_ctrl = getattr(self, "non_cat_group_controller", NON_GROUP_MEMBER_CONTROLLER)
        if not non_group_ctrl:
            pytest.skip("Test requires 'non_cat_group_controller' with no CAT identity/mismatched CAT/version")

        nodes_granted_wrong = []
        nodes_denied_wrong = []
        for node_id in nodes_to_test:
            try:
                await non_group_ctrl.SendCommand(
                    nodeId=node_id,
                    endpoint=PRIVILEGED_ENDPOINT,
                    command=PRIVILEGED_COMMAND,
                )
                nodes_granted_wrong.append(node_id)
            except InteractionModelError as e:
                nodes_denied_wrong.append((node_id, e.status))
            except Exception:
                nodes_denied_wrong.append((node_id, "Exception"))

        # --- Step 5: Record which nodes allowed/denied operation ---
        self.print_step(5, "Check and assert proper enforcement based on CAT matching")

        # All nodes whose CAT matches the ACE should grant to the in-group member (others should deny)
        expected_granted = set(GROUPED_NODES)
        actual_granted = set(nodes_granted)
        asserts.assert_equal(
            actual_granted, expected_granted,
            f"Nodes granting operation to group member do not match expected CAT-based membership. Expected {expected_granted}, got {actual_granted}"
        )

        # All nodes should deny to out-of-group subject
        asserts.assert_equal(
            set(nodes_granted_wrong), set(),
            f"Operation should not be allowed for client with wrong CAT version/id, but got: {nodes_granted_wrong}"
        )

        # --- Step 6: Optionally, check node logs for CAT subject reason (not possible in this api-only script) ---

        # --- Post-conditions: Cleaned up in fixture. ---

if __name__ == "__main__":
    default_matter_test_main()
```

**How to use:**
- Save as `tests/test_TC_CSA_CAT_0001.py` in your test directory.
- Your test runner/environment must provide/make available:
  - Lists of node IDs in `GROUPED_NODES` (with proper CAT) and `NON_GROUPED_NODES` (wrong or no CAT).
  - A controller identity set as `self.cat_group_controller` matching the target CAT, and `self.non_cat_group_controller` for an identity *without* the CAT (or with a mismatched version).
  - Other controller credentials/environment as required for your Matter testbed.
- The actual CAT value (0x002A), version, endpoints, and operation may require customization for your environment.
- The test fixture ensures ACLs are restored after test.
- Full step-to-code mapping and assertion/traceability as shown in referenced project style.