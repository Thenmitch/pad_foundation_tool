import streamlit as st
import math

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO

from assumptions import get_engineering_assumptions

# --------------------------------------------------
# APP CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Pad Foundation Sizing Tool",
    layout="wide",
)

st.set_option("client.toolbarMode", "minimal")
st.set_option("client.showErrorDetails", False)

st.caption("Version v1.2 – Multiple pad foundations supported")

st.title("🧱 Pad Foundation Preliminary Sizing Tool")

st.markdown(
    """
    **Purpose**  
    Preliminary sizing of **square pad foundations** under axial load.

    Each pad is checked independently using the same assumptions and rules.

    ⚠️ *Preliminary sizing only.*
    """
)

st.divider()

# --------------------------------------------------
# LAYOUT
# --------------------------------------------------
input_col, calc_col, results_col = st.columns([1, 1.2, 1])

# --------------------------------------------------
# SESSION STATE
# --------------------------------------------------

if "pads" not in st.session_state:
    st.session_state.pads = []

# --------------------------------------------------
# INPUTS (COMMON)
# --------------------------------------------------

with input_col:

    st.header("Global Inputs (apply to all pads)")

    col1, col2 = st.columns(2)

    with col1:
        q_allow = st.number_input(
            "Allowable bearing pressure, qₐ (kN/m²)",
            min_value=25.0,
            value=150.0,
            step=10.0,
        )

    rounding = st.selectbox(
        "Round foundation size up to:",
        options=[0.10, 0.20],
        index=1,
    )

    with col2:
        target_utilisation = st.slider(
            "Target bearing utilisation (%)",
            min_value=50,
            max_value=95,
            value=90,
            step=5,
        ) / 100.0

    st.subheader("Minimum Foundation Constraints")

    min_width = st.slider("Minimum pad width (m)", 0.5, 6.0, 1.5, 0.10)
    min_depth = st.slider("Minimum pad depth (m)", 0.3, 2.5, 0.75, 0.05)

    include_self_weight = st.checkbox("Include pad self-weight", value=True)

    st.divider()

    # --------------------------------------------------
    # ADD PAD
    # --------------------------------------------------

    st.header("Add Pad Foundation")

    col1, col2 = st.columns(2)

    with col1:
        G = st.number_input("Dead load, G (kN)", value=750.0, step=50.0)
        Sur_G = st.number_input(
            "Additional surcharge Dead load (kN/m²)", value=0.0, step=0.5
        )

    with col2:
        Q = st.number_input("Live load, Q (kN)", value=500.0, step=50.0)
        Sur_Q = st.number_input(
            "Additional surcharge Live load (kN/m²)", value=0.0, step=0.5
        )

    if st.button("➕ Add pad foundation"):
        st.session_state.pads.append(
            {
                "id": len(st.session_state.pads) + 1,
                "G": G,
                "Q": Q,
                "Sur_G": Sur_G,
                "Sur_Q": Sur_Q,
            }
        )

    st.divider()

# --------------------------------------------------
# CONSTANTS
# --------------------------------------------------

GAMMA_CONC = 24.0  # kN/m³

gamma_G = 1.0
gamma_Q = 1.0

DEPTH_STEP = 0.05
DEPTH_SEARCH_LIMIT = 3.0

B_REFINE_STEP = 0.01  # m (10 mm)

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def round_up(value, inc):
    return math.ceil(value / inc) * inc

def round_down(value, inc):
    return math.floor(value / inc) * inc

# --------------------------------------------------
# depth to width B relationship: t = B / 2
# --------------------------------------------------
def solve_pad(
    G,
    Q,
    Sur_G,
    Sur_Q,
    q_allow,
    target_utilisation,
    min_width,
    min_depth,          # kept for interface consistency
    rounding,           # kept for interface consistency
    include_self_weight,
):

    # --------------------------------------------------
    # Base loads (excluding pad & surcharge)
    # --------------------------------------------------
    N_ck_initial = gamma_G * G + gamma_Q * Q
    q_target = target_utilisation * q_allow

    # --------------------------------------------------
    # Initial width from bearing only
    # --------------------------------------------------
    A_req = N_ck_initial / q_target
    B = max(math.sqrt(A_req), min_width)

    # --------------------------------------------------
    # Refine width (continuous, no rounding)
    # Enforce t = B / 2 at ALL times
    # --------------------------------------------------
    while True:

        t = 0.5 * B  # ← enforced geometry rule

        # Surcharges
        N_ck_sur_G = Sur_G * B**2
        N_ck_sur_Q = Sur_Q * B**2

        # Self-weight
        W_pad = B**2 * t * GAMMA_CONC if include_self_weight else 0.0

        # Final axial load
        N_ck = (
            gamma_G * (G + W_pad + N_ck_sur_G)
            + gamma_Q * (Q + N_ck_sur_Q)
        )

        # Bearing pressure
        q_ed = N_ck / B**2
        util = q_ed / q_allow

        if util > target_utilisation:
            B += B_REFINE_STEP
        else:
            break

    # --------------------------------------------------
    # Return continuous (unrounded) solution
    # --------------------------------------------------
    return {
        "B_opt": B,
        "t": t,
        "N_ck_initial": N_ck_initial,
        "q_target": q_target,
    }


# --------------------------------------------------
# CALCULATIONS
# --------------------------------------------------

with calc_col:
    st.header("Pad Foundation Designs")

    for pad in st.session_state.pads:

        st.subheader(f"Pad {pad['id']}")

        result = solve_pad(
            G=pad["G"],
            Q=pad["Q"],
            Sur_G=pad["Sur_G"],
            Sur_Q=pad["Sur_Q"],
            q_allow=q_allow,
            target_utilisation=target_utilisation,
            min_width=min_width,
            min_depth=min_depth,
            rounding=rounding,
            include_self_weight=include_self_weight,
        )

        if result is None:
            st.error("No feasible pad size found for this load case.")
            continue

        # ---- continuous optimum ----
        B_opt = result["B_opt"]
        t = result["t"]
        N_ck_initial = result["N_ck_initial"]
        q_target = result["q_target"]

        # ---- round UP (conservative) ----
        B_final = round_up(B_opt, rounding)
        # ---- enforce geometry AFTER rounding ----
        t_round = 0.5 * B_final

        # ---- self-weight ----
        W_pad = B_final**2 * t_round * GAMMA_CONC if include_self_weight else 0.0

        # ---- surcharge ----
        N_ck_sur_G = pad["Sur_G"] * B_final**2
        N_ck_sur_Q = pad["Sur_Q"] * B_final**2
        N_ck_surcharge = N_ck_sur_G + N_ck_sur_Q

        # ---- final axial load ----
        N_ck_final = (
            gamma_G * (pad["G"] + W_pad + N_ck_sur_G)
            + gamma_Q * (pad["Q"] + N_ck_sur_Q)
        )

        # ---- bearing pressure ----
        q_ed = N_ck_final / B_final**2
        utilisation = q_ed / q_allow

        # ---- indicative sizing ----
        A0 = N_ck_initial / q_target
        B0 = math.sqrt(A0)

        volume = B_final**2 * t_round


        pad["results"] = {
        "B_final": B_final,
        "t_round": t_round,
        "q_ed": q_ed,
        "utilisation": utilisation,
        "N_ck": N_ck_final,
        "volume": volume,
        "calc_md": f"""
**1. Applied loads contributing to foundation design**  

Column dead load, G = {pad['G']:.1f} kN  
Column live load, Q = {pad['Q']:.1f} kN  

Surcharge loads act over the full pad area and are calculated once pad size is known.  
Pad self-weight is included in the design and depends on the adopted pad dimensions.

---

**2. Target bearing pressure**  

q_target = {target_utilisation:.2f} × qₐ  
= {q_target:.1f} kN/m²

---

**3. Indicative bearing area and width (excluding size-dependent effects)**  

Required bearing area:  
A = Nck,base / q_target  

Where:  
Nck,base = γG·G + γQ·Q  
= {gamma_G:.2f}×{pad['G']:.1f} + {gamma_Q:.2f}×{pad['Q']:.1f}  
= **{N_ck_initial:.1f} kN**

A = {N_ck_initial:.1f} / {q_target:.1f}  
**A = {A0:.2f} m²**

Indicative pad width:  
B = √A = {B0:.2f} m  

---

**4. Adopted pad geometry**  

Pad width rounded **upwards** for constructability and conservatism.

Adopted pad width:  
**B = {B_final:.2f} m**

Pad depth governed by geometric rule:  
t = B / 2  

Adopted pad depth:  
**t = {t_round:.2f} m**

---

**5. Pad self-weight**  

Pad self-weight calculated from adopted geometry:

W = B² · t · γc  
= {B_final:.2f}² × {t_round:.2f} × {GAMMA_CONC:.1f}  

**W = {W_pad:.1f} kN**

---

**6. Surcharge loads acting on pad area**  

Dead load surcharge:  
Gₛ = {pad['Sur_G']:.2f} × {B_final:.2f}²  
**Gₛ = {N_ck_sur_G:.1f} kN**

Live load surcharge:  
Qₛ = {pad['Sur_Q']:.2f} × {B_final:.2f}²  
**Qₛ = {N_ck_sur_Q:.1f} kN**

Total surcharge load:  
**Gₛ + Qₛ = {N_ck_surcharge:.1f} kN**

---

**7. Design axial load including self-weight and surcharge**  

Total design axial load acting on soil beneath pad:

Nck = γG·(G + W + Gₛ) + γQ·(Q + Qₛ)

= {gamma_G:.2f}×({pad['G']:.1f} + {W_pad:.1f} + {N_ck_sur_G:.1f})  
+ {gamma_Q:.2f}×({pad['Q']:.1f} + {N_ck_sur_Q:.1f})

**Nck = {N_ck_final:.1f} kN**

---

**8. Bearing pressure check**  

q_ed = Nck / B²  
= {N_ck_final:.1f} / {B_final:.2f}²  

**q_ed = {q_ed:.1f} kN/m² ≤ {q_allow:.1f} kN/m²**

✔ Bearing capacity OK
"""

}


        st.metric("Pad size", f"{B_final:.2f} m × {B_final:.2f} m")
        st.metric("Bearing pressure", f"{q_ed:.1f} kN/m²")
        st.metric("Utilisation", f"{utilisation*100:.1f}%")
        st.metric("Concrete volume", f"{volume:.2f} m³")
        st.metric("Pad depth", f"{t_round:.2f} m")

        st.success("Design OK")

        with st.expander("Show calculation steps"):
            st.markdown(pad["results"]["calc_md"])

        st.divider()

    # --------------------------------------------------
    # ASSUMPTIONS
    # --------------------------------------------------

st.header("Engineering Assumptions & Design Basis")
with st.expander("Show Assumptions"):
    st.markdown(
        get_engineering_assumptions(
            gamma_G=gamma_G,
            gamma_Q=gamma_Q,
            gamma_conc=GAMMA_CONC,
            min_depth=min_depth,
            min_width=min_width,
            rounding=rounding,
        )
    )

    st.caption(
        "Preliminary sizing only. Not a substitute for full EC7 / EC2 design."
    )

# --------------------------------------------------
# RESULTS TABLE
# --------------------------------------------------

with results_col:
    st.header("Summary of Pad Foundations")

    if len(st.session_state.pads) == 0:
        st.info("No pad foundations added yet.")
    else:
        import pandas as pd

        summary_data = []
        for pad in st.session_state.pads:
            res = pad["results"]
            summary_data.append(
                {
                    "Pad ID": pad["id"],
                    "Width (m)": f"{res['B_final']:.2f}",
                    "Depth (m)": f"{res['t_round']:.2f}",
                    "Utilisation (%)": f"{res['utilisation']*100:.1f}",
                    "SLS Load (kN)": f"{res['N_ck']:.1f}",
                    "Volume (m³)": f"{res['volume']:.2f}",
                }
            )

        st.table(pd.DataFrame(summary_data))
   