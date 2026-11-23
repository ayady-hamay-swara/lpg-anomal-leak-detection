def risk_score(pressure: float, pressure_hh: float, level: float, heat_rise: float,
               leak_strength: float, sensor_problem: bool, weights: dict) -> tuple[int, list[str]]:
    pressure_margin = max(0.0, min(1.0, pressure / pressure_hh))
    level_margin = max(0.0, min(1.0, level / 85.0))
    factors = []
    score = int(round(pressure_margin * weights["pressure_margin"] + level_margin * weights["level_margin"]
                      + min(1.0, heat_rise / 1.5) * weights["heat"]
                      + leak_strength * weights["leak"]
                      + (weights["sensor"] if sensor_problem else 0)))
    if pressure_margin > 0.55:
        factors.append(f"Pressure is {pressure_margin:.0%} of the High-High limit")
    if level_margin > 0.55:
        factors.append(f"Level is {level_margin:.0%} of the 85% fill limit")
    if heat_rise >= 1.5:
        factors.append("Tank temperature trend exceeds the heat-watch threshold")
    if leak_strength:
        factors.append("Possible loss of containment is supported by leak evidence")
    if sensor_problem:
        factors.append("Sensor validity problems reduce AI confidence")
    if not factors:
        factors.append("No strong abnormal pressure, level, heat or leak evidence")
    return min(100, score), factors[:3]
