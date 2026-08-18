import numpy as np
import pandas as pd


def design_lcl_filter(
    S_n_va,
    U_ll_v,
    f_sw_hz,
    f_grid_hz=50,
    voltage_drop_pu=0.10,
    L1_ratio=0.7,
    capacitor_reactive_power_pu=0.05,
    inductor_resistance_percent=1.0,
    damping_resistor_factor=1/3
):
    """
    Basic LCL filter design for a three-phase grid-connected voltage source converter.

    The design procedure is:
    1. Calculate rated current.
    2. Determine total inductance from allowed voltage drop.
    3. Split total inductance into converter-side and grid-side inductors.
    4. Determine filter capacitance from allowed reactive power at grid frequency.
    5. Calculate LCL resonance frequency.
    6. Estimate physical inductor resistances and capacitor damping resistor.

    Parameters
    ----------
    S_n_va : float
        Rated apparent power of the converter [VA].

    U_ll_v : float
        Rated line-to-line AC voltage [V].

    f_sw_hz : float
        Switching frequency [Hz].

    f_grid_hz : float
        Grid frequency [Hz].

    voltage_drop_pu : float
        Allowed voltage drop across total filter inductance at rated current [p.u.].

    L1_ratio : float
        Share of total inductance placed on converter side.
        Example: 0.7 means L1 = 70 % of L_total and L2 = 30 %.

    capacitor_reactive_power_pu : float
        Capacitor reactive power at grid frequency relative to rated power.
        Typical value: 0.02 ... 0.05.

    inductor_resistance_percent : float
        Physical series resistance of inductors as percent of their reactance at grid frequency.
        Typical value: 0.5 ... 2 %.

    damping_resistor_factor : float
        Factor for damping resistor calculation:
        R_d = damping_resistor_factor / (omega_res * C)

        Typical initial value: 1/3.

    Returns
    -------
    pandas.DataFrame
        LCL filter design results.
    """

    # --------------------------------------------------
    # 1. Basic rated quantities
    # --------------------------------------------------

    U_phase_v = U_ll_v / np.sqrt(3)
    I_n_a = S_n_va / (np.sqrt(3) * U_ll_v)

    omega_grid = 2 * np.pi * f_grid_hz

    # --------------------------------------------------
    # 2. Total inductance from allowed voltage drop
    # --------------------------------------------------

    delta_U_phase_v = voltage_drop_pu * U_phase_v

    X_L_total_ohm = delta_U_phase_v / I_n_a

    L_total_h = X_L_total_ohm / omega_grid

    # --------------------------------------------------
    # 3. Split total inductance into L1 and L2
    # --------------------------------------------------

    L1_h = L1_ratio * L_total_h
    L2_h = (1 - L1_ratio) * L_total_h

    X_L1_grid_ohm = omega_grid * L1_h
    X_L2_grid_ohm = omega_grid * L2_h

    # --------------------------------------------------
    # 4. Capacitor from allowed reactive power
    # --------------------------------------------------

    Q_C_var = capacitor_reactive_power_pu * S_n_va

    C_f = Q_C_var / (3 * omega_grid * U_phase_v**2)

    # --------------------------------------------------
    # 5. LCL resonance frequency
    # --------------------------------------------------

    omega_res = np.sqrt((L1_h + L2_h) / (L1_h * L2_h * C_f))
    f_res_hz = omega_res / (2 * np.pi)

    # --------------------------------------------------
    # 6. Physical inductor resistances
    # --------------------------------------------------

    R1_ohm = X_L1_grid_ohm * inductor_resistance_percent / 100
    R2_ohm = X_L2_grid_ohm * inductor_resistance_percent / 100

    # --------------------------------------------------
    # 7. Damping resistor in series with capacitor
    # --------------------------------------------------

    R_d_ohm = damping_resistor_factor / (omega_res * C_f)

    # --------------------------------------------------
    # 8. Checks and auxiliary values
    # --------------------------------------------------

    X_C_grid_ohm = 1 / (omega_grid * C_f)
    X_C_res_ohm = 1 / (omega_res * C_f)

    I_C_grid_a = U_phase_v / X_C_grid_ohm
    I_C_grid_pu = I_C_grid_a / I_n_a

    P_R1_w = 3 * I_n_a**2 * R1_ohm
    P_R2_w = 3 * I_n_a**2 * R2_ohm
    P_R_total_w = P_R1_w + P_R2_w

    P_R_d_w = 3 * I_C_grid_a**2 * R_d_ohm

    f_res_min = 10 * f_grid_hz
    f_res_max = 0.5 * f_sw_hz

    if f_res_hz < f_res_min:
        resonance_check = "WARNING: resonance frequency is too close to grid frequency"
    elif f_res_hz > f_res_max:
        resonance_check = "WARNING: resonance frequency is too close to switching frequency"
    else:
        resonance_check = "OK"

    results = {
        "Rated apparent power S_n [kVA]": S_n_va / 1000,
        "Line-to-line voltage U_LL [V]": U_ll_v,
        "Phase voltage U_phase [V]": U_phase_v,
        "Grid frequency f_grid [Hz]": f_grid_hz,
        "Switching frequency f_sw [Hz]": f_sw_hz,
        "Rated current I_n [A]": I_n_a,

        "Allowed voltage drop [p.u.]": voltage_drop_pu,
        "Allowed phase voltage drop [V]": delta_U_phase_v,
        "Total filter reactance X_L_total [ohm]": X_L_total_ohm,
        "Total inductance L_total [mH]": L_total_h * 1000,

        "L1 ratio [-]": L1_ratio,
        "Converter-side inductance L1 [mH]": L1_h * 1000,
        "Grid-side inductance L2 [mH]": L2_h * 1000,
        "X_L1 at grid frequency [ohm]": X_L1_grid_ohm,
        "X_L2 at grid frequency [ohm]": X_L2_grid_ohm,

        "Capacitor reactive power Q_C [kVAr]": Q_C_var / 1000,
        "Capacitor reactive power [p.u.]": capacitor_reactive_power_pu,
        "Filter capacitance C [uF]": C_f * 1e6,

        "LCL resonance frequency f_res [Hz]": f_res_hz,
        "X_C at grid frequency [ohm]": X_C_grid_ohm,
        "X_C at resonance frequency [ohm]": X_C_res_ohm,

        "Capacitor current at grid frequency [A]": I_C_grid_a,
        "Capacitor current at grid frequency [p.u.]": I_C_grid_pu,

        "Inductor resistance factor [% of X_L]": inductor_resistance_percent,
        "Converter-side resistance R1 [ohm]": R1_ohm,
        "Grid-side resistance R2 [ohm]": R2_ohm,
        "Total inductor copper losses [W]": P_R_total_w,

        "Damping resistor factor [-]": damping_resistor_factor,
        "Damping resistor R_d [ohm]": R_d_ohm,
        "Approx. damping resistor losses [W]": P_R_d_w,

        "Resonance frequency check": resonance_check,
    }

    return pd.DataFrame(results.items(), columns=["Quantity", "Value"])


# ============================================================
# Example usage
# ============================================================

S_n = 150e3       # Rated power [VA]
U_ll = 690        # Rated line-to-line voltage [V]
f_sw = 15_000     # Switching frequency [Hz]

df = design_lcl_filter(
    S_n_va=S_n,
    U_ll_v=U_ll,
    f_sw_hz=f_sw,
    f_grid_hz=50,
    voltage_drop_pu=0.10,
    L1_ratio=0.7,
    capacitor_reactive_power_pu=0.05,
    inductor_resistance_percent=1.0,
    damping_resistor_factor=1/3
)

pd.set_option("display.float_format", "{:.6f}".format)
print(df)