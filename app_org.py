import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import time
from datetime import datetime, timedelta
import warnings
import random
import json
import requests
from io import StringIO
import os

# Warnungen unterdrücken
warnings.simplefilter(action='ignore', category=FutureWarning)

# Seitenkonfiguration
st.set_page_config(
    page_title="Alnatura Foodtrend-Dashboard",
    page_icon="🍔",
    layout="wide"
)

# Titel und Beschreibung
st.title("Alnatura Foodtrend-Dashboard")
st.markdown("Entdecke die neuesten Lebensmitteltrends in Deutschland")

# Sidebar
with st.sidebar:
    st.header("Einstellungen")

    # Datenquelle auswählen - Standardmäßig Beispieldaten verwenden
    datenquelle = st.radio(
        "Datenquelle auswählen",
        ["Beispieldaten", "pytrends API", "Externe API"]
    )

    # Lebensmittelkategorien
    lebensmittel_kategorien = {
        "Beliebte Küchen": ["Italienisches Essen", "Chinesisches Essen", "Deutsches Essen"],
        "Diät-Trends": ["Vegane Ernährung", "Keto Diät", "Trennkost Diät"],
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

#Laden der GeoJSON-Daten für Deutschland
@st.cache_data(ttl=86400)  # Cache für 24 Stunden
def load_germany_geojson():
    try:
        # Lokale Datei verwenden, falls vorhanden
        try:
            with open("germany_geojson.json", "r") as f:
                geojson = json.load(f)

                # Füge IDs hinzu für einfachere Zuordnung, falls noch nicht vorhanden
                for feature in geojson['features']:
                    if 'id' not in feature:
                        state_name = feature['properties']['name']
                        iso_code = next((code for code, data in bundeslaender.items()
                                        if data['name'] == state_name), None)
                        if iso_code:
                            feature['id'] = iso_code

                return geojson
        except FileNotFoundError:
            pass  # Wenn lokale Datei nicht existiert, von GitHub laden

        # GeoJSON für deutsche Bundesländer von GitHub laden
        url = "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/main/2_bundeslaender/4_niedrig.geo.json"

        # Verwende einen benutzerdefinierten User-Agent, um höflich zu sein
        headers = {
            "User-Agent": "FoodTrendsDashboard/1.0 (Studentenprojekt)",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)

        # Prüfe auf Fehler
        response.raise_for_status()

        geojson = json.loads(response.text)

        # Füge IDs hinzu für einfachere Zuordnung
        for feature in geojson['features']:
            state_name = feature['properties']['name']
            # Finde den ISO-Code für diesen Bundeslandnamen
            iso_code = next((code for code, data in bundeslaender.items()
                            if data['name'] == state_name), None)
            if iso_code:
                feature['id'] = iso_code

        # Speichere die Daten lokal für zukünftige Verwendung
        try:
            with open("germany_geojson.json", "w") as f:
                json.dump(geojson, f)
        except Exception as e:
            st.warning(f"Konnte GeoJSON nicht lokal speichern: {str(e)}")

        return geojson

    except Exception as e:
        st.error(f"Fehler beim Laden der GeoJSON-Daten: {str(e)}")

        # Fallback: Leeres GeoJSON mit minimaler Struktur
        fallback_geojson = {
            "type": "FeatureCollection",
            "features": []
        }

        return fallback_geojson

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

# Funktion zum Abrufen von Daten aus der pytrends API mit verbesserter Fehlerbehandlung
@st.cache_data(ttl=7200)  # Cache für 2 Stunden
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

        # Konfiguriere die Session für bessere Fehlerbehandlung
        try:
            # Versuche mit dem neuen Parameter (urllib3 >= 2.0.0)
            retry_strategy = urllib3.Retry(
                total=5,  # Erhöht von 3 auf 5
                backoff_factor=2,  # Erhöht von 1 auf 2
                status_forcelist=[429, 500, 502, 503, 504],  # Füge 429 explizit hinzu
                allowed_methods=["GET", "POST"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
        except TypeError:
            # Fallback für ältere Versionen (urllib3 < 2.0.0)
            retry_strategy = urllib3.Retry(
                total=5,
                backoff_factor=2,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["GET", "POST"]
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Füge einen benutzerdefinierten User-Agent hinzu
        session.headers.update({
            "User-Agent": "FoodTrendsDashboard/1.0 (Studentenprojekt)",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
        })

        # Initialisiere pytrends mit der angepassten Session
        pytrends = TrendReq(
            hl='de-DE',
            timeout=(15, 45),  # Erhöhte Timeouts
            tz=360,
            requests_args={'verify': True}
        )

        # Baue die Payload - Auf Deutschland beschränken
        geo = "DE"

        # Füge längere Verzögerung hinzu, um Rate-Limiting zu vermeiden
        time.sleep(random.uniform(3.0, 5.0))  # Erhöht von 1.0-3.0 auf 3.0-5.0

        # Reduziere die Anzahl der Keywords, wenn zu viele vorhanden sind
        # pytrends erlaubt maximal 5 Keywords pro Anfrage
        if len(keywords) > 3:
            st.info(f"Zu viele Keywords ({len(keywords)}). Verwende nur die ersten 3, um API-Limits zu vermeiden.")
            keywords = keywords[:3]

        # Verwende einen einzelnen Testbegriff zuerst, um zu prüfen, ob die API funktioniert
        try:
            pytrends.build_payload(
                kw_list=["Pizza"],  # Testbegriff
                cat=71,  # Lebensmittel & Getränke Kategorie
                timeframe='today 12-m',  # Längerer Zeitraum für stabilere Ergebnisse
                geo=geo
            )

            # Prüfe, ob die API funktioniert
            test_data = pytrends.interest_over_time()
            if test_data.empty:
                raise Exception("pytrends API liefert leere Daten zurück")

            # Längere Pause nach erfolgreicher Testanfrage
            time.sleep(random.uniform(5.0, 8.0))

        except Exception as e:
            st.error(f"pytrends API-Test fehlgeschlagen: {str(e)}")
            return pd.DataFrame(), pd.DataFrame()

        # Jetzt die eigentliche Anfrage mit den gewünschten Keywords
        pytrends.build_payload(
            kw_list=keywords,
            cat=71,  # Lebensmittel & Getränke Kategorie
            timeframe=zeitraum,
            geo=geo
        )

        # Füge längere Verzögerung hinzu
        time.sleep(random.uniform(4.0, 7.0))  # Erhöht von 1.5-3.5 auf 4.0-7.0

        # Hole das Interesse über Zeit
        interesse_über_zeit = pytrends.interest_over_time()

        if interesse_über_zeit.empty:
            st.warning("pytrends lieferte leere Zeitreihendaten zurück. Verwende Beispieldaten.")
            return beispieldaten_generieren(keywords, zeitraum)

        # Hole das Interesse nach Region (Bundesländer)
        try:
            # Füge längere Verzögerung hinzu
            time.sleep(random.uniform(5.0, 8.0))  # Erhöht von 1.5-3.5 auf 5.0-8.0

            # Hole Daten für deutsche Bundesländer
            interesse_nach_region_raw = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True)

            if interesse_nach_region_raw.empty:
                raise Exception("Leere Regionaldaten erhalten")

            # Mapping von pytrends Regionennamen zu ISO-Codes
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

        # Versuche, die Daten lokal zu speichern
        try:
            # Speichere die Daten als CSV
            interesse_über_zeit.to_csv(f"trends_zeit_{'-'.join(keywords)}_{zeitraum.replace(' ', '_')}.csv")
            interesse_nach_region.to_csv(f"trends_region_{'-'.join(keywords)}_{zeitraum.replace(' ', '_')}.csv")
        except Exception as e:
            st.warning(f"Konnte Daten nicht lokal speichern: {str(e)}")

        return interesse_über_zeit, interesse_nach_region

    except Exception as e:
        st.error(f"Fehler beim Abrufen der Trends-Daten: {str(e)}")

        # Versuche, gespeicherte Daten zu laden, falls vorhanden
        try:
            zeit_datei = f"trends_zeit_{'-'.join(keywords)}_{zeitraum.replace(' ', '_')}.csv"
            region_datei = f"trends_region_{'-'.join(keywords)}_{zeitraum.replace(' ', '_')}.csv"

            if os.path.exists(zeit_datei) and os.path.exists(region_datei):
                st.info("Verwende gespeicherte Daten aus vorherigen Anfragen.")
                interesse_über_zeit = pd.read_csv(zeit_datei, index_col=0, parse_dates=True)
                interesse_nach_region = pd.read_csv(region_datei, index_col=0)
                return interesse_über_zeit, interesse_nach_region
        except Exception:
            pass

        # Wenn alles fehlschlägt, verwende Beispieldaten
        return beispieldaten_generieren(keywords, zeitraum)

# NEUE FUNKTION: Externe API für Lebensmittelinformationen
@st.cache_data(ttl=3600)  # Cache für 1 Stunde
def externe_api_daten_abrufen(lebensmittel):
    """
    Diese Funktion ruft Daten von der Open Food Facts API ab.
    Die API benötigt keinen API-Schlüssel und liefert Informationen zu Lebensmitteln.
    """
    try:
        # Bereite die Anfrage vor
        base_url = "https://world.openfoodfacts.org/cgi/search.pl"

        # Parameter für die Suche
        params = {
            "search_terms": lebensmittel,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": 10  # Begrenze auf 10 Ergebnisse
        }

        # Füge einen benutzerdefinierten User-Agent hinzu
        headers = {
            "User-Agent": "FoodTrendsDashboard/1.0 (Studentenprojekt)",
            "Accept": "application/json"
        }

        # Sende die Anfrage
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # Löse eine Exception aus, wenn der Status-Code nicht 200 ist

        # Verarbeite die Antwort
        data = response.json()

        # Extrahiere relevante Informationen
        produkte = []

        if "products" in data and len(data["products"]) > 0:
            for product in data["products"]:
                produkt_info = {
                    "name": product.get("product_name", "Unbekannt"),
                    "marke": product.get("brands", "Unbekannt"),
                    "herkunftsland": product.get("countries", "Unbekannt"),
                    "nährwert_score": product.get("nutriscore_grade", "?"),
                    "kategorien": product.get("categories", ""),
                    "zutaten": product.get("ingredients_text", "Keine Informationen"),
                    "bild_url": product.get("image_url", "")
                }
                produkte.append(produkt_info)

        return produkte

    except Exception as e:
        st.error(f"Fehler beim Abrufen der Lebensmittelinformationen: {str(e)}")
        return []

# Hole die Keywords für die ausgewählte Kategorie
keywords = lebensmittel_kategorien[ausgewählte_kategorie]

# Verarbeite die Daten basierend auf der ausgewählten Datenquelle
if datenquelle == "Externe API":
    # Zeige die externe API-Integration
    st.header("Lebensmittelinformationen aus externer API")

    st.markdown("""
    Dieser Abschnitt zeigt, wie man eine externe API in das Dashboard integriert.
    Wir verwenden die Open Food Facts API, um Informationen zu Lebensmitteln abzurufen.
    """)

    # Eingabefeld für die Lebensmittelsuche
    suchbegriff = st.text_input("Lebensmittel suchen", value="Schokolade")

    if st.button("Suchen"):
        with st.spinner(f"Suche nach Informationen zu '{suchbegriff}'..."):
            # Rufe Daten von der externen API ab
            produkte = externe_api_daten_abrufen(suchbegriff)

            if produkte:
                st.success(f"{len(produkte)} Produkte gefunden!")

                # Zeige die Produkte in Tabs an
                tabs = st.tabs([f"Produkt {i+1}" for i in range(min(5, len(produkte)))])

                for i, tab in enumerate(tabs):
                    if i < len(produkte):
                        produkt = produkte[i]
                        with tab:
                            cols = st.columns([1, 2])

                            with cols[0]:
                                if produkt["bild_url"]:
                                    st.image(produkt["bild_url"], width=150)
                                else:
                                    st.info("Kein Bild verfügbar")

                            with cols[1]:
                                st.subheader(produkt["name"])
                                st.write(f"**Marke:** {produkt['marke']}")
                                st.write(f"**Herkunftsland:** {produkt['herkunftsland']}")

                                # Nutri-Score visualisieren
                                if produkt["nährwert_score"] != "?":
                                    score_farben = {
                                        "a": "green", "b": "lightgreen",
                                        "c": "yellow", "d": "orange", "e": "red"
                                    }
                                    score = produkt["nährwert_score"].lower()
                                    farbe = score_farben.get(score, "gray")

                                    st.markdown(f"""
                                    **Nutri-Score:** <span style='background-color:{farbe};
                                    padding:2px 8px; border-radius:12px; color:white;
                                    font-weight:bold;'>{score.upper()}</span>
                                    """, unsafe_allow_html=True)

                                st.write("**Kategorien:**")
                                st.write(produkt["kategorien"])

                            st.write("**Zutaten:**")
                            st.write(produkt["zutaten"] if produkt["zutaten"] else "Keine Zutatenliste verfügbar")

                # Zeige eine Tabelle mit allen Produkten
                st.subheader("Alle gefundenen Produkte")

                # Erstelle ein DataFrame für die Tabelle
                df_produkte = pd.DataFrame([{
                    "Name": p["name"],
                    "Marke": p["marke"],
                    "Herkunft": p["herkunftsland"],
                    "Nutri-Score": p["nährwert_score"].upper() if p["nährwert_score"] != "?" else "?"
                } for p in produkte])

                st.dataframe(df_produkte)

                # Visualisierung: Verteilung der Nutri-Scores
                nutri_scores = [p["nährwert_score"].upper() for p in produkte if p["nährwert_score"] != "?"]
                if nutri_scores:
                    score_counts = pd.Series(nutri_scores).value_counts().sort_index()

                    fig = px.bar(
                        x=score_counts.index,
                        y=score_counts.values,
                        labels={"x": "Nutri-Score", "y": "Anzahl Produkte"},
                        title=f"Verteilung der Nutri-Scores für '{suchbegriff}'",
                        color=score_counts.index,
                        color_discrete_map={"A": "green", "B": "lightgreen", "C": "yellow", "D": "orange", "E": "red"}
                    )

                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Keine Produkte für '{suchbegriff}' gefunden.")

else:
    # Hole die Daten für pytrends oder Beispieldaten
    with st.spinner(f"Lade {'Beispiel' if datenquelle == 'Beispieldaten' else 'pytrends'}-Daten..."):
        if datenquelle == "pytrends API":
            # Versuche, die Daten abzurufen, mit Fallback zu Beispieldaten
            interesse_über_zeit, interesse_nach_region = trends_daten_abrufen(
                keywords,
                zeitraum_optionen[ausgewählter_zeitraum]
            )
            # Fallback zu Beispieldaten, wenn keine Daten gefunden wurden
            if interesse_über_zeit.empty:
                st.warning("""
                Keine Daten von pytrends gefunden oder API-Fehler aufgetreten.
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
- **Datenquelle:** Die Daten stammen aus der pytrends API, der Open Food Facts API oder sind Beispieldaten.
- **Region:** Alle Daten beziehen sich ausschließlich auf Deutschland.
""")

# Cache-Steuerung
if st.sidebar.button("Cache leeren (bei Problemen)"):
    st.cache_data.clear()
    st.success("Cache wurde geleert. Lade die Seite neu, um neue Daten abzurufen.")