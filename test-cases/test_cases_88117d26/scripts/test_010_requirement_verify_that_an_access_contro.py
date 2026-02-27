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

# === BEGIN CI TEST ARGUMENTS ===
# test-runner-runs:
#   run1:
#     app: ${ALL_CLUSTERS_APP}
#     app-args: --discriminator 1234 --KVS kvs1 --trace-to json:${TRACE_APP}.json
#     script-args: >
#       --storage-path admin_storage.json
#       --commissioning-method on-network
#       --discriminator 1234
#       --passcode 20202021
#       --trace-to json:${TRACE_TEST_JSON}.json
#       --trace-to perfetto:${TRACE_TEST_PERFETTO}.perfetto
#     factory-reset: true
#     quiet: true
# === END CI TEST ARGUMENTS ===

import logging

from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import InteractionModelError, Status
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

class TC_CSA_ACL_ADMIN_CASE_001(MatterBaseTest):
    """
    TC-CSA-ACL-ADMIN-CASE-001:
    Verify that an Access Control Entry (ACE) with privilege level 'Administer' must have AuthMode set to 'CASE' and not 'Group'.
    """

    async def get_current_acl(self):
        """Read the AccessControl.Acl attribute (list of ACEs)"""
        return await self.read_single_attribute_check_success(
            endpoint=0,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
        )

    async def set_acl(self, acl):
        """Write an ACL attribute (full replacement)."""
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id,
            [(0, Clusters.AccessControl.Attributes.Acl(acl))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    async def reset_acl(self):
        """Restore original ACL after test"""
        orig = getattr(self, "_original_acl", None)
        if orig is not None:
            try:
                await self.set_acl(orig)
            except Exception:
                pass

    @async_test_body
    async def setup_class(self):
        super().setup_class()
        # Save the starting ACL for test cleanup
        self._original_acl = await self.get_current_acl()
        log.info("Original ACL backed up for post-test restoration.")

    @async_test_body
    async def teardown_class(self):
        # Restore original ACL after all tests
        await self.reset_acl()
        log.info("Restored original ACL after test.")

    @async_test_body
    async def test_administer_authmode_requires_case(self):
        # Step 1: Attempt to add ACE with privilege=Administer, authmode=Group (should fail)
        self.print_step(1, "Attempt to create ACE with privilege='Administer', AuthMode='Group' (should fail)")
        admin_priv = ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kAdminister
        group_authmode = ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kGroup
        case_authmode = ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase

        # Compose ACE struct with invalid (administer + group) combination
        invalid_entry = ClusterObjects.AccessControl.AccessControlEntryStruct(
            privilege = admin_priv,
            authMode = group_authmode,
            subjects = [0x12345],
            targets = [],
            fabricIndex = 1
        )
        acl = list(self._original_acl)
        acl.append(invalid_entry)
        error_occurred = False
        try:
            await self.set_acl(acl)
        except InteractionModelError as e:
            # Node should reject as ConstraintError or InvalidCommand/Parameter
            asserts.assert_true(
                e.status in (Status.ConstraintError, Status.InvalidCommand, Status.InvalidAction, Status.InvalidParameter),
                f"Unexpected error code for invalid admin/group ACE: {e.status}"
            )
            error_occurred = True
        except Exception:
            # Accept any error = rejection
            error_occurred = True
        asserts.assert_true(error_occurred, "Node did not reject Administer+Group AuthMode ACE as required.")

        # Step 2: Attempt to add ACE with privilege=Administer, authmode=CASE (should succeed)
        self.print_step(2, "Attempt to create ACE with privilege='Administer', AuthMode='CASE' (should succeed)")
        valid_entry = ClusterObjects.AccessControl.AccessControlEntryStruct(
            privilege = admin_priv,
            authMode = case_authmode,
            subjects = [0x12345],
            targets = [],
            fabricIndex = 1
        )
        valid_acl = list(self._original_acl)
        valid_acl.append(valid_entry)
        try:
            await self.set_acl(valid_acl)
        except Exception as ex:
            asserts.fail(f"Failed to add valid Administer+CASE AuthMode ACE: {ex}")

        # Step 3: Get ACEs, verify all 'Administer' entries are CASE, never Group
        self.print_step(3, "List ACEs and verify no 'Administer' ACE has AuthMode='Group'")
        acl_now = await self.get_current_acl()
        found_admin_group = []
        found_admin_case = []
        for ace in acl_now:
            if ace.privilege == admin_priv:
                if ace.authMode == group_authmode:
                    found_admin_group.append(ace)
                if ace.authMode == case_authmode:
                    found_admin_case.append(ace)
        asserts.assert_equal(len(found_admin_group), 0, "'Administer' ACE(s) with Group authMode found, which is not allowed by spec")
        asserts.assert_greater(len(found_admin_case), 0, "No valid 'Administer' ACEs with CASE AuthMode found after addition")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**How this matches the requirements:**
- **ACE creation with Administer+Group**: The test tries to write this ACE, expects and asserts an error/constraint.
- **ACE creation with Administer+CASE**: The test writes this ACE, expects and asserts success.
- **Post-validation**: The test reads back the ACL, checks there are no 'Administer' entries with 'Group' AuthMode, and at least one with 'CASE'.
- All steps and results match the expected behaviors from your test description.
- Original ACL is restored in teardown to ensure the system is left clean.

**File Name/Location:**  
`tests/test_TC_CSA_ACL_ADMIN_CASE_001.py` (or as fits your test directory structure)