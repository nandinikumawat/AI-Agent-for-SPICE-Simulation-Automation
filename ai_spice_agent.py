#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import csv  # ==== NEW: for CSV output
import json
import argparse
import subprocess
from pathlib import Path

# ==== NEW: run sweep headlessly to export CSV/plots (used by both modes)
def sweep_and_export(gate, vdd, temps, loads_list, single_load_line, jpg_flag):
    import csv
    csv_rows = []
    all_metric_names = set()
    metric_points_by_temp = {}

    for t in temps:
        for load_text in (loads_list or [""]):
            load_line = f"Cl out 0 {load_text}" if load_text else single_load_line
            cap_tag = sanitize_cap_for_tag(load_text) if load_text else "noC"

            net = build_netlist(gate, vdd, int(t), load_line, cap_tag, interactive=False)
            deck_name = f"agent_run_{t}C_{cap_tag}.cir"
            print(f"\n[CSV sweep] TEMP={t}C, Cload={load_text or 'n/a'} ...")
            meas = run_ngspice(net, deck_name, interactive=False)

            # parse -> ps
            if meas:
                meas_ps = meas_to_ps(meas)
                print("  (ps):", pretty_ps(meas_ps))
            else:
                meas_ps = {}

            # waveform PNG (optional)
            dat = f"sim_{t}C_{cap_tag}.dat"
            png = f"agent_run_{t}C_{cap_tag}.png"
            _ = plot_from_wrdata(dat, png, gate)

            # CSV row
            row = {
                "gate": gate,
                "vdd_V": vdd,
                "temp_C": int(t),
                "load": load_text or "",
                "load_fF": cap_text_to_fF(load_text) if load_text else ""
            }
            for k, v in meas_ps.items():
                row[k] = float(v)
                all_metric_names.add(k)
            csv_rows.append(row)

            # collect points for delay-vs-C plots
            c_val = cap_text_to_fF(load_text) if load_text else None
            for k, v in meas_ps.items():
                metric_points_by_temp.setdefault(k, {}).setdefault(int(t), []).append((c_val, float(v)))

    # write CSV
    base_cols = ["gate", "vdd_V", "temp_C", "load", "load_fF"]
    metric_cols = sorted(all_metric_names)
    header = base_cols + metric_cols
    out_csv = "meas_sweep.csv"
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        for r in csv_rows:
            for m in metric_cols:
                if m not in r:
                    r[m] = ""
            w.writerow(r)
    print(f"\nSaved CSV: {out_csv}")

    # plots of delay vs Cload
    for metric_name, temp_map in metric_points_by_temp.items():
        plot_delay_vs_cload(temp_map, metric_name)
    print("Generated delay-vs-Cload plots.")

TEMP_RE = re.compile(r"-?\d+")

def coerce_temp_to_int(x):
    """Accepts 25, '25', '25 C', {'value':25}, {'temperature': '25C'}, etc."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return int(round(float(x)))
    if isinstance(x, dict):
        # try common keys
        for k in ("value", "temp", "temperature"):
            if k in x and x[k] is not None:
                return coerce_temp_to_int(x[k])
        # fall back: search any numeric in dict values
        for v in x.values():
            t = coerce_temp_to_int(v)
            if t is not None:
                return t
        return None
    # string-ish fallback
    m = TEMP_RE.search(str(x))
    return int(m.group(0)) if m else None

def coerce_temp_list(xs, fallback):
    out = []
    if not xs:
        return [fallback]
    for item in xs:
        t = coerce_temp_to_int(item)
        if t is not None:
            out.append(t)
    return out or [fallback]


# ---------- Unit helpers (preserve fF/pF text) ----------
UNIT_CANON = {"ff":"fF","pf":"pF","nf":"nF","uf":"uF","mf":"mF","f":"F"}

def format_cap_for_netlist(x):
    """Preserve user-entered capacitance text: '5 fF' -> '5fF', 12 -> '12pF'."""
    if isinstance(x, (int, float)):
        num = f"{int(x)}" if float(x).is_integer() else f"{x:g}"
        return num + "pF"
    s = str(x).strip()
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([a-zA-Z]+)?$", s)
    if not m:
        return s
    num = m.group(1)
    unit = (m.group(2) or "").lower()
    if unit == "":
        return f"{num}pF"
    unit = UNIT_CANON.get(unit, UNIT_CANON.get(unit.lower(), unit))
    return f"{num}{unit}"

def sanitize_cap_for_tag(s):
    """Turn '5fF' into '5fF' tag-safe (remove spaces/slashes)."""
    return re.sub(r"[^0-9a-zA-Z]", "", str(s))

# ==== NEW: helpers to parse load text to numeric fF (for plotting/CSV)
CAP_TO_FF = {
    "ff": 1.0,
    "pf": 1e3,
    "nf": 1e6,
    "uf": 1e9,
    "mf": 1e12,
    "f":  1e15,
}
def cap_text_to_fF(txt):
    """
    '5fF' -> 5.0, '10pF' -> 10000.0 (fF), '0.02nF' -> 20000.0 (fF).
    If parsing fails, returns None.
    """
    if not txt:
        return None
    s = str(txt).strip()
    m = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z]+)\s*$", s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit not in CAP_TO_FF:
        return None
    return val * CAP_TO_FF[unit]

# ========== Model include (PTM 45nm) ==========
MODEL_PATH = "45nm_LP.pm"
if not Path(MODEL_PATH).exists():
    raise FileNotFoundError(
        f"Model file not found: {MODEL_PATH}\n"
        "Place 45nm_LP.pm next to this script or update MODEL_PATH."
    )
MODEL_INCLUDE = f'.include "{MODEL_PATH}"'

# ========== (Optional) Gemini for parsing ==========
USE_GEMINI = False
try:
    import google.generativeai as genai
    if os.getenv("GEMINI_API_KEY"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        _gem_model = genai.GenerativeModel("gemini-2.5-flash-lite")
        USE_GEMINI = True
except Exception:
    USE_GEMINI = False

# ========== Gate templates (now file names include {cap_tag}) ==========
TEMPLATES = {
    "inverter": """
* CMOS inverter (PTM 45nm)
Vdd vdd 0 dc {vdd}
Vin in  0 pulse(0 {vdd} 1n 20p 20p 1n 2n)

* D G S B
Mn out in  0   0   nmos W=1u L=45n
Mp out in  vdd vdd pmos W=2u L=45n

{load_cap}

{model_include}
.temp {temperature}

.control
  let v50 = {vdd}/2
  set filetype=ascii

  tran 1p 6n
  run

  * measurements (first edges ~1.0 ns)
  meas tran tPLH trig v(in)  val=v50 fall=1 targ v(out) val=v50 rise=1 TD=0.9n
  meas tran tPHL trig v(in)  val=v50 rise=1 targ v(out) val=v50 fall=1 TD=0.9n

  * also expose picosecond versions inside ngspice
  let tPLH_ps = tPLH*1e12
  let tPHL_ps = tPHL*1e12
  print tPLH_ps
  print tPHL_ps
  set appendwrite
  wrdata meas_ps_{temperature}C_{cap_tag}.dat tPLH_ps tPHL_ps

  * ASCII dump for Python plotting (includes time as first column)
  wrdata sim_{temperature}C_{cap_tag}.dat time v(in) v(out)

  {plot_cmd}
.endc

.end
""",

    "nand2": """
* CMOS 2-input NAND (PTM 45nm) — pulse in1, hold in2 = VDD for robust .meas
Vdd  vdd 0 dc {vdd}
Vin1 in1 0 pulse(0 {vdd} 1n 10p 10p 200p 2000p)
Vin2 in2 0 {vdd}

* D  G   S  B
Mn1 out in1 n1  0   nmos W=1u L=45n
Mn2 n1  in2 0   0   nmos W=1u L=45n
Mp1 out in1 vdd vdd pmos W=2u L=45n
Mp2 out in2 vdd vdd pmos W=2u L=45n

{load_cap}

{model_include}
.temp {temperature}

.control
  let v50 = {vdd}/2
  set filetype=ascii

  tran 1p 6n
  run

  * in1 edges (~1.0 ns and ~1.2 ns)
  meas tran tPHL_in1 trig v(in1) val=v50 rise=1 targ v(out) val=v50 fall=1 TD=0.9n
  meas tran tPLH_in1 trig v(in1) val=v50 fall=1 targ v(out) val=v50 rise=1 TD=1.1n

  * picosecond views
  let tPHL_in1_ps = tPHL_in1*1e12
  let tPLH_in1_ps = tPLH_in1*1e12
  print tPHL_in1_ps
  print tPLH_in1_ps
  set appendwrite
  wrdata meas_ps_{temperature}C_{cap_tag}.dat tPHL_in1_ps tPLH_in1_ps

  wrdata sim_{temperature}C_{cap_tag}.dat time v(in1) v(in2) v(out)

  {plot_cmd}
.endc

.end
""",

    "nor2": """
* CMOS 2-input NOR (PTM 45nm) — pulse in1, hold in2 = 0 for robust .meas
Vdd  vdd 0 dc {vdd}
Vin1 in1 0 pulse(0 {vdd} 1n 10p 10p 200p 2000p)
Vin2 in2 0 0

* D  G   S  B
Mn1 out in1 0   0   nmos W=1u L=45n
Mn2 out in2 0   0   nmos W=1u L=45n
Mp1 out in1 vdd vdd pmos W=2u L=45n
Mp2 out in2 vdd vdd pmos W=2u L=45n

{load_cap}

{model_include}
.temp {temperature}

.control
  let v50 = {vdd}/2
  set filetype=ascii

  tran 1p 6n
  run

  * in1 edges (~1.0 ns and ~1.2 ns)
  meas tran tPLH_in1 trig v(in1) val=v50 fall=1 targ v(out) val=v50 rise=1 TD=0.9n
  meas tran tPHL_in1 trig v(in1) val=v50 rise=1 targ v(out) val=v50 fall=1 TD=1.1n

  let tPLH_in1_ps = tPLH_in1*1e12
  let tPHL_in1_ps = tPHL_in1*1e12
  print tPLH_in1_ps
  print tPHL_in1_ps
  set appendwrite
  wrdata meas_ps_{temperature}C_{cap_tag}.dat tPLH_in1_ps tPHL_in1_ps

  wrdata sim_{temperature}C_{cap_tag}.dat time v(in1) v(in2) v(out)

  {plot_cmd}
.endc

.end
"""
}

# ---------- Parse “load sweep” from free text ----------
def parse_load_sweep(prompt: str):
    """
    Supports:
      - 'loads 5,10,20,50 fF'
      - 'load 5-50 fF step 5 fF'
      - 'load sweep 5fF to 50fF step 5fF'
      - 'sweepC 5fF:50fF:5fF'
    Returns list like ['5fF','10fF',...], or None.
    """
    s = " ".join(prompt.lower().split())

    # sweepC 5fF:50fF:5fF
    m = re.search(r"sweepc\s+([0-9\.]+)\s*([a-zA-Z]+)\s*:\s*([0-9\.]+)\s*([a-zA-Z]+)\s*:\s*([0-9\.]+)\s*([a-zA-Z]+)", s)
    if m:
        v1,u1,v2,u2,st,us = m.groups()
        u1 = UNIT_CANON.get(u1,u1); u2 = UNIT_CANON.get(u2,u2); us = UNIT_CANON.get(us,us)
        if u1==u2==us:
            start = float(v1); stop = float(v2); step = float(st)
            vals = []
            x = start
            # Include both ends safely
            while (step>0 and x<=stop+1e-18) or (step<0 and x>=stop-1e-18):
                vals.append(format_cap_for_netlist(f"{x:g}{u1}"))
                x += step
            return vals

    # load 5-50 fF step 5 fF   or   load sweep 5fF to 50fF step 5fF
    m = re.search(r"load(?:\s+sweep)?\s+([0-9\.]+)\s*([a-zA-Z]+)?\s*(?:-|to)\s*([0-9\.]+)\s*([a-zA-Z]+)?(?:\s*step\s*([0-9\.]+)\s*([a-zA-Z]+)?)?", s)
    if m:
        v1,u1,v2,u2,st,us = m.groups()
        # If one unit missing, borrow the other
        u = (u1 or u2 or "fF")
        u = UNIT_CANON.get(u,u)
        start = float(v1); stop = float(v2)
        step = float(st) if st else (stop - start)  # default single hop if no step
        vals = []
        x = start
        while (step>0 and x<=stop+1e-18) or (step<0 and x>=stop-1e-18):
            vals.append(format_cap_for_netlist(f"{x:g}{u}"))
            x += step
        return vals

    # loads 5,10,20,50 fF
    m = re.search(r"loads?\s+([0-9\.,\s]+)\s*([a-zA-Z]+)", s)
    if m:
        nums = [n.strip() for n in m.group(1).split(",") if n.strip()]
        unit = UNIT_CANON.get(m.group(2), m.group(2))
        return [format_cap_for_netlist(f"{n}{unit}") for n in nums]

    return None

# ---------- Basic rules parsing ----------
def parse_with_rules(prompt: str) -> dict:
    out = {"gate":"inverter","vdd":0.8,"temperature":25,"load":"10 fF","sweep":None}
    if re.search(r"\bnand2?\b", prompt, re.I): out["gate"]="nand2"
    elif re.search(r"\bnor2?\b", prompt, re.I): out["gate"]="nor2"
    else: out["gate"]="inverter"
    m = re.search(r"vdd\s*[:=]?\s*([0-9\.]+)\s*v?", prompt, re.I)
    if m: out["vdd"]=float(m.group(1))
    m = re.search(r"temps?\s*[:=]?\s*([\-0-9,\s]+)\s*°?\s*c", prompt, re.I)
    if m:
        vals = [int(x) for x in re.split(r"\s*,\s*", m.group(1).strip()) if x]
        out["sweep"]=vals; out["temperature"]=vals[0]
    else:
        m2 = re.search(r"([\-]?\d+)\s*°?\s*c", prompt, re.I)
        if m2: out["temperature"]=int(m2.group(1))
    m = re.search(r"load\s*[:=]?\s*([0-9a-zA-Z\.\s]+(?:ff|pf|nf|uf|mf|f)?)", prompt, re.I)
    if m: out["load"]=m.group(1).strip()
    # NEW: try load sweep
    loads = parse_load_sweep(prompt)
    if loads:
        out["loads"] = loads
    return out

def parse_with_gemini(prompt: str) -> dict:
    if not USE_GEMINI:
        return parse_with_rules(prompt)
    try:
        resp = _gem_model.generate_content(
            "Extract JSON with keys: gate, vdd, temperature, load (string), loads (list of strings optional), sweep (list of temps).\n"
            "Only output JSON.\nUser: " + prompt
        )
        txt = re.sub(r"```json|```", "", resp.text.strip()).strip()
        data = json.loads(txt)
        if not data.get("loads"):
            # also parse manually for ranges if Gemini missed
            data["loads"] = parse_load_sweep(prompt)
        return data
    except Exception:
        return parse_with_rules(prompt)

# ---- utilities to format measurements in ps for Python output
ALLOW_KEYS = {"tplh","tphl","tplh_in1","tphl_in1","tplh_in2","tphl_in2"}
MEAS_STDOUT_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*?)\s*=\s*([\-+0-9.eE]+)\b')

def parse_meas(stdout_text: str):
    out = {}
    for line in stdout_text.splitlines():
        m = MEAS_STDOUT_RE.match(line)
        if m:
            k = m.group(1).lower()
            if k in ALLOW_KEYS:
                out[m.group(1)] = m.group(2)
    return out

def parse_meas_dat():
    out = {}
    if not os.path.exists("meas.dat"): return out
    with open("meas.dat","r") as f:
        for line in f:
            m = MEAS_STDOUT_RE.match(line)
            if m:
                k = m.group(1).lower()
                if k in ALLOW_KEYS:
                    out[m.group(1)] = m.group(2)
    return out

def meas_to_ps(meas_dict):
    try:
        return {k: float(v) * 1e12 for k, v in meas_dict.items()}
    except Exception:
        return {}

def pretty_ps(meas_ps):
    return {k: f"{val:.3f} ps" for k, val in meas_ps.items()}

def normalize_params(parsed: dict, prompt_text: str) -> dict:
    gate = (parsed.get("gate") or "inverter").lower()

    try:
        vdd = float(parsed.get("vdd")) if parsed.get("vdd") is not None else 0.8
    except Exception:
        vdd = 0.8

    # temperature (robust to dict/str/number)
    temperature = parsed.get("temperature")
    temperature = coerce_temp_to_int(temperature)

    if temperature is None:
        # try to scrape from prompt as last resort
        m = re.search(r'(?:temp(?:erature)?\s*[:=]?\s*)?(-?\d+)\s*°?\s*c', prompt_text, re.I)
        temperature = int(m.group(1)) if m else 27

    # sweep (robust to dict entries)
    temps = coerce_temp_list(parsed.get("sweep"), temperature)

    # Single load (fallback)
    load_raw = parsed.get("load")
    load_cap_line = "* no load capacitor" if not load_raw or str(load_raw).strip()=="" else f"Cl out 0 {format_cap_for_netlist(load_raw)}"

    # Load sweep list (strings already formatted like '5fF')
    loads_list = parsed.get("loads") or None
    if loads_list:
        loads_list = [format_cap_for_netlist(x) for x in loads_list]
    else:
        # if no sweep, still provide 1-element list for unified logic
        loads_list = [format_cap_for_netlist(load_raw) if load_raw else ""]

    return {
        "gate": gate,
        "vdd": vdd,
        "temperature": int(temperature),
        "sweep": [int(t) for t in temps],
        "load_cap": load_cap_line,
        "loads_list": loads_list
    }

# ========== Build & Run ==========
def build_netlist(gate: str, vdd: float, temp_c: int, load_cap_line: str, cap_tag: str, interactive: bool) -> str:
    if interactive:
        plot_vecs = "v(in) v(out)" if gate == "inverter" else "v(in1) v(out)"
        plot_cmd = f"plot {plot_vecs}"
    else:
        plot_cmd = ""
    return TEMPLATES[gate].format(
        vdd=vdd,
        temperature=temp_c,
        load_cap=load_cap_line,
        model_include=MODEL_INCLUDE,
        plot_cmd=plot_cmd,
        cap_tag=cap_tag
    )

def run_ngspice(netlist_text: str, filename: str, interactive: bool):
    with open(filename, "w") as f:
        f.write(netlist_text)

    if interactive:
        subprocess.Popen(["ngspice", filename])
        print("ngspice launched (interactive). Close the plot window to end the run.")
        return {}

    cp = subprocess.run(["ngspice", "-b", filename], capture_output=True, text=True)

    with open("ngspice_stdout.txt","a") as f: f.write(f"\n[{filename}]\n{cp.stdout}\n")
    with open("ngspice_stderr.txt","a") as f: f.write(f"\n[{filename}]\n{cp.stderr}\n")

    meas = parse_meas(cp.stdout)
    if not meas:
        meas = parse_meas_dat()
    return meas

# ---------- PNG from wrdata ----------
def plot_from_wrdata(dat_path: str, png_path: str, gate: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not os.path.exists(dat_path):
        return False

    with open(dat_path, "r") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    header_idx = None
    for i, ln in enumerate(lines[:20]):
        if "time" in ln.lower():
            header_idx = i
            break
    if header_idx is None:
        header_idx = 0

    header = re.split(r"\s+", lines[header_idx])
    cols = {name: idx for idx, name in enumerate(header)}

    in_name = "v(in)" if gate == "inverter" else "v(in1)"
    out_name = "v(out)"

    def find_col(name):
        for k, idx in cols.items():
            if k.lower() == name.lower():
                return idx
        return None

    ti = find_col("time")
    ii = find_col(in_name)
    oi = find_col(out_name)
    if ti is None or ii is None or oi is None:
        return False

    times, vin, vout = [], [], []
    for ln in lines[header_idx+1:]:
        parts = re.split(r"\s+", ln)
        try:
            times.append(float(parts[ti]))
            vin.append(float(parts[ii]))
            vout.append(float(parts[oi]))
        except Exception:
            continue

    if not times:
        return False

    plt.figure(figsize=(10, 5))
    plt.plot(times, vin, label=in_name)
    plt.plot(times, vout, label=out_name)
    plt.xlabel("Time (s)")
    plt.ylabel("Voltage (V)")
    plt.title(Path(png_path).stem)
    plt.legend()
    plt.tight_layout()
    plt.savefig(png_path, dpi=150)
    plt.close()
    return True

def to_jpg(png_path: str, jpg_path: str):
    try:
        from PIL import Image
        im = Image.open(png_path).convert("RGB")
        im.save(jpg_path, "JPEG", quality=92)
        return True
    except Exception:
        pass
    try:
        subprocess.run(["convert", png_path, jpg_path], check=True)
        return True
    except Exception:
        return False

# ==== NEW: helper to plot delay vs Cload for each temp/metric
def plot_delay_vs_cload(temp_to_metric_points, metric_name):
    """
    temp_to_metric_points: dict[tempC] -> list of (C_fF, delay_ps)
    Writes 'delay_vs_Cload_{metric}_{temp}C.png' files.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for tempC, points in temp_to_metric_points.items():
        pts = sorted([(c, d) for (c, d) in points if c is not None and d is not None], key=lambda x: x[0])
        if not pts:
            continue
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]

        plt.figure(figsize=(7,4))
        plt.plot(xs, ys, marker="o")
        plt.xlabel("C_load (fF)")
        plt.ylabel(f"{metric_name} (ps)")
        plt.title(f"{metric_name} vs C_load @ {tempC}°C")
        plt.tight_layout()
        fname = f"delay_vs_Cload_{metric_name}_{tempC}C.png"
        plt.savefig(fname, dpi=150)
        plt.close()

# ========== CLI ==========
def main():
    ap = argparse.ArgumentParser(description="ngspice AI agent (PTM45) with load-cap sweep")
    ap.add_argument("--mode", choices=["batch","interactive"], default="interactive",
                    help="Run mode: interactive opens ngspice GUI; batch extracts measurements.")
    ap.add_argument("--open-images", action="store_true",
                    help="After batch, open all generated images with the OS default viewer.")
    ap.add_argument("--jpg", action="store_true",
                    help="Export JPG in addition to (or instead of) PNG.")
    args = ap.parse_args()

    prompt = input("Enter your simulation request: ").strip()
    parsed = parse_with_gemini(prompt) if USE_GEMINI else parse_with_rules(prompt)
    params = normalize_params(parsed, prompt)

    # For interactive: just use first temp & first load
    if params.get("sweep"):
        params["temperature"] = int(params["sweep"][0])

    print(f"\nParsed params: {params}")

    gate = params["gate"]
    vdd  = params["vdd"]
    temps = params["sweep"]
    loads_list = params["loads_list"]  # list of strings like '5fF'
    single_load_line = params["load_cap"]  # legacy single-load line

    if args.mode == "interactive":
        temp_c = params["temperature"]
        load_text = loads_list[0] if loads_list and loads_list[0] else None
        load_line = f"Cl out 0 {load_text}" if load_text else single_load_line
        cap_tag = sanitize_cap_for_tag(load_text) if load_text else "noC"
        net = build_netlist(gate, vdd, temp_c, load_line, cap_tag, interactive=True)
        run_ngspice(net, f"agent_run_{temp_c}C_{cap_tag}.cir", interactive=True)
    else:
        # ==== NEW: we'll aggregate results to CSV and make plots
        csv_rows = []
        all_metric_names = set()
        # per-metric per-temp point collectors for plots
        metric_points_by_temp = {}  # dict[metric_name] -> dict[tempC] -> list[(C_fF, delay_ps)]

        image_files = []
        for t in temps:
            for load_text in (loads_list or [""]):
                load_line = f"Cl out 0 {load_text}" if load_text else single_load_line
                cap_tag = sanitize_cap_for_tag(load_text) if load_text else "noC"

                net = build_netlist(gate, vdd, int(t), load_line, cap_tag, interactive=False)
                deck_name = f"agent_run_{t}C_{cap_tag}.cir"
                print(f"\nRunning batch @ TEMP={t}C, Cload={load_text or 'n/a'} ...")
                meas = run_ngspice(net, deck_name, interactive=False)

                # (1) Pretty print
                if meas:
                    meas_ps = meas_to_ps(meas)  # dict like {"tPLH": ps, "tPHL": ps} or NAND2 keys
                    print("Measurements (ps):", pretty_ps(meas_ps))
                else:
                    meas_ps = {}
                    print("Measurements:", "(none)")

                # (2) Save wrdata -> PNG waveforms
                dat = f"sim_{t}C_{cap_tag}.dat"
                png = f"agent_run_{t}C_{cap_tag}.png"
                ok = plot_from_wrdata(dat, png, gate)
                if ok:
                    if args.jpg:
                        jpg = f"agent_run_{t}C_{cap_tag}.jpg"
                        if to_jpg(png, jpg):
                            image_files.append(jpg)
                        else:
                            image_files.append(png)
                    else:
                        image_files.append(png)

                # (3) Accumulate CSV row
                row = {
                    "gate": gate,
                    "vdd_V": vdd,
                    "temp_C": int(t),
                    "load": load_text or "",
                    "load_fF": cap_text_to_fF(load_text) if load_text else ""
                }
                # normalize measurement keys to lower for columns, but keep original names too
                for k, v in meas_ps.items():
                    # k might be 'tPLH', 'tPHL', 'tPLH_in1', ...
                    row[k] = float(v) if v is not None else ""
                    all_metric_names.add(k)
                csv_rows.append(row)

                # (4) Fill points for plotting delay vs Cload per temp/metric
                c_val = cap_text_to_fF(load_text) if load_text else None
                for k, v in meas_ps.items():
                    metric_points_by_temp.setdefault(k, {}).setdefault(int(t), []).append((c_val, float(v)))

        # ---- write CSV at end
        # Determine consistent header
        base_cols = ["gate", "vdd_V", "temp_C", "load", "load_fF"]
        metric_cols = sorted(all_metric_names)  # stable order
        header = base_cols + metric_cols
        out_csv = "meas_sweep.csv"
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in csv_rows:
                # ensure missing metric keys exist with blank
                for m in metric_cols:
                    if m not in r:
                        r[m] = ""
                w.writerow(r)
        print(f"\nSaved CSV: {out_csv}")

        # ---- make quick plots of delay vs Cload by metric & temp
        for metric_name, temp_map in metric_points_by_temp.items():
            plot_delay_vs_cload(temp_map, metric_name)
        print("Generated delay-vs-Cload plots for any metrics found.")

        if args.open_images and image_files:
            for img in image_files:
                try:
                    if os.name == "nt":
                        os.startfile(img)  # type: ignore
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", img])
                    else:
                        subprocess.Popen(["xdg-open", img])
                except Exception:
                    pass
            print("Opened all waveform images.")

if __name__ == "__main__":
    main()


if args.mode == "interactive":
    temp_c = params["temperature"]
    load_text = loads_list[0] if loads_list and loads_list[0] else None
    load_line = f"Cl out 0 {load_text}" if load_text else single_load_line
    cap_tag = sanitize_cap_for_tag(load_text) if load_text else "noC"
    net = build_netlist(gate, vdd, temp_c, load_line, cap_tag, interactive=True)
    run_ngspice(net, f"agent_run_{temp_c}C_{cap_tag}.cir", interactive=True)

    # NEW: also run the full sweep headlessly to produce CSV & plots
    sweep_and_export(gate, vdd, temps, loads_list, single_load_line, args.jpg)
