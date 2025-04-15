import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime
import warnings
import random
import json
import requests
from io import StringIO

# Warnungen unterdrücken
warnings.simplefilter(action='ignore', category=FutureWarning)

# Seitenkonfiguration
st.set_page_config(
    page_title="Food Trends Deutschland",
    page_icon="🍔",
    layout="wide"
)

# Titel und Beschreibung
st.title("Food Trends Deutschland")
st.markdown("Entdecke die neuesten Lebensmitteltrends in Deutschland")

# Sidebar für Eingaben
with st.sidebar:
    st.header("Einstellungen")

    # Datenquelle auswählen - Standardmäßig Beispieldaten verwenden
    datenquelle = st.radio(
        "Datenquelle auswählen",
        ["Beispieldaten", "Google Trends API"]
    )

    if datenquelle == "Google Trends API":
        st.warning("""
        **Hinweis zu API-Limits:**
        Google begrenzt die Anzahl der Anfragen. Bei Fehlern:
        1. Verwende Beispieldaten
        2. Wähle einen längeren Zeitraum
        """)

    # Lebensmittelkategorien
    lebensmittel_kategorien = {
        "Beliebte Küchen": ["Italienisches Essen", "Chinesisches Essen", "Deutsches Essen"],
        "Diät-Trends": ["Vegane Ernährung", "Keto Diät", "Paleo Diät"],
        "Beliebte Zutaten": ["Avocado", "Quinoa", "Kurkuma"],
        "Desserts": ["Käsekuchen", "Tiramisu", "Eis"],
        "Getränke": ["Kaffee", "Bubble Tea", "Smoothie"]
    }

    ausgewählte_kategorie = st.selectbox(
        "Lebensmittelkategorie auswählen",
        list(lebensmittel_kategorien.keys())
    )

    # Zeitraum auswählen
    zeitraum_optionen = {
        "Letzter Monat": "today 1-m",
        "Letzte 3 Monate": "today 3-m",
        "Letztes Jahr": "today 12-m"
    }
    ausgewählter_zeitraum = st.selectbox(
        "Zeitraum auswählen",
        list(zeitraum_optionen.keys())
    )

# Deutsche Bundesländer mit ISO-Codes und IDs
bundeslaender = {
    "DE-BW": {"name": "Baden-Württemberg", "id": 0},
    "DE-BY": {"name": "Bayern", "id": 1},
    "DE-BE": {"name": "Berlin", "id": 2},
    "DE-BB": {"name": "Brandenburg", "id": 3},
    "DE-HB": {"name": "Bremen", "id": 4},
    "DE-HH": {"name": "Hamburg", "id": 5},
    "DE-HE": {"name": "Hessen", "id": 6},
    "DE-MV": {"name": "Mecklenburg-Vorpommern", "id": 7},
    "DE-NI": {"name": "Niedersachsen", "id": 8},
    "DE-NW": {"name": "Nordrhein-Westfalen", "id": 9},
    "DE-RP": {"name": "Rheinland-Pfalz", "id": 10},
    "DE-SL": {"name": "Saarland", "id": 11},
    "DE-SN": {"name": "Sachsen", "id": 12},
    "DE-ST": {"name": "Sachsen-Anhalt", "id": 13},
    "DE-SH": {"name": "Schleswig-Holstein", "id": 14},
    "DE-TH": {"name": "Thüringen", "id": 15}
}

# Funktion zum Laden der GeoJSON-Daten für Deutschland
@st.cache_data
def load_germany_geojson():
    # GeoJSON für deutsche Bundesländer
    url = "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/main/2_bundeslaender/4_niedrig.geo.json"
    response = requests.get(url)
    geojson = json.loads(response.text)

    # Füge IDs hinzu für einfachere Zuordnung
    for feature in geojson['features']:
        state_name = feature['properties']['name']
        # Finde den ISO-Code für diesen Bundeslandnamen
        iso_code = next((code for code, data in bundeslaender.items()
                         if data['name'] == state_name), None)
        if iso_code:
            feature['id'] = iso_code

    return geojson

# Funktion zum Generieren von Beispieldaten für Deutschland
def beispieldaten_generieren(keywords, zeitraum):
    # Erstelle einen Datumsbereich basierend auf dem ausgewählten Zeitraum
    if "1-m" in zeitraum:
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
    elif "3-m" in zeitraum:
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
    else:  # 12-m
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=52, freq='W')

    # Erstelle Beispieldaten für das Interesse über Zeit
    daten = {}
    for keyword in keywords:
        # Generiere zufällige Trenddaten mit einigen Mustern
        basis = np.random.randint(30, 70)
        trend = np.random.normal(basis, 15, size=len(datumsbereich))
        # Stelle sicher, dass die Werte zwischen 0 und 100 liegen
        trend = np.clip(trend, 0, 100)
        daten[keyword] = trend

    interesse_über_zeit = pd.DataFrame(daten, index=datumsbereich)

    # Erstelle Beispieldaten für das Interesse nach Bundesland
    regionsdaten = {}
    for keyword in keywords:
        # Generiere zufällige Werte für jedes Bundesland
        regionsdaten[keyword] = [np.random.randint(0, 100) for _ in range(len(bundeslaender))]

    # Erstelle DataFrame mit Bundesland-Codes als Index
    interesse_nach_region = pd.DataFrame(
        regionsdaten,
        index=pd.Series(list(bundeslaender.keys()), name='iso_alpha')
    )
    # Füge Bundeslandnamen hinzu
    interesse_nach_region['bundesland'] = interesse_nach_region.index.map(
        lambda x: bundeslaender[x]['name'] if x in bundeslaender else x
    )

    return interesse_über_zeit, interesse_nach_region

# Funktion zum Abrufen von Daten aus der Google Trends API mit Kompatibilitätslösung
@st.cache_data(ttl=3600)
def trends_daten_abrufen(keywords, zeitraum):
    try:
        # Importiere pytrends
        from pytrends.request import TrendReq

        # Lösung für das method_whitelist / allowed_methods Problem
        # Erstelle eine eigene Session mit korrekten Retry-Parametern
        import requests
        from requests.adapters import HTTPAdapter

        # Prüfe, welche Version von urllib3 verwendet wird
        import urllib3
        session = requests.Session()

        try:
            # Versuche mit dem neuen Parameter (urllib3 >= 2.0.0)
            retry_strategy = urllib3.Retry(
                total=3,
                backoff_factor=1,
                allowed_methods=["GET", "POST"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
        except TypeError:
            # Fallback für ältere Versionen (urllib3 < 2.0.0)
            retry_strategy = urllib3.Retry(
                total=3,
                backoff_factor=1,
                method_whitelist=["GET", "POST"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Initialisiere pytrends mit der angepassten Session
        pytrends = TrendReq(
            hl='de-DE',
            timeout=(10, 30),
            tz=360,
            requests_args={'verify': True}
        )

        # Baue die Payload - Auf Deutschland beschränken
        geo = "DE"

        # Füge zufällige Verzögerung hinzu, um Rate-Limiting zu vermeiden
        time.sleep(random.uniform(1.0, 3.0))

        pytrends.build_payload(
            kw_list=keywords,
            cat=71,  # Lebensmittel & Getränke Kategorie
            timeframe=zeitraum,
            geo=geo
        )

        # Füge zufällige Verzögerung hinzu
        time.sleep(random.uniform(1.5, 3.5))

        # Hole das Interesse über Zeit
        interesse_über_zeit = pytrends.interest_over_time()

        # Hole das Interesse nach Region (Bundesländer)
        try:
            # Füge zufällige Verzögerung hinzu
            time.sleep(random.uniform(1.5, 3.5))

            # Hole Daten für deutsche Bundesländer
            interesse_nach_region_raw = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True)

            # Mapping von Google Trends Regionennamen zu ISO-Codes
            region_to_iso = {
                "Baden-Württemberg": "DE-BW",
                "Bayern": "DE-BY",
                "Berlin": "DE-BE",
                "Brandenburg": "DE-BB",
                "Bremen": "DE-HB",
                "Hamburg": "DE-HH",
                "Hessen": "DE-HE",
                "Mecklenburg-Vorpommern": "DE-MV",
                "Niedersachsen": "DE-NI",
                "Nordrhein-Westfalen": "DE-NW",
                "Rheinland-Pfalz": "DE-RP",
                "Saarland": "DE-SL",
                "Sachsen": "DE-SN",
                "Sachsen-Anhalt": "DE-ST",
                "Schleswig-Holstein": "DE-SH",
                "Thüringen": "DE-TH"
            }

            # Erstelle neue DataFrame mit ISO-Codes
            interesse_nach_region = pd.DataFrame(index=interesse_nach_region_raw.index)
            for col in interesse_nach_region_raw.columns:
                interesse_nach_region[col] = interesse_nach_region_raw[col]

            # Konvertiere Regionenindex zu ISO-Codes
            interesse_nach_region['iso_alpha'] = interesse_nach_region.index.map(
                lambda x: region_to_iso.get(x, "")
            )
            interesse_nach_region = interesse_nach_region.set_index('iso_alpha')
            interesse_nach_region['bundesland'] = interesse_nach_region.index.map(
                lambda x: bundeslaender[x]['name'] if x in bundeslaender else x
            )

        except Exception as e:
            st.warning(f"Konnte regionales Interesse nicht abrufen: {str(e)}")
            # Fallback zu Beispieldaten für die Region
            _, interesse_nach_region = beispieldaten_generieren(keywords, zeitraum)

        return interesse_über_zeit, interesse_nach_region
    except Exception as e:
        st.error(f"Fehler beim Abrufen der Trends-Daten: {str(e)}")
        return pd.DataFrame(), pd.DataFrame()

# Hole die Keywords für die ausgewählte Kategorie
keywords = lebensmittel_kategorien[ausgewählte_kategorie]

# Hole die Daten
with st.spinner(f"Lade {'Beispiel' if datenquelle == 'Beispieldaten' else 'Trends'}-Daten..."):
    if datenquelle == "Google Trends API":
        # Versuche, die Daten abzurufen, mit Fallback zu Beispieldaten
        interesse_über_zeit, interesse_nach_region = trends_daten_abrufen(
            keywords,
            zeitraum_optionen[ausgewählter_zeitraum]
        )
        # Fallback zu Beispieldaten, wenn keine Daten gefunden wurden
        if interesse_über_zeit.empty:
            st.warning("""
            Keine Daten von Google Trends gefunden oder API-Fehler aufgetreten.
            Zeige Beispieldaten stattdessen. Versuche es später erneut.
            """)
            interesse_über_zeit, interesse_nach_region = beispieldaten_generieren(
                keywords,
                zeitraum_optionen[ausgewählter_zeitraum]
            )
    else:
        interesse_über_zeit, interesse_nach_region = beispieldaten_generieren(
            keywords,
            zeitraum_optionen[ausgewählter_zeitraum]
        )

# Zeige die Daten an
if not interesse_über_zeit.empty:
    # Erstelle Tabs für verschiedene Visualisierungen
    tab1, tab2 = st.tabs(["Trend über Zeit", "Regionales Interesse"])

    with tab1:
        st.subheader("Interesse über Zeit")

        # Plotte das Interesse über Zeit
        fig = px.line(
            interesse_über_zeit,
            x=interesse_über_zeit.index,
            y=keywords,
            title=f"Interesse über Zeit in Deutschland ({ausgewählter_zeitraum})",
            labels={"value": "Interesse (0-100)", "variable": "Lebensmittel", "index": "Datum"}
        )
        fig.update_traces(line=dict(width=3))
        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            font=dict(family="Arial", size=12),
            plot_bgcolor="rgba(240, 240, 240, 0.5)",
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Erklärungstext in Klammern unterhalb des Graphen
        st.markdown("""
        *(So liest du diesen Graphen: Der Graph zeigt das relative Suchinteresse für die ausgewählten Lebensmittel über Zeit.
        Die Y-Achse (Interesse) reicht von 0 bis 100, wobei 100 das höchste Interesse darstellt.
        Die X-Achse zeigt den ausgewählten Zeitraum. Jede Linie repräsentiert einen Suchbegriff.
        Höhere Werte bedeuten mehr Interesse.)*
        """)

        # Zeige aktuelle Werte
        st.subheader("Aktuelle Werte")

        cols = st.columns(len(keywords))
        for i, keyword in enumerate(keywords):
            with cols[i]:
                if keyword in interesse_über_zeit.columns and len(interesse_über_zeit) > 1:
                    latest_value = interesse_über_zeit[keyword].iloc[-1]
                    previous_value = interesse_über_zeit[keyword].iloc[-2]
                    st.metric(
                        label=keyword,
                        value=int(latest_value),
                        delta=int(latest_value - previous_value)
                    )
                else:
                    st.metric(
                        label=keyword,
                        value="N/A"
                    )

        # Erklärungstext in Klammern unterhalb der Metriken
        st.markdown("""
        *(Was bedeuten diese Zahlen: Der aktuelle Wert zeigt das aktuelle Interesse am Suchbegriff (0-100).
        Die Veränderung zeigt, wie sich das Interesse im Vergleich zum vorherigen Zeitpunkt verändert hat.
        Negative Werte (rot) bedeuten abnehmendes Interesse, positive Werte (grün) bedeuten zunehmendes Interesse.)*
        """)

    with tab2:
        st.subheader("Regionales Interesse in Deutschland")

        # Erstelle ein Dropdown zur Auswahl des Keywords
        selected_keyword = st.selectbox(
            "Lebensmittel auswählen, um regionales Interesse anzuzeigen",
            keywords
        )

        # Prüfe, ob Daten für das ausgewählte Keyword vorhanden sind
        if selected_keyword in interesse_nach_region.columns:
            # Lade GeoJSON für Deutschland
            geojson_data = load_germany_geojson()

            # Erstelle eine Choroplethenkarte nur für Deutschland mit GeoJSON
            fig = px.choropleth(
                interesse_nach_region,
                geojson=geojson_data,
                locations=interesse_nach_region.index,
                featureidkey="id",
                color=selected_keyword,
                color_continuous_scale=px.colors.sequential.Viridis,
                hover_name="bundesland",
                title=f"Regionales Interesse für {selected_keyword} in Deutschland",
                labels={selected_keyword: "Interesse (0-100)"}
            )

            # Entferne Hintergrundkarte und zeige nur Deutschland
            fig.update_geos(
                fitbounds="locations",
                visible=False,
                projection_type="mercator"
            )

            # Anpassen des Layouts für bessere Darstellung
            fig.update_layout(
                margin={"r":0, "t":50, "l":0, "b":0},
                coloraxis_colorbar=dict(
                    title="Interesse",
                    thicknessmode="pixels", thickness=20,
                    lenmode="pixels", len=300,
                    yanchor="top", y=1,
                    ticks="outside"
                )
            )

            st.plotly_chart(fig, use_container_width=True)

            # Erklärungstext in Klammern unterhalb der Karte
            st.markdown("""
            *(So liest du diese Karte: Die Karte zeigt, in welchen Bundesländern das Interesse am ausgewählten Lebensmittel am größten ist.
            Dunklere Farben bedeuten höheres Interesse (0-100). Bewege die Maus über ein Bundesland, um den genauen Wert zu sehen.
            Die Farbskala rechts zeigt die Werte von niedrig (hell) bis hoch (dunkel).)*
            """)

            # Zeige die Bundesländer als Tabelle
            st.subheader(f"Bundesländer-Ranking für {selected_keyword}")

            # Extrahiere die Daten für das ausgewählte Keyword
            region_data = interesse_nach_region[[selected_keyword, 'bundesland']].sort_values(by=selected_keyword, ascending=False)
            region_data = region_data.rename(columns={selected_keyword: "Interesse", "bundesland": "Bundesland"})

            # Zeige alle Bundesländer als Tabelle
            st.dataframe(
                region_data.reset_index(drop=True),
                column_config={
                    "Bundesland": st.column_config.TextColumn("Bundesland"),
                    "Interesse": st.column_config.ProgressColumn(
                        "Interesse (0-100)",
                        format="%d",
                        min_value=0,
                        max_value=100,
                    ),
                },
                hide_index=True,
                use_container_width=True
            )

            # Erklärungstext in Klammern unterhalb der Tabelle
            st.markdown("""
            *(Was bedeutet diese Tabelle: Diese Tabelle zeigt alle Bundesländer, sortiert nach dem Interesse am ausgewählten Lebensmittel.
            Ein höherer Wert (0-100) bedeutet ein größeres Suchinteresse in diesem Bundesland.)*
            """)
        else:
            st.info(f"Keine regionalen Daten verfügbar für {selected_keyword}")

# Fußzeile mit Erklärung
st.markdown("---")
st.markdown("""
### Über die Daten

- **Interesse-Werte (0-100):** Die Werte zeigen das relative Suchinteresse, wobei 100 das höchste Interesse darstellt.
- **Zeitraum:** Die Daten beziehen sich auf den ausgewählten Zeitraum.
- **Datenquelle:** Die Daten stammen aus Google Trends oder sind Beispieldaten, wenn keine echten Daten verfügbar sind.
- **Region:** Alle Daten beziehen sich ausschließlich auf Deutschland.

**Hinweis zu API-Fehlern:** Wenn du Fehler siehst, versuche die Beispieldaten zu verwenden.
""")

# Cache-Steuerung
if st.sidebar.button("Cache leeren (bei Problemen)"):
    st.cache_data.clear()
    st.success("Cache wurde geleert. Lade die Seite neu, um neue Daten abzurufen.")
