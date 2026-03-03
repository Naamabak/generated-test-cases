```python
# File: tests/test_rpm_version_implemented_update.py

"""
Test Case for:
Requirement ID : TS.34_8.2.1_REQ_006

Requirement:
At each power up, the Radio Baseband Chipset SHALL check if “RPM version Implemented” on the module 
is different from file “EF-RPM Version Implemented” on the (U)SIM card. If different, 
the file is updated (as early as possible in power up) to match the module’s implemented RPM version.

References:
- GSMA TS.34 v8.0, Section 8.2.1, TS.34_8.2.1_REQ_006
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
- TS.34_8.2.4_REQ_008 (EF-RPM Version Information file structure)
"""

import pytest

# ----- MOCKS / PLACEHOLDER CLASSES (replace with actual integration/API for real device/UICC) -----

class MockUICC:
    """
    Simulates a UICC containing the EF-RPM Version Implemented file.
    """
    def __init__(self, rpm_version_file_value=1):
        self.ef_rpm_version_implemented = rpm_version_file_value
        self.file_write_log = []

    def read_rpm_version_file(self):
        return self.ef_rpm_version_implemented

    def write_rpm_version_file(self, value, time="early"):
        self.ef_rpm_version_implemented = value
        self.file_write_log.append({"value": value, "write_time": time})

    def get_write_log(self):
        return list(self.file_write_log)

class MockRadioBasebandChipset:
    """
    Simulates the Radio Baseband Chipset's stored RPM version and its power-up process.
    """
    def __init__(self, implemented_rpm_version=2):
        self.rpm_version_implemented = implemented_rpm_version
        self.log = []

    def set_rpm_version_implemented(self, version):
        self.rpm_version_implemented = version

    def get_rpm_version_implemented(self):
        return self.rpm_version_implemented

    def power_up(self, uicc: MockUICC):
        """
        During power-up, check if RPM version implemented (module) != UICC EF-RPM Version value.
        If so, update UICC as early as possible.
        """
        current_version = self.rpm_version_implemented
        uicc_version = uicc.read_rpm_version_file()
        self.log.append(
            f"During power up: Module RPM={current_version}, UICC EF-RPM={uicc_version}."
        )
        if current_version != uicc_version:
            # Simulate write as early as possible in the power up
            uicc.write_rpm_version_file(current_version, time="early_power_up")
            self.log.append(
                f"EF-RPM Version Implemented updated on UICC to {current_version} at early power up."
            )
        else:
            self.log.append("No update needed: versions match at power up.")

    def get_log(self):
        return list(self.log)

    def reset_log(self):
        self.log.clear()

# ----- TEST FIXTURES -----

@pytest.fixture
def uicc():
    """Returns a UICC with an initial EF-RPM Version value of 1 for default tests."""
    return MockUICC(rpm_version_file_value=1)

@pytest.fixture
def chipset():
    """Returns a chipset with the default implemented RPM version set to 2."""
    return MockRadioBasebandChipset(implemented_rpm_version=2)

# ----- TEST SCRIPT -----

def test_rpm_version_update_on_power_up(uicc, chipset):
    """
    TS.34_8.2.1_REQ_006:
    - If UICC EF-RPM Version differs from module's implemented RPM version, chipset updates the UICC file at early power up.
    - Update is logged and observable; after power up both values match.
    """
    # Step 1: Initial state - UICC version (1), module version (2)
    assert uicc.read_rpm_version_file() == 1
    assert chipset.get_rpm_version_implemented() == 2

    # Step 2: Power cycle device/module
    chipset.power_up(uicc)

    # Step 3: Check log for early write and successful update
    log = chipset.get_log()
    write_log = uicc.get_write_log()
    assert any("early_power_up" in str(entry) for entry in write_log), (
        "EF-RPM version was not updated as early as possible during power up!"
    )
    assert any("updated" in entry for entry in log), (
        "No log entry for RPM version update!"
    )
    # Step 4: UICC file should now match chipset version
    post_power_version = uicc.read_rpm_version_file()
    assert post_power_version == 2, "UICC EF-RPM Version did not update to match module version (2) after power up"

    # Step 5: Repeat for future version (simulate RPM version 3, UICC value 2)
    chipset.set_rpm_version_implemented(3)
    uicc.write_rpm_version_file(2, time="manual_update")
    chipset.reset_log()
    uicc.file_write_log.clear()

    chipset.power_up(uicc)
    write_log2 = uicc.get_write_log()
    assert uicc.read_rpm_version_file() == 3, "UICC EF-RPM Version did not update to match module version (3) after power up"
    assert any("early_power_up" in str(entry["write_time"]) for entry in write_log2), "File update was not performed early enough on power up"

    # Output logs for audit
    print("Power up/update log:", chipset.get_log())
    print("EF-RPM Version file write log:", uicc.get_write_log())

def test_no_update_when_versions_already_match(uicc, chipset):
    """
    If UICC EF-RPM Version matches module, no update is performed.
    """
    uicc.write_rpm_version_file(2, time="test_setup")
    chipset.set_rpm_version_implemented(2)
    chipset.reset_log()
    uicc.file_write_log.clear()

    chipset.power_up(uicc)
    # No writes during power up
    write_log = uicc.get_write_log()
    assert not write_log, "File write should not occur if RPM versions match at power up"
    assert any("No update needed" in l for l in chipset.get_log())

@pytest.mark.parametrize("initial_version,new_version", [(1, 2), (2, 3), (3, 1)])
def test_repeatable_version_upgrades(uicc, chipset, initial_version, new_version):
    """
    Test repeatedly upgrading/downgrading EF-RPM version with multiple simulated power-up cycles.
    """
    uicc.write_rpm_version_file(initial_version, time="setup")
    chipset.set_rpm_version_implemented(new_version)
    chipset.power_up(uicc)
    assert uicc.read_rpm_version_file() == new_version, (
        f"After upgrade: UICC version should be {new_version}, found: {uicc.read_rpm_version_file()}"
    )
    # Downgrade/flip again
    uicc.write_rpm_version_file(new_version-1, time="manual_test")
    chipset.set_rpm_version_implemented(new_version-1)
    chipset.power_up(uicc)
    assert uicc.read_rpm_version_file() == new_version-1, (
        "UICC RPM version file did not update after downgrade or repeated flip"
    )

def test_logged_as_early_in_power_up(uicc, chipset):
    """
    Optionally trace that the update/write is logged as 'early_power_up' (simulate early in boot).
    """
    uicc.write_rpm_version_file(0, time="manual")
    chipset.power_up(uicc)
    assert any("early_power_up" in str(l["write_time"]) for l in uicc.get_write_log()), (
        "EF-RPM Version file was not updated as early as possible during power up!"
    )
    print("Early power up update log:", uicc.get_write_log())

```
---

**How to Use:**
- Save as `tests/test_rpm_version_implemented_update.py`.
- Replace mocks with actual firmware/UICC integration if APIs exist.
- Run with:
  ```
  pytest tests/test_rpm_version_implemented_update.py
  ```
- Assertions and logs are designed to match GSMA TS.34_8.2.1_REQ_006, including early write verification, version consistency, proper upgrade/downgrade, and audit trail.

Let me know if you need hooks for hardware UICC/AT scripting or device debug log integration!
```