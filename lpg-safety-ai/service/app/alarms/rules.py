from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[3]

def load_alarm_rules() -> dict:
    with open(ROOT / "config" / "alarms.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    required = {"purpose","consequence_if_ignored","operator_action","response_time_min","priority"}
    for kind, rule in data["alarms"].items():
        missing = required - set(rule)
        if missing:
            raise ValueError(f"Alarm {kind} missing rationalisation fields: {sorted(missing)}")
    return data["alarms"]
