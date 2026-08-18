import os
import pandapower as pp
import numpy as np
import pandas as pd
from pandapower.pypower.idx_bus import BUS_TYPE, REF, PV, PQ, BASE_KV
from scipy.sparse import save_npz

json_path = r"..."
output_dir = r"..."

# Incializacija PandaPower omrežja
print("Nalaganje pandapower modela... ")
net = pp.from_json(json_path)
print("Model naložen.")
print(f"Buses:       {len(net.bus)}")
print(f"Lines:       {len(net.line)}")
print(f"Trafos:      {len(net.trafo)}")
print(f"Trafos 3W:   {len(net.trafo3w)}")
print(f"Loads:       {len(net.load)}")
print(f"Generators:  {len(net.gen)}")
print(f"SGen:        {len(net.sgen)}")
print(f"Ext grids:   {len(net.ext_grid)}")

# Inicalizacija PandaPower Load Flow 
print("Zagon pandapower Load Flow...")
pp.runpp(net, 
        algorithm="nr", 
        numba=False)

# Zbiralke
bus_internal = net._ppc["internal"]["bus"]
n_ref = (bus_internal[:, BUS_TYPE] == REF).sum()
n_pv = (bus_internal[:, BUS_TYPE] == PV).sum()
n_pq = (bus_internal[:, BUS_TYPE] == PQ).sum()
print("Internal buses:", len(bus_internal))
print("REF:", n_ref)
print("PV: ", n_pv)
print("PQ: ", n_pq)

# Jakobijeva matrika mapping
J = net._ppc["internal"]["J"]
# To so dejanski ppc indeksi, uporabljeni v NR
ref = net._ppc["internal"]["ref"].astype(int)
pv = net._ppc["internal"]["pv"].astype(int)
pq = net._ppc["internal"]["pq"].astype(int)

# vrstni red kot ga uporablja Newton-Raphson
pvpq = np.hstack((pv, pq))
n_pv = len(pv)
n_pq = len(pq)
n_pvpq = len(pvpq)
print()
print("Jakobijeva struktura:")
print(f"REF:  {len(ref)}")
print(f"PV:   {n_pv}")
print(f"PQ:   {n_pq}")
print(f"PVPQ: {n_pvpq}")
print()
print("J11 dP/dVa:", (n_pvpq, n_pvpq))
print("J12 dP/dVm:", (n_pvpq, n_pq))
print("J21 dQ/dVa:", (n_pq, n_pvpq))
print("J22 dQ/dVm:", (n_pq, n_pq))

# Preverjanje dimenzij Jakobija
expected_size = n_pvpq + n_pq
if J.shape != (expected_size, expected_size):
    raise RuntimeError(
        f"Nepričakovana dimenzija Jakobija: {J.shape}, "
        f"pričakovano ({expected_size}, {expected_size})"
    )

# Razdelitev Jakobija
J11 = J[:n_pvpq, :n_pvpq]
J12 = J[:n_pvpq, n_pvpq:]
J21 = J[n_pvpq:, :n_pvpq]
J22 = J[n_pvpq:, n_pvpq:]
print()
print("Dejanske dimenzije:")
print("J11:", J11.shape)
print("J12:", J12.shape)
print("J21:", J21.shape)
print("J22:", J22.shape)

# Določitev ppc bus mapping
bus_lookup = net._pd2ppc_lookups["bus"]
# Naredimo reverse mapping:
# ppc bus v vse pandapower buse, ki so mapirani nanj
ppc_to_pp_buses = {}
for pp_bus in net.bus.index:
    ppc_bus = int(bus_lookup[pp_bus])
    if ppc_bus >= 0:
        ppc_to_pp_buses.setdefault(ppc_bus, []).append(pp_bus)
def get_bus_info(ppc_bus):
    """
    Vrne informacije o pandapower busih, ki pripadajo
    določenemu internemu ppc busu.
    """
    pp_buses = ppc_to_pp_buses.get(int(ppc_bus), [])
    if not pp_buses:
        return [], ["AUXILIARY / INTERNAL BUS"]
    names = []
    for pp_bus in pp_buses:

        if "name" in net.bus.columns:
            names.append(str(net.bus.at[pp_bus, "name"]))
        else:
            names.append("")
    return pp_buses, names

# Mapping stolpcev Jakobija
column_mapping = []
# Prvih n_pvpq stolpcev = voltage angle Va
for j_col, ppc_bus in enumerate(pvpq):
    pp_buses, names = get_bus_info(ppc_bus)
    column_mapping.append({
        "J_column": j_col,
        "variable": "Va",
        "bus_type": "PV" if ppc_bus in pv else "PQ",
        "ppc_bus": int(ppc_bus),
        "pp_bus": pp_buses,
        "bus_name": names
    })
# Naslednjih n_pq stolpcev = voltage magnitude Vm
for i, ppc_bus in enumerate(pq):

    j_col = n_pvpq + i
    pp_buses, names = get_bus_info(ppc_bus)
    column_mapping.append({
        "J_column": j_col,
        "variable": "Vm",
        "bus_type": "PQ",
        "ppc_bus": int(ppc_bus),
        "pp_bus": pp_buses,
        "bus_name": names
    })
column_mapping = pd.DataFrame(column_mapping)

# Mapping vrstic Jakobija
row_mapping = []
# Prvih n_pvpq vrstic = P equations
for j_row, ppc_bus in enumerate(pvpq):
    pp_buses, names = get_bus_info(ppc_bus)
    row_mapping.append({
        "J_row": j_row,
        "equation": "P",
        "bus_type": "PV" if ppc_bus in pv else "PQ",
        "ppc_bus": int(ppc_bus),
        "pp_bus": pp_buses,
        "bus_name": names
    })
# Naslednjih n_pq vrstic = Q equations
for i, ppc_bus in enumerate(pq):
    j_row = n_pvpq + i
    pp_buses, names = get_bus_info(ppc_bus)
    row_mapping.append({
        "J_row": j_row,
        "equation": "Q",
        "bus_type": "PQ",
        "ppc_bus": int(ppc_bus),
        "pp_bus": pp_buses,
        "bus_name": names
    })
row_mapping = pd.DataFrame(row_mapping)

"""
Nalaganje Jakobija:

import pandas as pd
from scipy.sparse import load_npz
J = load_npz(os.path.join(output_dir, "Jacobian.npz"))
column_mapping = pd.read_csv("Jacobian_column_mapping.csv")
row_mapping = pd.read_csv("Jacobian_row_mapping.csv")

"""

# Inverzni Jakobij
print()
print("Izračun inverznega Jakobija...")
J_inv = np.linalg.inv(J.toarray())

# Numerično preverjanje inverza
identity_error = np.linalg.norm(
    J.toarray() @ J_inv - np.eye(J.shape[0]),
    ord=np.inf
)
print(
    "Napaka J @ J_inv - I:",
    f"{identity_error:.3e}"
)

# Pretvorba napetostnih občutljivosti v fizikalne enote
# Sistemska bazna moč/MVA
base_mva = float(net.sn_mva)
# Bazne napetosti PQ zbiralk/kV
# Vrstice spodnjega dela J^-1 pripadajo PQ zbiralkam.
base_kv_pq = bus_internal[
    pq,
    BASE_KV
].astype(float)
# Column vector:
# ena bazna napetost za vsako vrstico sensitivity matrike
base_kv_pq_col = base_kv_pq[:, np.newaxis]

# dV/dP
# Vrstice:
#   PQ zbiralke, kjer opazujemo napetost
# Stolpci:
#   PV + PQ zbiralke, kjer spreminjamo P
# pu / pu -> kV / MW
dV_dP_kV_per_MW = (
    J_inv[
        n_pvpq:,
        :n_pvpq
    ]
    * base_kv_pq_col
    / base_mva
)

# dV/dQ
# Vrstice:
#   PQ zbiralke, kjer opazujemo napetost
# Stolpci:
#   PQ zbiralke, kjer spreminjamo Q
# pu / pu -> kV / MVAr
dV_dQ_kV_per_MVAr = (
    J_inv[
        n_pvpq:,
        n_pvpq:
    ]
    * base_kv_pq_col
    / base_mva
)

# Napetostne občutljivosti
print()
print("Napetostne občutljivosti:")
print(
    "dV/dP [kV/MW]:   ",
    dV_dP_kV_per_MW.shape
)
print(
    "dV/dQ [kV/MVAr]: ",
    dV_dQ_kV_per_MVAr.shape
)
print()
print("S_base:", base_mva, "MVA")

# Mapping za dV/dP
# Vrstice dV/dP = PQ zbiralke,
# kjer merimo spremembo V
dV_dP_row_mapping = []
for i, ppc_bus in enumerate(pq):
    pp_buses, names = get_bus_info(ppc_bus)
    dV_dP_row_mapping.append({
        "row": i,
        "output": "V",
        "unit": "kV",
        "bus_type": "PQ",
        "ppc_bus": int(ppc_bus),
        "pp_bus": pp_buses,
        "bus_name": names,
        "base_kV": base_kv_pq[i]
    })
dV_dP_row_mapping = pd.DataFrame(
    dV_dP_row_mapping
)
# Stolpci dV/dP = PV + PQ zbiralke,
# kjer spreminjamo P
dV_dP_column_mapping = []
for j, ppc_bus in enumerate(pvpq):
    pp_buses, names = get_bus_info(ppc_bus)
    dV_dP_column_mapping.append({
        "column": j,
        "input": "P",
        "unit": "MW",
        "bus_type": (
            "PV" if ppc_bus in pv else "PQ"
        ),
        "ppc_bus": int(ppc_bus),
        "pp_bus": pp_buses,
        "bus_name": names
    })
dV_dP_column_mapping = pd.DataFrame(
    dV_dP_column_mapping
)

# Mapping za dV/dQ
# Vrstice dV/dQ = PQ zbiralke,
# kjer merimo spremembo V
dV_dQ_row_mapping = dV_dP_row_mapping.copy()
# Stolpci dV/dQ = PQ zbiralke,
# kjer spreminjamo Q
dV_dQ_column_mapping = []
for j, ppc_bus in enumerate(pq):
    pp_buses, names = get_bus_info(ppc_bus)
    dV_dQ_column_mapping.append({
        "column": j,
        "input": "Q",
        "unit": "MVAr",
        "bus_type": "PQ",
        "ppc_bus": int(ppc_bus),
        "pp_bus": pp_buses,
        "bus_name": names
    })
dV_dQ_column_mapping = pd.DataFrame(
    dV_dQ_column_mapping
)

# Shranjevanje originalnega Jakobija
save_npz(
    os.path.join(
        output_dir,
        "Jacobian.npz"
    ),
    J
)
column_mapping.to_csv(
    os.path.join(
        output_dir,
        "Jacobian_column_mapping.csv"
    ),
    index=False
)
row_mapping.to_csv(
    os.path.join(
        output_dir,
        "Jacobian_row_mapping.csv"
    ),
    index=False
)
np.savez(
    os.path.join(
        output_dir,
        "Jacobian_bus_sets.npz"
    ),
    ref=ref,
    pv=pv,
    pq=pq,
    pvpq=pvpq
)

# Shranjevanje napetostnih občutljivosti
np.savez_compressed(
    os.path.join(
        output_dir,
        "Voltage_sensitivities.npz"
    ),
    dV_dP_kV_per_MW=dV_dP_kV_per_MW,
    dV_dQ_kV_per_MVAr=dV_dQ_kV_per_MVAr,
    base_mva=base_mva,
    base_kv_pq=base_kv_pq
)

# Shranjevanje mappingov sensitivity matrik
dV_dP_row_mapping.to_csv(
    os.path.join(
        output_dir,
        "dV_dP_row_mapping.csv"
    ),
    index=False
)
dV_dP_column_mapping.to_csv(
    os.path.join(
        output_dir,
        "dV_dP_column_mapping.csv"
    ),
    index=False
)
dV_dQ_row_mapping.to_csv(
    os.path.join(
        output_dir,
        "dV_dQ_row_mapping.csv"
    ),
    index=False
)
dV_dQ_column_mapping.to_csv(
    os.path.join(
        output_dir,
        "dV_dQ_column_mapping.csv"
    ),
    index=False
)

print()
print("Vsi rezultati uspešno shranjeni.")