import streamlit as st
import pandas as pd
import plotly.express as px
import csv
import numpy as np
import io
import streamlit_authenticator as stauth

# 1. Konfiguracja strony (musi być pierwszą instrukcją Streamlita)
st.set_page_config(page_title="Dashboard Analityczny", layout="wide")

# --- BEZPIECZNE POBIERANIE DANYCH LOGOWANIA ZE SECRETS ---
try:
    names = st.secrets["credentials"]["names"]
    usernames = st.secrets["credentials"]["usernames"]
    passwords = st.secrets["credentials"]["passwords"]
except Exception:
    names = ['Stach', 'Tata']
    usernames = ['stach', 'tata']
    passwords = ['haslostacha123', 'haslotaty456']

authenticator = stauth.Authenticate(
    names,
    usernames,
    passwords,
    'panel_studiow_cookie',
    'kluczykszyfrujacytajny',
    cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login('Zaloguj się do systemu', 'main')

if authentication_status == False:
    st.error('Błędny login lub hasło')
elif authentication_status == None:
    st.warning('Wpisz swój login i hasło, aby uzyskać dostęp do panelu.')
elif authentication_status == True:

    # 2. Własny styl CSS
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #16161a, #24243e, #0f0c29); }

    [data-testid="stMetric"], [data-testid="stPlotlyChart"], div[data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 15px !important;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        overflow: hidden !important;
    }

    h1, h2, h3, p, div, label, span { color: #e0e0e0 !important; }

    /* Czysty styl zakładek */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 20px; 
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .stTabs [data-baseweb="tab"] { 
        background-color: transparent !important; 
        border: none !important;
        padding: 10px 10px; 
    }

    .stTabs [aria-selected="true"] { 
        border-bottom: 2px solid #00d2ff !important;
    }
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

    # Globalny słownik kolorów dla ocen
    kolory_ocen = {
        '3.0': '#6886c5',
        '3.5': '#4a6fa5',
        '4.0': '#2b4c7e',
        '4.5': '#1e3d59',
        '5.0': '#112233'
    }

    # ==========================================
    # FUNKCJA GENERUJĄCA RAPORT PDF (Z POLSKIMI ZNAKAMI)
    # ==========================================
    def generuj_pdf(srednia_ogolna, suma_ects, cel_ects, df_dane):
        try:
            pdfmetrics.registerFont(TTFont('ArialPL', 'C:\\Windows\\Fonts\\arial.ttf'))
            pdfmetrics.registerFont(TTFont('ArialPL-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
            font_normal = 'ArialPL'
            font_bold = 'ArialPL-Bold'
        except:
            font_normal = 'Helvetica'
            font_bold = 'Helvetica-Bold'

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        story = []
        
        styles = getSampleStyleSheet()
        
        styl_tytul = ParagraphStyle(
            'TytulRaportu',
            parent=styles['Heading1'],
            fontName=font_bold,
            fontSize=22,
            textColor=colors.HexColor('#1e3d59'),
            spaceAfter=15,
            alignment=0
        )
        styl_naglowek = ParagraphStyle(
            'NaglowekSekcji',
            parent=styles['Heading2'],
            fontName=font_bold,
            fontSize=14,
            textColor=colors.HexColor('#2b4c7e'),
            spaceBefore=15,
            spaceAfter=10
        )
        styl_tekst = ParagraphStyle(
            'TekstZwykly',
            parent=styles['Normal'],
            fontName=font_normal,
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6
        )

        story.append(Paragraph("Raport z Postępów w Studiach", styl_tytul))
        story.append(Paragraph("Oficjalne podsumowanie analityczne osiągnięć akademickich.", styl_tekst))
        story.append(Spacer(1, 10))

        status_stypendium = "Kwalifikuje się do progu stypendialnego (>= 4.5)" if srednia_ogolna >= 4.5 else "W trakcie budowania progu stypendialnego"
        
        dane_podsumowanie = [
            [Paragraph("<b>Średnia Ważona:</b>", styl_tekst), Paragraph(f"<b>{srednia_ogolna:.2f}</b>", styl_tekst)],
            [Paragraph("<b>Zdobyte ECTS:</b>", styl_tekst), Paragraph(f"<b>{suma_ects} / {cel_ects}</b>", styl_tekst)],
            [Paragraph("<b>Status:</b>", styl_tekst), Paragraph(f"<b>{status_stypendium}</b>", styl_tekst)]
        ]
        
        tabela_podsumowanie = Table(dane_podsumowanie, colWidths=[150, 350])
        tabela_podsumowanie.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f5f7fa')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#d1d8e0')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(tabela_podsumowanie)
        story.append(Spacer(1, 15))

        story.append(Paragraph("Ostatnio zrealizowane przedmioty", styl_naglowek))
        
        tabela_dane = [["Przedmiot", "Semestr", "ECTS", "Ocena"]]
        for _, row in df_dane.tail(10).iterrows():
            tabela_dane.append([str(row['przedmiot']), str(row['semestr']), str(row['ects']), str(row['ocena'])])

        tabela_dane_paragrafy = []
        for i, wiersz in enumerate(tabela_dane):
            nowy_wiersz = []
            for komorka in wiersz:
                styl_komorki = ParagraphStyle(
                    f'Komorka_{i}',
                    parent=styles['Normal'],
                    fontName=font_bold if i == 0 else font_normal,
                    fontSize=9,
                    textColor=colors.whitesmoke if i == 0 else colors.HexColor('#333333'),
                    alignment=1 if i > 0 else 0
                )
                nowy_wiersz.append(Paragraph(komorka, styl_komorki))
            tabela_dane_paragrafy.append(nowy_wiersz)
            
        tabela_przedmioty = Table(tabela_dane_paragrafy, colWidths=[240, 70, 70, 120])
        tabela_przedmioty.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b4c7e')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#ffffff')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d8e0')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(tabela_przedmioty)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    # ==========================================
    # PANEL BOCZNY I WYLOGOWANIE
    # ==========================================
    authenticator.logout('Wyloguj', 'sidebar')
    st.sidebar.write(f'Zalogowany użytkownik: **{name}**')
    st.sidebar.write("---")

    # ==========================================
    # TWORZENIE ZAKŁADEK
    # ==========================================
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

        semestry = sorted(df['semestr'].unique())
        ostatni_semestr = semestry[-1] if semestry else 0
        df_ostatni = df[df['semestr'] == ostatni_semestr]
        srednia_ostatni = (df_ostatni['ocena'] * df_ostatni['ects']).sum() / df_ostatni['ects'].sum() if not df_ostatni.empty else 0

        delta_sredniej = None
        if len(semestry) > 1:
            przedostatni_semestr = semestry[-2]
            df_przedostatni = df[df['semestr'] == przedostatni_semestr]
            srednia_przedostatni = (df_przedostatni['ocena'] * df_przedostatni['ects']).sum() / df_przedostatni['ects'].sum()
            delta_sredniej = srednia_ostatni - srednia_przedostatni

        col1, col2, col3 = st.columns(3)
        with col1:
            if wybrany_zakres == "Całe studia":
                st.metric("Zebrane punkty ECTS", f"{suma_ects_global} / {cel_ects}")
            else:
                st.metric(f"Zebrane ECTS ({wybrany_zakres})", f"{suma_ects_filtered}", f"Razem zdobyłeś: {suma_ects_global} / {cel_ects}")
            postep = min(suma_ects_global / cel_ects, 1.0)
            st.progress(postep, text=f"Postęp studiów: {int(postep * 100)}%")

        col2.metric(f"Średnia ważona ({wybrany_zakres})", f"{srednia_wazona_filtered:.2f}")

        if delta_sredniej is not None:
            col3.metric(f"Średnia (Semestr {ostatni_semestr})", f"{srednia_ostatni:.2f}", f"{delta_sredniej:.2f} względem poprzedniego")
        else:
            col3.metric(f"Średnia (Semestr {ostatni_semestr})", f"{srednia_ostatni:.2f}")

        # Przycisk pobierania PDF w panelu bocznym
        st.sidebar.write("---")
        st.sidebar.subheader("Generowanie Raportu")
        pdf_data = generuj_pdf(srednia_wazona_filtered, suma_ects_global, cel_ects, df)
        st.sidebar.download_button(
            label="Pobierz raport PDF",
            data=pdf_data,
            file_name="raport_studia.pdf",
            mime="application/pdf"
        )

        st.write("---")
        kol1, kol2 = st.columns(2)
        ustawienia_wykresu = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e0e0e0'))

        with kol1:
            st.subheader(f"Rozkład ocen ({wybrany_zakres})")
            rozklad = df_filtered['ocena'].value_counts().reset_index()
            rozklad.columns = ['Ocena', 'Liczba']
            rozklad['Ocena'] = rozklad['Ocena'].astype(str)
            if not rozklad.empty:
                wykres_kolo = px.pie(
                    rozklad, names='Ocena', values='Liczba', hole=0.4, 
                    color='Ocena', color_discrete_map=kolory_ocen
                )
                wykres_kolo.update_traces(textinfo='percent+label')
                wykres_kolo.update_layout(
                    **ustawienia_wykresu,
                    legend=dict(font=dict(color='#e0e0e0'), orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
                )
                st.plotly_chart(wykres_kolo, use_container_width=True)

        with kol2:
            st.subheader("Trend średniej (Całe studia)")
            srednia_semestr = df.groupby('semestr').apply(lambda x: (x['ocena'] * x['ects']).sum() / x['ects'].sum()).reset_index()
            srednia_semestr.columns = ['Semestr', 'Średnia']
            srednia_semestr['Semestr_etykieta'] = "Semestr " + srednia_semestr['Semestr'].astype(str)
            
            wykres_linia = px.line(srednia_semestr, x='Semestr_etykieta', y='Średnia', markers=True)
            wykres_linia.update_traces(
                line_color='#00d2ff', 
                marker=dict(size=10, color='#3a7bd5'),
                fill='tozeroy',
                fillcolor='rgba(0, 210, 255, 0.1)'
            )
            wykres_linia.update_layout(
                **ustawienia_wykresu, 
                xaxis_title=None, 
                yaxis=dict(range=[3.0, 5.2], gridcolor='rgba(255,255,255,0.05)'), 
                xaxis=dict(gridcolor='rgba(255,255,255,0.05)')
            ) 
            st.plotly_chart(wykres_linia, use_container_width=True)

        st.subheader(f"Ranking przedmiotów ({wybrany_zakres})")
        ranking = df_filtered.sort_values(by=['ocena', 'przedmiot'], ascending=[True, True]) 
        
        if not ranking.empty:
            ranking_kolory = ranking.copy()
            ranking_kolory['Ocena_kat'] = ranking_kolory['ocena'].astype(str)

            wykres_bar = px.bar(
                ranking_kolory, x='ocena', y='przedmiot', orientation='h', 
                color='Ocena_kat', color_discrete_map=kolory_ocen, 
                height=max(400, len(ranking) * 30)
            )
            wykres_bar.update_layout(
                **ustawienia_wykresu, 
                xaxis_title="Ocena", 
                yaxis_title=None, 
                xaxis=dict(range=[3.0, 5.2], gridcolor='rgba(255,255,255,0.05)'), 
                yaxis=dict(gridcolor='rgba(255,255,255,0.05)'),
                legend=dict(title="Ocena", font=dict(color='#e0e0e0'), orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
            )
            st.plotly_chart(wykres_bar, use_container_width=True)

        with st.expander("Kliknij, aby zobaczyć surowe dane"):
            df_do_tabeli = pd.concat([df_filtered, df_zal_filtered])
            st.dataframe(df_do_tabeli[['przedmiot', 'ocena_tekst', 'ects', 'semestr']].rename(columns={'ocena_tekst': 'ocena'}).sort_values(by=['semestr', 'ocena'], ascending=[True, False]), use_container_width=True)


    with zakladka2:
        st.title("Symulator Ocen i Średniej")
        st.write("Sprawdź, jak potencjalne oceny z poszczególnych przyszłych semestrów wpłyną na Twoją ogólną i cząstkową średnią!")
        
        if df_przyszle.empty:
            st.info("Nie znalazłem żadnych przedmiotów bez oceny w Twoim pliku CSV.")
        else:
            st.write("---")
            
            if st.button("Resetuj wszystkie oceny do domyślnych (4.0)"):
                for idx in df_przyszle.index:
                    st.session_state[f"suwak_{idx}"] = 4.0
                st.rerun()

            aktualna_suma_ocen = (df['ocena'] * df['ects']).sum()
            aktualna_suma_ects_do_sredniej = df['ects'].sum()
            aktualna_srednia = aktualna_suma_ocen / aktualna_suma_ects_do_sredniej if aktualna_suma_ects_do_sredniej > 0 else 0
            
            kol_sym1, kol_sym2 = st.columns([1, 1])
            
            with kol_sym1:
                st.subheader("Oczekiwane oceny według semestrów:")
                symulowane_oceny = {}
                przyszle_semestry = sorted(df_przyszle['semestr'].unique())
                
                for sem in przyszle_semestry:
                    st.markdown(f"### Semestr {sem}")
                    przedmioty_semestru = df_przyszle[df_przyszle['semestr'] == sem]
                    
                    for index, row in przedmioty_semestru.iterrows():
                        if f"suwak_{index}" not in st.session_state:
                            st.session_state[f"suwak_{index}"] = 4.0
                        
                        ocena = st.slider(f"{row['przedmiot']} (ECTS: {row['ects']})", min_value=3.0, max_value=5.0, step=0.5, key=f"suwak_{index}")
                        symulowane_oceny[index] = ocena
                    st.write("")
            
            with kol_sym2:
                st.subheader("Wynik Symulacji")
                
                przyszla_suma_ocen = sum(symulowane_oceny[idx] * df_przyszle.loc[idx, 'ects'] for idx in symulowane_oceny)
                przyszla_suma_ects = df_przyszle['ects'].sum()
                nowa_calkowita_srednia = (aktualna_suma_ocen + przyszla_suma_ocen) / (aktualna_suma_ects_do_sredniej + przyszla_suma_ects)
                roznica_calkowita = nowa_calkowita_srednia - aktualna_srednia
                
                st.metric(label="Przewidywana Średnia Końcowa (Całe studia)", 
                          value=f"{nowa_calkowita_srednia:.2f}", 
                          delta=f"{roznica_calkowita:.2f} w stosunku do obecnej")
                
                st.write("---")
                st.subheader("Wyniki cząstkowe dla przyszłych semestrów:")
                
                baza_biezaca_oceny = aktualna_suma_ocen
                baza_biezaca_ects = aktualna_suma_ects_do_sredniej
                baza_ects_global = suma_ects_global
                
                for sem in przyszle_semestry:
                    przedmioty_semestru = df_przyszle[df_przyszle['semestr'] == sem]
                    suma_ocen_sem = sum(symulowane_oceny[idx] * df_przyszle.loc[idx, 'ects'] for idx in przedmioty_semestru.index)
                    suma_ects_sem = przedmioty_semestru['ects'].sum()
                    
                    srednia_czysta_sem = suma_ocen_sem / suma_ects_sem if suma_ects_sem > 0 else 0
                    
                    baza_biezaca_oceny += suma_ocen_sem
                    baza_biezaca_ects += suma_ects_sem
                    srednia_kumulacyjna = baza_biezaca_oceny / baza_biezaca_ects if baza_biezaca_ects > 0 else 0
                    
                    roznica_kumulacyjna = srednia_kumulacyjna - aktualna_srednia
                    
                    baza_ects_global += suma_ects_sem
                    
                    st.markdown(f"**Semestr {sem}**")
                    k1, k2 = st.columns(2)
                    k1.metric(f"Średnia z semestru {sem}", f"{srednia_czysta_sem:.2f}")
                    
                    k2.metric(f"Średnia po semestrze {sem}", f"{srednia_kumulacyjna:.2f}", f"{roznica_kumulacyjna:.2f} względem obecnej")
                    st.markdown(f"<span style='color: #888888; font-size: 0.85em;'>Łączne ECTS po semestrze {sem}: {baza_ects_global} / {cel_ects}</span>", unsafe_allow_html=True)
                    st.write("")

                if nowa_calkowita_srednia >= 4.5:
                    st.success("Z takimi ocenami osiągasz próg stypendialny (4.5)!")
                else:
                    st.warning("Brakuje do progu stypendialnego wynoszącego 4.5.")