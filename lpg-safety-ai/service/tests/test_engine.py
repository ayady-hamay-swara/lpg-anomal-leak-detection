from app.sim.engine import Simulator
from app.sim.scenarios import apply_scenario

def test_reset_deterministic():
    a = Simulator(seed=42)
    b = Simulator(seed=42)
    assert a.run_seconds(10)["tags"] == b.run_seconds(10)["tags"]

def test_control_changes_level():
    sim = Simulator(seed=42)
    sim.apply_control({"tanks":{"T01":{"level_override_pct":78}}})
    sim.step()
    assert sim.tanks["T01"]["level_pct"] >= 77

def test_scenarios_create_frames():
    sim = Simulator(seed=42)
    for name in ("heat_wave","overfill","valve_leak","flange_seep","weld_rupture","radar_stuck","pump_seal","vapour_leak","maintenance_mode","alarm_flood","gas_detector_failure","normal_day"):
        if name == "normal_day":
            sim.reset(seed=42)
        else:
            apply_scenario(sim, name)
        assert sim.frame_dict()["tags"]
