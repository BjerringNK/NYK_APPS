# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# ---------- Hjælp ----------
def fmt_dkk(x: float) -> str:
    return f"{x:,.0f} kr".replace(",", ".")

def fmt_mio(x_mio: float) -> str:
    return f"{x_mio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def first_crossed_multiple_of_10m(prev_total: float, new_total: float) -> int | None:
    """Første passerede 10-mio.-grænse i mio. (10, 20, 30, …), ellers None."""
    ten = 10_000_000
    k_prev = int(prev_total // ten)
    k_new  = int(new_total  // ten)
    if k_new > k_prev:
        return (k_prev + 1) * 10
    return None

def normalize_limits(r: float, e: float, l: float):
    corrected = not (r < e < l)
    vals = sorted([r, e, l])
    return {"Rådgiver": vals[0], "Erhvervschef": vals[1], "Lokalbankdirektør": vals[2]}, corrected

def choose_role_first_time(total: float, bank_amount: float, limits: dict):
    """
    Før første Kredit-bevilling: Find laveste rolle som opfylder
      A) total ≤ rolle-grænse
      B) bank_amount ≤ 50% af rolle-grænsen
    Returnér (rolle, kort_begrundelse)
    """
    for role in ["Rådgiver", "Erhvervschef", "Lokalbankdirektør"]:
        lim = limits[role]
        if total <= lim and bank_amount <= lim / 2:
            short = (f"{role} kan bevilge, da samlet engagement {fmt_dkk(total)} ≤ {fmt_dkk(lim)} "
                     f"og bankdelen {fmt_dkk(bank_amount)} ≤ {fmt_dkk(lim/2)} (50%).")
            return role, short
    return "Kredit", "Kredit: Ingen decentral rolle kan opfylde både samlet grænse og 50%-kravet for bankdelen."

def choose_role_normal(total: float, limits: dict):
    """Efter første Kredit (eller uden tillægsregler): kun total ≤ rolle-grænse. Returnér (rolle, kort_begrundelse)."""
    if total <= limits["Rådgiver"]:
        return "Rådgiver", f"Rådgiver kan bevilge, da samlet engagement {fmt_dkk(total)} ≤ {fmt_dkk(limits['Rådgiver'])}."
    if total <= limits["Erhvervschef"]:
        return "Erhvervschef", f"Erhvervschef kan bevilge, da samlet engagement {fmt_dkk(total)} ≤ {fmt_dkk(limits['Erhvervschef'])}."
    if total <= limits["Lokalbankdirektør"]:
        return "Lokalbankdirektør", f"Lokalbankdirektør kan bevilge, da samlet engagement {fmt_dkk(total)} ≤ {fmt_dkk(limits['Lokalbankdirektør'])}."
    return "Kredit", "Kredit: Samlet engagement overstiger Lokalbankdirektørs grænse."

# ---------- UI ----------
st.title("Bevillingsberegner")

# Kundesegment øverst
segment = st.selectbox("Kundesegment", ["Erhverv", "Privat", "Privat og Erhverv"])
segment_has_priv = segment in ["Privat", "Privat og Erhverv"]
segment_has_biz  = segment in ["Erhverv", "Privat og Erhverv"]

# Ny erhvervskunde (radio) – huskeregel vises kun ved 'Ja'
new_business = False
if segment_has_biz:
    nb_choice = st.radio("Ny erhvervskunde?", ["Nej", "Ja"], horizontal=True, index=0)
    new_business = (nb_choice == "Ja")
    if new_business:
        st.info(
            "Huskeregel: Bevillinger til **nye erhvervskunder** med **nyt bankengagement > 500.000 kr.** "
            "eller **koncernengagement > 1 mio. kr.** skal bevilges af **rådgiver og centerledelse i fællesskab** "
            "inden for gældende bevillingsbeføjelser."
        )

st.divider()

# Vælg faciliteter
cf1, cf2 = st.columns(2)
with cf1:
    include_bank = st.checkbox("Omfatter **Bank**-faciliteter", value=True)
with cf2:
    include_rk = st.checkbox("Omfatter **Realkredit**", value=True)

if not include_bank and not include_rk:
    st.info("Vælg mindst én facilitet: **Bank** og/eller **Realkredit** for at indtaste engagement.")
st.divider()

# Engagement pr. facilitet
prev_bank = new_bank = 0.0
prev_rk = new_rk = 0.0

if include_bank:
    st.subheader("Bank – engagement")
    b1, b2 = st.columns(2)
    with b1:
        prev_bank = st.number_input("Nuværende Bank-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
    with b2:
        new_bank = st.number_input("Fremtidigt Bank-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")

if include_rk:
    st.subheader("Realkredit – engagement")
    r1, r2 = st.columns(2)
    with r1:
        prev_rk = st.number_input("Nuværende Realkredit-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
    with r2:
        new_rk = st.number_input("Fremtidigt Realkredit-engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")

# Privat Realkredit risikovurdering
owner_or_holiday = False
ltv_pct = None
debt_factor = None
if include_rk and segment_has_priv:
    st.markdown("**Privat Realkredit – risikovurdering (ejerbolig/fritidshus)**")
    p1, p2, p3 = st.columns([1,1,1])
    with p1:
        owner_or_holiday = st.checkbox("Ejerbolig/fritidshus", value=True)
    with p2:
        ltv_pct = st.number_input("LTV (%)", min_value=0.0, max_value=500.0, step=1.0, value=0.0)
    with p3:
        debt_factor = st.number_input("Gældsfaktor", min_value=0.0, max_value=50.0, step=0.1, value=0.0)

st.divider()

# Tidligere Kredit – punktopstillede regler + 50%-regel/eksempel
approved_by_credit_before = st.checkbox(
    "Tidligere bevilget i Kredit/Regional Kredit",
    value=False,
    help=(
        "**Hvis markeret:**\n"
        "- **10 mio.-spring:** Passeres et nyt multiplum af 10 mio. i **samlet engagement** (10, 20, 30, …) → bevilling i **Kredit**.\n"
        "- **Tillægsbeføjelse:** Hvis der **ikke** passeres et multiplum, og man er i **samme 10 mio.-blok**, kan bevilges decentralt.\n"
        "  · I blok **10–<20**: **Erhvervschef (tillægsbeføjelse)**\n"
        "  · I blok **20–<30** og derover: **Lokalbankdirektør (tillægsbeføjelse)**\n\n"
        "**Hvis ikke markeret (første gang):**\n"
        "- **50%-regel (Bank):** Den godkendende rolle må højst bevilge **Bank = 50%** af rolle-beføjelsen i 'samlet engagement'.\n"
        "- **Standardgrænser:** Rådgiver 3,0 mio.; Erhvervschef 5,0 mio.; Lokalbankdirektør 10,0 mio.\n"
        "- **Eksempel:** 5,0 mio. Realkredit + 0,2 mio. Bank = 5,2 mio. samlet → Rådgiver kan bevilge (bank 0,2 ≤ 3,0)."
    ),
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

# ---------- Beregning ----------
if btn:
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement** (Bank + Realkredit).")
        st.stop()
    if not include_bank and not include_rk:
        st.error("Vælg mindst én facilitet: **Bank** og/eller **Realkredit**.")
        st.stop()

    # RISIKOLÅN (Privat Realkredit, ejer/fritid + LTV>60 & GF>4)
    risk_override = False
    if include_rk and segment_has_priv and owner_or_holiday:
        if (ltv_pct is not None and debt_factor is not None) and (ltv_pct > 60 and debt_factor > 4):
            risk_override = True

    # Afgørelse + begrundelse (kort og brugbar)
    approver = ""
    reason = ""

    # Ny erhvervskunde – fællesbevilling (brug eksisterende tal: ny bank = new_bank, "koncern" = new_total)
    joint_required = bool(segment_has_biz and new_business and (new_bank > 500_000 or new_total > 1_000_000))

    if risk_override:
        approver = "Kreditpolitik & Bevilling (risikolån)"
        reason = ("Privat Realkredit til ejer-/fritidshus med LTV > 60% og gældsfaktor > 4 "
                  "→ skal bevilges i Kreditpolitik & Bevilling.")
    else:
        if approved_by_credit_before:
            # 10-mio.-regler (starter ved 10)
            first_crossed = first_crossed_multiple_of_10m(prev_total, new_total)
            if first_crossed is not None:
                lower = fmt_mio(first_crossed - 0.01)
                upper = fmt_mio(first_crossed)
                approver = "Kredit"
                reason = (f"Nuværende {fmt_dkk(prev_total)} → fremtidigt {fmt_dkk(new_total)} passerer "
                          f"grænsen ved {upper} mio. (fra ≤ {lower} mio. til ≥ {upper} mio.) "
                          f"→ tillægsbeføjelse kan ikke anvendes.")
            else:
                # Samme 10m-blok → tillægsbeføjelse
                block = int(new_total // 10_000_000)  # 0:<10, 1:10-<20, 2:20-<30, ...
                if block >= 1:
                    if block == 1:
                        approver = "Erhvervschef (tillægsbeføjelse)"
                        reason = "Tidligere Kredit, ingen 10-mio. passage; blok 10–<20 → Erhvervschef kan bevilge (tillægsbeføjelse)."
                    else:
                        approver = "Lokalbankdirektør (tillægsbeføjelse)"
                        reason = "Tidligere Kredit, ingen 10-mio. passage; blok ≥20 → Lokalbankdirektør kan bevilge (tillægsbeføjelse)."
                else:
                    approver, reason = choose_role_normal(new_total, limits)
        else:
            # Første gang i Kredit → 50%-regel (kun Bank)
            bank_amount = new_bank if include_bank else 0.0
            approver, reason = choose_role_first_time(new_total, bank_amount, limits)

    # Sammensæt badge + evt. fællesbevilling
    badge = approver
    if joint_required and approver not in ["Kredit", "Kreditpolitik & Bevilling (risikolån)"]:
        badge = f"{approver} — **fællesbevilling påkrævet (rådgiver + centerledelse)**"

    # ---------- Output ----------
    if corrected:
        st.warning("Grænserne var ikke stigende (Rådgiver < Erhvervschef < Lokalbankdirektør). "
                   "De er anvendt i stigende rækkefølge i beregningen.")

    st.subheader("Resultat")
    st.success(f"**Bevilger:** {badge}\n\n**Begrundelse:** {reason}")

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

















