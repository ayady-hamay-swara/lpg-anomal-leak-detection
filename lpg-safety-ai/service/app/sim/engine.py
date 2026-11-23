from __future__ import annotations
import math, random
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yaml
from app.sim.physics import gauge_pressure, level_from_mass, liquid_density, thermal_lag, hole_area_m2, liquid_leak_kg_s
from app.sim.instruments import analog_ma, loop_quality, noisy

ROOT = Path(__file__).resolve().parents[3]

class Simulator:
    def __init__(self, seed: int | None = None):
        with open(ROOT / "config" / "plant.yaml", "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.seed = seed if seed is not None else int(self.config["seed"])
        self.rng = random.Random(self.seed)
        self.reset(seed=self.seed)

    def reset(self, seed: int | None = None):
        if seed is not None:
            self.seed = seed
            self.rng = random.Random(seed)
        self.sim_seconds = 0
        self.speed = 60
        self.ambient_fixed = None
        self.ambient_offset = 0.0
        self.solar_gain = 4.0
        self.tanks = {}
        for tank in self.config["tanks"]:
            tid = tank["id"]
            mass = tank["volume_m3"] * 0.62 * liquid_density(30)
            self.tanks[tid] = {
                "liquid_mass": mass,
                "T_liquid": 30.0,
                "fill_pct": 100.0,
                "outlet_pct": 0.0,
                "pressure_override_barg": None,
                "temperature_override_c": None,
                "maintenance": False,
                "leaks": [],
                "sensor_faults": {},
                "history": [],
            }
        self.pipeline = {
            "segments": [dict(s, leak_area_mm2=0.0) for s in self.config["pipeline"]["segments"]],
            "inlet_flow": 180.0,
            "pump_on": True,
            "pump_speed": 70,
        }
        self.assets = self._build_assets()
        self.history = {}
        self.events = []
        self._frame = None

    def _build_assets(self):
        assets = []
        for tank in self.config["tanks"]:
            tid = tank["id"]
            assets += [
                {"code": f"XV-{tid}-IN", "type": "valve", "parent": tid, "state": "healthy", "corrosion_index": 0.1, "age_years": 8},
                {"code": f"XV-{tid}-OUT", "type": "valve", "parent": tid, "state": "healthy", "corrosion_index": 0.1, "age_years": 8},
                {"code": f"P-{tid}", "type": "pump", "parent": tid, "state": "healthy", "corrosion_index": 0.15, "age_years": 10},
            ]
        for seg in self.config["pipeline"]["segments"]:
            sid = seg["id"]
            for i in range(1, seg["flanges"] + 1):
                assets.append({"code": f"FLG-{sid}-{i:02d}", "type": "flange", "parent": sid, "segment_id": sid,
                               "state": "healthy", "area_mm2": 0.0, "corrosion_index": round(self.rng.random() * 0.35, 3),
                               "age_years": 3 + int(self.rng.random() * 12), "torque_ok": True})
        return assets

    def ambient_temperature(self) -> float:
        if self.ambient_fixed is not None:
            return max(-10.0, min(60.0, self.ambient_fixed + self.ambient_offset))
        hour = (self.sim_seconds / 3600.0) % 24
        w = self.config["weather"]
        return w["t_mean_c"] + w["t_amp_c"] * math.sin(2 * math.pi * (hour - 9) / 24) + self.ambient_offset

    def apply_control(self, body: dict):
        if "ambient_c" in body:
            value = body["ambient_c"]
            if not isinstance(value, (int, float)) or not -10 <= value <= 60:
                raise ValueError("ambient_c must be between -10 and 60")
            self.ambient_fixed = float(value)
        if "solar_gain_c" in body:
            value = float(body["solar_gain_c"])
            if not 0 <= value <= 8:
                raise ValueError("solar_gain_c must be between 0 and 8")
            self.solar_gain = value

        for tid, tank_control in body.get("tanks", {}).items():
            if tid not in self.tanks:
                continue
            tank = self.tanks[tid]

            if "fill_valve_pct" in tank_control:
                tank["fill_pct"] = max(0.0, min(100.0, float(tank_control["fill_valve_pct"])))
            if "outlet_valve_pct" in tank_control:
                tank["outlet_pct"] = max(0.0, min(100.0, float(tank_control["outlet_valve_pct"])))

            if tank_control.get("temperature_override_c") is not None:
                temperature = float(tank_control["temperature_override_c"])
                if not -10 <= temperature <= 100:
                    raise ValueError("temperature_override_c must be between -10 and 100")
                tank["temperature_override_c"] = temperature
                tank["T_liquid"] = temperature
            elif "temperature_override_c" in tank_control:
                tank["temperature_override_c"] = None

            if tank_control.get("pressure_override_barg") is not None:
                pressure = float(tank_control["pressure_override_barg"])
                if not 0 <= pressure <= 25:
                    raise ValueError("pressure_override_barg must be between 0 and 25")
                tank["pressure_override_barg"] = pressure
                tank["P_gauge"] = pressure
            elif "pressure_override_barg" in tank_control:
                tank["pressure_override_barg"] = None

            if tank_control.get("level_override_pct") is not None:
                level = float(tank_control["level_override_pct"])
                level = max(0.0, min(100.0, level))
                cfg = next(t for t in self.config["tanks"] if t["id"] == tid)
                tank["liquid_mass"] = level / 100.0 * cfg["volume_m3"] * liquid_density(tank["T_liquid"])
            if "maintenance" in tank_control:
                tank["maintenance"] = bool(tank_control["maintenance"])

        pipeline_control = body.get("pipeline")
        if isinstance(pipeline_control, dict):
            if "pump_on" in pipeline_control:
                self.pipeline["pump_on"] = bool(pipeline_control["pump_on"])
            if "pump_speed" in pipeline_control:
                speed = float(pipeline_control["pump_speed"])
                if not 0 <= speed <= 100:
                    raise ValueError("pump_speed must be between 0 and 100")
                self.pipeline["pump_speed"] = speed
            if "inlet_flow" in pipeline_control:
                flow = float(pipeline_control["inlet_flow"])
                if not 0 <= flow <= 500:
                    raise ValueError("inlet_flow must be between 0 and 500")
                self.pipeline["inlet_flow"] = flow

        for leak in body.get("leaks", []):
            asset = next((a for a in self.assets if a["code"] == leak["asset"]), None)
            if asset is None:
                continue
            area = max(0.0, min(2500.0, float(leak["area_mm2"])))
            mode = leak.get("mode", "leaking" if area > 0 else "healthy")
            asset["area_mm2"] = area
            asset["state"] = "healthy" if area <= 0 else mode
            asset["growth_mm2_per_h"] = max(0.0, min(5.0, float(leak.get("growth_mm2_per_h", 0.0))))
            if asset["type"] == "valve" and asset["parent"] in self.tanks:
                tank_leaks = [a for a in self.tanks[asset["parent"]]["leaks"] if a is not asset]
                self.tanks[asset["parent"]]["leaks"] = tank_leaks + ([asset] if area > 0 else [])

        for fault in body.get("sensor_faults", []):
            tag = fault["tag"]
            tid = next((tid for tid in self.tanks if tid in tag), "T01")
            self.tanks[tid].setdefault("sensor_faults", {})[tag] = fault["type"]

    def step(self):
        dt = 1.0
        self.sim_seconds += dt
        ambient = self.ambient_temperature()
        for tank_cfg in self.config["tanks"]:
            tid = tank_cfg["id"]
            tank = self.tanks[tid]
            target = ambient + self.solar_gain
            tank["T_liquid"] = thermal_lag(tank["T_liquid"], target, dt, tank_cfg["thermal_tau_hours"])
            rho = liquid_density(tank["T_liquid"], self.config["product"]["rho_20_kg_m3"], self.config["product"]["beta_per_c"])
            fill_flow = tank["fill_pct"] / 100.0 * 0.25 * 1000.0
            outlet_flow = tank["outlet_pct"] / 100.0 * 0.20 * 1000.0
            leak_kg_s = 0.0
            for asset in tank["leaks"]:
                area = asset.get("area_mm2", 0.0) / 1e6
                pressure = gauge_pressure(tank["T_liquid"], self.config["product"]["propane_fraction"])
                leak_kg_s += liquid_leak_kg_s(area, rho, pressure)
                area = asset.get("area_mm2", 0.0)
                asset["area_mm2"] = area + asset.get("growth_mm2_per_h", 0.0) / 3600.0
            tank["liquid_mass"] = max(0.0, tank["liquid_mass"] + (fill_flow - outlet_flow - leak_kg_s) * dt)
            tank["P_gauge"] = gauge_pressure(tank["T_liquid"], self.config["product"]["propane_fraction"])
            tank["level_pct"] = level_from_mass(tank["liquid_mass"], tank["T_liquid"], tank_cfg["volume_m3"])
        for seg in self.pipeline["segments"]:
            seg["leak_area_mm2"] = sum(a.get("area_mm2", 0.0) for a in self.assets
                                         if a.get("segment_id") == seg["id"] and a.get("state") != "healthy")
        self._frame = self.tag_frame()
        return self._frame

    def tag_frame(self):
        ts = (datetime.now(timezone.utc) + timedelta(seconds=self.sim_seconds)).isoformat()
        tags = {}
        for tid, tank in self.tanks.items():
            level = tank.get("level_pct", 62.0)
            pressure = tank.get("P_gauge", gauge_pressure(tank["T_liquid"]))
            tags[f"LT-{tid}"] = {"value": round(level, 3), "ma": round(analog_ma(level, 0, 100), 3), "quality": "good"}
            tags[f"LT-{tid}B"] = {"value": round(level + self.rng.gauss(0, 0.1), 3), "ma": round(analog_ma(level, 0, 100), 3), "quality": "good"}
            tags[f"PT-{tid}"] = {"value": round(noisy(pressure, 0.02, self.rng), 3), "ma": round(analog_ma(pressure, 0, 25), 3), "quality": "good"}
            for suffix in "ABC":
                tags[f"TT-{tid}{suffix}"] = {"value": round(noisy(tank["T_liquid"], 0.05, self.rng), 3), "quality": "good"}
            gas = min(100.0, sum(a.get("area_mm2", 0.0) for a in self.assets if a.get("parent") == tid) * 0.5)
            tags[f"GD-{tid}"] = {"value": round(gas, 2), "quality": "good"}
        tags["AT-AMB"] = {"value": round(self.ambient_temperature(), 3), "quality": "good"}
        for seg_index, seg in enumerate(self.pipeline["segments"], 1):
            base = 12.0 - seg_index * 0.15 - seg["leak_area_mm2"] * 0.001
            flow = max(0.0, self.pipeline["inlet_flow"] - seg_index * seg["leak_area_mm2"] * 0.02)
            tags[f"PT-S{seg_index}"] = {"value": round(noisy(base, 0.02, self.rng), 3), "quality": "good"}
            tags[f"FT-S{seg_index}"] = {"value": round(noisy(flow, 0.5, self.rng), 3), "quality": "good"}
        return {"ts": ts, "sim_speed": self.speed, "tags": tags}

    def frame_dict(self):
        if self._frame is None:
            self._frame = self.tag_frame()
        return self._frame

    def run_seconds(self, seconds: int):
        for _ in range(seconds):
            self.step()
        return self.frame_dict()
