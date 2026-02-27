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

# matter-testing imports follow the test structure shown in the project.
import matter.clusters as Clusters
from matter.testing.decorators import async_test_body
from matter.testing.matter_testing import MatterBaseTest
from matter.testing.runner import default_matter_test_main
from matter import ChipDeviceCtrl

log = logging.getLogger(__name__)

class TC_CSA_SEC_001(MatterBaseTest):
    """
    Test Case TC-CSA-SEC-001:
    Verifies that application-layer end-to-end security is enforced and malicious devices attempting to establish
    secure communication via fraudulent mDNS responses are detected and prevented.
    """

    # Optional setup if required by test infra
    @async_test_body
    async def setup_class(self):
        super().setup_class()
        log.info("[Setup] Test environment initialized and mDNS enabled.")

    @async_test_body
    async def test_malicious_mdns_blocked(self):
        # Step 0: Pre-conditions
        # (Environment setup should have at least one legitimate and one malicious device)
        log.info("Step 0: Verify test environment setup: 1+ legitimate, 1+ malicious device, mDNS operational.")

        # Step 1: Initiate mDNS discovery from trusted application/client
        log.info("Step 1: Initiate mDNS discovery.")
        discovered_devices = await self.default_controller.DiscoverCommissionableNodes()
        log.info(f"Discovered during mDNS: {discovered_devices}")

        # Filtering for known legitimate and malicious device values (IDs can be configured externally or as fixtures)
        # For demonstration, let's assume:
        # - legitimate device's discriminator is 1234 (could be node ID, address, etc.)
        # - malicious device's discriminator is 9999

        legitimate_found = False
        malicious_found = False
        malicious_descriptor = None

        for dev in discovered_devices:
            if dev['discriminator'] == 1234:
                legitimate_found = True
            if dev['discriminator'] == 9999:
                malicious_found = True
                malicious_descriptor = dev

        asserts.assert_true(legitimate_found, "Legitimate device not detected during mDNS scan")
        asserts.assert_true(malicious_found, "Malicious device not detected during mDNS scan (required for this test)")

        # Step 2: Have both legitimate and malicious devices respond to mDNS query (already observed above)
        # Step 3: Malicious device replies with fraudulent/mimicked data (assumed through testbed or mDNS manipulation)
        log.info("Step 2-3: Both legitimate and malicious device responses captured.")

        # Step 4: Attempt to establish secure session with both devices
        log.info("Step 4: Try to establish secure session with both devices.")

        # Attempt with legitimate device (expected: success)
        try:
            session = await self.default_controller.PairDevice(nodeId=0x1234, discriminator=1234, setupPinCode=20202021)
            asserts.assert_is_not_none(session, "Failed to establish secure session with legitimate device")
            log.info("Secure session established with legitimate device.")
        except Exception as exc:
            asserts.fail(f"Failed to pair with legitimate device: {exc}")

        # Attempt with malicious device (expected: should NOT succeed)
        session_failed = False
        alert_logged = False
        try:
            await self.default_controller.PairDevice(nodeId=0x9999, discriminator=9999, setupPinCode=22222222)
        except Exception as exc:
            session_failed = True
            log.info("Malicious device pairing attempt failed as expected.")
            # Check for presence of relevant message (alert/log handling can be product-specific)
            if "fraudulent" in str(exc).lower() or "security" in str(exc).lower(): 
                alert_logged = True

        asserts.assert_true(session_failed, "Malicious device was able to pair (should have been blocked).")
        log.info("Step 5: Security mechanism correctly blocked malicious device.")

        # Step 6: Verify logs for alert/entry on fraud attempt (basic log check simulation here)
        if malicious_descriptor:
            # In actual infra, would check log output, events, or error status, here we just check our flag.
            asserts.assert_true(alert_logged, "No security alert or log on fraudulent pairing attempt.")

        # Step 7: Ensure communication with legitimate device is unaffected
        # (Example: Try to read an attribute from legitimate device)
        try:
            value = await self.read_single_attribute_check_success(
                cluster=Clusters.BasicInformation,
                attribute=Clusters.BasicInformation.Attributes.NodeLabel,
                endpoint=0,
                device_id=0x1234
            )
            asserts.assert_is_not_none(value, "Legitimate device communication failed after malicious attempt.")
            log.info("Legitimate device communication verified.")
        except Exception as exc:
            asserts.fail(f"Failed to communicate with legitimate device post-malicious attempt: {exc}")

        # Step 8: Post-conditions (Log/alert verified above, malicious blocked, legitimate unaffected)

if __name__ == "__main__":
    default_matter_test_main()
```
**File path:** `tests/test_TC_CSA_SEC_001.py`

---

**NOTES:**
- This assumes the test runner can provide at least one legitimate and one malicious device for pairing/discovery.
- Device discriminators, node IDs, and PINs are example placeholders. Use real or testbed-provided identifiers.
- If infrastructure provides better hooks for log/assert/alert verification, adapt Step 6 accordingly.
- For a real environment, the `"fraudulent"`/`"security"` message check should be replaced with integration to device or system logs.
- All Matter/CHIP utility and interaction patterns (test class structure, async test wrapper, controller use, assertions, etc.) match your project style.