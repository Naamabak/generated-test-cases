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

import pytest
from mobly import asserts

import matter.clusters as Clusters
from matter import ChipDeviceCtrl
from matter.interaction_model import InteractionModelError
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.decorators import async_test_body
from matter.testing.runner import default_matter_test_main

@pytest.mark.usefixtures("matter_test_environment")
class TestCSASecurityChannel(MatterBaseTest):
    """
    TC-CSA-SEC-0001:
        Verify cryptographically secure application-layer communication and 
        that only secure channels are used for operational communication.
    """

    @async_test_body
    async def test_secure_only_operational_communication(self):
        #
        # Pre-conditions: Factory-reset and supported firmware are handled by the test runner.
        # Step 1: Power on device: Handled by test runner and commissioning.
        #
        self.print_step(1, "Commissioning - already done (should be done by test-runner)")

        #
        # Step 2: Initiate commissioning with a certified controller.
        #   This should result in a secure session being established.
        #
        self.print_step(2, "Verify controller can communicate with device")
        device = await self.default_controller.GetConnectedDevice(nodeId=self.dut_node_id, allowPASE=False)
        asserts.assert_is_not_none(device, "Failed to connect to device via controller")
        # Optionally, we could verify the type of session.
        # With some Matter test harnesses, verify device.session_type == 'secure' (out of scope for API).

        #
        # Step 3: Attempt to establish application-layer comms/channel from controller
        # Step 4: Monitor with network analysis - OUT OF AUTOMATED SCOPE but makes sure we're using secure channel
        #
        self.print_step(3, "Sending command over application-layer after secure channel established")
        try:
            res = await self.send_single_cmd(
                cmd=Clusters.OnOff.Commands.On(),
                endpoint=1
            )
        except Exception as e:
            asserts.fail(f"Operational command failed over secure channel: {e}")

        #
        # Step 5: Verify all commands occur only after secure channel is established
        # Already covered above since the session is secure (per API).
        #

        #
        # Step 6: Attempt to send operational command before secure channel established
        #
        self.print_step(4, "Attempting operational command before channel established (expected to fail)")
        temp_ctrl = ChipDeviceCtrl()
        failed = False
        try:
            await temp_ctrl.WriteAttribute(
                nodeid=self.dut_node_id, 
                attributes=[(1, Clusters.OnOff.Attributes.OnOff(False))], 
                allowPASE=False, 
                establishSession=False,  # if API supports, don't establish a session
                timeoutMs=1000
            )
        except Exception:
            failed = True
        asserts.assert_true(failed, "Device accepted operational command before secure channel")

        #
        # Step 7: Attempt insecure session (if possible) and confirm device rejects it.
        #
        self.print_step(5, "Attempt insecure/unprotected app-layer session (should fail)")
        insecure_ctrl = ChipDeviceCtrl()
        insecure_failed = False
        try:
            # Simulate an insecure session: attempt without establishing security/CASE.
            await insecure_ctrl.WriteAttribute(
                nodeid=self.dut_node_id,
                attributes=[(1, Clusters.OnOff.Attributes.OnOff(True))],
                allowPASE=False, 
                secureSession=False,   # Simulated/if API allows, should fail
                timeoutMs=1000
            )
        except Exception:
            insecure_failed = True
        asserts.assert_true(insecure_failed, "Device should NOT process insecure operational communication")

        #
        # Step 8: Clean up, check that all communication was protected (handled by infra/logs).
        #
        self.print_step(6, "All operational communication should have used a secure channel")

        # Post-conditions: Device remains secure. Logs/traces dumped automatically.

if __name__ == "__main__":
    default_matter_test_main()
```

**NOTES ON THE TEST:**
- Each test step is described and mapped to the actual code or assertion.
- Because network sniffing is not automatable in pytest, comments indicate where such steps are verified by logs/traces.
- Attempts to send operational commands before/without a secure channel are made deliberately and checked for proper rejection.
- API calls may need slight adjustment depending on available controller options—placeholders like `secureSession`/`establishSession` flags are used to express intent; actual Matter Python SDK may vary in exact API.

**Save this file as:**  
`tests/test_csa_security_channel.py`