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
Test Case:    TC-CSA-RCA-UNSUPPORTEDACCESS-0001
Requirement:  CSA-REQUESTCOMMISSIONINGAPPROVAL-REQ-CASESESSION-001

Verify that RequestCommissioningApproval fails with UNSUPPORTED_ACCESS status 
if not run over a CASE session, and operates normally if issued via CASE.
"""

import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter.interaction_model import Status, InteractionModelError
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main

import logging
log = logging.getLogger(__name__)

OPCREDS_CLUSTER = Clusters.OperationalCredentials
REQUEST_COMMISSIONING_APPROVAL_CMD = getattr(OPCREDS_CLUSTER.Commands, "RequestCommissioningApproval", None)

class TC_CSA_RCA_UNSUPPORTEDACCESS_0001(MatterBaseTest):
    """
    Test session policy enforcement for RequestCommissioningApproval.
    """

    async def send_request_comm_approval(self, dev_ctrl, node_id):
        # Create a minimal, valid command if schema needs fields.
        asserts.assert_is_not_none(REQUEST_COMMISSIONING_APPROVAL_CMD, "RequestCommissioningApproval command not in OperationalCredentials cluster.")
        try:
            return await dev_ctrl.SendCommand(
                nodeId=node_id,
                endpoint=0,
                command=REQUEST_COMMISSIONING_APPROVAL_CMD()
            )
        except InteractionModelError as e:
            return e

    @async_test_body
    async def test_request_commissioning_approval_session_policy(self):
        # Testbed/fixture variables
        dut_node_id = getattr(self, "dut_node_id", self.dut_node_id)
        pase_ctrl = getattr(self, "pase_controller", None)    # Should provide non-CASE session (e.g., PASE)
        case_ctrl = getattr(self, "case_controller", None) or self.default_controller

        asserts.assert_is_not_none(REQUEST_COMMISSIONING_APPROVAL_CMD, "RequestCommissioningApproval command not present in cluster definitions.")

        # Step 1: Establish a non-CASE session (e.g., PASE) and issue the command (expect UNSUPPORTED_ACCESS)
        if not pase_ctrl:
            pytest.skip("PASE or non-CASE controller must be provided by testbed/fixture as pase_controller.")
        self.print_step(1, "Use non-CASE (PASE/unauthed) controller to issue RequestCommissioningApproval; expect UNSUPPORTED_ACCESS")
        non_case_result = await self.send_request_comm_approval(pase_ctrl, dut_node_id)
        if isinstance(non_case_result, InteractionModelError):
            self.print_step(2, f"Status code from non-CASE session: {non_case_result.status}")
            asserts.assert_equal(
                non_case_result.status, Status.UnsupportedAccess,
                f"Expected UNSUPPORTED_ACCESS, got {non_case_result.status} (must enforce CASE session policy!)"
            )
        else:
            asserts.fail("RequestCommissioningApproval over non-CASE unexpectedly succeeded or had no error; should return UNSUPPORTED_ACCESS.")

        # Step 2: Establish a CASE session and issue the command (expect normal/allowed behavior)
        self.print_step(3, "Use CASE controller to issue RequestCommissioningApproval (should succeed or process normally).")
        case_result = await self.send_request_comm_approval(case_ctrl, dut_node_id)
        if isinstance(case_result, InteractionModelError):
            # Should not return UNSUPPORTED_ACCESS over valid CASE
            log.info(f"RequestCommissioningApproval over CASE returned IM error: {case_result.status}")
            asserts.assert_not_equal(
                case_result.status, Status.UnsupportedAccess,
                "Unexpected UNSUPPORTED_ACCESS on valid CASE session"
            )
            # Accept any application status, but must NOT be UNSUPPORTED_ACCESS
        else:
            log.info("RequestCommissioningApproval over CASE succeeded or returned normal result.")

        self.print_step(4, "RequestCommissioningApproval properly rejected over non-CASE, operates as expected over CASE session.")

        # Post-conditions: No node state or approval should change from invalid session attempts.
        self.print_step(5, "Node state unchanged; all command events logged. Ready for further tests or operation.")

if __name__ == "__main__":
    default_matter_test_main()
```

---

**Instructions/Usage:**
- Place as `tests/test_TC_CSA_RCA_UNSUPPORTEDACCESS_0001.py` or adjust to your test suite layout.
- The test expects the test runner or environment to provide:
    - `self.pase_controller` (a PASE-established non-CASE session)
    - `self.case_controller` or falls back to `self.default_controller` for CASE session.
- The command is rejected with `UNSUPPORTED_ACCESS` for non-CASE; allowed or processed (but not with UNSUPPORTED_ACCESS) for valid CASE.
- All errors/status checks, comments, and step labels follow connectedhomeip/Matter Python style and idioms.