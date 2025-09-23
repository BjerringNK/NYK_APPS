# app.py
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

# ---------- Hjælpefunktioner ----------
def fmt_dkk(x: float) -> str:
    """Dansk tusindtalsformat med punktum og uden decimaler."""
    return f"{x:,.0f} kr".replace(",", ".")

def crossed_multiple_of_10m(prev_total: float, new_total: float) -> int | None:
    """
    Returner størrelsen (20, 30, 40, …) hvis et multiplum af 10 mio. er passeret,
    ellers None. Kun relevant fra 20 mio. og op.
    """
    ten_m = 10_000_000
    if new_total < 20_000_000:
        return None
    k_prev = int(prev_total // ten_m)
    k_new = int(new_total // ten_m)
    if k_new > k_prev and k_new >= 2:  # 2*10=20 mio. eller højere
        return k_new * 10
    return None

def decide_approver(prev_total: float,
                    new_total: float,
                    is_bank_facility: bool,
                    approved_by_credit_before: bool):
    """
    Beregn bevilger samt detalje-flags:
    - 50%-regel aktiv (kun før første Kredit + bankfacilitet)
    - Tillægsbeføjelse aktiv (tidligere Kredit, 20mio+ blok, og ingen 10mio-passage)
    - Hvilket multiplum der evt. blev passeret
    """
    # 50%-regel kun før første Kredit-bevilling og kun for bankfaciliteter
    half_rule_active = is_bank_facility and not approved_by_credit_before

    # Grænser (halveres hvis 50%-regel)
    limits = {
        "Rådgiver": 6_000_000,
        "Erhvervschef": 10_000_000,
        "Lokalbankdirektør": 20_000_000
    }
    if half_rule_active:
        limits = {k: v / 2 for k, v in limits.items()}

    # Har vi passeret et nyt multiplum af 10 mio. siden sidste total?
    crossed = None
    if approved_by_credit_before:
        crossed = crossed_multiple_of_10m(prev_total, new_total)

    # Tillægsbeføjelse: tidligere Kredit + i samme 10m-blok (og 20mio+)
    same_block = int(prev_total // 10_000_000) == int(new_total // 10_000_000)
    addon_active = approved_by_credit_before and new_total >= 20_000_000 and crossed is None and same_block

    # Afgør bevilger
    if crossed is not None:
        approver = f"Kredit (pga. passeret {crossed} mio.)"
    elif addon_active:
        # Overstyrer normal 20m-grænse når vi er i samme blok efter tidligere Kredit
        approver = "Erhvervschef eller Lokalbankdirektør (tillægsbeføjelse)"
    else:
        # Normal afgørelse på baggrund af (evt. halverede) grænser
        if new_total <= limits["Rådgiver"]:
            approver = "Rådgiver"
        elif new_total <= limits["Erhvervschef"]:
            approver = "Erhvervschef"
        elif new_total <= limits["Lokalbankdirektør"]:
            approver = "Lokalbankdirektør"
        else:
            approver = "Kredit"

    details = {
        "limits": limits,
        "half_rule_active": half_rule_active,
        "addon_active": addon_active,
        "crossed_multiple": crossed
    }
    return approver, details

# ---------- UI ----------
st.title("Bevillingsberegner")
st.markdown("Indtast **samlet engagement** før og efter ændring (ansøgning).")

c1, c2 = st.columns(2)
with c1:
    prev_total = st.number_input(
        "Nuværende samlet engagement (DKK)",
        min_value=0.0,
        step=100_000.0,
        format="%.0f",
        value=0.0
    )
with c2:
    new_total = st.number_input(
        "Fremtidigt samlet engagement (DKK) – efter ansøgning",
        min_value=0.0,
        step=100_000.0,
        format="%.0f",
        value=0.0
    )

st.divider()

c3, c4 = st.columns(2)
with c3:
    is_bank_facility = st.checkbox(
        "Bankfacilitet (anvend 50%-regel før første Kredit-bevilling)",
        value=True,
        help="Gælder kun indtil sagen første gang er bevilget i Kredit."
    )
with c4:
    approved_by_credit_before = st.checkbox(
        "Sagen har tidligere været bevilget i Kredit/Regional Kredit",
        value=False,
        help="Aktiverer regler om 10 mio.-spring og tillægsbeføjelse i samme 10 mio.-blok."
    )

btn = st.button("Beregn bevilger", use_container_width=True)

if btn:
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement**.")
        st.stop()

    approver, info = decide_approver(
        prev_total=prev_total,
        new_total=new_total,
        is_bank_facility=is_bank_facility,
        approved_by_credit_before=approved_by_credit_before
    )

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
        lim = info["limits"]
        st.markdown(
            f"""
- 50%-regel aktiv: **{info['half_rule_active']}**  
- Tillægsbeføjelse aktiv: **{info['addon_active']}**  
- Grænser brugt:
  - Rådgiver ≤ **{fmt_dkk(lim['Rådgiver'])}**
  - Erhvervschef ≤ **{fmt_dkk(lim['Erhvervschef'])}**
  - Lokalbankdirektør ≤ **{fmt_dkk(lim['Lokalbankdirektør'])}**
  - Over dette: **Kredit**
- Passert 10-mio. multiplum (20,30,40,…): **{('Ja – ' + str(info['crossed_multiple']) + ' mio.') if info['crossed_multiple'] else 'Nej'}**
"""
        )

    st.caption(
        "50%-reglen gælder kun for bankfaciliteter indtil sagen første gang er bevilget i Kredit. "
        "Hvis sagen tidligere er bevilget i Kredit, kan Erhvervschef eller Lokalbankdirektør anvende tillægsbeføjelsen "
        "inden for samme 10 mio.-blok (20–30, 30–40, …). Passeres et multiplum af 10 mio., skal bevillingen ske via Kredit."
    )
