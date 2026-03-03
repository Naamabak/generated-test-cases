```python
# File: tests/test_extended_periodic_timers.py

"""
Test Case for:
Requirement ID : TS.34_9.4_REQ_001

Requirement:
The IoT Device SHALL support the extended periodic timers, both for PLU (circuit switched domain) and PRU/PTU (packet-switched domain).

References:
- GSMA TS.34 v8.0, Section 9.4, TS.34_9.4_REQ_001
- 3GPP TS 24.008, 3GPP TS 24.301
- a737efcc-3d4d-4f4e-97b0-a65e5d835d6e_TS.34-v8.pdf
"""

import pytest

# --- MOCK INTERFACE (replace with integration to your actual device API/network/protocol analyzer) ---

class MockTimerDevice:
    """
    Mock for an IoT Device supporting extended periodic timers for PLU (CS) and PRU/PTU (PS).
    """
    def __init__(self):
        # Timer values in seconds (configurable for test)
        self.plu_timer_cs = 3600      # PLU (CS domain) timer, default 1 hour
        self.pru_ptu_timer_ps = 3600  # PRU/PTU (PS domain) timer, default 1 hour
        self.message_log = []         # List of (domain, msg_type, sent_time, timer_value)
        self.simulated_time = 0       # Used instead of time.time() for speed/step
        self.timer_history = []

    def configure_plu_timer(self, value_sec):
        self.plu_timer_cs = value_sec
        self.timer_history.append(('PLU', value_sec))
    
    def configure_pru_ptu_timer(self, value_sec):
        self.pru_ptu_timer_ps = value_sec
        self.timer_history.append(('PRU/PTU', value_sec))

    def advance_time(self, seconds):
        """Advance simulated time and send periodic update/attach messages as needed."""
        previous_time = self.simulated_time
        self.simulated_time += seconds

        # Send LU in CS domain for each elapsed interval of self.plu_timer_cs
        next_lu = previous_time + self.plu_timer_cs - (previous_time % self.plu_timer_cs)
        while next_lu <= self.simulated_time:
            self.message_log.append(('CS', 'LU', next_lu, self.plu_timer_cs))
            next_lu += self.plu_timer_cs

        # Send RAU/TAU in PS domain for each elapsed interval of self.pru_ptu_timer_ps
        next_tau = previous_time + self.pru_ptu_timer_ps - (previous_time % self.pru_ptu_timer_ps)
        while next_tau <= self.simulated_time:
            self.message_log.append(('PS', 'RAU/TAU', next_tau, self.pru_ptu_timer_ps))
            next_tau += self.pru_ptu_timer_ps

    def get_cs_messages(self):
        return [msg for msg in self.message_log if msg[0] == 'CS']
    
    def get_ps_messages(self):
        return [msg for msg in self.message_log if msg[0] == 'PS']

    def get_last_message_time_and_interval(self, domain):
        msgs = [msg for msg in self.message_log if msg[0] == domain]
        if len(msgs) < 2:
            return None, None
        last = msgs[-1][2]
        penultimate = msgs[-2][2]
        interval = last - penultimate
        timer = msgs[-1][3]
        return interval, timer

    def clear_log(self):
        self.message_log.clear()
        self.simulated_time = 0

    def read_config(self):
        # Simulate config/AT/OMA DM output for timer value validation
        return {
            "PLU_timer": self.plu_timer_cs,
            "PRU_PT_timer": self.pru_ptu_timer_ps,
        }

    def get_timer_config_history(self):
        return self.timer_history

# --- TEST FIXTURE ---

@pytest.fixture
def device():
    dev = MockTimerDevice()
    yield dev
    dev.clear_log()

# --- TEST SCRIPT ---

@pytest.mark.parametrize("plu_secs,pru_secs,advance,domain,msgtype", [
    (3600, 1800, 10800, 'CS', 'LU'),
    (4800, 2400, 14400, 'PS', 'RAU/TAU'),
    (86400, 7200, 172800, 'CS', 'LU')   # Test for maximum extended timer (24 hours)
])
def test_extended_periodic_timers_generate_expected_intervals(device, plu_secs, pru_secs, advance, domain, msgtype):
    """
    Verify that device can be configured for extended PLU (CS) and PRU/PTU (PS) timer values,
    and that periodic Location Update and area updates are observed at those intervals.
    """

    # Step 1: Configure timers: extended values, both CS and PS
    device.configure_plu_timer(plu_secs)
    device.configure_pru_ptu_timer(pru_secs)
    # Simulate total time window (advance contained in one or more periods)
    device.advance_time(advance)

    # Step 2: Gather periodic message logs and check intervals
    msgs = device.get_cs_messages() if domain == 'CS' else device.get_ps_messages()
    expected_interval = plu_secs if domain == 'CS' else pru_secs

    # Should see multiple events spaced by the configured timer value (within ± a tolerance for simulated time)
    intervals = []
    prev_time = None
    for msg in msgs:
        if prev_time is not None:
            interval = msg[2] - prev_time
            intervals.append(interval)
        prev_time = msg[2]

    for idx, interval in enumerate(intervals):
        assert abs(interval - expected_interval) < 1, (
            f"Interval between {msgtype} messages #{idx + 2} and #{idx + 1} does not match expected timer ({interval} vs {expected_interval})"
        )

    print(f"{msgtype} message times: {[msg[2] for msg in msgs]}, intervals: {intervals}")
    print("Config for test:", device.read_config())
    print("Timer config history:", device.get_timer_config_history())


@pytest.mark.parametrize("new_plu,new_pru,chosen", [(1800, 900, 'PLU'), (5400, 1200, 'PRU/PTU')])
def test_timer_changes_apply_and_are_respected(device, new_plu, new_pru, chosen):
    """
    Test that timer changes can be applied and take effect for both domains.
    """
    device.configure_plu_timer(3600)
    device.configure_pru_ptu_timer(3600)
    device.advance_time(3600)

    if chosen == 'PLU':
        device.configure_plu_timer(new_plu)
    else:
        device.configure_pru_ptu_timer(new_pru)
    device.clear_log()
    device.advance_time(3 * max(new_plu, new_pru))

    # Should see messages with the new periodicity
    msgs = device.get_cs_messages() if chosen == 'PLU' else device.get_ps_messages()
    timer_val = new_plu if chosen == 'PLU' else new_pru
    for i in range(1, len(msgs)):
        assert abs(msgs[i][2] - msgs[i - 1][2] - timer_val) < 1, \
            f"{chosen} message spacing ({msgs[i][2] - msgs[i - 1][2]}) != timer {timer_val}"

    print(f"Applied new {chosen} timer and resulting message intervals: {[msgs[i][2] - msgs[i - 1][2] for i in range(1, len(msgs))]}")


def test_config_and_message_encoding_verification(device):
    """
    Confirm timer config is visible/readable and messages carry correct values (simulated as timer_value in msg).
    """
    device.configure_plu_timer(7200)
    device.configure_pru_ptu_timer(1500)
    device.advance_time(9000)
    cs_msgs = device.get_cs_messages()
    ps_msgs = device.get_ps_messages()
    # Timer value provided in each msg
    for msg in cs_msgs + ps_msgs:
        timer_setting = device.read_config()["PLU_timer"] if msg[0] == "CS" else device.read_config()["PRU_PT_timer"]
        assert msg[3] == timer_setting
    print("Message contents for timer value validation:", cs_msgs, ps_msgs)


def test_device_supports_max_extended_timer(device):
    """
    Test device with maximum supported timer values (per 3GPP, e.g., 24hr for PLU, protocol maximum for PRU/PTU).
    """
    max_plu = 24 * 3600      # 24 hours in seconds
    max_pru_ptu = 24 * 3600  # Assuming same max for test; check 3GPP for PS domain max if required
    device.configure_plu_timer(max_plu)
    device.configure_pru_ptu_timer(max_pru_ptu)
    device.advance_time(2 * max_plu + 1)
    cs_msgs = device.get_cs_messages()
    ps_msgs = device.get_ps_messages()
    # Should see at least two periodic messages for each in the test window; intervals must match max timer
    assert cs_msgs[1][2] - cs_msgs[0][2] == max_plu
    assert ps_msgs[1][2] - ps_msgs[0][2] == max_pru_ptu
    print("Tested device with maximum extended timers. CS:", cs_msgs, "| PS:", ps_msgs)
```
---

**Usage/Integration Instructions:**

- Save as `tests/test_extended_periodic_timers.py`
- Replace mock/device interface with real device, SIM, or network protocol adapter APIs as available.
- Run with:
  ```bash
  pytest tests/test_extended_periodic_timers.py
  ```
- All test steps, parameter variations, message logs, and printouts correspond to TS.34_9.4_REQ_001 and exit/pass criteria per the requirement.

Let me know if you need this adapted for live integration, AT command automation, or protocol capture decode!