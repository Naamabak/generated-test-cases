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
import logging
import pytest

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

# --- Setup: Node identities, CAT versions, and group privilege resource ---
CAT_VERSION_N = 2
CAT_VERSION_N_MINUS_1 = 1

# --- Sample subject value construction per CAT and version (per spec) ---
def cat_subject(cat_id: int, version: int) -> int:
    """Encode the CAT subject for use in the ACL and match Node identities"""
    return (0xFFFFFFFD00000000 | (cat_id & 0xFFFF) << 16 | (version & 0xF))

GROUP_CAT_ID = 0x0101  # Example CAT
GROUP_PRIVILEGE_TARGET_ENDPOINT = 1
GROUP_PRIVILEGE_CLUSTER = Clusters.OnOff
GROUP_PRIVILEGE_ATTRIBUTE = Clusters.OnOff.Attributes.OnOff

# Node identity definitions for test harness (test runner should inject these)
NODE_A_ID = 0xA1A1A1A1  # CAT version N   (latest)
NODE_B_ID = 0xB1B1B1B1  # CAT version N-1 (older)
NODE_C_ID = 0xC1C1C1C1  # CAT version N   (or N+1, optional)

# --- Privilege and AuthMode enums ---
PRIVILEGE_OPERATE = ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kOperate
AUTHMODE_GROUP = ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kGroup

class TC_CSA_CAT_0001(MatterBaseTest):
    """
    Test Case ID:      TC-CSA-CAT-0001
    Requirement ID:    CSA-CAT-REQ-001

    Verify CAT version in NOCs and ACL entries enforces privilege scoping based on version.
    """

    async def get_acl(self):
        return await self.read_single_attribute_check_success(
            endpoint=0,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
        )

    async def set_acl(self, acl):
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id, [(0, Clusters.AccessControl.Attributes.Acl(acl))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    async def get_onoff_priv_result(self, dev_ctrl, node_id):
        """Attempt to read or operate the OnOff attribute as group member."""
        try:
            # Here, try READ – or perform an OP that requires group privilege
            value = await dev_ctrl.ReadAttribute(
                nodeId=node_id,
                attributes=[(GROUP_PRIVILEGE_TARGET_ENDPOINT, GROUP_PRIVILEGE_CLUSTER, GROUP_PRIVILEGE_ATTRIBUTE)],
            )
            return True, value
        except InteractionModelError as e:
            if e.status in [Status.AccessDenied, Status.UnsupportedAccess]:
                return False, None
            raise
        except Exception:
            return False, None

    def make_group_acl_entry(self, cat_version):
        """Construct an ACE granting group privilege for a specific CAT Version."""
        return ClusterObjects.AccessControl.AccessControlEntryStruct(
            privilege=PRIVILEGE_OPERATE,
            authMode=AUTHMODE_GROUP,
            subjects=[cat_subject(GROUP_CAT_ID, cat_version)],
            targets=[ClusterObjects.AccessControl.TargetStruct(endpoint=GROUP_PRIVILEGE_TARGET_ENDPOINT)],
            fabricIndex=1
        )

    @pytest.fixture(autouse=True, scope="class")
    async def setup_and_teardown(self, request):
        # Backup the original ACL prior to running the test; restore after.
        self._original_acl = await self.get_acl()
        yield
        await self.set_acl(self._original_acl)

    @async_test_body
    async def test_cat_version_privilege_enforcement(self):
        # --- Step 1: Configure ACL to grant group privilege for CAT version N-1 (old version) ---
        self.print_step(1, "Set ACL to grant group privileges for CAT version N-1 (old version)")
        acl = list(self._original_acl)
        ace_v_n_minus_1 = self.make_group_acl_entry(CAT_VERSION_N_MINUS_1)
        acl.append(ace_v_n_minus_1)
        await self.set_acl(acl)

        # --- Step 2: Confirm Node A (version N) and Node B (version N-1) both have group privilege ---
        self.print_step(2, "Confirm both Node A and B can access target resource as group member")
        # Assumed injected: self.node_a_ctrl, self.node_b_ctrl are DeviceControllers using Node A and B credentials
        node_a_ctrl = getattr(self, "node_a_ctrl", None)
        node_b_ctrl = getattr(self, "node_b_ctrl", None)
        asserts.assert_is_not_none(node_a_ctrl, "Node A (CAT N) controller not available as test fixture")
        asserts.assert_is_not_none(node_b_ctrl, "Node B (CAT N-1) controller not available as test fixture")

        ok, _ = await self.get_onoff_priv_result(node_a_ctrl, self.dut_node_id)
        asserts.assert_true(ok, "Node A (CAT N) should have group privilege (old CAT version ACE)")
        ok, _ = await self.get_onoff_priv_result(node_b_ctrl, self.dut_node_id)
        asserts.assert_true(ok, "Node B (CAT N-1) should have group privilege (old CAT version ACE)")

        # --- Step 3: Update NOC and ACL to CAT version N (increment version) ---
        self.print_step(3, "Update NOC and ACL to CAT version N (increment CAT version in ACL)")
        # In a real test lab you would update the NOC for at least Node A and Node C to have CAT version N.
        # For this script, we assume test infra has injected correct credentials for updated controllers.
        ace_v_n = self.make_group_acl_entry(CAT_VERSION_N)
        acl_updated = [e for e in acl if not (
            hasattr(e, "authMode") and e.authMode == AUTHMODE_GROUP
            and hasattr(e, "subjects") and cat_subject(GROUP_CAT_ID, CAT_VERSION_N_MINUS_1) in e.subjects
        )]
        acl_updated.append(ace_v_n)
        await self.set_acl(acl_updated)

        # --- Step 4: Attempt group operation from both Node A and Node B ---
        self.print_step(4, "Attempt group operation from Node A (CAT N) and Node B (CAT N-1) — only A should succeed now")
        ok_a, _ = await self.get_onoff_priv_result(node_a_ctrl, self.dut_node_id)
        ok_b, _ = await self.get_onoff_priv_result(node_b_ctrl, self.dut_node_id)
        asserts.assert_true(ok_a, "Node A (CAT N) should retain group privilege after update to CAT version N")
        asserts.assert_false(ok_b, "Node B (CAT N-1) should lose group privilege after CAT version update")

        # --- Step 5: (Optional) Add new Node C with CAT N or N+1, attempt group operation ---
        node_c_ctrl = getattr(self, "node_c_ctrl", None)
        if node_c_ctrl is not None:
            self.print_step(5, "Attempt group operation from Node C (CAT N or higher) — should succeed")
            ok_c, _ = await self.get_onoff_priv_result(node_c_ctrl, self.dut_node_id)
            asserts.assert_true(ok_c, "Node C (CAT N or higher) should be granted group privilege")

        # --- Step 6: (Optional) Analyze & log system status/events ---
        self.print_step(6, "Check logs for correct privilege enforcement (manual/infra step)")

        # Post-condition: Only matching/higher CAT versions retain group privilege; older versions lose it.

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions:**
- Save as e.g. `tests/test_TC_CSA_CAT_0001.py`.
- This script expects the test harness to provide `self.node_a_ctrl`, `self.node_b_ctrl`, and `self.node_c_ctrl` as appropriate controllers set up for each logical node/CAT version.
- The script is step-commented and asserts all expected privilege grants and removals according to CAT version and current ACL state, matching your described test scenario and your project’s test structure.
- If needed, update CAT/subject encoding to match your implementation’s CAT/ACL format. For a real testbed, CATs and NOCs should actually be regenerated/installed as per your environment’s capabilities.
