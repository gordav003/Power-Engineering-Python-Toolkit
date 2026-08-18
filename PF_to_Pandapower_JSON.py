PF_DIR = r"..."     # NASTAVI DIXI PATH
PF_PYTHON = r"..."  # NASTAVI DIXI PYTHON PATH
import sys
import os
import numpy as np

# PowerFactory DLL
os.environ["PATH"] = PF_DIR + os.pathsep + os.environ["PATH"]
# PowerFactory Python modul
sys.path.append(PF_PYTHON)

import powerfactory as pf
from pandapower.converter.powerfactory import from_pfd
import pandapower.converter.powerfactory.pp_import_functions as ppif
from pandapower.control.util.auxiliary import (
    get_min_max_q_mvar_from_characteristics_object
    as original_get_q_limits
)

# ------------------------------------------------------------
# Pandapower PowerFactory converter workaround - ZGENERIRANO
# ------------------------------------------------------------
# ext_grid nima vhodnega p_mw, zato preskočimo izračun
# Q capability curve za ext_grid.
# Za gen in sgen ostane originalna funkcionalnost.
def safe_get_q_limits(net, element, element_index):
    if element == "ext_grid":
        if "min_q_mvar" in net.ext_grid.columns:
            min_q_mvar = net.ext_grid.at[
                element_index, "min_q_mvar"
            ]
        else:
            min_q_mvar = np.nan
        if "max_q_mvar" in net.ext_grid.columns:
            max_q_mvar = net.ext_grid.at[
                element_index, "max_q_mvar"
            ]
        else:
            max_q_mvar = np.nan
        return min_q_mvar, max_q_mvar
    return original_get_q_limits(
        net,
        element,
        element_index
    )
# Zamenjamo samo funkcijo znotraj PF converterja
ppif.get_min_max_q_mvar_from_characteristics_object = safe_get_q_limits

# Izklopi INFO izpise PF v PP converterja
import logging
logging.getLogger(
    "pandapower.converter.powerfactory.pp_import_functions"
).setLevel(logging.ERROR)
logging.getLogger(
    "pandapower.converter.powerfactory.export_pfd_to_pp"
).setLevel(logging.ERROR)

# Povezava s PowerFactory
app = pf.GetApplication()
if app is None:
    raise RuntimeError("PowerFactory Application ni bilo mogoče inicializirati.")
app.Show()
print(app)
print("PowerFactory connection OK")

# Inicializacija projekta
project_name = "SLO_model_2025"
result = app.ActivateProject(project_name)
if result != 0:
    raise RuntimeError(f"Projekta '{project_name}' ni bilo mogoče aktivirati.")
project = app.GetActiveProject()
print("Active project:", project)

# Zagon PowerFactory Load Flow
ldf = app.GetFromStudyCase("ComLdf")
if ldf is None:
    raise RuntimeError("ComLdf ni bil najden v aktivnem Study Case-u.")
print("Zagon Load Flow:", ldf)
ldf_result = ldf.Execute()
print("Load flow result:", ldf_result)
if ldf_result != 0:
    raise RuntimeError(
        "PowerFactory load flow ni konvergiral. "
    )
print("PowerFactory load flow converged.")

# Pretvorba PowerFactory v PandaPower
print("Zagon pretvorbe PowerFactory v PandaPower...")
net = from_pfd(app, 
               prj_name=project_name, 
               path_dst=r"...",         # NASTAVI PATH ZA IZHOD
               flag_graphics="no geodata",
               export_controller=False)
print("Pretvorba končana")
print(f"Buses:       {len(net.bus)}")
print(f"Lines:       {len(net.line)}")
print(f"Trafos:      {len(net.trafo)}")
print(f"Trafos 3W:   {len(net.trafo3w)}")
print(f"Loads:       {len(net.load)}")
print(f"Generators:  {len(net.gen)}")
print(f"SGen:        {len(net.sgen)}")
print(f"Ext grids:   {len(net.ext_grid)}")
