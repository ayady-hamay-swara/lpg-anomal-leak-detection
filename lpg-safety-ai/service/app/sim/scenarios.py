from app.sim.engine import Simulator

SCENARIOS = {"normal_day","heat_wave","overfill","valve_leak","flange_seep","weld_rupture","radar_stuck","pump_seal","vapour_leak","maintenance_mode","alarm_flood","gas_detector_failure"}

def apply_scenario(sim: Simulator, name: str):
    if name not in SCENARIOS:
        raise ValueError("Unknown scenario")
    sim.reset(seed=sim.seed)
    if name == "heat_wave":
        sim.apply_control({"ambient_c": 40, "tanks": {"T01": {"fill_valve_pct": 30}}})
        sim.ambient_offset = 10
    elif name == "overfill":
        sim.apply_control({"tanks": {"T01": {"level_override_pct": 78, "fill_valve_pct": 100, "outlet_valve_pct": 0}}})
    elif name == "valve_leak":
        sim.apply_control({"leaks": [{"asset":"XV-T01-OUT","area_mm2":70.685,"mode":"leaking"}]})
    elif name == "flange_seep":
        sim.apply_control({"leaks": [{"asset":"FLG-S2-07","area_mm2":0.1,"mode":"seeping","growth_mm2_per_h":0.5}]})
    elif name == "weld_rupture":
        sim.apply_control({"leaks": [{"asset":"FLG-S3-01","area_mm2":2500,"mode":"rupture"}]})
    elif name == "radar_stuck":
        sim.apply_control({"tanks":{"T01":{"level_override_pct":60}},"sensor_faults":[{"tag":"LT-T01","type":"stuck"}]})
    elif name == "pump_seal":
        sim.apply_control({"leaks":[{"asset":"P-T01","area_mm2":12.5,"mode":"leaking"}]})
    elif name == "vapour_leak":
        sim.apply_control({"ambient_c":30,"leaks":[{"asset":"XV-T01-OUT","area_mm2":20,"mode":"leaking"}]})
    elif name == "maintenance_mode":
        sim.apply_control({"tanks":{"T02":{"maintenance":True,"level_override_pct":90}}})
    elif name == "alarm_flood":
        sim.apply_control({"leaks":[{"asset":"FLG-S4-01","area_mm2":2500,"mode":"rupture"}]})
    elif name == "gas_detector_failure":
        sim.apply_control({"leaks":[{"asset":"FLG-S2-05","area_mm2":30,"mode":"leaking"}],"sensor_faults":[{"tag":"GD-S2","type":"stuck_zero"}]})
    return sim
