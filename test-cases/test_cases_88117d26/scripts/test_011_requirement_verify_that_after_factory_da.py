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
import logging

import matter.clusters as Clusters
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

log = logging.getLogger(__name__)

class TC_CSA_ACL_RESET_0001(MatterBaseTest):
    """
    Test Case: TC-CSA-ACL-RESET-0001
    Requirement: CSA-ACL-REQ-FDR-001

    Verifies that after a Factory Data Reset (FDR), the device's Access Control List (ACL) is empty.
    """

    @async_test_body
    async def test_acl_is_empty_after_factory_data_reset(self):
        # Step 1: Read and record the current contents of the Node’s ACL (assert at least one entry exists)
        self.print_step(1, "Read and record the Node's ACL before FDR, verify at least one ACE exists")
        acl_before = await self.read_single_attribute_check_success(
            endpoint=0,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl
        )
        log.info(f"ACL before factory reset: {acl_before}")
        asserts.assert_is_instance(acl_before, list, "ACL should be a list of ACEs.")
        asserts.assert_greater(len(acl_before), 0, "There must be at least one entry in ACL before FDR.")

        # Step 2: Initiate Factory Data Reset (FDR)
        self.print_step(2, "Send FactoryReset command to the device.")
        try:
            # The AdministratorCommissioning cluster is typically at endpoint 0
            await self.send_single_cmd(
                cmd=Clusters.AdministratorCommissioning.Commands.FactoryReset(),
                endpoint=0
            )
        except InteractionModelError as e:
            # Some implementations may close the session immediately and return no response, treat as success if disconnected.
            if e.status not in (Status.Success, Status.Busy):
                asserts.fail(f"Factory Reset command failed: {e}")

        # Step 3: Wait for node to fully restart after FDR
        self.print_step(3, "Wait for device to fully restart and complete Factory Data Reset.")
        await self.default_controller.WaitForDeviceReset(self.dut_node_id)  # This uses the test infra's helper
        # Optionally, add a short sleep if necessary for actual hardware restarts:
        # import asyncio; await asyncio.sleep(5)

        # Step 4: Re-establish communication with the Node (test infra should recommission post-FDR automatically)
        self.print_step(4, "Re-establish secure communication with the Node after FDR.")
        await self.matter_test_config.ensure_commissioned(self.default_controller, self.dut_node_id)

        # Step 5/6: Read ACL again from device; verify ACL is empty (zero entries)
        self.print_step(5, "Read ACL after FDR and verify there are zero entries.")
        acl_after = await self.read_single_attribute_check_success(
            endpoint=0,
            cluster=Clusters.AccessControl,
            attribute=Clusters.AccessControl.Attributes.Acl
        )
        log.info(f"ACL after factory reset: {acl_after}")
        asserts.assert_is_instance(acl_after, list, "ACL after FDR should be a list.")
        asserts.assert_equal(len(acl_after), 0, "ACL must be empty after Factory Data Reset.")

        self.print_step(6, "Verified ACL is empty post-Factory Data Reset. Test complete.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions/Notes:**
- Save as `tests/test_TC_CSA_ACL_RESET_0001.py`.
- This script follows your project's consistent test file format and logging conventions.
- `WaitForDeviceReset` and `ensure_commissioned` are assumed helper utilities in your test harness; adjust if your infra requires manual polling/recommissioning after FDR.
- If your device inserts required default ACEs after reset (per spec or vendor config), adjust the assertion or mark these exceptions (else, truly expect zero entries).
- All test steps (step comments and loggings) match the manual test case citation.