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
#     factory-reset: true
#     quiet: true
#     app-args: --discriminator 1234 --KVS kvs1 --trace-to json:${TRACE_APP}.json
#     script-args: >
#       --storage-path admin_storage.json
#       --commissioning-method on-network
#       --discriminator 1234
#       --passcode 20202021
#       --trace-to json:${TRACE_TEST_JSON}.json
#       --trace-to perfetto:${TRACE_TEST_PERFETTO}.perfetto
# === END CI TEST ARGUMENTS ===

import logging

from mobly import asserts
import pytest

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.exceptions import ChipStackError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

# Set up constants/mock ARL for this test context (to be adapted for an actual testbed)
ARL_LIST = [
    "RemoveFabric",       # Example: ARL could restrict RemoveFabric during commissioning
    # Add other restrictions as required by your DUT's config
]
ADMIN_SUBJECT = 0x100  # Example CAT ID for an admin (CASE Authenticated Tag)
NON_ADMIN_SUBJECT = 0x200  # Example CAT ID for a non-admin
COMMISSIONING_ENDPOINT = 0     # AccessControl typically lives at root endpoint (0)

class TC_CSA_PASE_ARL_0001(MatterBaseTest):
    """
    TC-CSA-PASE-ARL-0001:
    Verify that only Administrative Subjects are implicitly granted administrative access privileges during commissioning,
    except for items listed in the Commissioning Access Restriction List (ARL).
    """

    async def get_current_acl(self):
        acl = await self.read_single_attribute_check_success(
            endpoint=COMMISSIONING_ENDPOINT,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
        )
        return acl

    async def set_acl(self, acl):
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id, [(COMMISSIONING_ENDPOINT, Clusters.AccessControl.Attributes.Acl(acl))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    def get_admin_entry(self):
        # Minimal admin entry allowing all admin privileges
        return ClusterObjects.AccessControl.AccessControlEntryStruct(
            fabricIndex=1,
            privilege=ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kAdminister,
            authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase,
            subjects=[ADMIN_SUBJECT],
            targets=[],  # All targets
        )

    def get_nonadmin_entry(self):
        # Minimal non-admin entry allowing view only
        return ClusterObjects.AccessControl.AccessControlEntryStruct(
            fabricIndex=1,
            privilege=ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kView,
            authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase,
            subjects=[NON_ADMIN_SUBJECT],
            targets=[],
        )

    @pytest.fixture(autouse=True, scope="class")
    async def setup_and_teardown_acl(self, request):
        # Backup current ACL before test and restore after
        self.original_acl = await self.get_current_acl()
        yield
        await self.set_acl(self.original_acl)

    @async_test_body
    async def test_commissioning_access_rights(self):
        # === Step 1: Initiate commissioning (handled by test runner) ===
        self.print_step(1, "Node commissioning initiated (should already be in commissioning).")

        # === Step 2.1: Try admin functions (modify ACL) as Admin Subject during commissioning ===
        # Here we use "default_controller" which is associated with our Admin Subject; test infra must ensure this mapping.
        self.print_step(2, "Attempt admin functions as Admin Subject during commissioning")
        acl = list(self.original_acl)
        test_entry = self.get_admin_entry()  # As admin, add another admin entry as a test
        acl.append(test_entry)
        success_admin = False
        try:
            await self.set_acl(acl)
            success_admin = True
        except Exception as e:
            log.error(f"Admin access denied unexpectedly: {e}")
            success_admin = False
        asserts.assert_true(success_admin, "Admin Subject should be able to modify ACL (unless ARL denies it)")

        # === Step 3: Record outcome for each admin function ===
        # Step covers recording which operations succeed/fail as seen in the test results/logs.

        # === Step 4: Attempt same admin functions as Non-Admin Subject ===
        # For this, we expect a secondary controller mapped to the non-admin subject.
        self.print_step(3, "Attempt admin functions as Non-Admin Subject during commissioning")
        non_admin_ctrl = getattr(self, "non_admin_controller", None)
        if not non_admin_ctrl:
            pytest.skip("Secondary controller for Non-Admin Subject not set by test harness.")

        denied_non_admin = False
        try:
            await non_admin_ctrl.WriteAttribute(
                self.dut_node_id,
                [(COMMISSIONING_ENDPOINT, Clusters.AccessControl.Attributes.Acl(acl))]
            )
        except (InteractionModelError, ChipStackError) as e:
            denied_non_admin = True
        asserts.assert_true(denied_non_admin, "Non-Admin Subject should NOT be able to modify ACL during commissioning")

        # === Step 5: Attempt actions *explicitly restricted* in ARL as Admin Subject ===
        # Example: RemoveFabric restriction
        for arl_item in ARL_LIST:
            self.print_step(4, f"Attempt {arl_item} as Admin Subject (expect ARL restriction)")
            arl_cmd = getattr(Clusters.OperationalCredentials.Commands, arl_item, None)
            if arl_cmd is None:
                log.warning(f"ARL item {arl_item} does not have a direct command mapping for test; skipping this ARL item.")
                continue
            try:
                await self.send_single_cmd(cmd=arl_cmd(), endpoint=COMMISSIONING_ENDPOINT)
                asserts.fail(f"Admin Subject should be denied {arl_item} due to ARL in commissioning")
            except InteractionModelError as e:
                asserts.assert_true(
                    e.status in [Status.AccessDenied, Status.UnsupportedAccess],
                    f"{arl_item} as admin should be restricted by ARL: got status {getattr(e, 'status', None)}"
                )

        # === Step 6: Attempt actions *not* listed in ARL as Admin Subject ===
        self.print_step(5, "Attempt non-ARL-restricted admin function as Admin Subject (should succeed)")
        # Example: AddNOC (which may not be restricted in ARL)
        try:
            await self.send_single_cmd(
                cmd=Clusters.OperationalCredentials.Commands.AddNOC(NOCValue=b'', ICACValue=None, AdminVendorId=0xFFF1),
                endpoint=COMMISSIONING_ENDPOINT
            )
            addnoc_success = True
        except Exception:
            addnoc_success = False
        asserts.assert_true(addnoc_success, "Admin Subject should be able to execute AddNOC if not ARL-restricted")

        # === Step 7: Record all responses, access results, logs (done via asserts & logs above) ===

        # === Step 8: Terminate commissioning phase and attempt same operations post-commissioning ===
        self.print_step(6, "Commissioning ended; attempt admin op as Admin Subject (should now only have explicit privileges)")

        # Simulate end of commissioning (how this is done depends on your product; e.g., remove PASE session, close channel)
        try:
            await self.end_commissioning_phase()
        except Exception:
            log.warning("Unable to explicitly end commissioning phase in demo test -- ensure real env supports this.")

        # Now, attempt modifying ACL as admin subject after commissioning.
        post_commissioning_denied = False
        try:
            acl2 = list(self.original_acl)
            acl2.append(self.get_admin_entry())
            await self.set_acl(acl2)
        except (InteractionModelError, ChipStackError) as e:
            post_commissioning_denied = True
        # Per spec, implicit admin access should be revoked post-commissioning; this may succeed/fail based on ACL state.
        asserts.assert_true(post_commissioning_denied, "Implicit admin access over commissioning channel should be revoked post-commissioning")

    async def end_commissioning_phase(self):
        # Placeholder: Simulate closing PASE commission session; adapt to how testbed ends commissioning in your infra
        # Typical approaches: controller.command('CloseCommissioningWindow') or remove PASE/fall back to operational channel
        await self.default_controller.CloseCommissioningWindow(self.dut_node_id)

if __name__ == '__main__':
    default_matter_test_main()
```

**NOTES:**
- This script follows the MatterBaseTest/pytest hybrid style used in your project.
- You must map testbed fixtures so `default_controller` is an administrative subject (e.g., CASE CAT = admin) and `non_admin_controller` (if present) is a non-admin.
- The ARL is modeled as a simple Python list for this example; ensure you read/capture the actual ARL configuration from your DUT when running in a real environment.
- Actual command implementations and commissioning-phase simulation must be adapted to your product's API/testbed (e.g., how to close the commissioning channel, support for multiple subjects, etc.).
- All results and failures are asserted and logged.
- Remove/revert any test ACL/subjects as needed in additional teardown, if your runner doesn't revert at fixture scope.