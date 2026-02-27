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

from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

REQUIRED_FIELDS = [
    "fabricIndex",
    "privilege",
    "authMode",
    "targets",
    "subjects"
]

def __ace_field_present(entry, name):
    # Accept both .name (dataclass/namespace) or dict["name"]
    return hasattr(entry, name) or (isinstance(entry, dict) and name in entry)

def __ace_field_value(entry, name):
    return getattr(entry, name, None) if hasattr(entry, name) else entry.get(name, None)

class TC_CSA_ACE_0001(MatterBaseTest):
    """
    TC-CSA-ACE-0001:
    Verify that each Access Control Entry (ACE) in the ACL contains the required fields:
    FabricIndex, Privilege level, AuthMode, list of target Clusters, and list of source Subjects.
    """

    @async_test_body
    async def test_acl_ace_required_fields(self):
        #
        # Step 1: Read the complete ACL attribute
        #
        self.print_step(1, "Read ACL attribute from device.")
        acl_entries = await self.read_single_attribute_check_success(
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl,
            endpoint=0,
        )
        asserts.assert_is_instance(acl_entries, list, "ACL attribute should be a list of ACEs.")
        asserts.assert_true(len(acl_entries) > 0, "ACL list should have at least one ACE.")

        #
        # Steps 2-9: For each ACE, inspect and check required fields
        #
        missing_fields_by_entry = []
        invalid_fields_by_entry = []

        for idx, ace in enumerate(acl_entries):
            entry_info = f"ACE[{idx}]"

            # --- Step 3: FabricIndex ---
            asserts.assert_true(
                __ace_field_present(ace, "fabricIndex"),
                f"{entry_info} missing fabricIndex"
            )
            fabric_index = __ace_field_value(ace, "fabricIndex")
            asserts.assert_is_not_none(
                fabric_index, f"{entry_info} fabricIndex is None"
            )
            asserts.assert_true(
                isinstance(fabric_index, int) and fabric_index > 0,
                f"{entry_info} fabricIndex should be a positive integer"
            )

            # --- Step 4: Privilege ---
            asserts.assert_true(
                __ace_field_present(ace, "privilege"),
                f"{entry_info} missing privilege"
            )
            privilege = __ace_field_value(ace, "privilege")
            # Expect int (enum), check range (per spec) or string (enum name)
            asserts.assert_true(
                isinstance(privilege, int) or isinstance(privilege, str),
                f"{entry_info} privilege should be enum int or str"
            )

            # --- Step 5: AuthMode ---
            asserts.assert_true(
                __ace_field_present(ace, "authMode"),
                f"{entry_info} missing authMode"
            )
            auth_mode = __ace_field_value(ace, "authMode")
            asserts.assert_true(
                isinstance(auth_mode, int) or isinstance(auth_mode, str),
                f"{entry_info} authMode should be enum int or str"
            )

            # --- Step 6: Targets (list of target clusters, endpoints, device types) ---
            asserts.assert_true(
                __ace_field_present(ace, "targets"),
                f"{entry_info} missing targets"
            )
            targets = __ace_field_value(ace, "targets")
            asserts.assert_false(
                targets is None,
                f"{entry_info} targets is None"
            )
            # Per Matter spec, this can be empty (wildcard), but must be present as list or list-like
            asserts.assert_true(
                isinstance(targets, list),
                f"{entry_info} targets must be a list"
            )
            # Each element in targets should be a TargetStruct, or dict, or equivalent with at least one identifier
            for t in targets:
                has_any = (
                    __ace_field_present(t, "cluster") or
                    __ace_field_present(t, "endpoint") or
                    __ace_field_present(t, "deviceType")
                )
                asserts.assert_true(
                    has_any,
                    f"{entry_info} target missing all optional target fields"
                )

            # --- Step 7: Subjects (list of subject Node IDs or CATs, may be empty for wildcard) ---
            asserts.assert_true(
                __ace_field_present(ace, "subjects"),
                f"{entry_info} missing subjects"
            )
            subjects = __ace_field_value(ace, "subjects")
            asserts.assert_false(
                subjects is None,
                f"{entry_info} subjects is None"
            )
            asserts.assert_true(
                isinstance(subjects, list),
                f"{entry_info} subjects must be a list"
            )
            # Each subject: expecting int (nodeid or CAT val)
            for subject in subjects:
                asserts.assert_true(
                    isinstance(subject, int),
                    f"{entry_info} subjects entry '{subject}' must be int (nodeid or CAT)"
                )

            # --- Step 8-9: Record per-ACE result (here just verify, no output if all OK) ---
            # (Optional: could append detailed info to a log or result collector.)

        #
        # Step 10: If we got here, all ACEs have been checked and are valid as per requirement
        #
        self.print_step(2, "All ACEs in ACL contain required fields with valid values.")

if __name__ == "__main__":
    default_matter_test_main()
```

**Instructions:**
- Save as `tests/test_TC_CSA_ACE_0001.py` (or similar, in your test directory).
- This script uses the project’s standard MatterBaseTest, async_test_body decoration, and mobly assertions for consistency.
- The script reads the ACL from the DUT, then validates for each Access Control Entry:
    - The presence and type of all required fields (fabricIndex, privilege, authMode, targets, subjects).
    - That all values are syntactically valid (not None, proper types, etc.).
    - All required fields are present for every ACE.
- The script prints out logical steps for traceability (similar to referenced tests).
- No device settings are changed, ensuring the ACL state remains as found.

**Note:** If your schema uses slightly different attribute or field names than shown, adjust the attribute accesses accordingly. The script is robust for both Namespace and dict forms.