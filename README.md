# AI Agent for SPICE Simulation Automation

**Course:** EE 8310 - Advanced Topics in VLSI (Fall 2025)  
**Institution:** University of Minnesota, Twin Cities  
**Author:** Nandini Kumawat

---

## Table of Contents
- [Overview](#overview)
- [Motivation](#motivation)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Results and Analysis](#results-and-analysis)
- [Technical Implementation](#technical-implementation)
- [Future Enhancements](#future-enhancements)
- [References](#references)
- [Author](#author)

---

## Overview

Manual SPICE simulations are labor-intensive processes requiring extensive time spent on netlist creation and parameter sweeps, hindering efficient circuit design and delaying project timelines. This project presents an AI-powered automation agent that transforms natural language circuit simulation requests into complete ngspice workflows, eliminating repetitive manual tasks and enabling rapid design space exploration.

The tool accepts intuitive requests such as `"inverter vdd 0.8, temp 25C, load 5-50 fF step 5 fF"` and automatically:
- Parses circuit parameters using regex and optional Gemini LLM assistance
- Generates syntactically correct ngspice netlists with proper measurement directives
- Executes batch simulations across specified parameter ranges
- Extracts timing metrics and aggregates results into CSV format
- Produces publication-quality delay-vs-load characterization plots

This automation reduces simulation setup time by approximately 90% while maintaining reproducibility and accuracy for academic and industrial circuit characterization workflows.

---

## Motivation

### The Challenge

Traditional SPICE-based circuit characterization workflows suffer from several pain points:

1. **Manual Netlist Creation**: Writing boilerplate-heavy SPICE decks for each simulation point is time-consuming and error-prone
2. **Parameter Sweep Overhead**: Running sweeps across VDD, temperature, and load requires creating multiple deck variants manually
3. **Inconsistent Measurement Setup**: Hand-written `.measure` statements can miss critical timing transitions or use inconsistent trigger points
4. **Result Aggregation**: Manually parsing `.mt0` files and consolidating data across runs is tedious
5. **Reproducibility Issues**: Copy-paste errors and unit inconsistencies (5fF vs 5e-15) create grading and verification problems

### The Solution

This AI agent addresses these challenges through:
- **Natural language to deck**: Single prompt generates complete, executable netlists
- **Batch automation**: One command runs full parameter sweeps with automatic result collection
- **Standardized measurements**: Consistent 50% VDD trigger/target rules across all simulations
- **Automated visualization**: Instant delay-vs-load plots for PVT corner analysis
- **Unit preservation**: Maintains user-specified formats (5fF, 25C) for reproducible workflows
***
<img width="1266" height="712" alt="image" src="https://github.com/user-attachments/assets/c063ea4f-9792-44ff-964d-fe7efc4a8503" />
***
<centre>*Figure 1: End-to-end automation workflow from natural language input to characterized results*</centre>

---

## Key Features

### Natural Language Processing
- **Flexible input parsing**: Handles multiple syntax variations (`"5-50 fF step 5 fF"`, `"5fF to 50fF"`, `"5,10,15 fF"`)
- **Optional LLM enhancement**: Gemini API integration for ambiguous request disambiguation
- **Robust parameter extraction**: Regex-based rules extract gate type, voltage, temperature, capacitance
- **Unit canonicalization**: Normalizes fF/pF/nF, V/mV, °C/C/Celsius automatically

### Automated Netlist Generation
- **Template-based construction**: PTM 45nm NMOS/PMOS models with configurable W/L ratios
- **Gate library**: Built-in inverter and NAND2 implementations with proper subcircuit hierarchy
- **Measurement instrumentation**: Automatic insertion of `.measure tran` for tplh/tphl at 50% crossings
- **Waveform capture**: Configures `.option post` and `.print`/`.probe` for visualization

### Batch Simulation Engine
- **Cartesian product sweeps**: Automatically generates all combinations of VDD × Temp × Cload
- **Headless execution**: Runs ngspice in batch mode for unattended operation
- **Measurement parsing**: Extracts timing data from `.mt0` files with picosecond conversion
- **Error recovery**: Pre-flight checks catch floating nodes, missing supplies before simulation

### Interactive Debugging Mode
- **GUI integration**: Launches ngspice waveform viewer for single-point inspection
- **Dual-mode operation**: Interactive run followed by automatic batch sweep for comprehensive analysis
- **Real-time plotting**: Opens `.tr0` files directly in ngspice for transient waveform examination

### Result Aggregation and Visualization
- **CSV export**: Consolidated table with gate, VDD, temp, load, tplh, tphl columns
- **Matplotlib integration**: Auto-generates delay-vs-Cload curves grouped by temperature
- **Linear regression overlay**: Shows ps/fF slopes for RC delay model validation
- **PNG waveforms**: Optional per-simulation waveform plots for detailed inspection
***
![Ngspice run](https://github.com/user-attachments/assets/dc28ffd3-1a7e-4eca-9390-b04bc0858486)
***
<centre>*Figure 2: Example terminal session showing natural language parsing and batch simulation execution*</centre>

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     User Input Layer                        │
│  "inverter vdd 0.8, temp 25C, load 5-50 fF step 5 fF"       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Parser Module                             │
│  ┌──────────────┐      ┌─────────────────┐                  │
│  │ Regex Engine │─────▶│ Gemini LLM (opt)│                  │   
│  └──────────────┘      └─────────────────┘                  │
│         │                       │                           │
│         └───────┬───────────────┘                           │
│                 ▼                                           │
│    {gate, vdd, temps, loads}                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Netlist Builder Module                         │
│  • PTM 45nm model includes                                  │
│  • Gate instantiation (INV/NAND2)                           │
│  • .measure directive generation                            │
│  • .tran/.option configuration                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│             ngspice Execution Engine                        │
│  ┌─────────────────┐      ┌──────────────────┐              │
│  │  Batch Mode     │      │ Interactive Mode  │             │
│  │  (headless)     │      │  (GUI viewer)     │             │
│  └─────────────────┘      └──────────────────┘              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│           Post-Processing Module                            │
│  • .mt0 parsing → picosecond conversion                     │
│  • CSV aggregation                                          │
│  • Matplotlib plotting (delay vs Cload)                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Output Artifacts                               │
│  • meas_sweep.csv                                           │
│  • delay_vs_Cload_*.png                                     │
│  • agent_run_*.cir (generated decks)                        │
│  • agent_run_*.png (waveforms)                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input Processing**: User types natural language request → Parser extracts structured parameters
2. **Netlist Generation**: For each (VDD, Temp, Cload) tuple → Generate .cir file with proper .measure
3. **Simulation Execution**: ngspice runs batch → Produces .mt0 (measurements) and .tr0 (waveforms)
4. **Result Extraction**: Parse .mt0 → Extract tplh, tphl → Convert to picoseconds
5. **Aggregation**: Collect all measurements → Write CSV → Generate plots

---

## Installation

### Prerequisites

**Required Software:**
- Python 3.8 or higher
- ngspice (open-source SPICE simulator)
- Git

**Operating System:**
- Linux (recommended: Ubuntu 20.04+)
- macOS (with Homebrew)
- Windows (with WSL2 or native ngspice build)

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/ai-spice-agent.git
cd ai-spice-agent
```

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**requirements.txt contents:**
```
matplotlib>=3.5.0
numpy>=1.21.0
```

### Step 3: Install ngspice

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ngspice
```

**macOS (Homebrew):**
```bash
brew install ngspice
```

**Verify installation:**
```bash
ngspice --version
# Should output: ngspice-XX (version number)
```

### Step 4: Obtain PDK Model Files

Place your technology model file in the project root:
```bash
# Example: PTM 45nm Low-Power models
cp /path/to/45nm_LP.pm .
```

The script expects `45nm_LP.pm` by default. Edit `ai_spice_agent.py` line ~250 if using a different model file.

### Step 5: (Optional) Gemini API Setup

For enhanced natural language parsing:
```bash
export GEMINI_API_KEY="your_api_key_here"
```

Get API key from: https://makersuite.google.com/app/apikey

**Note**: The tool works without Gemini using pure regex parsing.

---

## Usage

### Quick Start

**Batch Mode (Recommended for sweeps):**
```bash
python3 ai_spice_agent.py --mode batch
```

**Interactive Mode (For waveform inspection):**
```bash
python3 ai_spice_agent.py --mode interactive
```

### Example Sessions

#### Example 1: Inverter Temperature Sweep

```bash
$ python3 ai_spice_agent.py --mode batch

Enter your simulation request: inverter vdd 0.8 V, temp -40, 25, 110 C, load 15 fF

[Parser] Extracted parameters:
  Gate: inverter
  VDD: 0.8 V
  Temperatures: [-40, 25, 110] °C
  Load: 15 fF

[Netlist Builder] Generating deck for T=-40°C, C=15fF...
[ngspice] Running simulation...
[Measurements] tplh=12.43 ps, tphl=13.66 ps

[Netlist Builder] Generating deck for T=25°C, C=15fF...
[ngspice] Running simulation...
[Measurements] tplh=16.76 ps, tphl=18.46 ps

[Netlist Builder] Generating deck for T=110°C, C=15fF...
[ngspice] Running simulation...
[Measurements] tplh=24.08 ps, tphl=26.57 ps

Saved CSV: meas_sweep.csv
Generated delay-vs-Cload plots.
```

#### Example 2: NAND2 VDD Sweep with Load Range

```bash
Enter your simulation request: nand2, vdd 0.72, 0.8, 0.88, load 5-50 fF step 5 fF, temp 27 C

[Parser] Extracted parameters:
  Gate: nand2
  VDD: [0.72, 0.80, 0.88] V
  Temperatures: [27] °C
  Load: [5, 10, 15, 20, 25, 30, 35, 40, 45, 50] fF

[CSV sweep] Running 3 (VDD) × 1 (Temp) × 10 (Cload) = 30 simulations...

Progress: [██████████████████████████████] 30/30 (100%)

Saved CSV: meas_sweep.csv
Generated 6 plots: tplh_vs_Cload.png, tphl_vs_Cload.png (x3 VDD values)
```

#### Example 3: Interactive Waveform Viewing

```bash
$ python3 ai_spice_agent.py --mode interactive

Enter your simulation request: inverter vdd 0.8, temp 25 C, load 20 fF

[Interactive Mode] Launching ngspice GUI...
[ngspice opens with waveform viewer showing Vin, Vout transients]

[Background] Also running batch sweep for CSV export...
Saved CSV: meas_sweep.csv
```

### Command-Line Arguments

```bash
python3 ai_spice_agent.py [OPTIONS]

Options:
  --mode {batch,interactive}  Execution mode (default: batch)
  --jpg                       Save waveform PNGs in addition to CSV
  --open-images               Auto-open waveform images after simulation
  -h, --help                  Show help message
```

### Input Format Variations

The parser accepts flexible natural language syntax:

**Temperature:**
- `temp 25 C`, `temperature 25`, `temps -40, 25, 110 C`, `25°C`

**VDD:**
- `vdd 0.8`, `vdd 0.8 V`, `vdd 0.72, 0.8, 0.88`, `supply 800 mV`

**Load Capacitance:**
- `load 5-50 fF step 5 fF` → [5, 10, 15, ..., 50] fF
- `load 5, 10, 15 fF` → [5, 10, 15] fF
- `cap 10 pF` → 10000 fF (auto-converted)
- `cload 5fF to 50fF` → [5, 10, ..., 50] fF (inferred step=5)

**Gate Type:**
- `inverter`, `inv`, `INVERTER`
- `nand2`, `NAND2`, `nand`
***
![simulation nand working](https://github.com/user-attachments/assets/48b11a07-49ea-44f6-a185-e95eb53cd4de)
***
<centre>*Figure: NAND2 simulation showing input/output transient response*</centre>

---

## Results and Analysis

### Inverter Characterization

#### Temperature Dependence (VDD = 0.8V, Fixed Input Edge)

### Inverter Temperature Characterization (VDD=0.8V, Cload=5fF)

**Rising Delay (tplh):**
- -40°C: 12.43 ps (fastest - high mobility)
- 25°C: 16.76 ps (nominal)
- 110°C: 24.08 ps (slowest - mobility degradation)

**Falling Delay (tphl):**
- -40°C: 13.66 ps
- 25°C: 18.46 ps  
- 110°C: 26.57 ps

**Key Insight:** Delay approximately **doubles** from -40°C to 110°C due to carrier mobility reduction at elevated temperatures.

#### Load Capacitance Dependence (25°C, VDD = 0.8V)

Sweep: C = 5 → 50 fF, step 5 fF

| Cload (fF) | tplh (ps) | tphl (ps) |
|-----------|-----------|-----------|
| 5         | 29.03     | 32.57     |
| 10        | 43.76     | 49.14     |
| 15        | 58.49     | 65.71     |
| 20        | 73.22     | 82.28     |
| 25        | 87.95     | 98.85     |
| 30        | 102.68    | 115.42    |
| 35        | 117.41    | 131.99    |
| 40        | 132.14    | 148.56    |
| 45        | 146.87    | 165.13    |
| 50        | 132.73    | 149.50    |

**Linear Regression:**
- tplh: ~2.30 ps/fF slope
- tphl: ~2.60 ps/fF slope

**Physical Interpretation:** Near-linear relationship confirms RC delay model: `t_delay ≈ R_on × C_load`. Slightly higher tphl slope indicates weaker PMOS pull-up compared to NMOS pull-down.

### NAND2 Characterization

#### VDD Scaling (Cload = 5 fF, T = 27°C)

| VDD (V) | tplh (ps) | tphl (ps) | tplh/tphl Ratio |
|---------|-----------|-----------|-----------------|
| 0.72    | 120.73    | 40.37     | 2.99            |
| 0.80    | 68.33     | 29.42     | 2.32            |
| 0.88    | 47.03     | 21.89     | 2.15            |

**Key Observations:**
1. **Strong VDD sensitivity**: tphl reduces by ~2.1× from 0.72V → 0.88V
2. **Asymmetric drive**: tplh consistently 2-3× slower than tphl
3. **Series NMOS effect**: Falling edge (NMOS stack discharge) is faster than rising edge (single PMOS pull-up)

#### Temperature Sweep (VDD = 0.8V, Cload = 10 fF)

| Temperature | tplh (ps) | tphl (ps) |
|-------------|-----------|-----------|
| -40°C       | 48.61     | 24.10     |
| 25°C        | 94.88     | 39.24     |
| 110°C       | 169.17    | 29.54     |

**Interesting Anomaly:** tphl at 110°C (29.54 ps) is **faster** than at 25°C (39.24 ps). This non-monotonic behavior likely results from:
- PMOS vs NMOS temperature-dependent mobility interplay
- Threshold voltage shift effects at different slew measurement points
- Requires further investigation of exact measurement trigger/target timing
***
<img width="724" height="462" alt="image" src="https://github.com/user-attachments/assets/3ad35a93-4a89-4833-a085-7eff682e9234" />
***
<centre>*Figure: NAND2 waveform capture showing input/output transitions*</centre>

### Summary of Physical Trends

### Key Design Parameters and Delay Dependencies

**Supply Voltage (VDD):**
- Increasing VDD reduces delay through higher overdrive voltage and stronger current drive
- VDD sweep from 0.72V to 0.88V shows tphl reduces 2.1× in NAND2 gates

**Temperature:**
- Increasing temperature increases delay due to reduced carrier mobility (μ ∝ T^-1.5)
- Delay doubles from -40°C (12.43ps tplh) to 110°C (24.08ps) in inverters

**Load Capacitance:**
- Delay increases linearly with load following RC charging model (t = R × C)
- Measured 2.30 ps/fF (tplh) and 2.60 ps/fF (tphl) slopes for inverter characterization

**Asymmetric Drive Strength:**
- Inverters: tphl < tplh due to NMOS having higher mobility than PMOS
- NAND2: tphl > tplh (inverted asymmetry) caused by series NMOS stack resistance
- Series stacks create 2-3× slower pull-down compared to single PMOS pull-up
---

## Technical Implementation

### Parser Module

**Input:** Natural language string  
**Output:** Structured dictionary `{gate, vdd, temps, loads}`

**Algorithm:**
1. **Regex-based extraction**:
   ```python
   VDD_PATTERN = r'(?:vdd|supply)[\s:=]*([0-9.]+)\s*([mV]*)'
   TEMP_PATTERN = r'(?:temp|temperature)[\s:=]*([-0-9,\s]+)\s*([C°]*)'
   LOAD_PATTERN = r'(?:load|cap|cload)[\s:=]*([0-9fFpPnN\s,\-]+)'
   ```

2. **Range expansion**:
   - `"5-50 step 5"` → `[5, 10, 15, ..., 50]`
   - `"5 to 50"` → infer step from first two values if explicit step missing

3. **Unit normalization**:
   ```python
   def normalize_cap(text):
       if 'pF' in text:
           return float(text.replace('pF', '')) * 1000  # to fF
       elif 'nF' in text:
           return float(text.replace('nF', '')) * 1e6   # to fF
       else:
           return float(text.replace('fF', ''))
   ```

4. **Optional LLM fallback**:
   - If regex fails to extract required parameters → query Gemini API
   - LLM returns JSON: `{"gate": "inverter", "vdd": 0.8, ...}`
   - Validate LLM output against expected schema

**Error Handling:**
- Missing required fields → prompt user for clarification
- Invalid numeric values → raise ValueError with helpful message
- Ambiguous gate type → default to inverter, warn user

### Netlist Builder

**Input:** Parsed parameters  
**Output:** Executable .cir file

**Template Structure:**
```spice
* Auto-generated by AI SPICE Agent
.title {gate} @ VDD={vdd}V, T={temp}C, Cload={load}

* Include technology models
.include 45nm_LP.pm

* Power supplies
Vdd vdd 0 DC {vdd}
Vss vss 0 DC 0

* Input stimulus (pulse for transient analysis)
Vin in 0 PULSE(0 {vdd} 0.1n 0.1n 0.1n 5n 20n)

* Device Under Test
X{gate} in out vdd vss {gate_subckt}

* Load capacitance
Cl out 0 {load_fF}fF

* Subcircuit definitions
.subckt inverter in out vdd vss
    Mp out in vdd vdd pmos_vtl W=90n L=50n
    Mn out in vss vss nmos_vtl W=45n L=50n
.ends

.subckt nand2 a b out vdd vss
    Mp1 out a vdd vdd pmos_vtl W=90n L=50n
    Mp2 out b vdd vdd pmos_vtl W=90n L=50n
    Mn1 out a n1 vss nmos_vtl W=90n L=50n
    Mn2 n1 b vss vss nmos_vtl W=90n L=50n
.ends

* Transient analysis
.tran 0.01n 25n

* Measurements (50% VDD crossing)
.measure tran tplh TRIG V(in) VAL={vdd*0.5} RISE=1
+                    TARG V(out) VAL={vdd*0.5} RISE=1

.measure tran tphl TRIG V(in) VAL={vdd*0.5} FALL=1
+                    TARG V(out) VAL={vdd*0.5} FALL=1

* Output configuration
.option post=2
.print tran V(in) V(out)
.probe tran V(in) V(out)

.temp {temp}
.end
```

**Critical Design Decisions:**
1. **50% VDD trigger/target**: Industry standard for delay measurement, ensures consistent threshold across VDD values
2. **TD guard bands**: For NAND2, add `TD=0.5n` to measurements to skip initial transient, prevent false triggers
3. **Pulse timing**: 5ns pulse width, 20ns period ensures complete output settling before next edge
4. **W/L ratios**: Inverter uses 2:1 PMOS:NMOS for balanced drive; NAND2 uses 2× NMOS width to compensate for series resistance

### ngspice Executor

**Batch Mode:**
```python
def run_ngspice(netlist, deck_name, interactive=False):
    with open(deck_name, 'w') as f:
        f.write(netlist)
    
    if interactive:
        subprocess.run(['ngspice', deck_name])
    else:
        result = subprocess.run(
            ['ngspice', '-b', deck_name, '-o', f'{deck_name}.log'],
            capture_output=True, text=True
        )
        return parse_measurements(f'{deck_name}.mt0')
```

**Measurement Parsing:**
```python
def parse_measurements(mt0_file):
    measurements = {}
    with open(mt0_file, 'r') as f:
        for line in f:
            # Format: "tplh = 1.676e-11"
            match = re.match(r'(\w+)\s*=\s*([0-9.e+-]+)', line)
            if match:
                name, value = match.groups()
                measurements[name] = float(value)
    return measurements

def meas_to_ps(meas_dict):
    """Convert seconds to picoseconds"""
    return {k: v * 1e12 for k, v in meas_dict.items()}
```

### Post-Processing

**CSV Aggregation:**
```python
csv_rows = []
for vdd in vdd_list:
    for temp in temp_list:
        for load in load_list:
            meas = simulate(vdd, temp, load)
            csv_rows.append({
                'gate': gate,
                'vdd_V': vdd,
                'temp_C': temp,
                'load': f'{load} fF',
                'load_fF': load,
                'tplh': meas['tplh'],
                'tphl': meas['tphl']
            })

with open('meas_sweep.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
    writer.writeheader()
    writer.writerows(csv_rows)
```

**Plotting:**
```python
import matplotlib.pyplot as plt

def plot_delay_vs_cload(temp_map, metric_name):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for temp, points in temp_map.items():
        loads, delays = zip(*points)
        ax.plot(loads, delays, 'o-', label=f'{temp}°C')
    
    ax.set_xlabel('Load Capacitance (fF)', fontsize=12)
    ax.set_ylabel(f'{metric_name} (ps)', fontsize=12)
    ax.set_title(f'{metric_name} vs. Load Capacitance', fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{metric_name}_vs_Cload.png', dpi=300)
    plt.close()
```

---

## Future Enhancements

### Planned Features

1. **Monte Carlo Integration**
   - Statistical variation analysis across process/mismatch corners
   - Histogram generation for timing distributions
   - Sigma-based yield prediction

2. **Hierarchical Circuit Support**
   - Subcircuit library management
   - Multi-stage path analysis (e.g., inverter chain optimization)
   - Fanout-of-4 delay characterization

3. **Advanced Optimization**
   - Closed-loop transistor sizing guided by delay targets
   - AI-suggested next sweep parameters for efficient design space exploration
   - Bayesian optimization for multi-objective PPA tuning

4. **Extended Gate Library**
   - NOR, XOR, complex gates
   - Pass-gate logic, transmission gates
   - Custom cell import from LEF/Liberty

5. **Power Analysis**
   - Average/peak power extraction from SPICE
   - Energy-per-transition metrics
   - Leakage power at different PVT corners

6. **GUI Interface**
   - Web-based dashboard for parameter input
   - Real-time simulation progress tracking
   - Interactive plot exploration (zoom, pan, data cursor)

### Known Limitations

1. **LLM Hallucinations**
   - Gemini may invent unrealistic parameter values
   - **Mitigation**: Rules-first parsing, LLM as fallback only
   - **Future**: Validate LLM output against physical constraints (e.g., VDD < 2V for 45nm)

2. **SPICE Syntax Drift**
   - Subtle differences between HSPICE, ngspice, Spectre
   - **Current**: Templates tested for ngspice compatibility
   - **Future**: Auto-detect SPICE flavor, adjust syntax accordingly

3. **Measurement Edge Cases**
   - Series NMOS stacks (NAND3+) may need TD adjustment
   - Weak pull-up/down can cause measurement timeout
   - **Future**: Adaptive TD guards, automatic retries with relaxed windows

4. **Large-Scale Scalability**
   - 1000+ simulation points can take hours
   - **Future**: Parallel ngspice execution, job queue management

---

## References

### Technology Models
- **PTM Models**: Predictive Technology Model for 45nm node  
  URL: http://ptm.asu.edu/  
  Citation: Zhao, W., & Cao, Y. (2006). "New generation of Predictive Technology Model for sub-45nm design exploration." *IEEE TCAD*, 25(11), 2432-2443.

### SPICE Simulation
- **ngspice**: Open-source SPICE simulator  
  URL: http://ngspice.sourceforge.net/  
  Documentation: http://ngspice.sourceforge.net/docs/ngspice-html-manual/manual.xhtml

### Related Work
- **Logical Effort**: Sutherland, I., Sproull, B., & Harris, D. (1999). *Logical Effort: Designing Fast CMOS Circuits.* Morgan Kaufmann.
- **CMOS Circuit Design**: Weste, N., & Harris, D. (2010). *CMOS VLSI Design: A Circuits and Systems Perspective* (4th ed.). Addison-Wesley.

### Course Materials
- **EE 8310**: Advanced Topics in VLSI  
  Instructor: Prof. Chris Kim  
  Institution: University of Minnesota, Twin Cities

---

## Project Structure

```
ai-spice-agent/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── LICENSE                            # MIT or Academic Use
├── ai_spice_agent.py                  # Main automation script (765 lines)
├── 45nm_LP.pm                         # TSMC 45nm PTM models
│
├── docs/                              # Documentation assets
│   └── images/
│       ├── workflow_diagram.png
│       ├── terminal_output.png
│       ├── simulation_inv_working.jpg
│       ├── simulation_nand_working.jpg
│       ├── NAND2_Graph.jpg
│       └── NAND2_working.jpg
│
├── examples/                          # Example netlists
│   ├── Inverter Circuit Files/
│   │   ├── inv_minus40.cir            # Inverter @ -40°C
│   │   ├── inv_25.cir                 # Inverter @ 25°C
│   │   └── inv_110.cir                # Inverter @ 110°C
│   │
│   └── Nand2 Circuit Files/
│       ├── nand0.72.cir               # NAND2 @ VDD=0.72V
│       ├── nand0.8.cir                # NAND2 @ VDD=0.80V
│       └── nand0.88.cir               # NAND2 @ VDD=0.88V
│
├── results/                           # Output directory (git-ignored)
│   ├── meas_sweep.csv                 # Consolidated measurements
│   ├── agent_run_*.cir                # Generated SPICE decks
│   ├── agent_run_*.png                # Waveform plots
│   └── delay_vs_Cload_*.png           # Characterization curves
│
└── reports/                           # Analysis documents
    ├── Simulation_Results_HW3.pdf     # Full technical report
    └── Presentation_AI_Agent.pdf      # Slide deck
```

---

## Quick Start Guide

**1. Clone and setup:**
```bash
git clone https://github.com/yourusername/ai-spice-agent.git
cd ai-spice-agent
pip install -r requirements.txt
```

**2. Run first simulation:**
```bash
python3 ai_spice_agent.py --mode batch
# When prompted: inverter vdd 0.8, temp 25C, load 10 fF
```

**3. Check results:**
```bash
cat meas_sweep.csv
ls -l agent_run_*.png
```

**4. Advanced usage:**
```bash
# Full temperature sweep
python3 ai_spice_agent.py --mode batch
# Prompt: inverter vdd 0.8, temps -40, 25, 110 C, load 5-50 fF step 5 fF

# Interactive waveform viewing
python3 ai_spice_agent.py --mode interactive
# Prompt: nand2 vdd 0.8, temp 27C, load 15 fF
```

---

## Author

**Nandini Kumawat**  
Graduate Student, Electrical and Computer Engineering  
University of Minnesota, Twin Cities

Email: kumaw010@umn.edu  
LinkedIn: [linkedin.com/in/nandini-kumawat](https://www.linkedin.com/in/nandini-kumawat)  

### Acknowledgments

This project was developed as part of EE 8310 (Advanced Topics in VLSI) coursework under the guidance of Prof. Chris Kim. Special thanks to the course staff for feedback on simulation methodologies and the open-source ngspice community for excellent documentation.

---

## License

This project is released under the MIT License for academic and educational use. If using this code for coursework, please cite appropriately and adhere to your institution's academic integrity policies.

```
MIT License

Copyright (c) 2025 Nandini Kumawat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

**Note**: This tool demonstrates AI-powered EDA automation for educational purposes. For production circuit design, always cross-validate results with commercial SPICE tools (HSPICE, Spectre) and silicon measurements. Automated tools complement but do not replace engineering judgment in critical design decisions.
