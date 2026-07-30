import streamlit as st
import pandas as pd
import plotly.express as px
import csv
import numpy as np
import io

# 1. Konfiguracja strony
st.set_page_config(page_title="Dashboard Analityczny", layout="wide")

# --- PROSTE I BEZPIECZNE LOGOWANIE ---
def check_password():
    def password_entered():
        if st.session_state["username"] in ["stach", "tata"] and st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.subheader("Zaloguj się do systemu")
        st.text_input("Login", key="username")
        st.text_input("Hasło", type="password", key="password")
        st.button("Zaloguj", on_click=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        st.subheader("Zaloguj się do systemu")
        st.text_input("Login", key="username")
        st.text_input("Hasło", type="password", key="password")
        st.button("Zaloguj", on_click=password_entered)
        st.error("😕 Błędny login lub hasło")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Przycisk wylogowania w panelu bocznym
if st.sidebar.button("Wyloguj"):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.write(f"Zalogowany użytkownik: **{st.session_state['username']}**")
st.sidebar.write("---")

# --- WŁASNY STYL CSS ---
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #16161a, #24243e, #0f0c29); }
[data-testid="stMetric"], [data-testid="stPlotlyChart"], div[data-testid="stExpander"] {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(12px);
    border-radius: 15px !important;
    border: 1px solid rgba(255, 255, 255, 0.05);
    padding: 15px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
}
h1, h2, h3, p, div, label, span { color: #e0e0e0 !important; }
.stTabs [data-baseweb="tab-list"] { gap: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.stTabs [data-baseweb="tab"] { background-color: transparent !important; border: none !important; padding: 10px 10px; }
.stTabs [aria-selected="true"] { border-bottom: 2px solid #00d2ff !important; }
</style>
""", unsafe_allow_html=True)

# 3. Wczytywanie danych
@st.cache_data
def load_data():
    df = pd.read_csv("oceny.csv", sep=";", decimal=",", quoting=csv.QUOTE_NONE, encoding="utf-8-sig")
    df.columns = [c.replace('"', '').replace('\ufeff', '') for c in df.columns]
    for col in df.columns:
        df[col] = df[col].astype(str).str.replace('"', '')
    
    df['ocena_tekst'] = df['ocena'].str.strip().str.upper()
    df['czy_zal'] = df['ocena_tekst'] == 'ZAL'
    
    df['ocena'] = df['ocena'].str.strip().replace(['nan', ''], np.nan)
    df['ocena'] = df['ocena'].str.replace(',', '.')
    df['ocena'] = pd.to_numeric(df['ocena'], errors='coerce')
    df['ects'] = df['ects'].astype(int)
    df['semestr'] = df['semestr'].astype(int)
    return df

df_pelne = load_data()
df = df_pelne[df_pelne['ocena'].notna()]
df_zal = df_pelne[df_pelne['czy_zal']]
df_przyszle = df_pelne[df_pelne['ocena'].isna() & ~df_pelne['czy_zal']].copy()

kolory_ocen = {'3.0': '#6886c5', '3.5': '#4a6fa5', '4.0': '#2b4c7e', '4.5': '#1e3d59', '5.0': '#112233'}

zakladka1, zakladka2 = st.tabs(["Panel Główny", "Symulator Przyszłości"])

with zakladka1:
    st.sidebar.title("Filtrowanie danych")
    lista_semestrow = ["Całe studia"] + [f"Semestr {s}" for s in sorted(df_pelne['semestr'].unique())]
    wybrany_zakres = st.sidebar.selectbox("Wybierz zakres do analizy:", lista_semestrow)

    if wybrany_zakres == "Całe studia":
        df_filtered = df
        df_zal_filtered = df_zal
    else:
        nr_semestru = int(wybrany_zakres.replace("Semestr ", ""))
        df_filtered = df[df['semestr'] == nr_semestru]
        df_zal_filtered = df_zal[df_zal['semestr'] == nr_semestru]

    st.title("Dashboard Ocenowy")
    st.write("---")

    suma_ects_global = df['ects'].sum() + df_zal['ects'].sum()
    cel_ects = 180
    suma_ects_filtered = df_filtered['ects'].sum() + df_zal_filtered['ects'].sum()
    
    suma_ects_do_sredniej = df_filtered['ects'].sum()
    srednia_wazona_filtered = (df_filtered['ocena'] * df_filtered['ects']).sum() / suma_ects_do_sredniej if suma_ects_do_sredniej > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        if wybrany_zakres == "Całe studia":
            st.metric("Zebrane punkty ECTS", f"{suma_ects_global} / {cel_ects}")
        else:
            st.metric(f"Zebrane ECTS ({wybrany_zakres})", f"{suma_ects_filtered}", f"Razem zdobyłeś: {suma_ects_global} / {cel_ects}")
        postep = min(suma_ects_global / cel_ects, 1.0)
        st.progress(postep, text=f"Postęp studiów: {int(postep * 100)}%")

    col2.metric(f"Średnia ważona ({wybrany_zakres})", f"{srednia_wazona_filtered:.2f}")
    col3.metric("Status", "Aktywny semestr")

    st.write("---")
    kol1, kol2 = st.columns(2)
    ustawienia_wykresu = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e0e0e0'))

    with kol1:
        st.subheader(f"Rozkład ocen ({wybrany_zakres})")
        rozklad = df_filtered['ocena'].value_counts().reset_index()
        rozklad.columns = ['Ocena', 'Liczba']
        rozklad['Ocena'] = rozklad['Ocena'].astype(str)
        if not rozklad.empty:
            wykres_kolo = px.pie(rozklad, names='Ocena', values='Liczba', hole=0.4, color='Ocena', color_discrete_map=kolory_ocen)
            wykres_kolo.update_traces(textinfo='percent+label')
            wykres_kolo.update_layout(**ustawienia_wykresu, legend=dict(font=dict(color='#e0e0e0'), orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
            st.plotly_chart(wykres_kolo, use_container_width=True)

    with kol2:
        st.subheader("Trend średniej (Całe studia)")
        srednia_semestr = df.groupby('semestr').apply(lambda x: (x['ocena'] * x['ects']).sum() / x['ects'].sum()).reset_index()
        srednia_semestr.columns = ['Semestr', 'Średnia']
        srednia_semestr['Semestr_etykieta'] = "Semestr " + srednia_semestr['Semestr'].astype(str)
        
        wykres_linia = px.line(srednia_semestr, x='Semestr_etykieta', y='Średnia', markers=True)
        wykres_linia.update_traces(line_color='#00d2ff', marker=dict(size=10, color='#3a7bd5'), fill='tozeroy', fillcolor='rgba(0, 210, 255, 0.1)')
        wykres_linia.update_layout(**ustawienia_wykresu, xaxis_title=None, yaxis=dict(range=[3.0, 5.2], gridcolor='rgba(255,255,255,0.05)'), xaxis=dict(gridcolor='rgba(255,255,255,0.05)')) 
        st.plotly_chart(wykres_linia, use_container_width=True)

with zakladka2:
    st.title("Symulator Ocen i Średniej")
    st.write("Sprawdź, jak potencjalne oceny wpłyną na Twoją średnią!")
    if df_przyszle.empty:
        st.info("Brak przedmiotów bez oceny.")
    else:
        st.write("Tutaj działa symulator.")