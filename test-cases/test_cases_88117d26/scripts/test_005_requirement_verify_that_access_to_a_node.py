```python
#
#    Copyright (c) 2024 Project CHIP Authors
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

import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.exceptions import ChipStackError
from matter.interaction_model import InteractionModelError, Status
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

# Test configuration constants. In a real test environment, these could be provided via --int-arg etc.
TARGET_ENDPOINT = 1  # Example endpoint
TARGET_CLUSTER = Clusters.OnOff
TARGET_ATTRIBUTE = Clusters.OnOff.Attributes.OnOff
PRIVILEGE = "view"  # The privilege level we want to test ("view", "operate", etc.)
TEST_SUBJECT = 0xABCDEF  # Subject id not initially in ACL (e.g. a test CASE Authenticated Tag)

class TestCSAACL0001(MatterBaseTest):
    """
    TC-CSA-ACL-0001: Verify that access to a Node’s Targets is denied unless the Access Control system explicitly grants the required privilege to a given Subject.
    """

    async def get_current_acl(self):
        """Read the current AccessControl.Acl attribute from the DUT"""
        result = await self.read_single_attribute_check_success(
            endpoint=0,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
        )
        return result

    async def set_acl(self, acl_entries):
        """Write the given ACL to the DUT"""
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id, [(0, Clusters.AccessControl.Attributes.Acl(acl_entries))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    async def reset_acl(self):
        """Restore the original ACL (best effort: used in teardown)."""
        current_acl = self.__dict__.get("original_acl", None)
        if current_acl is not None:
            try:
                await self.set_acl(current_acl)
            except Exception:
                pass

    @pytest.fixture(autouse=True, scope="class")
    async def setup_and_teardown(self, request):
        # Record original ACL before testing
        self.original_acl = await self.get_current_acl()
        yield
        await self.reset_acl()

    @async_test_body
    async def test_acl_required_privilege(self):
        # === Step 0: Preparation ===
        # This test assumes: node is running, Targets configured, and ACL present.
        # Save original ACL for possible restoration.

        # === Step 1: Attempt to access a Target as a subject NOT in the ACL ===
        # We'll try a read on the OnOff attribute using the subject whose access is not allowed.

        # For simulating an access as a specific Subject, your test framework/environment
        # must allow sending operations as that Subject (e.g., another commissioning, or special setup).
        # This is represented here by self.secondary_controller -- adapt as per your env.
        secondary_controller = getattr(self, "test_subject_controller", None)
        if not secondary_controller:
            pytest.skip("The test_subject_controller for the Subject not in the ACL must be set by the test harness.")

        # (1) Attempt read attribute (should be denied)
        self.print_step(1, f"Attempting to access {TARGET_CLUSTER.__name__}::{TARGET_ATTRIBUTE.__name__} as Subject {hex(TEST_SUBJECT)} [not in ACL]")
        access_denied = False
        try:
            await secondary_controller.ReadAttribute(
                nodeId=self.dut_node_id,
                attributes=[(TARGET_ENDPOINT, TARGET_CLUSTER, TARGET_ATTRIBUTE)]
            )
        except InteractionModelError as e:
            access_denied = (e.status == Status.AccessDenied or e.status == Status.UnsupportedAccess)
        except ChipStackError:
            # Any underlying denial may bubble up as a stack error.
            access_denied = True
        asserts.assert_true(access_denied, "Step 2: Access should be denied to subject not in ACL")

        # === Step 2: Grant access in the ACL ===

        # Compose an updated ACL with a new entry allowing the required privilege on the target to our subject.
        # This structure matches the ClusterObject schema for AccessControlEntry.
        # Find the DeviceType/Endpoint info as needed for 'targets'; here, we use endpoint only.
        new_entry = ClusterObjects.AccessControl.AccessControlEntryStruct(
            fabricIndex=1,  # May need to set to current fabricIndex, not 1, if known
            privilege=ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kView,  # or adapt for needed privilege
            authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase,  # Assumes CASE for subject
            subjects=[TEST_SUBJECT],
            targets=[ClusterObjects.AccessControl.TargetStruct(endpoint=TARGET_ENDPOINT)],
        )
        acl = list(self.original_acl)                # Preserve all original entries
        acl.append(new_entry)                        # Add permission for test subject

        self.print_step(2, f"Updating ACL to grant required privilege to Subject {hex(TEST_SUBJECT)} for endpoint {TARGET_ENDPOINT}")
        await self.set_acl(acl)

        # === Step 3: Attempt to access again (should succeed) ===
        access_granted = False
        try:
            value = await secondary_controller.ReadAttribute(
                nodeId=self.dut_node_id,
                attributes=[(TARGET_ENDPOINT, TARGET_CLUSTER, TARGET_ATTRIBUTE)]
            )
            access_granted = True
        except Exception as e:
            access_granted = False
        asserts.assert_true(access_granted, "Step 5: Access should be allowed after granting privilege in ACL")

if __name__ == "__main__":
    default_matter_test_main()
```