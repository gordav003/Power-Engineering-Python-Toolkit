import numpy as np
import pandas as pd


def design_lc_filter(
    S_n_va,
    U_ll_v,
    f_sw_hz,
    f_res_hz,
    f_grid_hz=50,
    voltage_drop_pu=0.10,
    inductor_resistance_percent=1.0,
    damping_resistor_factor=1/3
):
    """
    LC filter design for a three-phase voltage source converter.

    The function calculates:
    - rated current
    - inductor value from allowed PCC voltage drop
    - capacitor value from desired resonance frequency
    - physical inductor series resistance
    - damping resistor in series with the capacitor branch

    Parameters

    S_n_va : float
        Rated apparent power [VA]

    U_ll_v : float
        Rated line-to-line AC voltage [V]

    f_sw_hz : float
        Switching frequency [Hz]

    f_res_hz : float
        Desired resonance frequency [Hz]

    f_grid_hz : float
        Grid frequency [Hz]

    voltage_drop_pu : float
        Allowed voltage drop across the inductor at rated current [p.u.]

    inductor_resistance_percent : float
        Physical inductor resistance as percentage of X_L at grid frequency.
        Typical value: 0.5 % ... 2 %

    damping_resistor_factor : float
        Factor for damping resistor calculation.
        Typical initial value: 1/3

        R_d = damping_resistor_factor / (omega_res * C)

    Returns

    pandas.DataFrame
        LC filter design results.
    """

    # Basic values
    U_phase_v = U_ll_v / np.sqrt(3)
    I_n_a = S_n_va / (np.sqrt(3) * U_ll_v)

    # Allowed voltage drop
    delta_U_phase_v = voltage_drop_pu * U_phase_v

    # Inductor reactance at grid frequency
    X_L_grid_ohm = delta_U_phase_v / I_n_a

    # Inductance
    L_h = X_L_grid_ohm / (2 * np.pi * f_grid_hz)

    # Resonance angular frequency
    omega_res = 2 * np.pi * f_res_hz

    # Capacitance
    C_f = 1 / (omega_res**2 * L_h)

    # Physical inductor resistance
    R_L_ohm = X_L_grid_ohm * inductor_resistance_percent / 100

    # Damping resistor in series with capacitor
    R_d_ohm = damping_resistor_factor / (omega_res * C_f)

    # Reactances
    X_L_sw_ohm = 2 * np.pi * f_sw_hz * L_h
    X_C_grid_ohm = 1 / (2 * np.pi * f_grid_hz * C_f)
    X_C_res_ohm = 1 / (2 * np.pi * f_res_hz * C_f)

    # Capacitor current at grid frequency
    I_C_grid_a = U_phase_v / X_C_grid_ohm
    I_C_grid_pu = I_C_grid_a / I_n_a

    # Inductor copper losses
    P_R_L_w = 3 * I_n_a**2 * R_L_ohm

    # Damping resistor losses at grid frequency, approximate
    # Since R_d is in series with C, capacitor branch current is approximately used.
    P_R_d_w = 3 * I_C_grid_a**2 * R_d_ohm

    # Impedances
    Z_L_grid = R_L_ohm + 1j * X_L_grid_ohm
    Z_C_damped_grid = R_d_ohm - 1j * X_C_grid_ohm

    # Resonance frequency check
    f_res_min = 10 * f_grid_hz
    f_res_max = 0.5 * f_sw_hz

    if f_res_hz < f_res_min:
        resonance_check = "WARNING: f_res is too close to grid frequency"
    elif f_res_hz > f_res_max:
        resonance_check = "WARNING: f_res is too close to switching frequency"
    else:
        resonance_check = "OK"

    results = {
        "Rated apparent power S_n [kVA]": S_n_va / 1000,
        "Line-to-line voltage U_LL [V]": U_ll_v,
        "Grid frequency f_grid [Hz]": f_grid_hz,
        "Switching frequency f_sw [Hz]": f_sw_hz,
        "Resonance frequency f_res [Hz]": f_res_hz,
        "Rated current I_n [A]": I_n_a,
        "Allowed voltage drop [p.u.]": voltage_drop_pu,
        "Inductance L [mH]": L_h * 1000,
        "Capacitance C [uF]": C_f * 1e6,
        "Physical inductor resistance R_L [ohm]": R_L_ohm,
        "Damping resistor factor [-]": damping_resistor_factor,
        "Damping resistor R_d [ohm]": R_d_ohm,
        "Capacitor current at grid frequency [p.u.]": I_C_grid_pu,
        "Inductor copper losses P_R_L [W]": P_R_L_w,
        "Resonance frequency check": resonance_check,
    }

    return pd.DataFrame(results.items(), columns=["Quantity", "Value"])

# Example usage

S_n = 150e3       # 150 kVA
U_ll = 690        # 690 V
f_sw = 15_000     # 15 kHz
f_res = 2_200     # 2.2 kHz

df = design_lc_filter(
    S_n_va=S_n,
    U_ll_v=U_ll,
    f_sw_hz=f_sw,
    f_res_hz=f_res,
    f_grid_hz=50,
    voltage_drop_pu=0.10,
    inductor_resistance_percent=1.0,
    damping_resistor_factor=1/3
)

pd.set_option("display.float_format", "{:.6f}".format)
print(df)