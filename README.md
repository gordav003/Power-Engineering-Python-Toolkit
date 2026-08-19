# Power Engineering Python Toolkit

A collection of practical Python tools for **electrical power engineering**, developed for study, research, and engineering analysis.

The repository currently focuses on:

- LC and LCL filter design for grid-connected converters
- DIgSILENT PowerFactory to pandapower model conversion
- Newton-Raphson Jacobian extraction from pandapower
- Voltage sensitivity calculation using the inverse Jacobian

## Repository Contents

| Script | Description |
|---|---|
| [`LC_filter_Calc.py`](LC_filter_Calc.py) | Designs a three-phase LC output filter from converter rating, voltage, switching frequency, desired resonance frequency, and allowed voltage drop. Calculates the inductor, capacitor, damping resistor, estimated losses, and resonance-frequency checks. |
| [`LCL_filter_Calc.py`](LCL_filter_Calc.py) | Designs a three-phase LCL filter for a grid-connected voltage-source converter. Calculates converter-side and grid-side inductors, filter capacitance, resonance frequency, damping resistor, losses, and basic design checks. |
| [`PF_to_Pandapower_JSON.py`](PF_to_Pandapower_JSON.py) | Connects to DIgSILENT PowerFactory, runs a load flow, converts the active PowerFactory project to a pandapower network, and exports the converted model. Includes a workaround for `ext_grid` reactive-power capability handling in the pandapower PowerFactory converter. |
| [`Export_Jacobian.py`](Export_Jacobian.py) | Loads a pandapower network, runs Newton-Raphson power flow, extracts and maps the Jacobian matrix, calculates its inverse, derives voltage sensitivities `dV/dP` and `dV/dQ`, and exports matrices and mapping files. |

## Requirements

Core packages:

```bash
pip install numpy pandas scipy pandapower
```

For `PF_to_Pandapower_JSON.py`, you additionally need:

- a working **DIgSILENT PowerFactory** installation
- the PowerFactory Python module compatible with your installation
- correct paths to the PowerFactory installation and Python module
- an accessible PowerFactory project and active study case

## Installation

Clone the repository:

```bash
git clone https://github.com/gordav003/Power-Engineering-Python-Toolkit.git
cd Power-Engineering-Python-Toolkit
```

Install the Python dependencies:

```bash
pip install numpy pandas scipy pandapower
```

## Usage

### LC filter design

Run:

```bash
python LC_filter_Calc.py
```

The example at the bottom of the script defines:

- rated apparent power
- line-to-line voltage
- switching frequency
- desired resonance frequency
- grid frequency
- allowed inductor voltage drop
- inductor resistance estimate
- damping resistor factor

The main function is:

```python
design_lc_filter(
    S_n_va,
    U_ll_v,
    f_sw_hz,
    f_res_hz,
    f_grid_hz=50,
    voltage_drop_pu=0.10,
    inductor_resistance_percent=1.0,
    damping_resistor_factor=1/3,
)
```

It returns a `pandas.DataFrame` containing the calculated filter parameters and design checks.

### LCL filter design

Run:

```bash
python LCL_filter_Calc.py
```

The main function is:

```python
design_lcl_filter(
    S_n_va,
    U_ll_v,
    f_sw_hz,
    f_grid_hz=50,
    voltage_drop_pu=0.10,
    L1_ratio=0.7,
    capacitor_reactive_power_pu=0.05,
    inductor_resistance_percent=1.0,
    damping_resistor_factor=1/3,
)
```

The design procedure:

1. Calculates the rated converter current.
2. Determines total filter inductance from the allowed voltage drop.
3. Splits the inductance into converter-side `L1` and grid-side `L2` components.
4. Calculates the filter capacitance from the allowed capacitor reactive power.
5. Calculates the LCL resonance frequency.
6. Estimates inductor resistances and copper losses.
7. Calculates a series damping resistor for the capacitor branch.
8. Checks whether the resonance frequency lies between approximately `10 * f_grid` and `0.5 * f_sw`.

### PowerFactory to pandapower conversion

Before running [`PF_to_Pandapower_JSON.py`](PF_to_Pandapower_JSON.py), configure the paths at the top of the script:

```python
PF_DIR = r"..."
PF_PYTHON = r"..."
```

Also set the required PowerFactory project and output path:

```python
project_name = "..."
```

and:

```python
path_dst = r"..."
```

Then run:

```bash
python PF_to_Pandapower_JSON.py
```

The script:

1. loads the PowerFactory Python API
2. connects to PowerFactory
3. activates the selected project
4. executes the active-study-case load flow
5. converts the PowerFactory model using pandapower's PowerFactory converter
6. prints a summary of the converted network

> **Note:** PowerFactory Python integration depends on the PowerFactory version and its bundled/supported Python environment. Make sure the configured Python interpreter and PowerFactory module are compatible.

### Jacobian and voltage sensitivity export

Before running [`Export_Jacobian.py`](Export_Jacobian.py), configure:

```python
json_path = r"..."
output_dir = r"..."
```

Then run:

```bash
python Export_Jacobian.py
```

The script performs a Newton-Raphson power flow in pandapower and extracts the internal Jacobian:

```text
        | dP/dVa   dP/dVm |
J   =   |                 |
        | dQ/dVa   dQ/dVm |
```

It identifies REF, PV, and PQ buses and creates row/column mappings between the internal PYPOWER/pandapower indices and the original pandapower buses.

The inverse Jacobian is then used to calculate voltage sensitivities:

- `dV/dP` in **kV/MW**
- `dV/dQ` in **kV/MVAr**

#### Generated files

The configured output directory receives:

```text
Jacobian.npz
Jacobian_column_mapping.csv
Jacobian_row_mapping.csv
Jacobian_bus_sets.npz
Voltage_sensitivities.npz
dV_dP_row_mapping.csv
dV_dP_column_mapping.csv
dV_dQ_row_mapping.csv
dV_dQ_column_mapping.csv
```

`Jacobian.npz` stores the sparse Newton-Raphson Jacobian, while `Voltage_sensitivities.npz` stores the calculated voltage-sensitivity matrices and base quantities.

## Engineering Notes

The filter-design scripts are intended as **engineering calculation and initial-design tools**. Component values, resonance limits, damping, thermal loading, harmonic performance, converter control interactions, grid impedance variation, and component tolerances should be verified before applying the results to real hardware.

The Jacobian and sensitivity calculations depend on pandapower's internal power-flow representation. When upgrading pandapower, verify that the internal structures used by the script remain compatible.

## Project Structure

```text
Power-Engineering-Python-Toolkit/
├── Export_Jacobian.py
├── LCL_filter_Calc.py
├── LC_filter_Calc.py
├── PF_to_Pandapower_JSON.py
└── README.md
```

## Contributing

Suggestions, corrections, and additional power-engineering utilities are welcome through issues or pull requests.

---

**Power Engineering Python Toolkit** is intended to grow as a practical collection of reusable tools for power-system analysis, converter engineering, and research workflows.
