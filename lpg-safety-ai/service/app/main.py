from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncio, yaml
from app.sim.engine import Simulator
from app.sim.scenarios import apply_scenario, SCENARIOS
from app.alarms.engine import AlarmEngine
from app.alarms.rules import load_alarm_rules
from app.ai.limits import forecast_limit
from app.ai.risk import risk_score

ROOT = Path(__file__).resolve().parents[2]
with open(ROOT / "config" / "plant.yaml", "r", encoding="utf-8") as f:
    PLANT = yaml.safe_load(f)

app = FastAPI(title="LPG Safety AI Advisory", version="0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
sim = Simulator()
alarms = AlarmEngine()
rules = load_alarm_rules()

@app.on_event("startup")
async def run_loop():
    async def loop():
        while True:
            sim.step()
            await asyncio.sleep(1.0)
    asyncio.create_task(loop())

def assessment_for_state():
    assessments = []
    for cfg in PLANT["tanks"]:
        tid = cfg["id"]
        tank = sim.tanks[tid]
        pressure = tank.get("P_gauge", 0.0)
        level = tank.get("level_pct", 0.0)
        pressure_hh = cfg["design_pressure_barg"] * PLANT["limits"]["pressure_hh_fraction"]
        heat_rise = max(0.0, sim.ambient_temperature() - tank["T_liquid"])
        leak_assets = [a for a in sim.assets if a.get("parent") == tid and a.get("state") != "healthy"]
        leak_strength = min(1.0, sum(a.get("area_mm2", 0.0) for a in leak_assets) / 25.0)
        sensor_problem = bool(tank.get("sensor_faults"))
        score, factors = risk_score(pressure, pressure_hh, level, heat_rise, leak_strength, sensor_problem, PLANT["risk_weights"])
        prediction = forecast_limit(tank, cfg, sim.ambient_temperature() + 10.0, PLANT["product"]["propane_fraction"])
        confidence = "low" if sensor_problem else "high"
        limits = ["Model values are not plant-certified"]
        if sensor_problem:
            limits.append("A tank instrument fault reduces confidence; use independent plant indications")
        suspects = []
        for asset in sorted(leak_assets, key=lambda a: a.get("corrosion_index", 0), reverse=True)[:3]:
            suspects.append({"asset":asset["code"],"probability":round(1.0/max(1,len(leak_assets)),3),"state":asset["state"]})
        assessments.append({"subject":tid,"risk_score":score,"confidence":confidence,"top_factors":factors,
                            "leak_suspects":suspects,"predictions":prediction,
                            "limitations":limits})
    return assessments

@app.get("/health")
def health():
    return {"status":"ok","mode":"simulator-only","equipment_write_path":False}

@app.get("/state")
def state():
    frame = sim.frame_dict()
    assessments = assessment_for_state()
    return {"frame":frame,"tank_summary":sim.tanks,"assets":sim.assets,"assessment":assessments,"active_alarms":alarms.active()}

@app.get("/history")
def history(tag: str = Query(...), minutes: int = 120):
    values = sim.history.get(tag, [])[-minutes:] if isinstance(sim.history, dict) else []
    return {"tag":tag,"minutes":minutes,"values":values}

@app.post("/sim/control")
def control(body: dict):
    try:
        sim.apply_control(body)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"status":"applied","frame":sim.frame_dict()}

@app.post("/sim/scenario/{name}")
def scenario(name: str):
    try:
        apply_scenario(sim, name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"status":"started","scenario":name,"frame":sim.frame_dict()}

@app.post("/sim/reset")
def reset(body: dict | None = None):
    seed = (body or {}).get("seed", PLANT["seed"])
    sim.reset(seed=int(seed))
    return {"status":"reset","frame":sim.frame_dict()}

@app.post("/sim/speed")
def speed(body: dict):
    factor = body.get("factor")
    if factor not in (1,10,60,600):
        raise HTTPException(status_code=422, detail="factor must be 1, 10, 60 or 600")
    sim.speed = factor
    return {"speed":factor}

@app.get("/ai/assessment")
def ai_assessment():
    return assessment_for_state()

@app.get("/assets")
def assets():
    return sim.assets

@app.get("/alarms")
def alarm_list(state: str | None = None):
    result = alarms.active() if state == "active" else list(alarms.alarms.values())
    return result

@app.post("/alarms/{alarm_id}/ack")
def ack(alarm_id: str, body: dict | None = None):
    try:
        return alarms.acknowledge(alarm_id, (body or {}).get("user","operator"))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/alarms/{alarm_id}/shelve")
def shelve(alarm_id: str, body: dict):
    try:
        return alarms.shelve(alarm_id, body.get("reason","nuisance"), int(body.get("duration_min",60)))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc,KeyError) else 422, detail=str(exc))

@app.post("/sim/generate")
def generate(days: int = 14, seed: int = 1):
    sim.reset(seed=seed)
    sim.run_seconds(days * 86400)
    return {"status":"generated","days":days,"seed":seed}
