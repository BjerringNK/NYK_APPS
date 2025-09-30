# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# ---------- Hjælp ----------
def fmt_dkk(x: float) -> str:
    return f"{x:,.0f} kr".replace(",", ".")

def fmt_mio(x_mio: float) -> str:
    return f"{x_mio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def first_crossed_multiple_of_10m(prev_total: float, new_total: float) -> int | None:
    """
    Returnér første passerede 10-mio.-grænse i mio. (10, 20, 30, …),
    hvis samlet engagement krydser en sådan grænse; ellers None.
    """
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

def choose_role_first_time_explain(total: float, bank_amount: float, limits: dict):
    """
    Første gang (aldrig i Kredit): vælg LAVESTE rolle, der opfylder
      A) total ≤ rolle-grænse
      B) bank_amount ≤ 50% af rolle-grænsen
    Returnerer (rolle, begrundelseslinjer)
    """
    lines = []
    for role in ["Rådgiver", "Erhvervschef", "Lokalbankdirektør"]:
        lim = limits[role]
        a = total <= lim
        b = bank_amount <= lim / 2
        lines.append(
            f"{role}: A) samlet {fmt_dkk(total)} ≤ {fmt_dkk(lim)} = {a}; "
            f"B) bank {fmt_dkk(bank_amount)} ≤ {fmt_dkk(lim/2)} (50%) = {b}."
        )
        if a and b:
            lines.insert(0, f"{role} kan bevilge, da både A og B er opfyldt.")
            return role, lines
    lines.insert(0, "Ingen decentral rolle kan opfylde både A og B → Kredit.")
    return "Kredit", lines

def choose_role_normal_explain(total: float, limits: dict):
    """
    Efter første Kredit (eller ikke under tillægsregler): kun A) total ≤ rolle-grænse.
    Returnerer (rolle, begrundelseslinjer)
    """
    lines = [
        f"Samlet engagement {fmt_dkk(total)} sammenholdes med grænserne:"
        f" Rådgiver {fmt_dkk(limits['Rådgiver'])}, "
        f"Erhvervschef {fmt_dkk(limits['Erhvervschef'])}, "
        f"Lokalbankdirektør {fmt_dkk(limits['Lokalbankdirektør'])}."
    ]
    if total <= limits["Rådgiver"]:
        lines.append("Rådgiver kan bevilge, da samlet engagement er under/lig Rådgiver-grænsen.")
        return "Rådgiver", lines
    if total <= limits["Erhvervschef"]:
        lines.append("Erhvervschef kan bevilge, da samlet engagement er under/lig Erhvervschef-grænsen.")
        return "Erhvervschef", lines
    if total <= limits["Lokalbankdirektør"]:
        lines.append("Lokalbankdirektør kan bevilge, da samlet engagement er under/lig LBD-grænsen.")
        return "Lokalbankdirektør", lines
    lines.append("Ingen decentral grænse kan rumme totalen → Kredit.")
    return "Kredit", lines

# ---------- UI ----------
st.title("Bevillingsberegner")

# Kundesegment øverst
segment = st.selectbox("Kundesegment", ["Erhverv", "Privat", "Privat og Erhverv"])
segment_has_priv = segment in ["Privat", "Privat og Erhverv"]
segment_has_biz  = segment in ["Erhverv", "Privat og Erhverv"]

# Ny erhvervskunde (radio)
new_business = False
if segment_has_biz:
    nb_choice = st.radio("Ny erhvervskunde?", ["Nej", "Ja"], horizontal=True, index=0)
    new_business = (nb_choice == "Ja")
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

    # Privat Realkredit risikolån (override)
    risk_override = False
    risk_reason = ""
    if include_rk and segment_has_priv and owner_or_holiday:
        if (ltv_pct is not None and debt_factor is not None) and (ltv_pct > 60 and debt_factor > 4):
            risk_override = True
            risk_reason = "Privat Realkredit til ejer-/fritidshus med LTV > 60% og gældsfaktor > 4"

    reason_lines = []  # forklaring til resultat
    joint_required = False
    first_crossed = None
    addon_active = False
    approver = ""

    # Ny erhvervskunde – logik: hvis Ja og (bank > 500k eller samlet > 1m) → fællesbevilling
    if segment_has_biz and new_business:
        if (include_bank and new_bank > 500_000) or (new_total > 1_000_000):
            joint_required = True
            reason_lines.append(
                "Ny erhvervskunde: bankdelen over 500.000 kr. eller samlet engagement over 1 mio. kr. "
                "→ fællesbevilling (rådgiver + centerledelse) kræves."
            )
        else:
            reason_lines.append("Ny erhvervskunde: under tærsklerne for fællesbevilling.")

    if risk_override:
        approver = "Kreditpolitik & Bevilling (risikolån)"
        reason_lines.insert(0, risk_reason + " → skal bevilges i Kreditpolitik & Bevilling.")
    else:
        if approved_by_credit_before:
            # 10-mio.-regler (starter ved 10)
            first_crossed = first_crossed_multiple_of_10m(prev_total, new_total)
            if first_crossed is not None:
                approver = "Kredit"
                lower = fmt_mio(first_crossed - 0.01)
                upper = fmt_mio(first_crossed)
                reason_lines.insert(
                    0,
                    f"Nuværende {fmt_dkk(prev_total)} → fremtidigt {fmt_dkk(new_total)} "
                    f"passerer grænsen ved {upper} mio. (fra ≤ {lower} mio. til ≥ {upper} mio.) "
                    f"→ tillægsbeføjelse kan ikke anvendes."
                )
            else:
                # Samme 10m-blok → tillægsbeføjelse
                block = int(new_total // 10_000_000)  # 0:<10, 1:10-<20, 2:20-<30, ...
                if block >= 1:
                    addon_active = True
                    if block == 1:
                        approver = "Erhvervschef (tillægsbeføjelse)"
                        reason_lines.insert(0, "Tidligere Kredit: ingen 10-mio.-passage; blok 10–<20 → Erhvervschef (tillægsbeføjelse).")
                    else:
                        approver = "Lokalbankdirektør (tillægsbeføjelse)"
                        reason_lines.insert(0, "Tidligere Kredit: ingen 10-mio.-passage; blok ≥20 → Lokalbankdirektør (tillægsbeføjelse).")
                else:
                    approver, lines = choose_role_normal_explain(new_total, limits)
                    reason_lines = lines + reason_lines
        else:
            # Første gang i Kredit → 50%-regel (kun Bank)
            bank_amount = new_bank if include_bank else 0.0
            approver, lines = choose_role_first_time_explain(new_total, bank_amount, limits)
            reason_lines = lines + reason_lines

    # ---------- Output ----------
    if corrected:
        st.warning("Grænserne var ikke stigende (Rådgiver < Erhvervschef < Lokalbankdirektør). "
                   "De er anvendt i stigende rækkefølge i beregningen.")

    st.subheader("Resultat")
    badge = approver
    if joint_required and approver not in ["Kredit", "Kreditpolitik & Bevilling (risikolån)"]:
        badge = f"{approver} — **fællesbevilling påkrævet (rådgiver + centerledelse)**"
    st.success(f"**Bevilger:** {badge}")

    st.markdown("#### Logik bag afgørelsen")
    st.markdown("\n".join([f"- {line}" for line in reason_lines]))

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
















