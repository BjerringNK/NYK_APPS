# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# ---------------- Hjælp ----------------
def fmt_dkk(x: float) -> str:
    return f"{x:,.0f} kr".replace(",", ".")

def crossed_multiple_of_10m(prev_total: float, new_total: float):
    """Returnér (20, 30, ...), hvis et nyt 10 mio.-multiplum er passeret; ellers None."""
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

ROLE_ORDER = ["Rådgiver", "Erhvervschef", "Lokalbankdirektør", "Kredit"]

def max_role(a: str | None, b: str | None) -> str | None:
    if a is None: return b
    if b is None: return a
    return a if ROLE_ORDER.index(a) >= ROLE_ORDER.index(b) else b

def base_role(total: float, limits: dict) -> str:
    if total <= limits["Rådgiver"]:
        return "Rådgiver"
    if total <= limits["Erhvervschef"]:
        return "Erhvervschef"
    if total <= limits["Lokalbankdirektør"]:
        return "Lokalbankdirektør"
    return "Kredit"

# ---------------- UI ----------------
st.title("Bevillingsberegner")
st.markdown("Indtast **samlet engagement** før og efter ændring (ansøgning).")

c1, c2 = st.columns(2)
with c1:
    prev_total = st.number_input("Nuværende samlet engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
with c2:
    new_total = st.number_input("Fremtidigt samlet engagement (DKK) – efter ansøgning",
                                min_value=0.0, step=100_000.0, format="%.0f")

st.divider()

# Valg: Bank og/eller Realkredit
c0, c00 = st.columns(2)
with c0:
    include_bank = st.checkbox("Omfatter **BANK**-faciliteter", value=True)
with c00:
    include_rk = st.checkbox("Omfatter **REALkredit**", value=False)

# Segment
c3, c4 = st.columns(2)
with c3:
    segment = st.selectbox("Kundesegment", ["Privat", "Erhverv"])

# Privat + Realkredit -> risikulogik
owner_or_holiday, ltv_pct, debt_factor = False, None, None
if include_rk and segment == "Privat":
    st.markdown("**Privat Realkredit – risikovurdering (ejerbolig/fritidshus)**")
    c41, c42, c43 = st.columns([1,1,1])
    with c41:
        owner_or_holiday = st.checkbox("Ejerbolig/fritidshus", value=True)
    with c42:
        ltv_pct = st.number_input("LTV (%)", min_value=0.0, max_value=500.0, step=1.0, value=0.0)
    with c43:
        debt_factor = st.number_input("Gældsfaktor", min_value=0.0, max_value=50.0, step=0.1, value=0.0)

st.divider()

# Erhverv -> ny kunde + beløb
new_business, new_bank_exposure, group_exposure = False, 0.0, 0.0
if segment == "Erhverv":
    st.markdown("**Erhverv – regler for nye erhvervskunder**")
    c51, c52, c53 = st.columns(3)
    with c51:
        new_business = st.checkbox("Ny erhvervskunde?", value=False,
                                   help="Koncernen har ikke (eller tidligere haft) kreditengagement i Nykredit.")
    with c52:
        new_bank_exposure = st.number_input("Nyt bankengagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
    with c53:
        group_exposure = st.number_input("Koncernengagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")

st.divider()

# Kredit-historik
approved_by_credit_before = st.checkbox(
    "Tidligere bevilget i Kredit/Regional Kredit", value=False,
    help="Aktiverer 10 mio.-spring og tillægsbeføjelse i samme 10 mio.-blok."
)

# Egne grænser
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

# ---------------- Beregning ----------------
if btn:
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement**.")
        st.stop()
    if not include_bank and not include_rk:
        st.error("Vælg mindst én facilitet: **Bank** og/eller **Realkredit**.")
        st.stop()

    limits, corrected = normalize_limits(limits_input["Rådgiver"], limits_input["Erhvervschef"], limits_input["Lokalbankdirektør"])

    # 50%-regel: kun BANK og kun før første Kredit-bevilling
    half_rule_active = include_bank and (not approved_by_credit_before)
    bank_limits_used = {k: (v/2 if half_rule_active else v) for k, v in limits.items()}
    rk_limits_used   = limits.copy()  # Realkredit halveres ikke

    # BANK-rolle (hvis valgt)
    bank_role = base_role(new_total, bank_limits_used) if include_bank else None
    # REALKREDIT-rolle (hvis valgt)
    rk_role   = base_role(new_total, rk_limits_used) if include_rk else None

    # RISIKOLÅN override (Privat Realkredit, ejer/fritid + LTV>60 & GF>4)
    risk_override = False
    risk_reason = ""
    if include_rk and segment == "Privat" and owner_or_holiday:
        if ltv_pct is not None and debt_factor is not None and ltv_pct > 60 and debt_factor > 4:
            risk_override = True
            risk_reason = "Privat Realkredit-lån til ejer-/fritidshus med LTV > 60% og gældsfaktor > 4"

    # 10-mio. passage & tillægsbeføjelse
    crossed = crossed_multiple_of_10m(prev_total, new_total) if approved_by_credit_before else None
    same_block = int(prev_total // 10_000_000) == int(new_total // 10_000_000)
    addon_active = approved_by_credit_before and new_total >= 20_000_000 and crossed is None and same_block

    # Kombiner Bank/Realkredit (strengeste)
    combined_base = max_role(bank_role, rk_role)

    # Endelig afgørelse (prioritet: risikolån > 10m passage > tillægsbeføjelse > kombineret base)
    if risk_override:
        approver = "Kreditpolitik & Bevilling (risikolån)"
    elif crossed is not None:
        approver = f"Kredit (pga. passeret {crossed} mio.)"
    elif addon_active:
        approver = "Erhvervschef eller Lokalbankdirektør (tillægsbeføjelse)"
    else:
        approver = combined_base

    # Ny erhvervskunde: krav om fællesbevilling
    joint_required = False
    if segment == "Erhverv" and (new_business := st.session_state.get("nb", None)) is None:
        # (streamlit checkbox-værdier kan hentes direkte; vi gemmer blot ikke i session)
        pass
    if segment == "Erhverv":
        new_business_flag = new_business if 'new_business' in locals() else False
        new_business_flag = st.session_state.get("new_business", new_business_flag)
        # reelt er 'new_business' fra ovenfor
        new_business_flag = new_business
        if new_business_flag and ((new_bank_exposure > 500_000) or (group_exposure > 1_000_000)):
            joint_required = True

    # --------- Resultat ----------
    if corrected:
        st.warning("Grænserne var ikke stigende (Rådgiver < Erhvervschef < Lokalbankdirektør). "
                   "De er anvendt i stigende rækkefølge i beregningen.")

    st.subheader("Resultat")
    highlight = approver
    if joint_required and approver not in ["Kredit", "Kredit (pga. passeret 20 mio.)", "Kreditpolitik & Bevilling (risikolån)"]:
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
        st.markdown(
            f"""
- Valgte faciliteter: **Bank = {include_bank}**, **Realkredit = {include_rk}**
- **50%-regel aktiv (Bank):** **{half_rule_active}**  
  - *Forklaring:* Bevillingsbeføjelserne kan **kun** anvendes til **bankfaciliteter** med **50% af beføjelsen i 'Samlet engagement'**, 
    indtil sagen **første gang** er bevilget i Kredit. Når aktiv, er bank-grænserne halveret i beregningen.
- **Risikolån (Privat Realkredit):** **{risk_override}**{(" — " + risk_reason) if risk_override else ""}  
- **Passert 10 mio. multiplum (20, 30, 40, …):** **{('Ja – ' + str(crossed) + ' mio.') if crossed else 'Nej'}**
- **Tillægsbeføjelse aktiv:** **{addon_active}** (tidligere Kredit, samme 10-mio.-blok, ingen passage)

**Bank – anvendte grænser:** {('Rådgiver ' + fmt_dkk(bank_limits_used['Rådgiver']) + ', Erhvervschef ' + fmt_dkk(bank_limits_used['Erhvervschef']) + ', Lokalbankdirektør ' + fmt_dkk(bank_limits_used['Lokalbankdirektør'])) if include_bank else '—'}  
**Bank – grundresultat:** {bank_role if include_bank else '—'}

**Realkredit – anvendte grænser:** {('Rådgiver ' + fmt_dkk(rk_limits_used['Rådgiver']) + ', Erhvervschef ' + fmt_dkk(rk_limits_used['Erhvervschef']) + ', Lokalbankdirektør ' + fmt_dkk(rk_limits_used['Lokalbankdirektør'])) if include_rk else '—'}  
**Realkredit – grundresultat:** {rk_role if include_rk else '—'}

**Kombineret grundresultat (strengeste af Bank/Realkredit):** {combined_base}
"""
        )

    st.caption(
        "• 50%-reglen halverer grænserne for **bankfaciliteter** indtil sagen første gang er bevilget i Kredit. "
        "• Ved **tidligere Kredit-bevilling** skal næste bevilling ske i **Kredit**, hvis det samlede engagement passerer et multiplum af 10 mio. kr. "
        "(20, 30, 40, …). Passeres ikke, kan **Erhvervschef eller Lokalbankdirektør** anvende tillægsbeføjelsen i samme 10-mio.-blok. "
        "• **Privat Realkredit** med LTV>60% og gældsfaktor>4 for ejer-/fritidshus bevilges i **Kreditpolitik & Bevilling**. "
        "• **Ny erhvervskunde** med nyt bankengagement > 500.000 kr. eller koncernengagement > 1 mio. kr. kræver **fællesbevilling** (rådgiver + centerledelse)."
    )



