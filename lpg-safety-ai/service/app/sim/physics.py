import math

def saturated_pressure_bar(temp_c: float, propane_fraction: float = 0.60) -> float:
    """Ideal-mixture LPG saturation pressure (P_abs bar) with A-B-C Antoine constants."""
    def psat_bar(component_a: float, b: float, c: float) -> float:
        mmhg = 10 ** (component_a - b / (c + temp_c))
        return mmhg * 0.00133322
    propane = psat_bar(6.82973, 813.2, 248.0)
    butane = psat_bar(6.80896, 935.86, 238.73)
    return propane_fraction * propane + (1.0 - propane_fraction) * butane

def gauge_pressure(temp_c: float, propane_fraction: float = 0.60) -> float:
    return max(0.0, saturated_pressure_bar(temp_c, propane_fraction) - 1.01325)

def liquid_density(temp_c: float, rho20: float = 530.0, beta: float = 0.0027) -> float:
    return rho20 * (1.0 - beta * (temp_c - 20.0))

def level_from_mass(mass_kg: float, temp_c: float, tank_volume_m3: float,
                    rho20: float = 530.0, beta: float = 0.0027) -> float:
    volume = mass_kg / liquid_density(temp_c, rho20, beta)
    return max(0.0, min(100.0, volume / tank_volume_m3 * 100.0))

def thermal_lag(temp_c: float, target_c: float, dt_s: float, tau_hours: float = 6.0) -> float:
    tau_s = tau_hours * 3600.0
    return temp_c + (target_c - temp_c) * dt_s / tau_s

def hole_area_m2(diameter_mm: float) -> float:
    d = diameter_mm / 1000.0
    return math.pi * d * d / 4.0

def liquid_leak_kg_s(area_m2: float, rho: float, gauge_pressure_barg: float,
                     liquid_head_pa: float = 0.0, cd: float = 0.6) -> float:
    dp = max(0.0, gauge_pressure_barg * 100000.0 + liquid_head_pa)
    return cd * area_m2 * math.sqrt(2.0 * rho * dp)

def vapor_leak_kg_s(area_m2: float, abs_pressure_bar: float, temp_c: float,
                    molar_mass: float = 50.0, k: float = 1.13, cd: float = 0.6) -> float:
    rs = 8314.0 / molar_mass
    pa = abs_pressure_bar * 100000.0
    term = k / (rs * (temp_c + 273.15))
    factor = (2.0 / (k + 1.0)) ** ((k + 1.0) / (k - 1.0))
    return cd * area_m2 * pa * math.sqrt(term * factor)
