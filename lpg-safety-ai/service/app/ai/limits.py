from app.sim.physics import gauge_pressure, level_from_mass

def forecast_limit(tank: dict, tank_cfg: dict, ambient_peak: float, propane_fraction: float = 0.60):
    level = tank.get("level_pct", 0.0)
    temp = tank.get("T_liquid", 30.0)
    pressure_h = tank_cfg["design_pressure_barg"] * 0.75
    pressure_hh = tank_cfg["design_pressure_barg"] * 0.90
    temp_peak = min(80.0, ambient_peak + 4.0)
    predicted_pressure = gauge_pressure(temp_peak, propane_fraction)
    predicted_level = level_from_mass(tank["liquid_mass"], temp_peak, tank_cfg["volume_m3"])
    return {"pressure_h_barg":round(pressure_h,3),"pressure_hh_barg":round(pressure_hh,3),
            "peak_pressure_barg":round(predicted_pressure,3),"peak_level_pct":round(predicted_level,2),
            "minutes_to_P_H":None,"minutes_to_P_HH":None,"minutes_to_level_85":None}
