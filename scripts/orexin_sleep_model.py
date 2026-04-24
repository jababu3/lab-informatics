
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

# ---------------------------------------------------------
# 1. PARAMETERS (Table 1 from Rempe et al., 2010) [4]
# ---------------------------------------------------------
# Time constants and scaling
delta_A = 0.01  # AMIN (Wake) scaling
delta_V = 0.01  # VLPO (Sleep) scaling
delta_R = 0.5   # REM scaling
delta_N = 0.5   # NREM scaling

# Threshold/Slope parameters for Morris-Lecar functions
epsilon_A = 3.0
epsilon_V = 3.0
epsilon_R = 0.3
epsilon_N = 0.3
gamma_A = 5.7
gamma_V = 3.77
gamma_R = 6.2
gamma_N = 6.0

# Tau parameters (Recovery variable time constants in hours)
tau1_A = 1.0; tau2_A = 2.0
tau1_V = 1.0; tau2_V = 2.0
tau1_R = 1.0; tau2_R = 2.0
tau1_N = 0.5; tau2_N = 1.7

# Synaptic Connection Strengths (g parameters) [4]
g_vlpo = 5.0      # VLPO -> AMIN
g_amin = 2.0      # AMIN -> VLPO
g_scn = 1.0       # SCN -> VLPO and AMIN (via Orexin)
g_orexin = 1.0    # Orexin -> AMIN (Assumed proportional to SCN in wake)
g_amin_rem = 2.5  # AMIN -> REM
g_rem = 0.4       # REM -> NREM
g_nrem = 5.0      # NREM -> REM
g_evlpo = 6.2     # eVLPO -> NREM

# Constant Drives [1, 4]
I_A0 = 3.3    # Background drive to AMIN
I_V0 = 0.45   # Background drive to VLPO
I_R0 = 1.1    # Background drive to REM
I_N0 = 1.9    # Background drive to NREM

# Homeostat parameters [2, 4]
g_hom = 5.5
alpha_h = 18.2  # Rise rate (wake)
beta_h = 4.2    # Decay rate (sleep)
h_max = 1.0

# eVLPO parameters (Equation 7) [3, 4]
a_e = 2.0
b_e = 1.0
c_e = 1.82
c_v = -0.3
k_xv = 1.0
k_x = 0.2

# REM Frequency scaling
sigma = 11.0

# ---------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------

def H_inf(x):
    """Sigmoidal activation function (Eq 1-2 text) [1]."""
    # Smooth approximation of Heaviside step function
    return 0.5 * (1 + np.tanh(x / 0.01))

def tau_func(x, t1, t2):
    """Voltage dependent time constant (Eq 1-2 text) [1]."""
    return t1 + (t2 - t1) * H_inf(x)

def f_func(x, y):
    """Cubic nullcline function for Morris-Lecar (Eq 1-2 text) [1]."""
    return 3 * x - x**3 + 2 - y

def circadian_drive(t):
    """
    Circadian pacemaker C(t) (Appendix) [5].
    Period is 24 hours.
    """
    omega = 2 * np.pi / 24.0
    return (0.97 * np.sin(omega * t) +
            0.22 * np.sin(2 * omega * t) +
            0.07 * np.sin(3 * omega * t) +
            0.03 * np.sin(4 * omega * t) +
            0.01 * np.sin(5 * omega * t))

def he_func(v, k):
    """Sigmoid for eVLPO dynamics (Eq 7) [3]."""
    return 0.5 * (1 + np.tanh(v / k))

# ---------------------------------------------------------
# 3. ODE SYSTEM
# ---------------------------------------------------------

def sleep_model(t, state):
    # Unpack state vector (10 variables)
    # x: activity, y: recovery
    xA, yA, xV, yV, xR, yR, xN, yN, xe, h = state

    # --- 1. Calculate Activation (H) functions ---
    H_A = H_inf(xA)
    H_V = H_inf(xV)
    
    # --- 2. Calculate Inputs ---
    
    # Circadian Input [1]
    C_t = circadian_drive(t)
    I_SCN = g_scn * C_t
    
    # Orexin Input [1]
    # Orexin is active if SCN is high AND VLPO is silent (1 - H_V)
    I_ORX = g_orexin * I_SCN * (1 - H_V)
    
    # Homeostatic Drive [2]
    I_HOM = g_hom * h
    
    # Synaptic Inputs (Inhibitory/Excitatory) [1-3]
    I_VLPO_to_A = g_vlpo * H_V
    I_AMIN_to_V = g_amin * H_A
    I_AMIN_to_REM = g_amin_rem * H_A  # AMIN strongly inhibits REM
    I_eVLPO_to_NREM = g_evlpo * xe
    I_NREM_to_REM = g_nrem * H_inf(xN)
    I_REM_to_NREM = g_rem * H_inf(xR)

    # --- 3. Differential Equations ---
    
    # -- Sleep/Wake Switch (AMIN vs VLPO) [1] --
    # AMIN (Wake-active)
    dxA = (f_func(xA, yA) - I_VLPO_to_A + I_ORX + I_A0 - I_HOM) / delta_A
    dyA = (epsilon_A * (gamma_A * H_A - yA)) / tau_func(xA, tau1_A, tau2_A)
    
    # VLPO (Sleep-active)
    dxV = (f_func(xV, yV) - I_AMIN_to_V - I_SCN + I_V0 + I_HOM) / delta_V
    dyV = (epsilon_V * (gamma_V * H_V - yV)) / tau_func(xV, tau1_V, tau2_V)
    
    # -- Homeostat (h) [2] --
    # Grows during wake (xA > 0), decays during sleep (xA < 0)
    # Using H_A as a smooth switch for the derivative
    dh = (alpha_h * (h_max - h) * H_A) - (beta_h * h * (1 - H_A))
    
    # -- eVLPO (Extended VLPO) [3] --
    # Slowly tracks VLPO, inhibited by AMIN
    # Note: Text Eq 7 uses he_func
    dxe = -xe + (c_e - a_e * he_func(xV + c_v, k_xv) - b_e * he_func(xA, k_x))
    
    # -- REM/NREM Switch [2, 3] --
    # REM-on
    dxR = (sigma * f_func(xR, yR) - I_AMIN_to_REM - I_NREM_to_REM + I_R0) / delta_R
    dyR = (sigma * epsilon_R * (gamma_R * H_inf(xR) - yR)) / tau_func(xR, tau1_R, tau2_R)
    
    # REM-off (NREM)
    dxN = (sigma * f_func(xN, yN) - I_eVLPO_to_NREM - I_REM_to_NREM + I_N0) / delta_N
    dyN = (sigma * epsilon_N * (gamma_N * H_inf(xN) - yN)) / tau_func(xN, tau1_N, tau2_N)

    return [dxA, dyA, dxV, dyV, dxR, dyR, dxN, dyN, dxe, dh]

# ---------------------------------------------------------
# 4. SIMULATION
# ---------------------------------------------------------

# Initial Conditions (Arbitrary start, let it stabilize)
y0 = [0.0, 0.0,  # AMIN (0, 1)
      -1.0, 0.0, # VLPO (2, 3) (start asleep)
      -2.0, 0.0, # REM (4, 5)
      -2.0, 0.0, # NREM (6, 7)
      0.0,       # eVLPO (8)
      0.3]       # h (9)

# Simulate for 48 hours
t_span = (0, 48)
t_eval = np.linspace(0, 48, 10000)

sol = solve_ivp(sleep_model, t_span, y0, t_eval=t_eval, method='BDF', rtol=1e-6, atol=1e-8)

# ---------------------------------------------------------
# 5. VISUALIZATION
# ---------------------------------------------------------

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

# Plot 1: Sleep/Wake Switch (AMIN vs VLPO)
# AMIN is sol.y[0], VLPO is sol.y[2]
ax1.plot(sol.t, sol.y[0], label='AMIN (Wake)', color='red', linewidth=1.5)
ax1.plot(sol.t, sol.y[2], label='VLPO (Sleep)', color='blue', linestyle='--', linewidth=1.5)
ax1.set_ylabel('Activity (x)')
ax1.set_title('Sleep/Wake Flip-Flop (Rempe et al., 2010)')
ax1.legend(loc='upper right')
ax1.grid(True, alpha=0.3)

# Plot 2: REM/NREM Switch
# Only relevant when AMIN is low (during sleep)
# REM is sol.y[4], NREM is sol.y[6]
ax2.plot(sol.t, sol.y[4], label='REM-on', color='green', linewidth=1.5)
ax2.plot(sol.t, sol.y[6], label='NREM (REM-off)', color='purple', linestyle=':', linewidth=1.5)
ax2.set_ylabel('Activity (x)')
ax2.set_title('REM/NREM Ultradian Rhythm')
ax2.legend(loc='upper right')
ax2.grid(True, alpha=0.3)

# Plot 3: Drives (Homeostat + Circadian)
# Calculate Circadian drive for plotting
C_vals = [circadian_drive(t) for t in sol.t]
# Homeostat is sol.y[9]
ax3.plot(sol.t, sol.y[9], label='Homeostat (h)', color='black', linewidth=1.5)
ax3.plot(sol.t, C_vals, label='Circadian (C)', color='orange', alpha=0.7)
ax3.set_ylabel('Drive Amplitude')
ax3.set_xlabel('Time (hours)')
ax3.legend(loc='upper right')
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('orexin_model_output.png')
print("Plot saved to orexin_model_output.png")
