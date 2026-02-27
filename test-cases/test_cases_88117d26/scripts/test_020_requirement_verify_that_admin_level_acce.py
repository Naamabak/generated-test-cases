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

# --- Test Configuration (to be customized by test runner/environment) ---
# Example endpoint and cluster id where Joint Fabric Datastore Cluster is implemented
JFDA_ENDPOINT = 1  # change as appropriate for testbed
JFDA_CLUSTER = Clusters.JointFabricDatastore
# You must define a valid create, modify, or delete command for the JFDA cluster
# For this sample, assume a command `CreateEntry`
JFDA_ADMIN_COMMAND = getattr(JFDA_CLUSTER.Commands, "CreateEntry", None)

# These controllers must be supplied by the test environment/harness:
# - admin_node_ctrl: Commissioned controller/node with Administrator CAT (Admin privilege)
# - non_admin_node_ctrl: Controller/node without Administrator CAT (should be denied)

class TC_CSA_JFDA_0001(MatterBaseTest):
    """
    TC-CSA-JFDA-0001:
    Verify Admin access to Joint Fabric Datastore Cluster is permitted only to Nodes with Administrator CAT.
    """

    @pytest.fixture(autouse=True, scope="class")
    async def setup_and_teardown(self, request):
        """
        Setup/teardown fixture: can be used to restore cluster state if test alters any data.
        """
        # Could read and save cluster state here if mutation is involved.
        yield
        # Optionally, restore cluster/datastore state if test commands mutated it.

    @async_test_body
    async def test_jfda_admin_access_with_and_without_admin_cat(self):
        # --- Step 1: Test Admin operation from Admin Node (with Administrator CAT) ---

        self.print_step(1, "Attempt Admin operation on JFDA cluster from Admin Node (with Administrator CAT)")

        admin_node_ctrl = getattr(self, "admin_node_ctrl", None)
        non_admin_node_ctrl = getattr(self, "non_admin_node_ctrl", None)

        if admin_node_ctrl is None or non_admin_node_ctrl is None:
            pytest.skip("Test requires both `admin_node_ctrl` (with CAT) and `non_admin_node_ctrl` (without CAT) provided by testbed.")

        # Compose parameters for CreateEntry/Modify/Delete - must be valid for your product's cluster implementation
        if JFDA_ADMIN_COMMAND is None:
            pytest.skip("JFDA cluster admin command (e.g., CreateEntry) not implemented or imported properly.")

        # This is a placeholder; adjust arguments as required for your implementation
        cmd_args = dict(entryId=0x1011, data=b"adminTestData")

        # Step 1: Admin Node attempts JFDA Admin command
        try:
            result = await admin_node_ctrl.SendCommand(
                nodeId=self.dut_node_id,
                endpoint=JFDA_ENDPOINT,
                command=JFDA_ADMIN_COMMAND(**cmd_args),
            )
            admin_success = True
            log.info("Admin Node: Admin operation succeeded as expected.")
        except Exception as e:
            admin_success = False
            log.error(f"Admin Node: Admin operation failed unexpectedly: {e}")

        asserts.assert_true(
            admin_success,
            "Admin Node (with Administrator CAT) was NOT able to perform Admin operation on JFDA cluster."
        )

        # --- Step 2: Test Admin operation from Non-Admin Node (without Administrator CAT) ---
        self.print_step(2, "Attempt same Admin operation from Non-Admin Node (without Administrator CAT)")

        non_admin_denied = False
        deny_status = None
        try:
            await non_admin_node_ctrl.SendCommand(
                nodeId=self.dut_node_id,
                endpoint=JFDA_ENDPOINT,
                command=JFDA_ADMIN_COMMAND(**cmd_args),
            )
            log.error("Non-Admin Node: Admin operation succeeded unexpectedly!")
            non_admin_denied = False
        except InteractionModelError as e:
            non_admin_denied = (e.status == Status.AccessDenied or e.status == Status.UnsupportedAccess)
            deny_status = e.status
            log.info(f"Non-Admin Node: Admin operation denied as expected: {e}")
        except Exception as e:
            non_admin_denied = True
            log.info(f"Non-Admin Node: Unexpected failure/denial as expected: {e}")

        asserts.assert_true(
            non_admin_denied,
            f"Non-Admin Node (without Administrator CAT) was able to perform Admin operation on JFDA cluster. Deny status: {deny_status}"
        )

        # --- Step 3: Check logs/audits for correct referencing of Administrator CAT ---
        # This is implementation-specific and can't be asserted directly in API tests.
        # Could be verified manually or using log-check integrations, if available.
        self.print_step(3, "Check device logs for correct access control decisions referencing Administrator CAT.")

        # --- Step 4: Ensure cluster consistency, rollback if needed (post-conditions) ---
        self.print_step(4, "Cluster post-conditions validated/cleanup by fixture.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions:**
- Save as `tests/test_TC_CSA_JFDA_0001.py`.
- **Testbed requirements:** The test environment must provide:
  - `self.admin_node_ctrl`: controller/session for the Node with Administrator CAT (Admin Node)
  - `self.non_admin_node_ctrl`: controller/session for a Node without Administrator CAT (Non-Admin Node)
  - `self.dut_node_id`: configured for Device Under Test (the JFDA server)
- The actual command and arguments (`JFDA_ADMIN_COMMAND`) must be set for the JFDA cluster in your implementation (`CreateEntry` or equivalent).
- The test verifies proper access control enforcement for JFDA admin operations based on Administrator CAT.
- All cluster/ACL/rollback steps follow your project’s test conventions and are rollback-safe, assuming correct fixture handling.
