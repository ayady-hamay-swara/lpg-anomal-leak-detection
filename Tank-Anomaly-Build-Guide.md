# Tank anomaly detection: build guide

## Overview

You are building a small system that watches tank pressure and flow, learns what normal looks like, and raises an alert for a slow leak that a fixed alarm line would miss for days. I tested every piece of code in this guide, so if something breaks on your machine, the cause is setup, not the code.

**Why this problem is real.** A plant has hundreds of sensors and nobody can watch them all. A fixed alarm such as "pressure below 13.0 bar" only fires when the damage is already done. A leak that loses 0.03 bar per hour never trips it during a whole 42-hour test window, yet the pattern is clearly abnormal.

**What you will have at the end**

- A simulator that creates 5 days of minute-by-minute readings for three tanks. Tank 7 starts leaking on Tuesday at 06:00.
- Three detectors: a fixed threshold, a rolling z-score, and an Isolation Forest.
- An evaluation script that prints how fast each detector reacts and how many false alarms it raises.
- A Streamlit dashboard that replays the data and shows "Possible slow leak, Tank 7, started Tuesday".
- A 2-minute demo script and a backup plan.

**What you should see.** These numbers come from running the exact code below on the simulated data:

| Detector | Alerts after the leak starts | False-alert minutes on healthy data |
| --- | --- | --- |
| Fixed threshold (13.0 bar) | Never (pressure stayed above 13.49 bar) | 0 |
| Rolling z-score | 1.2 hours | 0 |
| Isolation Forest | 1.4 hours | 3 |

The data is simulated, so say so on your poster and in your pitch. Simulated data is a good choice here because you control exactly when the leak starts, which makes the demo repeatable.

## Setup (about 1 to 2 hours)

Install Python and VS Code, make a project folder with its own virtual environment, install five packages, and run one test line before writing any project code.

1. **Install Python 3.11 or newer** from python.org. On Windows, tick "Add Python to PATH" on the first installer screen. Skipping this tick is the most common beginner problem.
2. **Install VS Code** from code.visualstudio.com, then add its "Python" extension.
3. **Make the project folder.** Create a folder called `tank-anomaly` and open it in VS Code (File, Open Folder). Open the built-in terminal with Terminal, New Terminal.
4. **Create a virtual environment.** This keeps this project's packages separate from everything else:

```bash
python -m venv .venv
```

5. **Activate it.** You know it worked when `(.venv)` appears at the start of the terminal line:

```bash
# Windows (PowerShell)
.venv\Scripts\activate

# Mac or Linux
source .venv/bin/activate
```

If Windows says scripts are disabled, run `Set-ExecutionPolicy -Scope Process Bypass` once in that terminal, then activate again.

6. **Create `requirements.txt`** with these five lines, then install them:

```text
numpy
pandas
scikit-learn
streamlit
plotly
```

```bash
pip install -r requirements.txt
```

7. **Test the install.** This should print `ok`:

```bash
python -c "import numpy, pandas, sklearn, streamlit, plotly; print('ok')"
```

**What each package does**

| Package | Its job here |
| --- | --- |
| numpy | Fast math on arrays of numbers |
| pandas | Tables of readings (rows are minutes, columns are sensors) |
| scikit-learn | The Isolation Forest model |
| streamlit | Turns a Python file into a web dashboard |
| plotly | The interactive charts |

If any step fails, copy the exact error message and ask me. Do not skip ahead, because every later step depends on this one.

## Project structure

The project is four Python files and one text file, each with a single job, so you always know where to look when something breaks.

```text
tank-anomaly/
  requirements.txt   the five packages
  simulate.py        Step 1: makes the fake sensor data
  detect.py          Steps 2, 3, 4: features, detectors, alert rule
  evaluate.py        Step 5: scores the detectors
  app.py             Step 6: the dashboard
  tank_data.csv      created by simulate.py (you do not write this)
```

**How the files connect.** `app.py` and `evaluate.py` both call `make_dataset()` from `simulate.py` and `fit_all()` from `detect.py`. Nothing else imports anything. Keep all files in the same folder.

**How the data flows**

1. `simulate.py` makes a table of readings: time, tank, pressure, flow, and a hidden `leak` flag used only for scoring.
2. `detect.py` learns each tank's normal daily pattern from its first 2 days, turns raw readings into features, and runs the three detectors.
3. `evaluate.py` and `app.py` read the scored table and show the results.

**Rules for yourself**

- Never train on the days that contain the leak. The model may only learn from known-healthy data.
- The `leak` column is the answer key. Detectors must never read it. Only the scoring script and the optional "reveal" checkbox use it.

## Step 1: simulate the sensor data (about 1 to 2 hours)

Create `simulate.py`, which fakes 5 days of one-reading-per-minute data for three tanks and injects a slow leak into Tank 7 only.

**What the fake data contains**

- **Pressure:** 15 bar on average, a gentle daily up-and-down of 0.3 bar (demand changes through the day), and random noise of 0.05 bar.
- **Flow:** 50 m3/h on average, moving opposite to pressure through the day, with noise of 1.0.
- **The leak (Tank 7):** starts on day 3 at 06:00, which is Tuesday. Pressure then sinks by 0.03 bar every hour and flow rises slightly. That is tiny: over 42 hours the pressure only falls about 1.3 bar.
- **Tanks 3 and 5:** perfectly healthy. They exist to prove the model does not cry wolf.

```python
"""Step 1: simulate tank sensor data, with a slow leak injected into one tank."""
import numpy as np
import pandas as pd

MIN_PER_DAY = 1440
START = "2026-10-31 00:00"  # a Saturday, so day 3 is a Tuesday


def simulate_tank(name, days=5, leak_day=None, leak_hour=6,
                  leak_rate=0.03, seed=0):
    """One tank, one reading per minute.

    leak_rate is bar lost per hour. 0.03 is deliberately tiny, so the
    pressure never gets near a fixed alarm line during the demo.
    """
    rng = np.random.default_rng(seed)
    n = days * MIN_PER_DAY
    t = pd.date_range(START, periods=n, freq="min")
    minute = np.arange(n) % MIN_PER_DAY
    daily = np.sin(2 * np.pi * minute / MIN_PER_DAY)   # daily demand cycle

    pressure = 15.0 + 0.30 * daily + rng.normal(0, 0.05, n)   # bar
    flow = 50.0 - 8.0 * daily + rng.normal(0, 1.0, n)         # m3/h

    leak = np.zeros(n, dtype=bool)
    if leak_day is not None:
        start = leak_day * MIN_PER_DAY + leak_hour * 60
        hours = np.clip((np.arange(n) - start) / 60, 0, None)
        pressure -= leak_rate * hours      # pressure slowly sinks
        flow += 0.2 * hours                # a little extra outflow
        leak[start:] = True

    return pd.DataFrame({"time": t, "tank": name, "pressure": pressure,
                         "flow": flow, "leak": leak})


def make_dataset():
    tanks = [
        simulate_tank("Tank 3", seed=3),
        simulate_tank("Tank 5", seed=5),
        simulate_tank("Tank 7", seed=7, leak_day=3, leak_hour=6),
    ]
    return pd.concat(tanks, ignore_index=True)


if __name__ == "__main__":
    df = make_dataset()
    df.to_csv("tank_data.csv", index=False)
    print(df.groupby("tank").size())
    print("saved tank_data.csv")
```

**Run it**

```bash
python simulate.py
```

You should see 7200 rows for each of the three tanks and the line `saved tank_data.csv`.

**Concepts to understand before moving on**

- `rng = np.random.default_rng(seed)` makes the random noise repeatable. The same seed gives the same data every time, which is exactly what you want for a demo.
- `np.sin(...)` builds the smooth daily cycle. One full wave per 1440 minutes (one day).
- `leak_rate * hours` is a ramp: zero before the leak, then growing steadily. That is what a slow leak looks like.
- The `leak` column is only the answer key for scoring and the "reveal" checkbox. Detectors never see it.

**Optional change.** Try `leak_rate=0.1` for a faster leak and watch every detector react sooner. Change it back to 0.03 for the demo.

## Step 2: learn "normal" and build features (about 2 hours)

Start `detect.py`: first learn each tank's normal daily pattern, then measure how far every new reading sits from that pattern, averaged over a one-hour window.

**Why not look at raw pressure?** Pressure naturally rises and falls through the day, so a slow leak hides inside that wave. If you subtract the expected daily pattern first, what remains (the residual) should be pure noise around zero. A leak shows up as a residual that keeps drifting below zero.

**The four features the model will see**

| Feature | Meaning | Why it helps |
| --- | --- | --- |
| `p_mean60` | Average pressure residual over the last 60 minutes | Drops steadily during a leak |
| `p_std60` | How jumpy the pressure residual was in the last hour | Catches sensor faults and bursts |
| `p_change60` | `p_mean60` now minus `p_mean60` one hour ago | The slope: how fast it is falling |
| `f_mean60` | Average flow residual over the last 60 minutes | Leaks often disturb flow too |

**Type this at the top of `detect.py`**

```python
"""Steps 2-3: features, three detectors, and the alert rule."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

MIN_PER_DAY = 1440
TRAIN_DAYS = 2             # the first 2 days of every tank are "known normal"
FIXED_LOW_BAR = 13.0       # the plain alarm line a fixed system would use
Z_LIMIT = -4.0             # z-score alarm when the 1-hour mean is this low
ALERT_MINUTES = 15         # alarm must hold this long before we alert
FEATURES = ["p_mean60", "p_std60", "p_change60", "f_mean60"]


# ---- Step 2: learn "normal" and build features ---------------------------
def _design(minute_of_day):
    w = 2 * np.pi * minute_of_day / MIN_PER_DAY
    return np.column_stack([np.ones_like(w), np.sin(w), np.cos(w),
                            np.sin(2 * w), np.cos(2 * w)])


def _minute_of_day(time):
    return (time.dt.hour * 60 + time.dt.minute).to_numpy()


def fit_baseline(train):
    """Fit the normal daily pattern of pressure and flow on healthy data."""
    X = _design(_minute_of_day(train["time"]))
    return {col: np.linalg.lstsq(X, train[col].to_numpy(), rcond=None)[0]
            for col in ("pressure", "flow")}


def add_features(df, baseline):
    """Residual = reading minus what we expect at that time of day."""
    df = df.copy()
    X = _design(_minute_of_day(df["time"]))
    p_res = df["pressure"] - X @ baseline["pressure"]
    f_res = df["flow"] - X @ baseline["flow"]
    df["p_mean60"] = p_res.rolling(60).mean()
    df["p_std60"] = p_res.rolling(60).std()
    df["p_change60"] = df["p_mean60"] - df["p_mean60"].shift(60)
    df["f_mean60"] = f_res.rolling(60).mean()
    return df.dropna().reset_index(drop=True)
```

**How to read this code**

- `_design` turns the time of day into a few smooth sine and cosine waves. `fit_baseline` finds the best blend of those waves that matches healthy pressure and flow. That blend is the "expected" daily pattern.
- `add_features` subtracts the expected pattern (the residual), then uses `.rolling(60)` to look at the latest 60 minutes at every row.
- `.dropna()` removes the first hour, where there are not yet 60 readings to average (and 60 more for `p_change60`).
- The baseline is fitted only on the first 2 days (`TRAIN_DAYS`), which you will see used in Step 4.

**Concept check.** If you set the rolling window to 5 minutes instead of 60, features get jumpier and detect faster but raise more false alarms. A longer window is calmer but slower. This trade-off is the main tuning knob of the whole project.

## Step 3: the three detectors (about 2 hours)

Add a `Detectors` class to `detect.py` that runs a fixed threshold, a rolling z-score and an Isolation Forest side by side, so you can show why the smarter ones win.

| Detector | What it asks | Catches | Weakness |
| --- | --- | --- | --- |
| Fixed threshold | Is pressure below 13.0 bar? | Big, sudden failures | Blind to slow drift until it is nearly too late |
| Rolling z-score | Is the 1-hour average residual unusually low (below -4 standard deviations)? | Slow drift in one signal | Looks at only one feature |
| Isolation Forest | Is this combination of all four features rare compared with healthy data? | Odd patterns across several signals at once | Harder to explain, needs a tuned cut-off |

**Add this below the Step 2 code in `detect.py`**

```python
# ---- Step 3: three detectors ---------------------------------------------
class Detectors:
    def __init__(self, train_features):
        self.mu = train_features["p_mean60"].mean()
        self.sd = train_features["p_mean60"].std()
        self.forest = IsolationForest(n_estimators=200, random_state=0)
        self.forest.fit(train_features[FEATURES])
        scores = self.forest.score_samples(train_features[FEATURES])
        self.score_limit = np.quantile(scores, 0.0005)   # rarest 0.05%

    def run(self, df):
        out = df.copy()
        out["z"] = (out["p_mean60"] - self.mu) / self.sd
        out["score"] = self.forest.score_samples(out[FEATURES])
        out["alarm_fixed"] = out["pressure"] < FIXED_LOW_BAR
        out["alarm_z"] = out["z"] < Z_LIMIT
        out["alarm_forest"] = out["score"] < self.score_limit
        return out
```

**Detector 1: fixed threshold.** One line: `pressure < 13.0`. It is your baseline and your punchline. In the demo it stays silent while the tank quietly loses pressure.

**Detector 2: rolling z-score.** A z-score says how many "normal wobbles" away from average a value is. `mu` and `sd` are the average and spread of `p_mean60` on healthy data. A z-score of -4 means the last hour of pressure is 4 normal wobbles below expected. That almost never happens by chance, so it is a leak signal. It is simple and easy to explain to judges.

**Detector 3: Isolation Forest.** This is the machine learning part.

1. Training: `fit` builds 200 random decision trees from healthy feature rows only. Each tree repeatedly splits the data at random points.
2. The idea: odd points get isolated in very few splits, normal points need many. The average split count becomes a score.
3. `score_samples` returns that score. Lower means more unusual.
4. `score_limit` is the 0.05th percentile of healthy scores. Anything scoring below it is rarer than 99.95% of healthy data, so it counts as an alarm.

**An honest note for your pitch.** On this simple data the z-score and the forest both catch the leak at nearly the same time. The forest earns its place because it uses several features at once, so it can also flag problems the z-score cannot, such as a sensor getting noisy (`p_std60`) or flow behaving oddly. Say that, and do not claim the forest is magic.

**Why `random_state=0`?** It fixes the randomness so the model gives identical results each run. Remove it and results change slightly every time, which is risky before a demo.

## Step 4: the alert rule and the training loop (about 1 hour)

Finish `detect.py` with a rule that turns raw alarms into alerts only when the alarm lasts 15 minutes, and a function that trains and scores every tank.

**Why wait 15 minutes?** One strange reading is usually noise. A real leak keeps going. Requiring 15 alarm minutes in a row removes one-off blips at the cost of 15 minutes of delay.

**Add this to the bottom of `detect.py`**

```python
# ---- Step 4: the alert rule and the training loop -------------------------
def to_alert(alarm, minutes=ALERT_MINUTES):
    """True only when the alarm has been on for `minutes` in a row."""
    return alarm.astype(int).rolling(minutes).sum().eq(minutes)


def fit_all(raw):
    """Train on each tank's healthy days, then score every tank."""
    results = []
    for _, tank_df in raw.groupby("tank"):
        tank_df = tank_df.reset_index(drop=True)
        cutoff = tank_df["time"].iloc[0] + pd.Timedelta(days=TRAIN_DAYS)
        baseline = fit_baseline(tank_df[tank_df["time"] < cutoff])
        feats = add_features(tank_df, baseline)
        train = feats[feats["time"] < cutoff]
        scored = Detectors(train).run(feats)
        scored["is_test"] = scored["time"] >= cutoff
        for name in ("fixed", "z", "forest"):
            scored[f"alert_{name}"] = to_alert(scored[f"alarm_{name}"])
        results.append(scored)
    return pd.concat(results, ignore_index=True)
```

**How `to_alert` works.** `alarm` is a column of True and False. `.astype(int)` turns that into 1 and 0. `.rolling(15).sum()` adds the last 15 values. If the sum is exactly 15, all 15 minutes were alarms, so it returns True.

**How `fit_all` works, line by line**

1. Loop over each tank, because each tank has its own normal behaviour.
2. `cutoff` is the start time plus 2 days. Everything before it is training data.
3. Fit the daily baseline on the training days only, then build features for all days.
4. Train the detectors on the training features only.
5. `is_test` marks the later days. You will judge the system only on those.
6. Convert each alarm column into an alert column using the 15-minute rule.

**Check that it works.** Run this in the terminal:

```bash
python -c "from simulate import make_dataset; from detect import fit_all; r = fit_all(make_dataset()); print(r.shape)"
```

Expected output is `(21243, 18)`: 18 columns, and 7081 rows per tank, because the first 119 minutes of each tank are dropped while the rolling windows fill up. The wait takes a few seconds while the three forests train.

**Known trap.** If you see `KeyError: 'p_mean60'`, Step 2 was not pasted correctly. If you see `ModuleNotFoundError: simulate`, your terminal is not inside the `tank-anomaly` folder.

## Step 5: evaluate the detectors (about 1 hour)

Create `evaluate.py`, which prints two numbers for each detector: how long it took to alert after the leak began, and how many false-alert minutes it raised on healthy data.

These two numbers are the honest scorecard of the project. Detection delay measures speed. False alerts measure how much people would learn to ignore the system.

```python
"""Step 5: how good is each detector? Delay on the leaky tank, false alarms elsewhere."""
import pandas as pd
from simulate import make_dataset
from detect import fit_all

res = fit_all(make_dataset())
test = res[res["is_test"]]

rows = []
for name in ("fixed", "z", "forest"):
    col = f"alert_{name}"
    leak_df = test[(test["tank"] == "Tank 7") & test["leak"]]
    hit = leak_df[leak_df[col]]
    if hit.empty:
        delay = "never"
    else:
        delay = f"{(hit['time'].iloc[0] - leak_df['time'].iloc[0]).total_seconds() / 3600:.1f} h"
    healthy = test[~test["leak"]]
    false_minutes = int(healthy[col].sum())
    rows.append({"detector": name, "detection delay": delay,
                 "false-alert minutes (healthy data)": false_minutes})

print(pd.DataFrame(rows).to_string(index=False))
```

**Run it**

```bash
python evaluate.py
```

**Expected output**

```text
detector detection delay  false-alert minutes (healthy data)
   fixed           never                                   0
       z           1.2 h                                   0
  forest           1.4 h                                   3
```

**What the code does**

- `test` keeps only the days after training. Judging on training data would be cheating.
- `leak_df` is Tank 7 after the leak begins. `hit` is the rows where the detector had raised an alert. The first hit time minus the leak start time is the detection delay.
- `healthy` is every row with no leak: all of Tanks 3 and 5, plus Tank 7 before the leak. Any alert there is a false alarm.

**How to read the result.** The fixed threshold never alerts during the 42 hours, because the pressure bottoms out at 13.49 bar. The z-score alerts after 1.2 hours with no false alarms. The forest alerts after 1.4 hours and raised one short false alert on Tank 3 (3 alert minutes, on Tuesday around 20:24). Report that honestly. It shows you measured the system instead of just showing the good case.

**Tuning knobs.** Change one at a time, re-run `evaluate.py`, and write down the three numbers each time.

| Knob | File | Raise it | Lower it |
| --- | --- | --- | --- |
| `Z_LIMIT` (-4.0) | `detect.py` | Closer to 0: faster, more false alarms | More negative: slower, fewer false alarms |
| `0.0005` in `np.quantile` | `detect.py` | More forest alarms, more false alerts | Fewer forest alarms, slower |
| `ALERT_MINUTES` (15) | `detect.py` | Slower, fewer false alerts | Faster, more false alerts |
| Window `60` in `rolling(60)` | `detect.py` | Calmer and slower | Faster and noisier |
| `leak_rate` (0.03) | `simulate.py` | Faster leak, quicker detection | Slower leak, harder to catch |

**A good experiment for your pitch.** Try `leak_rate=0.01`. A leak of 0.01 bar per hour is very hard to see by eye. Note which detectors still catch it and how long they take. "We tested three leak speeds" is a strong sentence in a presentation.

## Step 6: the dashboard (about 2 to 3 hours)

Create `app.py`, a Streamlit page that replays the data for one tank, shows "Silent" next to "LEAK DETECTED", and prints the alert message with the estimated start time.

This is the part judges actually look at, so it is what stops the project from feeling like "just a notebook".

**What the page shows**

- A sidebar with a tank picker, an Autoplay checkbox, a "reveal the true leak start" checkbox, and a slider for how many hours of the replay to show.
- Two status boxes: the fixed threshold (Silent or ALARM) and your model (Normal or LEAK DETECTED).
- A red banner such as "Possible slow leak, Tank 7, started Tuesday 06:36. Detected Tuesday 07:27." or a green "readings look normal" banner.
- A pressure chart with the fixed alarm line and an orange marker where the model flagged the leak.
- A second chart of the anomaly signal (the z-score) with its alarm limit.

```python
"""Step 6: the dashboard. Run with:  streamlit run app.py"""
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from detect import FIXED_LOW_BAR, Z_LIMIT, fit_all
from simulate import make_dataset

st.set_page_config(page_title="Tank leak monitor", layout="wide")


@st.cache_data
def load():
    return fit_all(make_dataset())


results = load()
test = results[results["is_test"]]

# ---- sidebar --------------------------------------------------------------
st.sidebar.header("Replay")
tank = st.sidebar.selectbox("Tank", sorted(test["tank"].unique()), index=2)
view_all = test[test["tank"] == tank].reset_index(drop=True)
max_hour = len(view_all) // 60 - 1
play = st.sidebar.checkbox("Autoplay")
show_truth = st.sidebar.checkbox("Reveal true leak start")

if "hour" not in st.session_state:
    st.session_state.hour = max_hour
if play and st.session_state.hour < max_hour:
    st.session_state.hour += 1
hour = st.sidebar.slider("Hours into replay", 1, max_hour, key="hour")

view = view_all.iloc[: hour * 60]
now = view["time"].iloc[-1]

# ---- status ---------------------------------------------------------------
st.title("Tank leak monitor")
st.caption(f"{tank} | simulated data | replay time: {now:%A %H:%M}")

fixed_on = bool(view["alert_fixed"].any())
model_hits = view[view["alert_forest"]]
model_on = not model_hits.empty

c1, c2 = st.columns(2)
c1.metric("Fixed threshold (below %.1f bar)" % FIXED_LOW_BAR,
          "ALARM" if fixed_on else "Silent")
c2.metric("Our model", "LEAK DETECTED" if model_on else "Normal")

if model_on:
    alert_time = model_hits["time"].iloc[0]
    before = view[(view["time"] < alert_time) & (view["z"] >= -1)]
    onset = before["time"].iloc[-1] if not before.empty else alert_time
    st.error(f"Possible slow leak, {tank}, started {onset:%A %H:%M}. "
             f"Detected {alert_time:%A %H:%M}.")
else:
    st.success(f"{tank}: readings look normal.")

# ---- pressure chart -------------------------------------------------------
fig = go.Figure()
fig.add_trace(go.Scatter(x=view["time"], y=view["pressure"],
                         name="Pressure (bar)", line=dict(width=2)))
fig.add_hline(y=FIXED_LOW_BAR, line_dash="dash",
              annotation_text="Fixed low-pressure alarm")
if model_on:
    fig.add_vline(x=alert_time, line_color="orange")
    fig.add_annotation(x=alert_time, y=1, yref="paper", showarrow=False,
                       text="Model flags it", font=dict(color="orange"))
if show_truth and view_all["leak"].any():
    truth = view_all[view_all["leak"]]["time"].iloc[0]
    if truth <= now:
        fig.add_vline(x=truth, line_dash="dot", line_color="gray")
fig.update_layout(title="Pressure", yaxis_range=[12.5, 15.8],
                  height=380, margin=dict(t=50, b=10))
st.plotly_chart(fig, width="stretch")

# ---- signal chart ---------------------------------------------------------
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=view["time"], y=view["z"], name="z-score"))
fig2.add_hline(y=Z_LIMIT, line_dash="dash", annotation_text="Alarm limit")
fig2.update_layout(title="Anomaly signal (how far below normal)",
                   height=240, margin=dict(t=50, b=10))
st.plotly_chart(fig2, width="stretch")

if play and st.session_state.hour < max_hour:
    time.sleep(0.15)
    st.rerun()
```

**Run it**

```bash
streamlit run app.py
```

Your browser opens at `http://localhost:8501`. The first load takes a few seconds while the models train. Every later change is instant because of `@st.cache_data`.

**What I tested.** I ran this page headlessly. Tank 7 at the full replay shows "Silent" for the fixed threshold and "LEAK DETECTED" for the model, with the banner "started Tuesday 06:36. Detected Tuesday 07:27." Tank 7 at hour 10 and Tank 3 show the green normal state. The true leak start is Tuesday 06:00, so the estimated start is about 36 minutes late. That is normal: the onset is estimated by walking back to the last time the signal was healthy.

**How the key pieces work**

- Streamlit re-runs the whole file from top to bottom every time you touch a control. That is why the slider value lives in `st.session_state`: it remembers where the replay is.
- `view = view_all.iloc[: hour * 60]` is the "live" trick. The page only sees the first N hours, so dragging the slider (or Autoplay) feels like data arriving in real time.
- `onset` looks backwards from the alert for the last moment the z-score was above -1, which marks where the drift began.
- `reveal true leak start` draws the answer key as a grey dotted line, so you can show judges the model was close.

**Polish ideas, in order of value**

1. Keep the layout exactly as it is; the side-by-side "Silent" versus "LEAK DETECTED" is your demo.
2. Add a title line under `st.title`, such as your team name.
3. Take a screenshot of the finished alert state for your backup slides.
4. Only after that, experiment with colours or extra charts.

## Step 7: the demo (about 2 hours including rehearsal)

The demo is a 2-minute story: a healthy tank, then a tank that leaks slowly, the fixed alarm staying silent, and your model catching it.

**Before you start.** Run `streamlit run app.py` and leave it open on Tank 7. Drag the "Hours into replay" slider all the way down to 1 so the story starts from the beginning. Autoplay only moves forward, so it does nothing if the slider is already at the end.

**The 2-minute script**

| Time | What you do | What you say |
| --- | --- | --- |
| 0:00 | Show the poster or title slide | "Plants have hundreds of sensors and nobody can watch them all. A fixed alarm only fires when it is almost too late." |
| 0:15 | Switch the picker to Tank 3 | "This is a healthy tank. Pressure rises and falls with daily demand. Everything is green." |
| 0:35 | Switch to Tank 7, slider at 1, tick Autoplay | "Same kind of tank. Watch the pressure." Let it run past hour 30. |
| 1:00 | Point at the fixed-threshold box | "The fixed alarm is still silent. Pressure never goes near the alarm line." |
| 1:15 | The red banner appears | "Our model flags a possible slow leak and estimates when it started." |
| 1:30 | Tick "Reveal true leak start" | "The real leak began at 06:00 Tuesday. We detected it about 1.4 hours later. The fixed alarm never fired." |
| 1:45 | Show the results table (slide or terminal) | "We learn each tank's normal daily pattern, then score every hour with a rolling z-score and an Isolation Forest." |
| 2:00 | Stop | "Next step: real sensor data from a pump station." |

**Timing warning.** Autoplay re-draws both charts for every simulated hour, so replay speed depends on your laptop. Time it in rehearsal. If it is too slow, change `time.sleep(0.15)` in `app.py` to `0.0`, or just drag the slider by hand.

**The 30-second pitch, if judges stop by your table**

> "Fixed alarms miss slow leaks. We built an anomaly detector that learns what normal looks like for each tank and flags the drift early. On simulated data it caught a 0.03 bar per hour leak in about an hour and a half, while a fixed threshold never fired during the 42-hour test window."

**Backup plan.** Things go wrong in front of judges, so prepare these before the event:

- A 60-second screen recording of the full demo working.
- A screenshot of the red alert state with the pressure chart.
- The `evaluate.py` output saved as text, to paste into a slide.
- The project folder on a USB stick or cloud drive, in case your laptop dies.
- Know the one-line fix: close the terminal, open a new one in the project folder, activate `.venv`, run `streamlit run app.py` again.

**Rehearsal checklist**

- [ ] `python evaluate.py` runs and the output matches the table in Step 5
- [ ] The dashboard shows the red banner for Tank 7 at full replay
- [ ] The dashboard shows green for Tank 3 and for Tank 7 at 10 hours
- [ ] Demo timed at 2 minutes or less, at least 3 times
- [ ] Backup recording and screenshot saved
- [ ] Browser zoom set to 125% so the back row can read it
- [ ] Laptop charged, charger packed, notifications turned off
- [ ] Poster finished with team names filled in
- [ ] Everyone on the team can explain each detector in one sentence

## Timeline

Plan for 12 to 15 working hours over two days if you have never written Python. Earlier I estimated 8 to 12 hours, but that assumed less time reading and fixing errors, so use this longer figure.

| Step | Hours | When |
| --- | --- | --- |
| Setup: Python, VS Code, packages | 1 to 2 | Day 1 morning |
| Step 1: simulator | 1 to 2 | Day 1 morning |
| Step 2: features | 2 | Day 1 afternoon |
| Step 3: detectors | 2 | Day 1 afternoon |
| Step 4: alert rule and training loop | 1 | Day 1 evening |
| Step 5: evaluation | 1 | Day 1 evening |
| Step 6: dashboard | 2 to 3 | Day 2 morning |
| Step 7: demo and rehearsal | 2 | Day 2 afternoon |

**Ground rules for working fast**

- Make it run first, then understand it, then improve it. Paste a section, run it, and only move on when it works.
- Run the code after every step. Finding a mistake one step later is far cheaper than finding it five steps later.
- Change one thing at a time. If two changes break it, you will not know which one did.
- Never spend more than 30 minutes stuck. Copy the full error message, with the last line and the line number, and ask for help.

**If you run out of time: the minimum viable version.** This takes about 6 to 7 hours and still tells the full story.

| Priority | Include | Skip |
| --- | --- | --- |
| Must | Steps 1 and 2, the fixed threshold, the z-score, and a basic dashboard with the slider | Autoplay, the reveal checkbox |
| Should | The Isolation Forest and `evaluate.py` | The second chart |
| Could | Autoplay, the reveal checkbox, extra tanks, the leak-speed experiment | Anything not listed in this guide |

In the minimum version, the machine learning claim rests on the Isolation Forest. If you drop it, change your form answer and poster from "Isolation Forest" to "statistical anomaly detection" so you never claim something you did not build.

**Suggested split for a team of two or three**

- Person A: Steps 1 to 4 (data and detectors).
- Person B: Step 6 (dashboard), starting with a fake status box while A finishes.
- Everyone: Step 5 together, then Step 7 and the poster.

## Common errors, stretch goals and judge questions

Most beginner problems are setup problems, so check this table before anything else.

**Common errors and fixes**

| Error or symptom | Cause | Fix |
| --- | --- | --- |
| `python` is not recognized | Python is not on PATH | Reinstall and tick "Add Python to PATH", or try `py` instead of `python` |
| Scripts are disabled (PowerShell) | Windows security setting | `Set-ExecutionPolicy -Scope Process Bypass`, then activate again |
| `No module named 'sklearn'` | Virtual environment not active, or package missing | Activate `.venv`, then `pip install scikit-learn` (installed as scikit-learn, imported as sklearn) |
| `No module named 'simulate'` | Terminal is in the wrong folder | `cd` into `tank-anomaly`; keep all files in that one folder |
| `KeyError: 'p_mean60'` | Step 2 code missing or mistyped | Re-paste the Step 2 block exactly |
| `IndentationError` | Mixed tabs and spaces from copy and paste | Re-paste the block, keep 4 spaces per level |
| `streamlit` is not recognized | Streamlit not on PATH | Run `python -m streamlit run app.py` |
| `TypeError` about `width` in `plotly_chart` | Older Streamlit version | `pip install --upgrade streamlit` |
| Port 8501 already in use | A previous dashboard is still running | Close the old terminal, or `streamlit run app.py --server.port 8502` |
| First dashboard load is slow | Three forests are training | Normal. It is cached afterwards |
| Numbers differ slightly from this guide | Different library versions | Fine if the story holds: fixed never fires, the model alerts within a few hours |

**If a block of code throws an error you cannot fix in 30 minutes.** Copy the whole terminal message from `Traceback` to the last line, plus the file name and line number, and ask. Do not retype code from memory. Paste it again from this guide.

**Stretch goals (only after the demo works)**

1. **Speed experiment:** run `evaluate.py` for leak rates 0.01, 0.03 and 0.1 and show the delays in a small table.
2. **Telegram alert:** send a message from `app.py` when the first alert appears.
3. **Real data:** swap the simulator for a public predictive maintenance dataset, and say clearly in your pitch that it replaced the simulated data.
4. **LSTM autoencoder:** a neural network that learns to reconstruct normal data and flags what it cannot. It is the most impressive extra and the most time-consuming. Attempt it only with a full day to spare.
5. **Link to the hardware project:** feed live MQ-6 readings from the ESP32 into this detector.

**Questions judges are likely to ask**

| Question | Short answer |
| --- | --- |
| Why simulated data? | We control exactly when the leak starts, so we can measure detection delay. Real plants rarely have labelled leaks. Real data is our next step. |
| Why not just set a tighter threshold? | Normal pressure already swings about 0.6 bar every day. A threshold tight enough to catch a 0.03 bar per hour leak would fire on healthy tanks daily. |
| Is it overfitted? | No. We train on each tank's first 2 days and judge on later days. Two healthy tanks test false alarms. |
| What is an Isolation Forest? | A model that builds many random decision trees. Unusual readings are separated in fewer splits, so they score as anomalies. |
| How many false alarms? | In our test, one short false alert on one healthy tank across three tanks and three days. It is tunable: fewer false alarms means slower detection. |
| Would it work in real time? | Yes. It uses only past readings in rolling windows. The dashboard replays recorded data to show it. |
| What are the limits? | Sensors drift over time, so the baseline must be refitted regularly. It detects abnormal patterns, not the cause of a leak. |
| Who would use it? | Plant operators and maintenance teams who cannot watch hundreds of sensors by eye. |

If a judge asks something you cannot answer, say so and describe how you would find out. That is a stronger answer than guessing.
