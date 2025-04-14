import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import time
from datetime import datetime
import warnings
import random
import requests

# Warnungen unterdrücken
warnings.simplefilter(action='ignore', category=FutureWarning)

# Seitenkonfiguration
st.set_page_config(
    page_title="Food Trends Dashboard",
    page_icon="🍔",
    layout="wide"
)

# Titel und Beschreibung
st.title("Food Trends Dashboard - Verbessert")
st.markdown("Entdecke die neuesten Trends bei Lebensmitteln mit einfachen, verständlichen Visualisierungen")

# Sidebar für Eingaben
with st.sidebar:
    st.header("Einstellungen")

    # Datenquelle auswählen: Beispieldaten oder TheMealDB API
    datenquelle = st.radio(
        "Datenquelle auswählen",
        ["Beispieldaten", "TheMealDB API"]
    )

   # if datenquelle == "TheMealDB API":
      #  st.info("Die Daten werden von der kostenlosen TheMealDB API abgerufen. Falls es zu Problemen kommt, werden Beispieldaten verwendet.")

    # Lebensmittelkategorien (wird nur bei Beispieldaten verwendet)
    lebensmittel_kategorien = {
        "Beliebte Küchen": ["Italienisches Essen", "Chinesisches Essen", "Deutsches Essen"],
        "Diät-Trends": ["Vegane Ernährung", "Keto Diät", "Paleo Diät"],
        "Beliebte Zutaten": ["Avocado", "Quinoa", "Kurkuma"],
        "Desserts": ["Käsekuchen", "Tiramisu", "Eis"],
        "Getränke": ["Kaffee", "Bubble Tea", "Smoothie"]
    }

    # Wenn Beispieldaten genutzt werden, kann eine Kategorie ausgewählt werden
    if datenquelle == "Beispieldaten":
        ausgewählte_kategorie = st.selectbox(
            "Lebensmittelkategorie auswählen",
            list(lebensmittel_kategorien.keys())
        )
    else:
        # Bei der API werden die Mahlzeiten dynamisch abgerufen – Kategorie wird ignoriert
        ausgewählte_kategorie = "TheMealDB"  # Platzhalter

    # Anzahl der Keywords
    max_keywords = st.slider(
        "Anzahl der Suchbegriffe (je weniger, desto stabiler)",
        min_value=1,
        max_value=5,
        value=3
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

    # Region auswählen
    regionen = {
        "Weltweit": "WORLD",
        "Deutschland": "DE",
        "Österreich": "AT",
        "Schweiz": "CH",
        "USA": "US",
        "Großbritannien": "GB",
        "Frankreich": "FR"
    }
    ausgewählte_region = st.selectbox(
        "Region auswählen",
        list(regionen.keys())
    )

# Funktion zum Generieren von Beispieldaten
def beispieldaten_generieren(keywords, zeitraum, region):
    # Erstelle einen Datumsbereich basierend auf dem ausgewählten Zeitraum
    if "1-m" in zeitraum:
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
    elif "3-m" in zeitraum:
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
    else:  # "12-m"
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=52, freq='W')

    # Erstelle Beispieldaten für das Interesse über Zeit
    daten = {}
    for keyword in keywords:
        basis = np.random.randint(30, 70)
        trend = np.random.normal(basis, 15, size=len(datumsbereich))
        trend = np.clip(trend, 0, 100)
        daten[keyword] = trend
    interesse_über_zeit = pd.DataFrame(daten, index=datumsbereich)

    # Erstelle Beispieldaten für das Interesse nach Region
    länder_iso = {
        "WORLD": "Weltweit",
        "DE": "Deutschland",
        "AT": "Österreich",
        "CH": "Schweiz",
        "US": "Vereinigte Staaten",
        "GB": "Großbritannien",
        "FR": "Frankreich",
        "IT": "Italien",
        "ES": "Spanien",
        "JP": "Japan",
        "CA": "Kanada",
        "AU": "Australien",
        "BR": "Brasilien",
        "RU": "Russland",
        "IN": "Indien",
        "CN": "China"
    }
    regionsdaten = {}
    for keyword in keywords:
        regionsdaten[keyword] = [np.random.randint(0, 100) for _ in range(len(länder_iso))]
    interesse_nach_region = pd.DataFrame(regionsdaten, index=pd.Series(list(länder_iso.keys()), name='iso_alpha'))
    interesse_nach_region['country'] = interesse_nach_region.index.map(lambda x: länder_iso.get(x, x))

    return interesse_über_zeit, interesse_nach_region

# Funktion zum Abrufen von Daten aus der TheMealDB API
@st.cache_data(ttl=3600)
def mealdb_daten_abrufen(zeitraum, region, max_keywords):
    url = "https://www.themealdb.com/api/json/v1/1/latest.php"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # Prüft auf HTTP-Fehler
        data = response.json()
        if "meals" in data and data["meals"]:
            # Extrahiere die Mahlzeitennamen
            meals = data["meals"]
            keywords = [meal["strMeal"] for meal in meals if meal.get("strMeal")]
            # Begrenze die Anzahl der Keywords auf max_keywords
            keywords = keywords[:max_keywords] if len(keywords) > max_keywords else keywords
        else:
            raise ValueError("Keine Mahlzeiten-Daten verfügbar.")
    except Exception as e:
        st.warning(f"Fehler beim Abrufen der TheMealDB API-Daten: {e}. Es werden Beispieldaten verwendet.")
        keywords = ["Pizza", "Burger", "Sushi"]  # Fallback-Keywords

    # Erstelle einen Datumsbereich basierend auf dem ausgewählten Zeitraum
    if "1-m" in zeitraum:
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
    elif "3-m" in zeitraum:
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=90, freq='D')
    else:  # "12-m"
        datumsbereich = pd.date_range(end=pd.Timestamp.now(), periods=52, freq='W')

    # Generiere simulierte Trenddaten für "Interesse über Zeit"
    daten = {}
    for keyword in keywords:
        basis = np.random.randint(30, 70)
        trend = np.random.normal(basis, 15, size=len(datumsbereich))
        trend = np.clip(trend, 0, 100)
        daten[keyword] = trend
    interesse_über_zeit = pd.DataFrame(daten, index=datumsbereich)

    # Generiere simulierte Daten für "Interesse nach Region"
    länder_iso = {
        "WORLD": "Weltweit",
        "DE": "Deutschland",
        "AT": "Österreich",
        "CH": "Schweiz",
        "US": "Vereinigte Staaten",
        "GB": "Großbritannien",
        "FR": "Frankreich",
        "IT": "Italien",
        "ES": "Spanien",
        "JP": "Japan",
        "CA": "Kanada",
        "AU": "Australien",
        "BR": "Brasilien",
        "RU": "Russland",
        "IN": "Indien",
        "CN": "China"
    }
    regionsdaten = {}
    for keyword in keywords:
        regionsdaten[keyword] = [np.random.randint(0, 100) for _ in range(len(länder_iso))]
    interesse_nach_region = pd.DataFrame(regionsdaten, index=pd.Series(list(länder_iso.keys()), name='iso_alpha'))
    interesse_nach_region['country'] = interesse_nach_region.index.map(lambda x: länder_iso.get(x, x))

    return interesse_über_zeit, interesse_nach_region

# Hole die Daten je nach ausgewählter Datenquelle
if datenquelle == "TheMealDB API":
    with st.spinner("Lade Daten von der TheMealDB API..."):
        # Der API-Aufruf liefert dynamisch die Mahlzeiten als Keywords
        interesse_über_zeit, interesse_nach_region = mealdb_daten_abrufen(
            zeitraum_optionen[ausgewählter_zeitraum],
            regionen[ausgewählte_region],
            max_keywords
        )
        # Überschreibe die Keywords anhand der API-Ergebnisse
        keywords = list(interesse_über_zeit.columns)
else:
    # Bei Beispieldaten werden Keywords aus der ausgewählten Lebensmittelkategorie genutzt
    keywords = lebensmittel_kategorien[ausgewählte_kategorie][:max_keywords]
    with st.spinner("Lade Beispieldaten..."):
        interesse_über_zeit, interesse_nach_region = beispieldaten_generieren(
            keywords,
            zeitraum_optionen[ausgewählter_zeitraum],
            regionen[ausgewählte_region]
        )

# Visualisierung der Daten
if not interesse_über_zeit.empty:
    # Erstelle Tabs für verschiedene Visualisierungen
    tab1, tab2 = st.tabs(["Trend über Zeit", "Regionales Interesse"])

    with tab1:
        st.subheader("Interesse über Zeit")

        st.markdown("""
        ### So liest du diesen Graphen:

        1. **Was wird angezeigt?** Der Graph zeigt das relative Suchinteresse (simuliert) für die ausgewählten Lebensmittel über Zeit.
        2. **Y-Achse (Interesse):** Die Werte reichen von 0 bis 100, wobei 100 das höchste Interesse darstellt.
        3. **X-Achse (Zeit):** Zeigt den ausgewählten Zeitraum.
        4. **Linien:** Jede Linie repräsentiert einen Suchbegriff. Höhere Werte bedeuten mehr Interesse.
        """)

        fig = px.line(
            interesse_über_zeit,
            x=interesse_über_zeit.index,
            y=keywords,
            title=f"Interesse über Zeit ({ausgewählter_zeitraum})",
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

        st.subheader("Aktuelle Werte")
        st.markdown("""
        ### Erklärung:

        - **Aktueller Wert:** Zeigt das aktuelle Interesse am Suchbegriff (0-100).
        - **Veränderung:** Zeigt, wie sich das Interesse im Vergleich zum vorherigen Zeitpunkt verändert hat.
          - 🔴 Negative Werte bedeuten abnehmendes Interesse
          - 🟢 Positive Werte bedeuten zunehmendes Interesse
        """)

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

    with tab2:
        st.subheader("Regionales Interesse")

        st.markdown("""
        ### So liest du diese Karte:

        1. **Was wird angezeigt?** Die Karte zeigt, in welchen Ländern das Interesse (simuliert) am ausgewählten Lebensmittel am größten ist.
        2. **Farbskala:** Dunklere Farben bedeuten höheres Interesse (0-100).
        3. **Hover:** Bewege die Maus über ein Land, um den genauen Wert zu sehen.
        4. **Legende:** Die Farbskala rechts zeigt die Werte von niedrig (hell) bis hoch (dunkel).
        """)

        selected_keyword = st.selectbox(
            "Lebensmittel auswählen, um regionales Interesse anzuzeigen",
            keywords
        )

        if selected_keyword in interesse_nach_region.columns:
            fig = px.choropleth(
                interesse_nach_region,
                locations=interesse_nach_region.index,
                color=selected_keyword,
                hover_name="country",  # Ländernamen für Hover
                color_continuous_scale=px.colors.sequential.Viridis,
                title=f"Regionales Interesse für {selected_keyword}",
                labels={selected_keyword: "Interesse (0-100)"}
            )
            fig.update_layout(
                geo=dict(
                    showframe=False,
                    showcoastlines=True,
                    projection_type='equirectangular'
                )
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader(f"Top 5 Länder für {selected_keyword}")
            st.markdown("""
            ### Erklärung:

            Diese Tabelle zeigt die 5 Länder mit dem höchsten Interesse am ausgewählten Lebensmittel.
            Ein höherer Wert (0-100) bedeutet ein größeres Suchinteresse in diesem Land.
            """)

            region_data = interesse_nach_region[[selected_keyword, 'country']].sort_values(by=selected_keyword, ascending=False)
            region_data = region_data.rename(columns={selected_keyword: "Interesse", "country": "Land"})
            st.dataframe(
                region_data.head(5).reset_index(drop=True),
                column_config={
                    "Land": st.column_config.TextColumn("Land"),
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
        else:
            st.info(f"Keine regionalen Daten verfügbar für {selected_keyword}")

# Fußzeile mit Erklärung
st.markdown("---")
st.markdown("""
### Über die Daten

- **Interesse-Werte (0-100):** Die Werte zeigen das relative, simulierte Suchinteresse, wobei 100 das höchste Interesse darstellt.
- **Zeitraum:** Die Daten beziehen sich auf den ausgewählten Zeitraum.
- **Datenquelle:** Die Daten werden entweder aus Beispieldaten oder (bei entsprechender Auswahl) von der TheMealDB API abgerufen.

**Hinweis:** Bei Problemen mit der API (z. B. Verbindungsproblemen) werden Beispieldaten verwendet.
""")

# Cache-Steuerung
if st.sidebar.button("Cache leeren (bei Problemen)"):
    st.cache_data.clear()
    st.success("Cache wurde geleert. Lade die Seite neu, um neue Daten abzurufen.")
