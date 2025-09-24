# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# ---------- Hjælp ----------
def fmt_dkk(x: float) -> str:
    return f"{x:,.0f} kr".replace(",", ".")

def crossed_multiple_of_10m(prev_total: float, new_total: float) -> int | None:
    """Returnér 20, 30, 40, … hvis et nyt 10 mio.-multiplum er passeret; ellers None."""
    ten = 10_000_000
    if new_total < 20_000_000:
        return None
    k_prev, k_new = int(prev_total // ten), int(new_total // ten)
    if k_new > k_prev and k_new >= 2:
        return k_new * 10
    return None

def normalize_limits(r: float, e: float, l: float):
    """Sørger for stigende grænser. Returnerer (limits, corrected_flag)."""
    corrected = not (r < e < l)
    vals = sorted([r, e, l])
    return {"Rådgiver": vals[0], "Erhvervschef": vals[1], "Lokalbankdirektør": vals[2]}, corrected

def decide_approver(prev_total: float,
                    new_total: float,
                    limits_input: dict,
                    is_bank_facility: bool,
                    approved_by_credit_before: bool):
    """Finder bevilger + detaljer (50%-regel, tillægsbeføjelse, passage)."""
    limits, corrected = normalize_limits(
        limits_input["Rådgiver"], limits_input["Erhvervschef"], limits_input["Lokalbankdirektør"]
    )

    # 50%-reglen: kun før første Kredit-bevilling OG kun for bankfacilitet
    half_rule_active = is_bank_facility and not approved_by_credit_before
    limits_used = {k: (v/2 if half_rule_active else v) for k, v in limits.items()}

    # Passeret nyt multiplum?
    crossed = crossed_multiple_of_10m(prev_total, new_total) if approved_by_credit_before else None

    # Tillægsbeføjelse: tidligere Kredit + 20mio+ + ingen passage + samme 10m-blok
    same_block = int(prev_total // 10_000_000) == int(new_total // 10_000_000)
    addon_active = approved_by_credit_before and new_total >= 20_000_000 and crossed is None and same_block

    # Afgør bevilger
    if crossed is not None:
        approver = f"Kredit (pga. passeret {crossed} mio.)"
    elif addon_active:
        approver = "Erhvervschef eller Lokalbankdirektør (tillægsbeføjelse)"
    else:
        if new_total <= limits_used["Rådgiver"]:
            approver = "Rådgiver"
        elif new_total <= limits_used["Erhvervschef"]:
            approver = "Erhvervschef"
        elif new_total <= limits_used["Lokalbankdirektør"]:
            approver = "Lokalbankdirektør"
        else:
            approver = "Kredit"

    return approver, {
        "limits_input": limits_input,
        "limits_used": limits_used,
        "limits_corrected": corrected,
        "half_rule_active": half_rule_active,
        "addon_active": addon_active,
        "crossed_multiple": crossed
    }

# ---------- UI ----------
st.title("Bevillingsberegner")
st.markdown("Indtast **samlet engagement** før og efter ændring (ansøgning).")

c1, c2 = st.columns(2)
with c1:
    prev_total = st.number_input("Nuværende samlet engagement (DKK)", min_value=0.0, step=100_000.0, format="%.0f")
with c2:
    new_total = st.number_input("Fremtidigt samlet engagement (DKK) – efter ansøgning",
                                min_value=0.0, step=100_000.0, format="%.0f")

st.divider()

# EGENE GRÆNSER (standard 6 / 10 / 20 mio.)
with st.expander("Bevillingsgrænser (kan ændres) – standard: 6 / 10 / 20 mio."):
    c3, c4, c5 = st.columns(3)
    with c3:
        lim_r = st.number_input("Rådgiver-grænse (DKK)", value=6_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with c4:
        lim_e = st.number_input("Erhvervschef-grænse (DKK)", value=10_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
    with c5:
        lim_l = st.number_input("Lokalbankdirektør-grænse (DKK)", value=20_000_000.0, min_value=0.0, step=100_000.0, format="%.0f")
limits_input = {"Rådgiver": lim_r, "Erhvervschef": lim_e, "Lokalbankdirektør": lim_l}

c6, c7 = st.columns(2)
with c6:
    is_bank_facility = st.checkbox("Bankfacilitet (anvend 50%-regel før første Kredit-bevilling)", value=True)
with c7:
    approved_by_credit_before = st.checkbox("Tidligere bevilget i Kredit/Regional Kredit", value=False)

btn = st.button("Beregn bevilger", use_container_width=True)

if btn:
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement**.")
        st.stop()

    approver, info = decide_approver(
        prev_total=prev_total,
        new_total=new_total,
        limits_input=limits_input,
        is_bank_facility=is_bank_facility,
        approved_by_credit_before=approved_by_credit_before
    )

    # Evt. advarsel hvis grænser blev normaliseret
    if info["limits_corrected"]:
        st.warning("Grænserne var ikke stigende (Rådgiver < Erhvervschef < Lokalbankdirektør). "
                   "De er anvendt i stigende rækkefølge i beregningen.")

    st.subheader("Resultat")
    st.success(f"**Bevilger:** {approver}")

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
- 50%-regel aktiv: **{info['half_rule_active']}**  
- Tillægsbeføjelse aktiv: **{info['addon_active']}**  
- Indtastede grænser:
  - Rådgiver: {fmt_dkk(li['Rådgiver'])}
  - Erhvervschef: {fmt_dkk(li['Erhvervschef'])}
  - Lokalbankdirektør: {fmt_dkk(li['Lokalbankdirektør'])}
- **Grænser anvendt** i beregningen:
  - Rådgiver ≤ **{fmt_dkk(lu['Rådgiver'])}**
  - Erhvervschef ≤ **{fmt_dkk(lu['Erhvervschef'])}**
  - Lokalbankdirektør ≤ **{fmt_dkk(lu['Lokalbankdirektør'])}**
  - Over dette: **Kredit**
- Passeret 10-mio. multiplum (20,30,40,…): **{('Ja – ' + str(info['crossed_multiple']) + ' mio.') if info['crossed_multiple'] else 'Nej'}**
"""
        )

    st.caption(
        "50%-reglen gælder kun for bankfaciliteter indtil sagen første gang er bevilget i Kredit. "
        "Hvis sagen tidligere er bevilget i Kredit, kan Erhvervschef eller Lokalbankdirektør anvende tillægsbeføjelser "
        "inden for samme 10 mio.-blok (20–30, 30–40, …). Passeres et multiplum af 10 mio., skal bevillingen ske via Kredit."
    )
