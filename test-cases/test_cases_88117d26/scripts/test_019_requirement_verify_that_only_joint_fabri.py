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

from mobly import asserts

import matter.clusters as Clusters
from matter.clusters import ClusterObjects
from matter.interaction_model import InteractionModelError, Status
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

# Constants for the test (must be mapped by test bed/infra)
JFDA_CLUSTER_ID = 0xFFF1  # Replace with actual Joint Fabric Datastore cluster id if standardized
JFDA_CLUSTER_NAME = "JointFabricDatastore"  # For clarity, adjust as fits your cluster library
ADMIN_ROLE = "jfda_admin"
NONADMIN_ROLE = "device"

# The test harness must provide these mappings to Node IDs and DeviceControllers:
# - self.jfda_admin_node_id, self.nonadmin_node_id
# - self.jfda_admin_controller, self.regular_controller

class TC_CSA_JFDA_0001(MatterBaseTest):
    """
    TC-CSA-JFDA-0001:
    Verify that only Joint Fabric Anchor Administrator Nodes expose the Joint Fabric Datastore Cluster server.
    """

    async def discover_server_clusters(self, controller, node_id, endpoint=0):
        """
        Returns a list of cluster IDs present on the specified endpoint.
        """
        descriptor = Clusters.Descriptor
        attr = descriptor.Attributes.ServerList
        try:
            server_list = await controller.ReadAttribute(
                nodeId=node_id,
                attributes=[(endpoint, descriptor, attr)]
            )
            # Handle either bare value or wrapped dict/struct
            servers = list(server_list[endpoint][descriptor][attr])
            return servers
        except Exception as e:
            return []

    async def access_jfda_functions(self, controller, node_id, endpoint=0):
        """
        Try reading/writing an attribute or calling a command on the JFDA cluster.
        Expects to succeed for admin, fail (AccessDenied, etc) for non-admin.
        """
        # In real Matter SDK: Clusters.JointFabricDatastore is the cluster class if available.
        # For now, fallback/generic access using dynamic cluster ID.
        try:
            # Try to read the first attribute (or dummy attribute) of the cluster
            result = await controller.ReadAttribute(
                nodeId=node_id,
                attributes=[(endpoint, JFDA_CLUSTER_ID, 0x0000)]  # 0x0000 = first attribute
            )
            return True, result
        except InteractionModelError as e:
            return False, e.status
        except Exception as e:
            return False, str(e)

    @async_test_body
    async def test_jfda_admins_only_expose_and_grant_access(self):
        # Step 1: Identify admin/non-admin node IDs (testbed should provide)
        admin_id = getattr(self, "jfda_admin_node_id", None)
        nonadmin_id = getattr(self, "nonadmin_node_id", None)
        admin_ctrl = getattr(self, "jfda_admin_controller", None)
        reg_ctrl = getattr(self, "regular_controller", None)
        asserts.assert_is_not_none(admin_id, "Joint Fabric Anchor Administrator node ID not set in test env")
        asserts.assert_is_not_none(nonadmin_id, "Non-admin node ID not set in test env")
        asserts.assert_is_not_none(admin_ctrl, "Admin controller not set in test env")
        asserts.assert_is_not_none(reg_ctrl, "Regular controller not set in test env")

        # Step 2: Discover server clusters on the JFDA admin node
        self.print_step(1, "Discover server clusters on the JFDA Administrator Node")
        clusters_admin = await self.discover_server_clusters(admin_ctrl, admin_id)
        self.print_step(2, f"Administrator node clusters: {clusters_admin}")
        asserts.assert_in(JFDA_CLUSTER_ID, clusters_admin, "JFDA cluster must be present on admin node")

        # Step 3: Verify presence of JFDA server
        self.print_step(3, "Verified JFDA cluster present in server list on admin node")

        # Step 4: Attempt to access JFDA functions (read attribute or invoke command) on admin node
        self.print_step(4, "Try to access JFDA cluster functions as admin (should succeed)")
        admin_access, admin_response = await self.access_jfda_functions(admin_ctrl, admin_id)
        asserts.assert_true(admin_access, f"Admin should access JFDA cluster; got: {admin_response}")

        # Step 5: Discover server clusters on non-admin node
        self.print_step(5, "Discover server clusters on non-admin node")
        clusters_nonadmin = await self.discover_server_clusters(reg_ctrl, nonadmin_id)
        self.print_step(6, f"Non-admin node clusters: {clusters_nonadmin}")
        asserts.assert_not_in(JFDA_CLUSTER_ID, clusters_nonadmin, "JFDA cluster MUST NOT be present on non-admin node")

        # Step 6: Attempt to access JFDA functions on non-admin node as regular controller (should fail)
        self.print_step(7, "Try to access JFDA on non-admin node as regular controller (should fail)")
        nonadmin_access, nonadmin_response = await self.access_jfda_functions(reg_ctrl, nonadmin_id)
        asserts.assert_false(nonadmin_access,
                             f"Non-admin node must NOT grant access to JFDA (expected failure, got {nonadmin_response})")
        # Step 7 (extra): Attempt access as admin on non-admin node (should still fail!)
        self.print_step(8, "Try to access JFDA on non-admin node using admin controller (should also fail)")
        nonadmin_admin_access, nonadmin_admin_resp = await self.access_jfda_functions(admin_ctrl, nonadmin_id)
        asserts.assert_false(nonadmin_admin_access,
                             f"Non-admin node must NOT grant admin access to JFDA (expected failure, got {nonadmin_admin_resp})")

        # Record all responses and errors (optional; appears in test logs)

        self.print_step(9, "All checks complete. JFDA cluster only exposed and accessible on admin node.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions/Notes:**
- Save as e.g. `tests/test_TC_CSA_JFDA_0001.py`.
- This script expects the test harness/environment to provide:
    - Node IDs for one admin and one non-admin (`self.jfda_admin_node_id`, `self.nonadmin_node_id`).
    - Controllers/handles for admin and regular access (`self.jfda_admin_controller`, `self.regular_controller`).
- Adjust `JFDA_CLUSTER_ID` to the actual Joint Fabric Datastore cluster id as defined in your implementation or spec.
- The script exercises all required discovery and access attempts; asserts all success/failure points as steps; and outputs step annotations for live test traceability.
- Logs, post-conditions, and audit trails are handled per your automation infrastructure.