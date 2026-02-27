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
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

# Test configuration for group-based ACL
GROUP_CAT_ID = 0x1010  # Example CAT ID for group
GROUP_CAT_VERSION = 1  # Example group version
TARGET_ENDPOINT = 1
TARGET_CLUSTER = Clusters.OnOff
TARGET_ATTRIBUTE = Clusters.OnOff.Attributes.OnOff

def cat_subject(cat_id: int, version: int) -> int:
    # Per CASE Authenticated Tag encoding for ACL subject: high bits mask | CAT id << 16 | version
    return (0xFFFFFFFD00000000 | (cat_id << 16) | version)

class TC_CSA_REMOVEACL_0001(MatterBaseTest):
    """
    TC-CSA-REMOVEACL-0001:
    Verify RemoveACLFromNode removes the ACL after group membership control.
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

    def make_group_acl_entry(self):
        return ClusterObjects.AccessControl.AccessControlEntryStruct(
            fabricIndex=1,
            privilege=ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kOperate,
            authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kGroup,
            subjects=[cat_subject(GROUP_CAT_ID, GROUP_CAT_VERSION)],
            targets=[ClusterObjects.AccessControl.TargetStruct(endpoint=TARGET_ENDPOINT)],
        )

    async def try_group_operation(self, ctrl):
        """
        Issue an operation (read/write OnOff) as group member.
        ctrl: Device controller with CAT/credential for the group.
        Returns: success (bool)
        """
        try:
            value = await ctrl.ReadAttribute(
                nodeId=self.dut_node_id,
                attributes=[(TARGET_ENDPOINT, TARGET_CLUSTER, TARGET_ATTRIBUTE)]
            )
            return True, value
        except InteractionModelError as e:
            # AccessDenied, etc
            return False, e
        except Exception as e:
            return False, e

    @async_test_body
    async def test_remove_acl_from_node(self):
        # Step 1: Ensure group-based ACL is present
        self.print_step(1, "Backup and install group-based ACL on the Node")
        orig_acl = await self.get_acl()
        try:
            # Add the group ACL entry
            acl = list(orig_acl)
            group_ace = self.make_group_acl_entry()
            acl.append(group_ace)
            await self.set_acl(acl)

            # Step 2: Ensure group op is allowed (simulate with group member ctrl from testbed)
            self.print_step(2, "Test group-controlled operation before removal")
            group_ctrl = getattr(self, "group_member_controller", None)
            if not group_ctrl:
                asserts.fail("Testbed must provide group_member_controller with correct CAT group identity.")
            success, _ = await self.try_group_operation(group_ctrl)
            asserts.assert_true(success, "Group-controlled operation must succeed before ACL removal.")

            # Step 3: Issue RemoveACLFromNode command
            self.print_step(3, "Issue RemoveACLFromNode command (must be supported by Node)")
            try:
                await self.send_single_cmd(
                    cmd=getattr(Clusters.AccessControl.Commands, "RemoveACLFromNode")(),
                    endpoint=0
                )
            except InteractionModelError as e:
                asserts.assert_true(
                    e.status in (Status.Success, Status.Busy),
                    f"Unexpected status from RemoveACLFromNode: {e.status}",
                )
            except Exception as e:
                asserts.fail(f"RemoveACLFromNode command failed: {e}")

            # Step 4: Wait a short while for Node to process (could be replaced with event/notification)
            import asyncio
            await asyncio.sleep(2)

            # Step 5: Read ACL to confirm it's empty
            self.print_step(4, "Verify ACL is now empty after RemoveACLFromNode")
            acl_after = await self.get_acl()
            asserts.assert_is_instance(acl_after, list, "ACL after removal should be a list.")
            asserts.assert_equal(len(acl_after), 0, "ACL is not empty after RemoveACLFromNode; expected zero entries.")

            # Step 6: Group operation should now fail due to no privileges
            self.print_step(5, "Attempt group-controlled operation after ACL removal (should fail)")
            success_post, result = await self.try_group_operation(group_ctrl)
            asserts.assert_false(
                success_post,
                f"Group-controlled operation erroneously succeeded after ACL removal. Access should be denied. Result: {result}"
            )
            self.print_step(6, "All results and node ACL state changes observed/logged.")

        finally:
            self.print_step(7, "Restoring original ACL (cleanup)")
            try:
                await self.set_acl(orig_acl)
            except Exception as e:
                log.warning(f"Failed to restore original ACL post-test: {e}")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Notes:**
- Save this as `tests/test_TC_CSA_REMOVEACL_0001.py`.
- Test runner must provide a group member controller (`self.group_member_controller`) representing a principal with the right CAT/group credentials.
- All steps include print_step annotations for traceability, and post-test cleanup restores the original ACL.
- On error, asserts and logging output the relevant status.
- Replace `RemoveACLFromNode` with the precise command in your cluster interface if differently named or located.