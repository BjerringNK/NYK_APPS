# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# ---------------- Hjælp ----------------
def fmt_dkk(x: float) -> str:
    return f"{x:,.0f} kr".replace(",", ".")

def crossed_multiple_of_10m(prev_total: float, new_total: float):
    """Returnér (20, 30, …) hvis et nyt 10 mio.-multiplum i samlet engagement er passeret; ellers None."""
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

def choose_role_first_time(total: float, bank_amount: float, limits: dict) -> str:
    """
    Før første Kredit-bevilling:
    Vælg den laveste rolle, der opfylder:
      A) total <= role_limit
      B) bank_amount <= role_limit / 2
    Ellers eskaler til næste rolle. Hvis ingen, returnér 'Kredit'.
    """
    for role in ["Rådgiver", "Erhvervschef", "Lokalbankdirektør"]:
        lim = limits[role]
        if total <= lim and bank_amount <= lim / 2:
            return role
    return "Kredit"

def choose_role_normal(total: float, limits: dict) -> str:
    """Efter første Kredit-bevilling (eller hvis bank-reglen ikke er relevant): kun A) total <= role_limit."""
    if total <= limits["Rådgiver"]:
        return "Rådgiver"
    if total <= limits["Erhvervschef"]:
        return "Erhvervschef"
    if total <= limits["Lokalbankdirektør"]:
        return "Lokalbankdirektør"
    return "Kredit"

# ---------------- UI ----------------
st.title("Bevillingsberegner")

# Vælg faciliteter
col_fac1, col_fac2 = st.columns(2)
with col_fac1:
    include_bank = st.checkbox("Omfatter **Bank**-faciliteter", value=True)
with col_fac2:
    include_rk = st.checkbox("Omfatter **Realkredit**", value=True)

if not include_bank and not include_rk:
    st.info("Vælg mindst én facilitet: **Bank** og/eller **Realkredit** for at indtaste engagement.")
st.divider()

# Segment
segment = st.selectbox("Kundesegment", ["Privat", "Erhverv"])

# Engagement pr. facilitet
prev_bank = new_bank = 0.0
prev_rk = new_rk = 0.0

if include_bank:
    st.subheader("Bank – engagement")
    cb1, cb2 = st.columns(2)
    with cb1:
        prev_bank = st.number_input("Nuværende Bank-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
    with cb2:
        new_bank = st.number_input("Fremtidigt Bank-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")

if include_rk:
    st.subheader("Realkredit – engagement")
    cr1, cr2 = st.columns(2)
    with cr1:
        prev_rk = st.number_input("Nuværende Realkredit-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
    with cr2:
        new_rk = st.number_input("Fremtidigt Realkredit-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")

# Privat Realkredit risikologik
owner_or_holiday = False
ltv_pct = None
debt_factor = None
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

# Tidligere Kredit
approved_by_credit_before = st.checkbox(
    "Tidligere bevilget i Kredit/Regional Kredit",
    value=False,
    help=(
        "Aktiverer 10 mio.-spring og tillægsbeføjelse i samme 10 mio.-blok.\n\n"
        "Hvis kunden ikke tidligere er bevilget i Kredit, gælder 50%-reglen for bankfaciliteter: "
        "Der kan decentralt bevilges bank op til 50% af den pågældende rolle-beføjelse i 'samlet engagement', "
        "før sagen første gang skal bevilges i Regional Kredit eller Kreditpolitik & Bevilling.\n"
        "Eksempel: Rådgiver-grænse 6 mio. → bank op til 3 mio.; Erhvervschef 10 mio. → 5 mio.; "
        "Lokalbankdirektør 20 mio. → 10 mio. "
        "(fx 5,0 mio. Realkredit + 0,2 mio. Bank = 5,2 mio. samlet → Rådgiver kan bevilge, fordi bankdelen 0,2 ≤ 3,0)."
    )
)

# Huskenote for Erhverv (kun tekst – ikke logik)
if segment == "Erhverv":
    st.info(
        "Huskeregel (ikke en del af beregningen): "
        "Bevillinger til **nye erhvervskunder** med **nyt bankengagement > 500.000 kr.** eller "
        "**koncernengagement > 1 mio. kr.** skal bevilges af **rådgiver og centerledelse i fællesskab** "
        "inden for gældende bevillingsbeføjelser."
    )

# Grænser (kan ændres)
with st.expander("Bevillingsgrænser (kan ændres) – standard: 6 / 10 / 20 mio."):
    c8, c9, c10 = st.columns(3)
    with c8:
        lim_r = st.number_input("Rådgiver-grænse (DKK)", value=6_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with c9:
        lim_e = st.number_input("Erhvervschef-grænse (DKK)", value=10_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with c10:
        lim_l = st.number_input("Lokalbankdirektør-grænse (DKK)", value=20_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")

limits, corrected = normalize_limits(lim_r, lim_e, lim_l)

# Samlede totals
prev_total = (prev_bank if include_bank else 0) + (prev_rk if include_rk else 0)
new_total  = (new_bank  if include_bank else 0) + (new_rk  if include_rk else 0)

st.markdown(
    f"""
**Samlet – nuværende:** {fmt_dkk(prev_total)}  
**Samlet – fremtidigt:** {fmt_dkk(new_total)}  
**Ændring:** {fmt_dkk(max(new_total - prev_total, 0))}
"""
)

btn = st.button("Beregn bevilger", use_container_width=True)

# ---------------- Beregning ----------------
if btn:
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement** (Bank + Realkredit).")
        st.stop()
    if not include_bank and not include_rk:
        st.error("Vælg mindst én facilitet: **Bank** og/eller **Realkredit**.")
        st.stop()

    # RISIKOLÅN override (Privat Realkredit, ejer/fritid + LTV>60 & GF>4)
    risk_override = False
    risk_reason = ""
    if include_rk and segment == "Privat" and owner_or_holiday:
        if ltv_pct is not None and debt_factor is not None and ltv_pct > 60 and debt_factor > 4:
            risk_override = True
            risk_reason = "Privat Realkredit-lån til ejer-/fritidshus med LTV > 60% og gældsfaktor > 4"

    if risk_override:
        approver = "Kreditpolitik & Bevilling (risikolån)"
        crossed = None
        addon_active = False
    else:
        # Tidligere Kredit → tjek 10 mio.-spring og tillægsbeføjelse
        crossed = crossed_multiple_of_10m(prev_total, new_total) if approved_by_credit_before else None
        same_block = int(prev_total // 10_000_000) == int(new_total // 10_000_000)
        addon_active = approved_by_credit_before and new_total >= 20_000_000 and crossed is None and same_block

        if approved_by_credit_before and crossed is not None:
            approver = f"Kredit (pga. passeret {crossed} mio.)"
        elif approved_by_credit_before and addon_active:
            approver = "Erhvervschef eller Lokalbankdirektør (tillægsbeføjelse)"
        else:
            # Første gang i Kredit (eller <20 mio. efter tidligere Kredit) → normal udvælgelse
            if not approved_by_credit_before:
                bank_amount = new_bank if include_bank else 0.0
                approver = choose_role_first_time(new_total, bank_amount, limits)
            else:
                approver = choose_role_normal(new_total, limits)

    # Output
    if corrected:
        st.warning("Grænserne var ikke stigende (Rådgiver < Erhvervschef < Lokalbankdirektør). "
                   "De er anvendt i stigende rækkefølge i beregningen.")

    st.subheader("Resultat")
    st.success(f"**Bevilger:** {approver}")

    st.markdown(
        f"""
### Engagement-opdeling
- **Bank:** nuværende {fmt_dkk(prev_bank)} → fremtidigt {fmt_dkk(new_bank)}{' (valgt)' if include_bank else ''}  
- **Realkredit:** nuværende {fmt_dkk(prev_rk)} → fremtidigt {fmt_dkk(new_rk)}{' (valgt)' if include_rk else ''}

### Samlet
- **Nuværende:** {fmt_dkk(prev_total)}
- **Fremtidigt:** {fmt_dkk(new_total)}
- **Ændring:** {fmt_dkk(max(new_total - prev_total, 0))}
"""
    )

    with st.expander("Regler anvendt (detaljer)"):
        half_rule_active = (not approved_by_credit_before) and include_bank
        st.markdown(
            f"""
- **50%-regel (kun før første Kredit, kun Bank) aktiv:** **{half_rule_active}**  
  - *Fortolkning:* For den rolle, der godkender, må **Bank-delen** højst være **50% af rolle-beføjelsen**.  
    Ved standardgrænser giver det: Rådgiver ≤ **3,0 mio.**, Erhvervschef ≤ **5,0 mio.**, Lokalbankdirektør ≤ **10,0 mio.**.
- **Privat Realkredit – risikolån:** **{risk_override}**{(" — " + risk_reason) if risk_override else ""}  
- **Tidligere Kredit – passeret 10-mio. multiplum (20, 30, 40, …):** **{('Ja – ' + str(crossed) + ' mio.') if (approved_by_credit_before and crossed) else 'Nej'}**  
- **Tillægsbeføjelse aktiv:** **{addon_active if approved_by_credit_before else False}**  

- **Grænser anvendt:**  
  - Rådgiver ≤ **{fmt_dkk(limits['Rådgiver'])}**  
  - Erhvervschef ≤ **{fmt_dkk(limits['Erhvervschef'])}**  
  - Lokalbankdirektør ≤ **{fmt_dkk(limits['Lokalbankdirektør'])}**  
  - Over dette: **Kredit**
"""
        )

    st.caption(
        "• Bevilger findes ud fra **samlet fremtidigt engagement** (Bank + Realkredit). "
        "• Før første Kredit-bevilling gælder, at **Bank-delen** højst må være **50% af den godkendende rolle-beføjelse**. "
        "• Ved tidligere Kredit-bevilling: Passeres et multiplum af 10 mio. kr., skal bevillingen ske i **Kredit**; ellers kan "
        "**Erhvervschef eller Lokalbankdirektør** anvende tillægsbeføjelse i samme 10-mio.-blok. "
        "• Privat Realkredit med **LTV > 60%** og **gældsfaktor > 4** (ejer-/fritidshus) bevilges i **Kreditpolitik & Bevilling**. "
        "• For **Erhverv** vises “ny erhvervskunde”-reglen kun som huskeregel (ikke del af beregningen)."
    )






