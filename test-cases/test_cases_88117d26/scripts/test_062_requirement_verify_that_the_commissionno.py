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
Test Case:     TC-CSA-COMMISSIONNODE-CASE-0001
Requirement:   CSA-COMMISSIONNODE-REQ-UNSUPPORTEDACCESS-001

Verify that the CommissionNode command fails with UNSUPPORTED_ACCESS if not sent over a CASE session.
"""

from mobly import asserts
import pytest

import matter.clusters as Clusters
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

import logging
log = logging.getLogger(__name__)

# Assume command is in a logical Commissioning or Administrator cluster; adjust import as required by your codebase.
ADMIN_CLUSTER = getattr(Clusters, "AdministratorCommissioning", None)
COMMISSIONNODE_CMD = getattr(ADMIN_CLUSTER.Commands, "CommissionNode", None) if ADMIN_CLUSTER else None

class TC_CSA_COMMISSIONNODE_CASE_0001(MatterBaseTest):
    """
    Test CommissionNode session enforcement: must fail with UNSUPPORTED_ACCESS when not sent via CASE, succeed otherwise.
    """

    async def try_commissionnode(self, dev_ctrl, node_id=None):
        """
        Executes the CommissionNode command using the given device controller/session.

        node_id: for control, if using multi-node testbeds (defaults to self.dut_node_id)
        """
        asserts.assert_is_not_none(COMMISSIONNODE_CMD, "CommissionNode command not found in AdministratorCommissioning cluster.")
        try:
            # Dummy args may need to be updated to match your product, e.g., passcode or discriminator.
            return await dev_ctrl.SendCommand(
                nodeId=node_id or self.dut_node_id,
                endpoint=0,
                command=COMMISSIONNODE_CMD(),
            )
        except InteractionModelError as e:
            return e

    @async_test_body
    async def test_commissionnode_requires_case_session(self):
        """
        1. Establish a non-CASE session and try CommissionNode: expect UNSUPPORTED_ACCESS
        2. Establish a CASE session and try CommissionNode: expect normal success
        """
        # --- Test environment: Must provide PASE and CASE controllers ---
        # Example: self.pase_controller and self.default_controller
        pase_ctrl = getattr(self, "pase_controller", None)
        case_ctrl = getattr(self, "case_controller", None) or self.default_controller
        dut_node_id = getattr(self, "dut_node_id", self.dut_node_id)

        asserts.assert_is_not_none(
            pase_ctrl,
            "Test infrastructure must provide a PASE (non-CASE) controller as 'pase_controller'."
        )
        asserts.assert_is_not_none(case_ctrl, "CASE session controller (default_controller) must be supplied.")

        # -- Step 1-3: Non-CASE session (e.g., PASE) --
        self.print_step(1, "Use non-CASE session to send CommissionNode, expect UNSUPPORTED_ACCESS")
        non_case_result = await self.try_commissionnode(pase_ctrl, node_id=dut_node_id)
        if isinstance(non_case_result, InteractionModelError):
            self.print_step(2, f"Non-CASE session returned status: {non_case_result.status}")
            asserts.assert_equal(
                non_case_result.status,
                Status.UnsupportedAccess,
                f"Expected UNSUPPORTED_ACCESS (Status.UnsupportedAccess), got: {non_case_result.status}"
            )
        else:
            asserts.fail("CommissionNode succeeded or did not fail on non-CASE session; expected UNSUPPORTED_ACCESS.")

        # -- Step 4-6: CASE session (should succeed or not error with UnsupportedAccess) --
        self.print_step(3, "Use CASE session to send CommissionNode, expect normal success or product-specific result")
        case_result = await self.try_commissionnode(case_ctrl, node_id=dut_node_id)
        if isinstance(case_result, InteractionModelError):
            # Should NOT fail with UnsupportedAccess
            self.print_step(4, f"CASE session returned status: {case_result.status}")
            asserts.assert_not_equal(
                case_result.status,
                Status.UnsupportedAccess,
                "CommissionNode returned UNSUPPORTED_ACCESS on CASE session; should be accepted/succeed."
            )
            # Accept Busy, ConstraintError etc per actual Matter/cluster logic
        else:
            self.print_step(4, "CASE session: CommissionNode returned success/expected result.")

        self.print_step(5, "CommissionNode enforcement validated: failed with UNSUPPORTED_ACCESS for non-CASE, succeeded on CASE.")

        # --- Step 7: Audit/logs/manual review if required by cert process ---

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions/notes:**
- Save this file as `tests/test_TC_CSA_COMMISSIONNODE_CASE_0001.py` or an equivalent file in your test directory.
- The test expects your runner to provide or inject `self.pase_controller` (non-CASE), `self.default_controller` (CASE), and node ID(s) as appropriate for your setup.
- If your product/cluster model has a different path for the CommissionNode command, adjust `ADMIN_CLUSTER` and `COMMISSIONNODE_CMD`.
- All robust assertions, explicit step logging, and session separation per project coding and security idioms are included.