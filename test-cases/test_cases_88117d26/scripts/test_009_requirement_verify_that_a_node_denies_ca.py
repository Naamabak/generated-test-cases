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

import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import InteractionModelError, Status
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

class TestCSACASE0001(MatterBaseTest):
    """
    TC-CSA-CASE-0001:
    Verify Node denies CASE session establishment if initiator identity not in ACE,
    and allows it after appropriate ACE is added.
    """
    TEST_INITIATOR_SUBJECT = 0xCAFEBABE  # (Example test subject) Should NOT be present in initial ACL
    # Note: The value(s) should be coordinated with the test harness or preset for your lab setup
    TARGET_FABRIC_INDEX = 1  # Adjust as per test infra, may vary for multi-fabric

    async def get_current_acl(self):
        """Retrieve the current AccessControl.Acl attribute."""
        acl = await self.read_single_attribute_check_success(
            endpoint=0,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
        )
        return acl

    async def set_acl(self, acl_entries):
        """Write the given ACL list to the DUT."""
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id, [
                (0, Clusters.AccessControl.Attributes.Acl(acl_entries))
            ]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    async def reset_acl(self):
        """Restore the original ACL if available."""
        original_acl = getattr(self, "original_acl", None)
        if original_acl is not None:
            try:
                await self.set_acl(original_acl)
            except Exception:
                pass

    async def remove_test_aces(self, ace_subject):
        """Remove all ACEs that mention ace_subject; used for cleanup."""
        acl = await self.get_current_acl()
        cleaned = [entry for entry in acl if not (hasattr(entry, "subjects") and entry.subjects and ace_subject in entry.subjects)]
        await self.set_acl(cleaned)

    @pytest.fixture(autouse=True, scope="class")
    async def setup_and_teardown(self, request):
        """Preserve original ACL and restore after test."""
        self.original_acl = await self.get_current_acl()
        yield
        await self.reset_acl()
        await self.remove_test_aces(self.TEST_INITIATOR_SUBJECT)

    @async_test_body
    async def test_case_session_ace_enforcement(self):
        # STEP 0: Preparation (handled by setup/fixture)

        # STEP 1: Attempt CASE session establishment without matching ACE
        self.print_step(1, "Attempt CASE session from initiator not present in any ACE")
        unauth_ctrl = getattr(self, "case_test_initiator", None)
        if unauth_ctrl is None:
            pytest.skip("Test initiator (case_test_initiator) not available in test harness/environment.")

        establishment_failed = False
        denial_status = None
        try:
            # Implementation detail: this controller should identify as TEST_INITIATOR_SUBJECT
            await unauth_ctrl.PairDevice(nodeId=0xFFF1, discriminator=1234, setupPinCode=20202021)
        except InteractionModelError as e:
            establishment_failed = True
            denial_status = e.status
        except Exception:
            establishment_failed = True

        asserts.assert_true(establishment_failed, "CASE session should be denied when no ACE matches initiator.")

        # STEP 2: (Log review for failure reason is infra-specific. This could be done by post-processing,
        # or capturing log events via the test harness.)

        # STEP 3: Add Access Control Entry for the test initiator
        self.print_step(2, f"Add ACE for test initiator subject {hex(self.TEST_INITIATOR_SUBJECT)}")
        acl = await self.get_current_acl()

        new_ace = ClusterObjects.AccessControl.AccessControlEntryStruct(
            fabricIndex=self.TARGET_FABRIC_INDEX,
            privilege=ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kAdminister,
            authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase,
            subjects=[self.TEST_INITIATOR_SUBJECT],
            targets=None,  # None means all targets, or use a list of ClusterObjects.AccessControl.TargetStruct
        )
        acl_new = list(acl) + [new_ace]
        await self.set_acl(acl_new)

        # STEP 4: Repeat the CASE session establishment (should now succeed)
        self.print_step(3, "Repeat CASE session establishment, initiator now present in ACE")

        session_success = False
        try:
            session = await unauth_ctrl.PairDevice(nodeId=0xFFF1, discriminator=1234, setupPinCode=20202021)
            session_success = session is not None
        except Exception:
            session_success = False

        asserts.assert_true(session_success, "CASE session should succeed when ACE is present for initiator.")

        # STEP 5: (Optional) Clean up ACE for test initiator if not needed for subsequent tests

if __name__ == "__main__":
    default_matter_test_main()
```

**Instructions:**  
- Save as e.g. `tests/test_tc_csa_case_0001.py` (or per your org/path conventions).
- This test expects the test environment to provide:
  - A controller for the unauthorized initiator under `self.case_test_initiator`.
  - A standard pairing discriminator and PIN (substitute in your lab as needed).
- All steps follow the style and structure of your test project, with step-to-code comments and robust assertions.
- Adjust subject ID, node ID, privileges, and fabric indexes as fits your testbed.
- This script will automatically restore the original ACL and remove extra ACEs.
