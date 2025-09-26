# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# ------------- Hjælpefunktioner -------------
def fmt_dkk(x: float) -> str:
    return f"{x:,.0f} kr".replace(",", ".")

def fmt_mio(x_mio: float) -> str:
    """Formatér mio.-tal med dansk decimal-komma, fx 29,99"""
    return f"{x_mio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def first_crossed_multiple_of_10m(prev_total: float, new_total: float) -> int | None:
    """
    Returnér den FØRSTE passerede grænse i mio. (20, 30, 40, …),
    hvis samlet engagement krydser et 10-mio.-multiplum; ellers None.
    """
    ten = 10_000_000
    if new_total < 20_000_000:
        return None
    k_prev = int(prev_total // ten)
    k_new  = int(new_total  // ten)
    if k_new > k_prev and k_new >= 2:
        # første passerede grænse er (k_prev+1)*10 mio.
        return (k_prev + 1) * 10
    return None

def normalize_limits(r: float, e: float, l: float):
    corrected = not (r < e < l)
    vals = sorted([r, e, l])
    return {"Rådgiver": vals[0], "Erhvervschef": vals[1], "Lokalbankdirektør": vals[2]}, corrected

def choose_role_first_time(total: float, bank_amount: float, limits: dict) -> str:
    """
    Første gang (aldrig i Kredit): vælg LAVESTE rolle, der opfylder:
      A) total ≤ role_limit
      B) bank_amount ≤ role_limit / 2
    Ellers eskaler. Hvis ingen opfylder, → Kredit.
    """
    for role in ["Rådgiver", "Erhvervschef", "Lokalbankdirektør"]:
        lim = limits[role]
        if total <= lim and bank_amount <= lim / 2:
            return role
    return "Kredit"

def choose_role_normal(total: float, limits: dict) -> str:
    if total <= limits["Rådgiver"]:
        return "Rådgiver"
    if total <= limits["Erhvervschef"]:
        return "Erhvervschef"
    if total <= limits["Lokalbankdirektør"]:
        return "Lokalbankdirektør"
    return "Kredit"

# ------------- UI -------------
st.title("Bevillingsberegner")

# Vælg faciliteter
cf1, cf2 = st.columns(2)
with cf1:
    include_bank = st.checkbox("Omfatter **Bank**-faciliteter", value=True)
with cf2:
    include_rk = st.checkbox("Omfatter **Realkredit**", value=True)

if not include_bank and not include_rk:
    st.info("Vælg mindst én facilitet: **Bank** og/eller **Realkredit** for at indtaste engagement.")
st.divider()

# Kundesegment
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

# Privat Realkredit risikovurdering
owner_or_holiday = False
ltv_pct = None
debt_factor = None
if include_rk and segment == "Privat":
    st.markdown("**Privat Realkredit – risikovurdering (ejerbolig/fritidshus)**")
    r1, r2, r3 = st.columns([1,1,1])
    with r1:
        owner_or_holiday = st.checkbox("Ejerbolig/fritidshus", value=True)
    with r2:
        ltv_pct = st.number_input("LTV (%)", min_value=0.0, max_value=500.0, step=1.0, value=0.0)
    with r3:
        debt_factor = st.number_input("Gældsfaktor", min_value=0.0, max_value=50.0, step=0.1, value=0.0)

st.divider()

# Tidligere Kredit – punktopstillede regler + 50%-regel/eksempel
approved_by_credit_before = st.checkbox(
    "Tidligere bevilget i Kredit/Regional Kredit",
    value=False,
    help=(
        "• Hvis markeret:\n"
        "   – 10 mio.-spring: Passeres et nyt multiplum af 10 mio. i **samlet engagement** (20, 30, 40, …), skal bevillingen ske i **Kredit**.\n"
        "   – Tillægsbeføjelse: Hvis der **ikke** passeres et multiplum, og man er i **samme 10 mio.-blok** (fx 21→25), kan **Erhvervschef eller Lokalbankdirektør** bevilge.\n"
        "• Hvis **ikke** markeret (første gang):\n"
        "   – **50%-regel for Bank**: Den godkendende rolle må højst bevilge **Bank = 50%** af rolle-beføjelsen i 'samlet engagement'.\n"
        "   – Standardgrænser ⇒ Rådgiver 3,0 mio., Erhvervschef 5,0 mio., Lokalbankdirektør 10,0 mio.\n"
        "   – Eksempel: 5,0 mio. Realkredit + 0,2 mio. Bank = 5,2 mio. samlet → Rådgiver kan bevilge (bank 0,2 ≤ 3,0)."
    )
)

# Huskenote for Erhverv
if segment == "Erhverv":
    st.info(
        "Huskeregel (ikke en del af beregningen): Bevillinger til **nye erhvervskunder** med "
        "**nyt bankengagement > 500.000 kr.** eller **koncernengagement > 1 mio. kr.** "
        "skal bevilges af **rådgiver og centerledelse i fællesskab** inden for gældende bevillingsbeføjelser."
    )

# Grænser (kan ændres)
with st.expander("Bevillingsgrænser (kan ændres) – standard: 6 / 10 / 20 mio."):
    g1, g2, g3 = st.columns(3)
    with g1:
        lim_r = st.number_input("Rådgiver-grænse (DKK)", value=6_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with g2:
        lim_e = st.number_input("Erhvervschef-grænse (DKK)", value=10_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with g3:
        lim_l = st.number_input("Lokalbankdirektør-grænse (DKK)", value=20_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
limits, corrected = normalize_limits(lim_r, lim_e, lim_l)

# Samlet engagement
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

# ------------- Beregning -------------
if btn:
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement** (Bank + Realkredit).")
        st.stop()
    if not include_bank and not include_rk:
        st.error("Vælg mindst én facilitet: **Bank** og/eller **Realkredit**.")
        st.stop()

    # RISIKOLÅN (Privat Realkredit, ejer/fritid + LTV>60 & GF>4)
    risk_override = False
    risk_reason = ""
    if include_rk and segment == "Privat" and owner_or_holiday:
        if (ltv_pct is not None and debt_factor is not None) and (ltv_pct > 60 and debt_factor > 4):
            risk_override = True
            risk_reason = "Privat Realkredit til ejer-/fritidshus med LTV > 60% og gældsfaktor > 4"

    if risk_override:
        approver = "Kreditpolitik & Bevilling (risikolån)"
        first_crossed = None
        addon_active = False
        crossing_reason = ""
    else:
        # Tidligere Kredit → 10m-spring og tillægsbeføjelse
        first_crossed = first_crossed_multiple_of_10m(prev_total, new_total) if approved_by_credit_before else None
        same_block = int(prev_total // 10_000_000) == int(new_total // 10_000_000)
        addon_active = approved_by_credit_before and new_total >= 20_000_000 and first_crossed is None and same_block

        if approved_by_credit_before and first_crossed is not None:
            approver = "Kredit"
            lower = fmt_mio(first_crossed - 0.01)
            upper = fmt_mio(first_crossed)
            crossing_reason = (
                f"Årsag: Nuværende engagement {fmt_dkk(prev_total)} → fremtidigt {fmt_dkk(new_total)} "
                f"passerer grænsen ved {upper} mio. (fra ≤ {lower} mio. til ≥ {upper} mio.). "
                "Tillægsbeføjelse kan derfor ikke anvendes; bevillingen skal ske i Kredit."
            )
        elif approved_by_credit_before and addon_active:
            approver = "Erhvervschef eller Lokalbankdirektør (tillægsbeføjelse)"
            crossing_reason = "Årsag: Ingen 10 mio.-passage og samme 10 mio.-blok – tillægsbeføjelse kan anvendes."
        else:
            # Første gang i Kredit (eller ikke omfattet af tillægsregler)
            bank_amount = new_bank if include_bank else 0.0
            if not approved_by_credit_before:
                approver = choose_role_first_time(new_total, bank_amount, limits)
            else:
                approver = choose_role_normal(new_total, limits)
            crossing_reason = ""

    # ------------- Output -------------
    if corrected:
        st.warning("Grænserne var ikke stigende (Rådgiver < Erhvervschef < Lokalbankdirektør). "
                   "De er anvendt i stigende rækkefølge i beregningen.")

    st.subheader("Resultat")
    st.success(f"**Bevilger:** {approver}")

    if risk_override:
        st.warning(f"Årsag: {risk_reason}.")
    elif approved_by_credit_before and first_crossed is not None:
        st.warning(crossing_reason)

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
**Første gang (ikke tidligere i Kredit):**
- 50%-regel (kun Bank) aktiv: **{half_rule_active}**
- Fortolkning: Den godkendende rolle må højst bevilge **Bank** svarende til **50%** af rolle-beføjelsen i 'samlet engagement'.
  Ved standardgrænser: Rådgiver ≤ **3,0 mio.**, Erhvervschef ≤ **5,0 mio.**, Lokalbankdirektør ≤ **10,0 mio.**.

**Tidligere bevilget i Kredit/Regional Kredit:**
- 10 mio.-spring (første passerede grænse): **{('Ja – ' + fmt_mio(first_crossed) + ' mio. (fra ≤ ' + fmt_mio(first_crossed - 0.01) + ' mio.)') if (approved_by_credit_before and first_crossed) else 'Nej'}**
- Tillægsbeføjelse (samme 10 mio.-blok, ingen passage): **{addon_active if approved_by_credit_before else False}**

**Privat Realkredit – risikolån:** **{risk_override}**{(' — ' + risk_reason) if risk_override else ''}

**Anvendte grænser:**
- Rådgiver ≤ **{fmt_dkk(limits['Rådgiver'])}**
- Erhvervschef ≤ **{fmt_dkk(limits['Erhvervschef'])}**
- Lokalbankdirektør ≤ **{fmt_dkk(limits['Lokalbankdirektør'])}**
- Over dette: **Kredit**
"""
        )

    st.caption(
        "• Bevilger fastlægges ud fra **samlet fremtidigt engagement** (Bank + Realkredit). "
        "• Før første Kredit-bevilling må **Bank-delen** maksimalt udgøre **50% af den godkendende rolle-beføjelse**. "
        "• Ved tidligere Kredit-bevilling: Passeres den **første** 10 mio.-grænse (fx 30 mio. – dvs. fra ≤ 29,99 til ≥ 30,00), "
        "kan tillægsbeføjelsen **ikke** anvendes og bevillingen skal ske i **Kredit**; "
        "ellers (samme 10 mio.-blok) kan **Erhvervschef eller Lokalbankdirektør** anvende tillægsbeføjelse. "
        "• Privat Realkredit med **LTV > 60%** og **gældsfaktor > 4** (ejer-/fritidshus) skal bevilges af **Kredit København**."
    )










