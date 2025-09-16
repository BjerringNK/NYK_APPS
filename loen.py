# -*- coding: utf-8 -*-
import streamlit as st

st.set_page_config(page_title="Lønkommentering – POC", page_icon="🤖", layout="wide")
st.title("Lønkommentering – Proof of Concept")

# ---------- Hjælpere ----------
def fmt_int_dots(x: int) -> str:
    return f"{int(x):,}".replace(",", ".")

def rj(width: int, s: str) -> str:
    return f"{s:>{width}}"

# ---------- Hardcodede defaults ----------
defaults = {
    # Stamdata (hardcoded)
    "kundenavn": "Hans",
    "virksomhedstype": "VSO",
    "virksomhedsnavn": "Hans VSO",

    # Nuværende
    "loen_nuv_tkr": 588,
    "kilde_nuv": "eSKAT",
    "info_nuv": "",

    # Fremtidigt (label ændret til 'Fremtidigt lønudtræk')
    "loen_frem_tekst_tkr": 611,            # var 'topskat'; nu brugt som fremtidigt lønudtræk
    "kilde_frem": "dialog med kunde",
    "info_frem": "",

    # Cashflow (tal til tabellen)
    "ebitda_tkr": 1230,
    "loen_frem_tkr": 611,
    "rente_tkr": 33,
    "skat_tkr": 129,
    "afdrag_tkr": 300,
    "info_cf": "",

    # Formue
    "egenkapital_vso_tkr": 1719,
    "udskudt_pct": 50,
    # note flyttet hertil:
    "info_formue": "Værdien vurderes reel og består af opsparet overskud",

    # Nederst
    "tilfoejet_af": "ADB",
    "dato": "15.09.2025",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------- UI ----------
st.subheader("Stamdata")
c1, c2, c3 = st.columns([1.2, 0.8, 1.2])
with c1:
    st.session_state.kundenavn = st.text_input("Kundenavn", st.session_state.kundenavn)
with c2:
    st.session_state.virksomhedstype = st.selectbox(
        "Virksomhedstype", ["VSO", "ApS", "Både VSO og ApS"],
        index=["VSO","ApS","Både VSO og ApS"].index(st.session_state.virksomhedstype)
    )
with c3:
    st.session_state.virksomhedsnavn = st.text_input("Virksomhedsnavn", st.session_state.virksomhedsnavn)

st.divider()

st.subheader("INDKOMST FRA ERHVERV TIL NUVÆRENDE BUDGET")
c1, c2 = st.columns([1, 1])
with c1:
    st.session_state.loen_nuv_tkr = st.number_input("Lønudtræk (t.kr.)", min_value=0, value=int(st.session_state.loen_nuv_tkr), step=1)
with c2:
    st.session_state.kilde_nuv = st.selectbox("Kilde", ["Kundens regnskab", "Dialog med kunden", "eSKAT"],
                                              index=["Kundens regnskab","Dialog med kunden","eSKAT"].index(st.session_state.kilde_nuv))
st.session_state.info_nuv = st.text_area("Yderligere info – Nuværende indkomst", st.session_state.info_nuv, height=140)

st.divider()

st.subheader("INDKOMST FRA ERHVERV TIL FREMTIDIGT BUDGET")
c1, c2 = st.columns([1, 1])
with c1:
    # label ændret som ønsket
    st.session_state.loen_frem_tekst_tkr = st.number_input("Fremtidigt lønudtræk (t.kr.)", min_value=0,
                                                           value=int(st.session_state.loen_frem_tekst_tkr), step=1)
with c2:
    st.session_state.kilde_frem = st.text_input("Kilde (tekst)", st.session_state.kilde_frem)
st.session_state.info_frem = st.text_area("Yderligere info – Fremtidigt budget", st.session_state.info_frem, height=140)

st.divider()

st.subheader("Budgetteret fremtidigt cashflow (tal)")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.session_state.ebitda_tkr = st.number_input("EBITDA (t.kr.)", min_value=0, value=int(st.session_state.ebitda_tkr), step=1)
with c2:
    st.session_state.loen_frem_tkr = st.number_input("Lønudtræk (t.kr.)", min_value=0, value=int(st.session_state.loen_frem_tkr), step=1)
with c3:
    st.session_state.rente_tkr = st.number_input("Renteudgift (t.kr.)", min_value=0, value=int(st.session_state.rente_tkr), step=1)
with c4:
    st.session_state.skat_tkr = st.number_input("Skat (t.kr.)", min_value=0, value=int(st.session_state.skat_tkr), step=1)
with c5:
    st.session_state.afdrag_tkr = st.number_input("Afdrag (t.kr.)", min_value=0, value=int(st.session_state.afdrag_tkr), step=1)
st.session_state.info_cf = st.text_area("Yderligere info – Cashflow", st.session_state.info_cf, height=140)

st.divider()

st.subheader("FORMUE FRA ERHVERV")
c1, c2 = st.columns([1, 1])
with c1:
    st.session_state.egenkapital_vso_tkr = st.number_input("Egenkapital i VSO (t.kr.)", min_value=0, value=int(st.session_state.egenkapital_vso_tkr), step=1)
with c2:
    st.session_state.udskudt_pct = st.number_input("Udskudt skat (%)", min_value=0, max_value=100, value=int(st.session_state.udskudt_pct), step=1)
# note er fjernet; teksten ligger her:
st.session_state.info_formue = st.text_area("Yderligere info – Formue", st.session_state.info_formue, height=140)

st.divider()

# Nederst: Tilføjet af + Dato (lige før knap)
c1, c2 = st.columns([1, 1])
with c1:
    st.session_state.tilfoejet_af = st.text_input("Tilføjet af", st.session_state.tilfoejet_af)
with c2:
    st.session_state.dato = st.text_input("Dato (dd.mm.åååå)", st.session_state.dato)

# ---------- Knap & output ----------
output_key = "generated_text_content"

if st.button("Lav lønkommentering", type="primary"):
    total_cf = (int(st.session_state.ebitda_tkr)
                - int(st.session_state.loen_frem_tkr)
                - int(st.session_state.rente_tkr)
                - int(st.session_state.skat_tkr)
                - int(st.session_state.afdrag_tkr))
    udskudt_belob = round(int(st.session_state.egenkapital_vso_tkr) * int(st.session_state.udskudt_pct) / 100)

    # Tekst præcis som i din specifikation + bundlinje
    tekst = (
        "INDKOMST FRA ERHVERV TIL NUVÆRENDE BUDGET:  \n"
        f"{st.session_state.kundenavn} har indkomst fra sin virksomhed {st.session_state.virksomhedstype} "
        f"hvorfra {st.session_state.kundenavn} har lønudtræk på t.kr. {fmt_int_dots(st.session_state.loen_nuv_tkr)} baseret på {st.session_state.kilde_nuv} \n \n"
        "INDKOMST FRA ERHVERV TIL FREMTIDIGT BUDGET:  \n"
        f"I det fremtidige budget er lønudtræk til topskattegrænsen medtaget igen på {fmt_int_dots(st.session_state.loen_frem_tekst_tkr)} t.kr. baseret på {st.session_state.kilde_frem}. \n \n"
        "På baggrund af det fremtidigt budgetterede cashflow, baseret på indkomst fra 2024  \n"
        "fremgår det, at der en er mulighed for at øge lønudtrækket.  \n \n"
        f"Budgetteret Fremtidigt Cashflow {st.session_state.virksomhedsnavn}: \n"
        f"EBIDTA:{rj(22,'')}+ {rj(5, fmt_int_dots(st.session_state.ebitda_tkr))} \n"
        f"Lønudtræk:{rj(17,'')}- {rj(5, fmt_int_dots(st.session_state.loen_frem_tkr))} \n"
        f"Renteudgift:{rj(17,'')}- {rj(5, fmt_int_dots(st.session_state.rente_tkr))} \n"
        f"Skat:{rj(30,'')}- {rj(5, fmt_int_dots(st.session_state.skat_tkr))} \n"
        f"Afdrag:{rj(25,'')}- {rj(5, fmt_int_dots(st.session_state.afdrag_tkr))} \n"
        "---------------------------------- \n"
        f"I alt:{rj(29,'')}+ {rj(5, fmt_int_dots(total_cf))} \n \n"
        "FORMUE FRA ERHVERV, HERUNDER UDSKUDT SKAT: \n"
        f"Egenkapitalen i VSO udgør {fmt_int_dots(st.session_state.egenkapital_vso_tkr)} tkr, hvormed der efter afledt udskudt skat på "
        f"{int(st.session_state.udskudt_pct)}% kunne medtages {fmt_int_dots(udskudt_belob)} tkr. {st.session_state.info_formue} \n \n"
        f"Tilføjet af {st.session_state.tilfoejet_af} d. {st.session_state.dato}"
    )

    st.session_state[output_key] = tekst
    st.text_area("Resultat", value=tekst, height=620)

elif output_key in st.session_state:
    st.text_area("Resultat", value=st.session_state[output_key], height=620)
