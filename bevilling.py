# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# -------------------- Hjælp --------------------
def fmt_dkk(x: float) -> str:
    """Dansk tusindtalsformat (punktum) uden decimaler."""
    return f"{x:,.0f} kr".replace(",", ".")

def crossed_multiple_of_10m(prev_total: float, new_total: float) -> int | None:
    """
    Returnér 20, 30, 40, … hvis et nyt 10 mio.-multiplum er passeret; ellers None.
    Gælder kun for nye totaler >= 20 mio.
    """
    ten = 10_000_000
    if new_total < 20_000_000:
        return None
    k_prev, k_new = int(prev_total // ten), int(new_total // ten)
    if k_new > k_prev and k_new >= 2:
        return k_new * 10
    return None

def normalize_limits(r: float, e: float, l: float):
    """Sikrer stigende grænser. Returnerer (limits, corrected_flag)."""
    corrected = not (r < e < l)
    vals = sorted([r, e, l])
    return {"Rådgiver": vals[0], "Erhvervschef": vals[1], "Lokalbankdirektør": vals[2]}, corrected

def decide_approver(
    prev_total: float,
    new_total: float,
    limits_input: dict,
    product: str,               # "Bank" | "Realkredit"
    segment: str,               # "Privat" | "Erhverv"
    owner_or_holiday: bool,     # kun relevant for Privat + Realkredit
    ltv_pct: float | None,      # kun relevant for Privat + Realkredit
    debt_factor: float | None,  # kun relevant for Privat + Realkredit
    approved_by_credit_before: bool,
    new_business: bool,         # ny erhvervskunde?
    new_bank_exposure: float,   # nyt bankengagement (DKK)
    group_exposure: float       # koncernengagement (DKK)
):
    """
    Returnerer (bevilger, detaljer-dict).
    Detaljer inkluderer alle aktiverede regler/flags.
    """

    # Normaliser grænser (og husk om vi måtte korrigere)
    limits, corrected = normalize_limits(
        limits_input["Rådgiver"], limits_input["Erhvervschef"], limits_input["Lokalbankdirektør"]
    )

    # 50%-reglen gælder kun for BANK-faciliteter og kun indtil første Kredit-bevilling
    half_rule_active = (product == "Bank") and (not approved_by_credit_before)
    limits_used = {k: (v/2 if half_rule_active else v) for k, v in limits.items()}

    # -------- RISIKOLÅN (Privat + Realkredit + ejerbolig/fritidshus) --------
    risk_override = False
    risk_reason = ""
    if (product == "Realkredit" and segment == "Privat" and owner_or_holiday):
        if ltv_pct is not None and debt_factor is not None:
            if (ltv_pct > 60) and (debt_factor > 4):
                risk_override = True
                risk_reason = "Privat Realkredit-lån til ejerbolig/fritidshus med LTV > 60% og gældsfaktor > 4"
        # Hvis værdier mangler, håndhæver vi ikke override; UI sikrer typisk input.

    # -------- 10-mio. passage & tillægsbeføjelse --------
    crossed = crossed_multiple_of_10m(prev_total, new_total) if approved_by_credit_before else None
    same_block = int(prev_total // 10_000_000) == int(new_total // 10_000_000)
    addon_active = approved_by_credit_before and new_total >= 20_000_000 and crossed is None and same_block

    # -------- Grund-approver (efter evt. 50%-regel) --------
    if new_total <= limits_used["Rådgiver"]:
        base_approver = "Rådgiver"
    elif new_total <= limits_used["Erhvervschef"]:
        base_approver = "Erhvervschef"
    elif new_total <= limits_used["Lokalbankdirektør"]:
        base_approver = "Lokalbankdirektør"
    else:
        base_approver = "Kredit"

    # -------- Ny erhvervskunde: fællesbevilling --------
    joint_required = False
    if (segment == "Erhverv") and new_business and (
        (new_bank_exposure > 500_000) or (group_exposure > 1_000_000)
    ):
        # Kræver rådgiver + centerledelse i fællesskab, inden for gældende beføjelser
        joint_required = True

    # -------- Endelig afgørelse i prioriteret rækkefølge --------
    if risk_override:
        approver = "Kreditpolitik & Bevilling (risikolån)"
    elif crossed is not None:
        approver = f"Kredit (pga. passeret {crossed} mio.)"
    elif addon_active:
        approver = "Erhvervschef eller Lokalbankdirektør (tillægsbeføjelse)"
    else:
        approver = base_approver

    details = {
        "limits_input": limits_input,
        "limits_used": limits_used,
        "limits_corrected": corrected,
        "half_rule_active": half_rule_active,
        "risk_override": risk_override,
        "risk_reason": risk_reason,
        "crossed_multiple": crossed,
        "addon_active": addon_active,
        "base_approver": base_approver,
        "joint_required": joint_required
    }
    return approver, details

# -------------------- UI --------------------
st.title("Bevillingsberegner")

st.markdown("Indtast **samlet engagement** før og efter ændring (ansøgning).")

c1, c2 = st.columns(2)
with c1:
    prev_total = st.number_input("Nuværende samlet engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
with c2:
    new_total = st.number_input("Fremtidigt samlet engagement (DKK) – efter ansøgning",
                                min_value=0.0, step=100_000.0, format="%.0f")

st.divider()

# Produkt & segment
c3, c4 = st.columns(2)
with c3:
    product = st.selectbox("Produkt", ["Bank", "Realkredit"])
with c4:
    segment = st.selectbox("Kundesegment", ["Privat", "Erhverv"])

# Privat + Realkredit → LTV & Gældsfaktor (ejerbolig/fritidshus)
owner_or_holiday = False
ltv_pct = None
debt_factor = None
if (product == "Realkredit") and (segment == "Privat"):
    st.markdown("**Privat Realkredit** – vurdering af risikolån i ejerbolig/fritidshus")
    c41, c42, c43 = st.columns([1,1,1])
    with c41:
        owner_or_holiday = st.checkbox("Ejerbolig/fritidshus", value=True,
                                       help="Marker hvis lånet vedrører ejerbolig eller fritidshus.")
    with c42:
        ltv_pct = st.number_input("LTV (%)", min_value=0.0, max_value=500.0, step=1.0, value=0.0)
    with c43:
        debt_factor = st.number_input("Gældsfaktor", min_value=0.0, max_value=50.0, step=0.1, value=0.0)

st.divider()

# Erhverv → Ny erhvervskunde + beløb
new_business = False
new_bank_exposure = 0.0
group_exposure = 0.0
if segment == "Erhverv":
    st.markdown("**Erhverv** – regler for nye erhvervskunder")
    c51, c52, c53 = st.columns(3)
    with c51:
        new_business = st.checkbox("Ny erhvervskunde?", value=False,
                                   help="Koncernen har ikke (eller har ikke tidligere haft) kreditengagement i Nykredit.")
    with c52:
        new_bank_exposure = st.number_input("Nyt bankengagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
    with c53:
        group_exposure = st.number_input("Koncernengagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")

st.divider()

# Kredit-historik
c6, c7 = st.columns(2)
with c6:
    approved_by_credit_before = st.checkbox(
        "Tidligere bevilget i Kredit/Regional Kredit", value=False,
        help="Aktiverer 10 mio.-spring og tillægsbeføjelse i samme 10 mio.-blok."
    )

# EGENE grænser
with st.expander("Bevillingsgrænser (kan ændres) – standard: 6 / 10 / 20 mio."):
    c8, c9, c10 = st.columns(3)
    with c8:
        lim_r = st.number_input("Rådgiver-grænse (DKK)", value=6_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with c9:
        lim_e = st.number_input("Erhvervschef-grænse (DKK)", value=10_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with c10:
        lim_l = st.number_input("Lokalbankdirektør-grænse (DKK)", value=20_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
limits_input = {"Rådgiver": lim_r, "Erhvervschef": lim_e, "Lokalbankdirektør": lim_l}

btn = st.button("Beregn bevilger", use_container_width=True)

if btn:
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement**.")
        st.stop()

    approver, info = decide_approver(
        prev_total=prev_total,
        new_total=new_total,
        limits_input=limits_input,
        product=product,
        segment=segment,
        owner_or_holiday=owner_or_holiday,
        ltv_pct=ltv_pct,
        debt_factor=debt_factor,
        approved_by_credit_before=approved_by_credit_before,
        new_business=new_business,
        new_bank_exposure=new_bank_exposure,
        group_exposure=group_exposure
    )

    if info["limits_corrected"]:
        st.warning("Grænserne var ikke stigende (Rådgiver < Erhvervschef < Lokalbankdirektør). "
                   "De er anvendt i stigende rækkefølge i beregningen.")

    st.subheader("Resultat")
    highlight = approver
    if info["joint_required"] and approver != "Kredit" and "Kreditpolitik" not in approver:
        highlight = f"{approver} — **kræver fællesbevilling (Rådgiver + centerledelse) for ny erhvervskunde**"
    st.success(f"**Bevilger:** {highlight}")

    st.markdown(
        f"""
**Nuværende engagement:** {fmt_dkk(prev_total)}  
**Fremtidigt engagement:** {fmt_dkk(new_total)}  
**Ændring:** {fmt_dkk(max(new_total - prev_total, 0))}
"""
    )

    with st.expander("Regler anvendt (detaljer)"):
        lu = info["limits_used"]
        li = info["limits_input"]
        st.markdown(
            f"""
- **50%-regel aktiv:** **{info['half_rule_active']}**  
  - *Uddybning:* Bevillingsbeføjelserne kan alene anvendes til **bankfaciliteter** med **50% af beføjelsen i 'Samlet engagement'**,
    indtil sagen **første gang** er bevilget i Kredit. Når 50%-reglen er aktiv, er grænserne halveret i beregningen nedenfor.
- **Risikolån (Privat Realkredit):** **{info['risk_override']}**{(" — " + info['risk_reason']) if info['risk_override'] else ""}  
- **Tillægsbeføjelse aktiv:** **{info['addon_active']}** (tidligere Kredit, samme 10 mio.-blok, ingen passage)  
- **Passert 10 mio. multiplum (20,30,40,…):** **{('Ja – ' + str(info['crossed_multiple']) + ' mio.') if info['crossed_multiple'] else 'Nej'}**  

- **Indtastede grænser:**  
  - Rådgiver: {fmt_dkk(li['Rådgiver'])}  
  - Erhvervschef: {fmt_dkk(li['Erhvervschef'])}  
  - Lokalbankdirektør: {fmt_dkk(li['Lokalbankdirektør'])}  

- **Grænser anvendt i beregning:**  
  - Rådgiver ≤ **{fmt_dkk(lu['Rådgiver'])}**  
  - Erhvervschef ≤ **{fmt_dkk(lu['Erhvervschef'])}**  
  - Lokalbankdirektør ≤ **{fmt_dkk(lu['Lokalbankdirektør'])}**  
  - Over dette: **Kredit**
"""
        )

    st.caption(
        "• Risikolån-reglen gælder for Privat Realkredit i ejerboliger/fritidshuse, når LTV > 60% og gældsfaktor > 4 – "
        "disse bevillinger skal ske i Kreditpolitik & Bevilling. "
        "• For nye erhvervskunder med nyt bankengagement > 500.000 kr. eller koncernengagement > 1 mio. kr. "
        "kræves fællesbevilling af rådgiver og centerledelse, inden for de gældende bevillingsbeføjelser. "
        "• 50%-reglen halverer grænserne for bankfaciliteter indtil sagen første gang er bevilget i Kredit. "
        "• Ved tidligere Kredit-bevilling skal næste bevilling ske i Kredit, når det samlede engagement passerer et multiplum af 10 mio. kr."
    )

