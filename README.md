# AI Agent for SPICE Simulation Automation

**Course:** EE 8310 - Advanced Topics in VLSI (Fall 2025)  
**University of Minnesota**

An AI-powered automation agent that transforms natural language requests into complete ngspice simulation workflows, eliminating manual netlist creation and parameter sweep setup for transistor-level circuit characterization.

## Key Features

- **Natural Language Processing**: Parse circuit simulation requests like `"inverter vdd 0.8, temp 25C, load 5-50 fF step 5 fF"` into executable SPICE decks
- **Automated Netlist Generation**: Dynamically generate ngspice netlists with proper `.tran`, `.measure`, `.print/.probe`, and `.option` directives
- **Batch Simulation Mode**: Automated parameter sweeps across VDD/temperature/load ranges with CSV aggregation
- **Interactive Mode**: One-click waveform visualization through ngspice GUI
- **Reproducible Results**: Preserves user-specified units (e.g., "5fF" remains "5fF", not "5e-15") for grading consistency
- **Comprehensive Characterization**: Automatic delay-vs-load plots and propagation delay analysis across PVT corners

## Results

### Propagation Delay Characterization

**Inverter @ VDD = 0.8V (fixed input edge)**
- Temperature sweep results:
  - -40°C: tplh ≈ 12.43 ps, tphl ≈ 13.66 ps
  - 25°C: tplh ≈ 16.76 ps, tphl ≈ 18.46 ps
  - 110°C: tplh ≈ 24.08 ps, tphl ≈ 26.57 ps
  - **Trend**: Delay roughly doubles from -40°C → 110°C

- Load sweep (25°C, VDD 0.8V, C = 5→50 fF, step 5 fF):
  - tplh: 29.03 → 132.73 ps ⇒ ~2.30 ps/fF slope
  - tphl: 32.57 → 149.50 ps ⇒ ~2.60 ps/fF slope
  - **Trend**: Near-linear with Cload (RC charging/discharging)

**NAND2 Characterization**
- VDD sweep (Cload = 5 fF, T = 27°C):
  - 0.72V: tphl ≈ 120.73 ps, tplh ≈ 40.37 ps
  - 0.80V: tphl ≈ 68.33 ps, tplh ≈ 29.42 ps
  - 0.88V: tphl ≈ 47.03 ps, tplh ≈ 21.89 ps
  - **Trend**: Strong VDD sensitivity, tphl shows stronger effect (series NMOS discharge path)

### Key Insights
- **VDD ↑ → delay ↓** (strong effect)
- **Temp ↑ → delay ↑** (mobility ↓; Vth shifts)
- **Cload ↑ → delay ↑ ~ linearly** (RC charging/discharging)
- **Falling vs rising**: typically tphl > tplh (drive asymmetry); NAND2 shows stronger asymmetry due to series NMOS stack

## Getting Started

### Prerequisites

- **Python 3.8+**
- **ngspice** (open-source SPICE simulator)
- **Python packages**:
  ```bash
  pip install matplotlib numpy
  ```
- **Optional**: Gemini LLM API key for enhanced natural language parsing
  ```bash
  export GEMINI_API_KEY="your_api_key_here"
  ```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-spice-agent.git
   cd ai-spice-agent
   ```

2. Ensure ngspice is installed:
   ```bash
   ngspice --version
   ```

3. Place your PDK model file (e.g., `45nm_LP.pm`) in the project directory

### Usage

#### Batch Mode (Automated Sweeps)

```bash
python3 ai_spice_agent.py --mode batch
```

**Example prompts:**
```
Enter your simulation request: inverter vdd 0.8 V, temp 25 C, load 5-50 fF step 5 fF
Enter your simulation request: nand2, vdd 0.72, 0.8, 0.88 load 10 fF temp 27 C
Enter your simulation request: inverter temps -40, 25, 110C vdd 0.8 load 15 fF
```

**Output:**
- `meas_sweep.csv` - Consolidated measurement results
- `agent_run_*.png` - Waveform plots for each simulation point
- `delay_vs_Cload_*.png` - Delay vs. load capacitance plots by metric

#### Interactive Mode (Waveform Viewing)

```bash
python3 ai_spice_agent.py --mode interactive
```

Opens ngspice GUI for real-time waveform inspection.

## Project Structure

```
ai-spice-agent/
├── ai_spice_agent.py              # Main automation script
├── 45nm_LP.pm                     # TSMC 45nm PDK model file
├── Inverter Circuit Files/        # Example inverter netlists
│   ├── inv_minus40.cir
│   ├── inv_25.cir
│   └── inv_110.cir
├── Nand2 Circuit Files/          # Example NAND2 netlists
│   ├── nand0.72.cir
│   ├── nand0.8.cir
│   └── nand0.88.cir
├── Initial Runs using Sourcecode/ # Validation screenshots
│   ├── NAND2 Graph.jpg
│   ├── simulation inv working.jpg
│   └── Ngspice run.jpg
├── meas_sweep.csv                 # Output: measurement results
├── Simulation_Results_HW3.pdf     # Full analysis report
└── README.md
```

## How It Works

### 1. Parser Module
- **Regex extraction**: Identifies gate type, VDD, temperature, load capacitance from natural language
- **Optional Gemini LLM**: Enhances parsing for complex/ambiguous requests
- **Unit canonicalization**: Handles fF, pF, nF, V, mV, °C, C uniformly

### 2. Netlist Builder
- **PTM 45nm models**: Inserts `.include 45nm_LP.pm`
- **Gate instantiation**: Automatically generates inverter or NAND2 subcircuits
- **Measurement directives**: Adds `.measure` statements for tplh, tphl at 50% VDD crossings
- **Waveform output**: Configures `.option post` and `.print`/`.probe` for visualization

### 3. ngspice Executor
- **Batch mode**: Runs headless, parses `.mt0` measurement tables
- **Interactive mode**: Launches ngspice GUI with `.tr0` waveform files
- **Error handling**: Pre-flight checks for floating nodes, missing supplies

### 4. Post-Processing
- **CSV aggregation**: Collects all measurements into single table
- **Matplotlib plots**: Auto-generates delay-vs-Cload curves by temperature
- **Unit preservation**: Maintains original user units in output files

## Example Output

### Delay vs. Load Capacitance (Inverter @ 25°C)

```
Cload (fF)    tplh (ps)    tphl (ps)
5             29.03        32.57
10            43.76        49.14
15            58.49        65.71
...
50            132.73       149.50
```

**Linear fit:** ~2.3-2.6 ps/fF (consistent with RC delay model)

### CSV Output Format

```csv
gate,vdd_V,temp_C,load,load_fF,tplh,tphl
inverter,0.8,-40,5 fF,5.0,12.43,13.66
inverter,0.8,25,5 fF,5.0,16.76,18.46
inverter,0.8,110,5 fF,5.0,24.08,26.57
...
```

## Technical Insights

### Achieved Benefits
- **90% reduction** in manual SPICE simulation effort
- **Reproducible workflows** for grading and peer review
- **Scalable to Monte Carlo** and hierarchical circuit builds
- **Closed-loop potential** with AI-suggested next sweep parameters

### Implementation Highlights
- **Robust parsing**: Handles "5 fF step 5 fF to 50 fF", "5fF-50fF", "5-50 fF" variations
- **Temperature coercion**: Accepts 25, "25", "25C", {"temperature": "25C"} formats
- **Measurement guards**: 50% VDD trigger/target rules prevent missed transitions
- **TD margin handling**: Adds timing delay for NAND2 to ensure valid measurement windows

### Limitations & Future Work
- **LLM hallucinations**: Mitigated by rules-first parsing + optional LLM assist
- **Syntax drift**: Templates curated for HSPICE/ngspice compatibility
- **Parser brittleness**: Added range parsing and unit canonicalization for robustness
- **Debugging overhead**: AI doesn't replace EDA debugging skills (.lis, .mt0 inspection)
- **Result validation**: Engineers must sanity-check measurements (e.g., stacking cases)

## References

- **PTM Models**: [Predictive Technology Model](http://ptm.asu.edu/)
- **ngspice**: [ngspice.sourceforge.net](http://ngspice.sourceforge.net/)
- **Course**: EE 8310 Advanced Topics in VLSI, University of Minnesota

## Author

**Nandini Kumawat**  
Graduate Student, Electrical and Computer Engineering  
University of Minnesota, Twin Cities  
Email: kumaw010@umn.edu  
LinkedIn: [linkedin.com/in/nandini-kumawat](https://www.linkedin.com/in/nandini-kumawat)

## License

This project was developed as part of coursework for EE 8310. Please respect academic integrity guidelines if using for educational purposes.

---

**Note**: This tool demonstrates AI-powered EDA automation but requires engineering judgment for production use. Always validate simulation results against known circuit behavior and commercial tools.
