from app.sim.physics import gauge_pressure, liquid_density, level_from_mass

def test_reference_pressure_table():
    by_temp = {0:2.24, 10:3.39, 20:4.81, 30:6.54, 40:8.61, 50:11.05, 60:13.89}
    for temp, expected in by_temp.items():
        assert abs(gauge_pressure(temp) - expected) / expected < 0.02

def test_density_and_level_temperature_expand():
    assert liquid_density(30) < liquid_density(20)
    mass = 200_000
    assert level_from_mass(mass, 40, 500) > level_from_mass(mass, 20, 500)
