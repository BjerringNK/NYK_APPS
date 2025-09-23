# app.py
import math
import streamlit as st

st.set_page_config(page_title="Bevillingsberegner", page_icon="✅", layout="centered")

def fmt_dkk(x: float) -> str:
    # Dansk tusindtalsformat (punktum) uden decimaler
    return f"{x:,.0f} kr".replace(",", ".")

def determine_approver(total: float, halved: bool) -> tuple[str, dict]:
    """
    Returnerer (bevilger, detaljer).
    halved=True anvender 50%-reglen (halverede grænser).
    """
    # Grundgrænser (DKK)
    base = {
        "Rådgiver": 6_000_000,
        "Erhvervschef": 10_000_000,
        "Lokalbankdirektør": 20_000_000
        # Over dette → Kredit
    }
    # 50%-regel før første Kredit-bevilling for bankfaciliteter
    if halved:
        base = {k: v / 2 for k, v in base.items()}

    # Afgør bevilger efter (samlet) total
    if total <= base["Rådgiver"]:
        who = "Rådgiver"
    elif total <= base["Erhvervschef"]:
        who = "Erhvervschef"
    elif total <= base["Lokalbankdirektør"]:
        who = "Lokalbankdirektør"
    else:
        who = "Kredit"

    return who, {"grænser": base}

def crossed_multiple_of_10m(prev_total: float, new_total: float) -> int | None:
    """
    Returnerer hvilket multiplum af 10 mio. (>=20) der er passeret,
    hvis noget; ellers None.
    """
    ten_m = 10_000_000
    # Kun relevant fra 20 mio. og op
    if new_total < 20_000_000:
        return None
    # Find det første k ∈ {2,3,...} hvor prev < k*10 <= new
    k_max = int(new_total // ten_m)
    for k in range(2, k_max + 1):
        boundary = k * ten_m
        if prev_total < boundary <= new_total:
            return boundary // ten_m  # returnér f.eks. 20, 30, ...
    return None

st.title("Bevillingsberegner")

st.markdown("Indtast **samlet engagement** før og efter ændring (ansøgning).")

col1, col2 = st.columns(2)
with col1:
    prev_total = st.number_input(
        "Nuværende samlet engagement (DKK)",
        min_value=0.0,
        step=100_000.0,
        format="%.0f",
    )
with col2:
    new_total = st.number_input(
        "Fremtidigt samlet engagement (DKK) – efter ansøgning",
        min_value=0.0,
        step=100_000.0,
        format="%.0f",
    )

st.divider()

c1, c2 = st.columns(2)
with c1:
    is_bank_facility = st.checkbox(
        "Bankfacilitet (anvend 50%-regel før første Kredit-bevilling)",
        value=True,
        help="Gælder kun indtil sagen første gang er bevilget i Kredit.",
    )
with c2:
    approved_by_kredit_before = st.checkbox(
        "Sagen har tidligere været bevilget i Kredit/Regional Kredit",
        value=False,
        help="Hvis ja, aktiveres reglen om spring ved 10 mio.-multipla.",
    )

btn = st.button("Beregn bevilger", use_container_width=True)

if btn:
    # Basal validering
    if new_total <= 0:
        st.error("Angiv et positivt **fremtidigt samlet engagement**.")
        st.stop()

    # 50%-reglen gælder kun for bankfaciliteter og kun før første Kredit-bevilling
    use_half = is_bank_facility and not approved_by_kredit_before

    bevilger, info = determine_approver(new_total, halved=use_half)

    # 10-mio.-regel: kun hvis tidligere bevilget i Kredit OG vi passerer 20,30,40...
    crossed = None
    if approved_by_kredit_before:
        crossed = crossed_multiple_of_10m(prev_total, new_total)
        if crossed is not None:
            bevilger = "Kredit (pga. passeret " + str(crossed) + " mio.)"

    # Output
    st.subheader("Resultat")
    st.success(f"**Bevilger:** {bevilger}")

    st.markdown(
        f"""
**Nuværende engagement:** {fmt_dkk(prev_total)}  
**Fremtidigt engagement:** {fmt_dkk(new_total)}  
**Ændring:** {fmt_dkk(max(new_total - prev_total, 0))}
"""
    )

    with st.expander("Regler anvendt (detaljer)"):
        g = info["grænser"]
        st.markdown(
            f"""
- 50%-regel aktiv: **{use_half}**  
- Grænser brugt:  
  - Rådgiver ≤ **{fmt_dkk(g['Rådgiver'])}**  
  - Erhvervschef ≤ **{fmt_dkk(g['Erhvervschef'])}**  
  - Lokalbankdirektør ≤ **{fmt_dkk(g['Lokalbankdirektør'])}**  
  - Over dette: **Kredit**
- Tidligere bevilget i Kredit: **{approved_by_kredit_before}**  
- Passert 10-mio. multiplum (20,30,40,…): **{('Ja – ' + str(crossed) + ' mio.') if crossed else 'Nej'}**
"""
        )

    st.caption(
        "Bemærk: 50%-reglen gælder kun for bankfaciliteter indtil sagen første gang er bevilget i Kredit. "
        "Hvis sagen tidligere er bevilget i Kredit, skal næste bevilling gå via Kredit, når det samlede engagement passerer et multiplum af 10 mio. kr. (20, 30, 40, …)."
    )
