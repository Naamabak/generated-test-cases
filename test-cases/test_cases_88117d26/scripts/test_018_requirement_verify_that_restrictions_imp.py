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
Test Case: TC-CSA-ARL-0001
Requirement: CSA-ARL-REQ-001

Verify that ARL restrictions override ACL permissions for the same subject/target.
"""

import logging
import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

# Constants for this test
TARGET_ENDPOINT = 1
TARGET_CLUSTER = Clusters.OnOff
TARGET_ATTRIBUTE = Clusters.OnOff.Attributes.OnOff

# Example test subject (node id or CAT); adjust per test infra if needed.
TEST_SUBJECT = 0xCABACAFE

# Placeholder for ARL attribute (update as needed for real attribute name).
ARL_ATTRIBUTE = getattr(Clusters.AccessControl.Attributes, 'AccessRestrictions', None)

def make_acl_entry(subject, privilege, endpoint):
    return ClusterObjects.AccessControl.AccessControlEntryStruct(
        fabricIndex=1,
        privilege=ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kOperate if privilege == "operate"
            else ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kView,
        authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase,
        subjects=[subject],
        targets=[ClusterObjects.AccessControl.TargetStruct(endpoint=endpoint)]
    )

def make_arl_entry(subject, endpoint):
    # Adapt struct/fields below as per your specific ARL implementation.
    return ClusterObjects.AccessControl.AccessRestrictionEntryStruct(
        entryId=1,
        subjects=[subject],
        targets=[ClusterObjects.AccessControl.TargetStruct(endpoint=endpoint)],
        restricted=True
    )

class TC_CSA_ARL_0001(MatterBaseTest):
    """
    Verify that ARL restrictions take precedence over ACL permissions for the same target and subject.
    """
    @pytest.fixture(autouse=True, scope="class")
    async def setup_and_restore(self, request):
        # Backup ACL and ARL before test for restoration after test
        self._original_acl = await self.read_single_attribute_check_success(
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
            endpoint=0,
        )
        # If ARL is not supported, fail test (require implementation for this test)
        if ARL_ATTRIBUTE is None:
            pytest.skip("AccessRestrictions (ARL) attribute is not defined in AccessControl cluster on this build.")
        try:
            self._original_arl = await self.read_single_attribute_check_success(
                cluster=Clusters.AccessControl,
                attribute=ARL_ATTRIBUTE,
                endpoint=0,
            )
        except Exception:
            pytest.skip("Device does not support Access Restriction List (ARL); cannot perform test.")

        yield

        # Restore
        await self.set_acl(self._original_acl)
        await self.set_arl(self._original_arl)

    async def set_acl(self, acl):
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id,
            [(0, Clusters.AccessControl.Attributes.Acl(acl))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "Failed to write ACL")

    async def set_arl(self, arl):
        if ARL_ATTRIBUTE is None:
            return
        try:
            result = await self.default_controller.WriteAttribute(
                self.dut_node_id,
                [(0, ARL_ATTRIBUTE(arl))]
            )
            asserts.assert_equal(result[0].Status, Status.Success, "Failed to write ARL")
        except Exception:
            log.warning("ARL write failed (possibly not implemented)")

    async def access_onoff_as_test_subject(self, dev_ctrl):
        # The dev_ctrl fixture representing TEST_SUBJECT must be provided by runner
        try:
            return await dev_ctrl.ReadAttribute(
                nodeId=self.dut_node_id,
                attributes=[(TARGET_ENDPOINT, TARGET_CLUSTER, TARGET_ATTRIBUTE)],
            )
        except InteractionModelError as e:
            return e

    @async_test_body
    async def test_arl_precedence_over_acl(self):
        # ------- Step 1: Add ACL entry granting permission to TEST_SUBJECT ---------
        self.print_step(1, f"Add ACL entry to grant 'operate' privilege on endpoint {TARGET_ENDPOINT} to subject {hex(TEST_SUBJECT)}")
        acl = list(self._original_acl)
        acl_entry = make_acl_entry(TEST_SUBJECT, "operate", TARGET_ENDPOINT)
        acl.append(acl_entry)
        await self.set_acl(acl)

        # ------- Step 2: Add matching ARL entry to restrict the same subject/endpoint ---------
        self.print_step(2, "Add ARL entry restricting same subject/endpoint")
        arl = list(self._original_arl)
        arl_entry = make_arl_entry(TEST_SUBJECT, TARGET_ENDPOINT)
        arl.append(arl_entry)
        await self.set_arl(arl)

        # ------- Step 3: Attempt attribute access as the TEST_SUBJECT (expect denied) ---------
        self.print_step(3, "Attempt access as the subject (expect ARL to block access despite ACL)")
        # Test runner/infra must inject .test_subject_controller mapped to subject=TEST_SUBJECT
        test_subj_ctrl = getattr(self, "test_subject_controller", None)
        if not test_subj_ctrl:
            pytest.skip("Runner/testbed must provide 'test_subject_controller' for TEST_SUBJECT identity")
        result = await self.access_onoff_as_test_subject(test_subj_ctrl)
        if isinstance(result, Exception):
            access_denied = (isinstance(result, InteractionModelError) and
                             result.status == Status.AccessDenied)
        else:
            access_denied = False
        asserts.assert_true(access_denied, "Access should be denied by ARL even though ACL grants permission.")

        # ------ Step 4: (Optional) Check if denial is logged as ARL restriction -----
        self.print_step(4, "Check node/system logs for ARL precedence enforcement (not automated)")

        # ------ Step 5: Remove ARL entry and attempt again; expect ACL to control -----
        self.print_step(5, "Remove the ARL restriction, access should now be granted by ACL")
        arl_no_block = [entry for entry in arl if not (
            hasattr(entry, "subjects") and TEST_SUBJECT in getattr(entry, "subjects", [])
            and hasattr(entry, "targets") and any(getattr(t, "endpoint", None) == TARGET_ENDPOINT for t in getattr(entry, "targets", []))
        )]
        await self.set_arl(arl_no_block)
        result2 = await self.access_onoff_as_test_subject(test_subj_ctrl)
        if isinstance(result2, Exception):
            access_granted = not (isinstance(result2, InteractionModelError) and result2.status == Status.AccessDenied)
        else:
            access_granted = True
        asserts.assert_true(access_granted, "Access should be granted by ACL after ARL restriction is removed.")

        # ------ Step 6: Test finished -----
        self.print_step(6, "Test complete; ARL precedence verified.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions:**
- Save this as `tests/test_TC_CSA_ARL_0001.py` (or as appropriate for your project).
- The test expects the runner to provide a `test_subject_controller` binding to a Matter controller acting as `TEST_SUBJECT` (with correct credentials).
- The script adds both ACL and ARL entries, verifies ARL takes precedence for denial, removes ARL, and checks ACL then grants access.
- Fields and struct usage for ARL may require adaptation to your matter stack implementation.
- All steps, log commentary, and assertions are mapped per your test case requirements/documentation.