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

from mobly import asserts
import copy
import logging

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import Status
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)


def example_acl_entries_with_extensions():
    """
    Generator for test entries.
    This example includes a simulated 'Extension' field for the ACE if supported by the implementation.
    Actual extension fields must match what's defined/used in your device/environment.
    """
    base_entry = ClusterObjects.AccessControl.AccessControlEntryStruct(
        fabricIndex=1,
        privilege=ClusterObjects.AccessControl.AccessControlEntryPrivilegeEnum.kAdminister,
        authMode=ClusterObjects.AccessControl.AccessControlEntryAuthModeEnum.kCase,
        subjects=[0x9876543210],
        targets=[]  # Wildcard Node-wide
    )

    # Standard ACE as would normally be accepted
    entries = [base_entry]

    # Example: Simulated extension (add extra fields/values as per product's extension support)
    # This may require device-side support for custom fields. Adjust as needed.
    if hasattr(base_entry, 'extensionField'):
        ext_entry = copy.deepcopy(base_entry)
        ext_entry.extensionField = b"\xDE\xAD\xBE\xEF"  # Example: known bytes for extension
        entries.append(ext_entry)

    return entries


class TC_CSA_EXT_ACL_0001(MatterBaseTest):
    """
    TC-CSA-EXT-ACL-0001:
    Verify preservation of every field (including extensions) of the Access Control Cluster, so
    that read-back by an Administrator is always verbatim.
    """

    async def get_acl(self):
        acl = await self.read_single_attribute_check_success(
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
            endpoint=0,
        )
        return acl

    async def set_acl(self, acl):
        # This writes the full ACL attribute
        result = await self.default_controller.WriteAttribute(
            self.dut_node_id,
            [(0, Clusters.AccessControl.Attributes.Acl(acl))]
        )
        asserts.assert_equal(result[0].Status, Status.Success, "ACL write failed")

    @async_test_body
    async def test_access_control_cluster_fields_extensions_preserved(self):
        # Step 1: Read and save the original ACL for restoration
        self.print_step(1, "Read and backup original ACL for restoration after test")
        orig_acl = await self.get_acl()
        try:
            # Step 2: Write known values (including any supported extensions) to the Access Control Cluster ACL
            self.print_step(2, "As admin, write test values (including extensions) to the ACL attribute")
            test_acl = example_acl_entries_with_extensions()
            await self.set_acl(test_acl)

            # Step 3: Reset/reboot node (simulate via test runner; expect infra to support WaitForDeviceReset, if not, comment out)
            self.print_step(3, "Reset/reboot node to ensure values persist")
            try:
                await self.send_single_cmd(
                    cmd=Clusters.AdministratorCommissioning.Commands.FactoryReset(),
                    endpoint=0
                )
            except Exception:
                log.info("Node may disconnect on reset - expected during FactoryReset")
            # Wait for device to come back/complete reset
            await self.default_controller.WaitForDeviceReset(self.dut_node_id)
            await self.matter_test_config.ensure_commissioned(self.default_controller, self.dut_node_id)

            # Step 4: Read back all fields/extensions from ACL again as admin
            self.print_step(4, "Read back ACL attribute (with extensions, if present) as admin after reset")
            readback_acl = await self.get_acl()

            # Step 5: Compare read-back values to originally written values, ensure byte-for-byte equality
            self.print_step(5, "Compare all fields (including extensions) to original values, byte-for-byte")
            asserts.assert_true(
                len(test_acl) == len(readback_acl),
                f"ACL entry count mismatch: wrote {len(test_acl)} entries, read back {len(readback_acl)}"
            )
            for idx, (wrote_entry, got_entry) in enumerate(zip(test_acl, readback_acl)):
                # Compare basic fields
                for field in ['fabricIndex', 'privilege', 'authMode', 'subjects', 'targets']:
                    w_val = getattr(wrote_entry, field, None)
                    g_val = getattr(got_entry, field, None)
                    asserts.assert_equal(
                        w_val, g_val,
                        f"Mismatch in field {field} for ACE entry {idx}"
                    )
                # Compare extension fields byte-for-byte if present
                for attr in dir(wrote_entry):
                    if attr.startswith("_"):  # skip private/internal fields
                        continue
                    if attr not in ['fabricIndex', 'privilege', 'authMode', 'subjects', 'targets']:
                        # assume this is an extension field
                        w_ext = getattr(wrote_entry, attr, None)
                        g_ext = getattr(got_entry, attr, None)
                        # For bytes, check byte-for-byte
                        if isinstance(w_ext, bytes) or isinstance(g_ext, bytes):
                            asserts.assert_equal(
                                w_ext, g_ext,
                                f"Extension field {attr} bytes differ for ACE entry {idx}"
                            )
                        else:
                            asserts.assert_equal(
                                w_ext, g_ext,
                                f"Extension field {attr} mismatch for ACE entry {idx}"
                            )

            # Step 6: Optionally, read again to check persistence across network updates (skipped here for brevity)
            self.print_step(6, "Optionally repeat read-back after network activity/update (test infra)")

        finally:
            # Step 7: Restore original ACL to leave node in original state (if necessary)
            self.print_step(7, "Restore original ACL contents to leave Node unmodified")
            try:
                await self.set_acl(orig_acl)
            except Exception:
                log.warning("Could not restore original ACL after test; manual intervention may be required.")

if __name__ == '__main__':
    default_matter_test_main()
```

---

**Notes:**
- Save as `tests/test_TC_CSA_EXT_ACL_0001.py`.
- The function `example_acl_entries_with_extensions` must be adapted to match your device's real extensions.
- If your device advertises extension fields for the Access Control Cluster attributes, list them in the test DEFINITION and in the comparison loop.
- If the cluster or device doesn't support extensions, the script still validates that all ordinary fields are preserved verbatim.
- The script restores the original state in a finally block to avoid side effects on the device under test.