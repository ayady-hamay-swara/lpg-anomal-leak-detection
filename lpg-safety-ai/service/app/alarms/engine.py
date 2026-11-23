from datetime import datetime, timezone
from uuid import uuid4

class AlarmEngine:
    def __init__(self):
        self.alarms = {}
        self.history = []

    def raise_alarm(self, kind: str, tag: str, priority: str, message: str, action: str):
        alarm_id = f"A-{uuid4().hex[:8]}"
        alarm = {"id": alarm_id,"tag":tag,"kind":kind,"priority":priority,"message":message,"action":action,
                 "state":"Active-Unacknowledged","raised_at":datetime.now(timezone.utc).isoformat(),"acked_at":None,
                 "shelved_until":None,"first_out":False}
        self.alarms[alarm_id] = alarm
        self.history.append(dict(alarm, event="raised"))
        return alarm

    def acknowledge(self, alarm_id: str, user: str = "operator"):
        alarm = self.alarms.get(alarm_id)
        if not alarm:
            raise KeyError("Alarm not found")
        alarm["state"] = "Active-Acknowledged"
        alarm["acked_at"] = datetime.now(timezone.utc).isoformat()
        alarm["acked_by"] = user
        self.history.append(dict(alarm, event="acked"))
        return alarm

    def shelve(self, alarm_id: str, reason: str, minutes: int = 60):
        alarm = self.alarms.get(alarm_id)
        if not alarm:
            raise KeyError("Alarm not found")
        if minutes < 1 or minutes > 480:
            raise ValueError("Shelving duration must be 1 to 480 minutes")
        alarm["state"] = "Shelved"
        alarm["shelve_reason"] = reason
        alarm["shelved_until"] = (datetime.now(timezone.utc).timestamp() + minutes * 60)
        return alarm

    def active(self):
        return [a for a in self.alarms.values() if a["state"] not in ("Normal","Cleared")]
