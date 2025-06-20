import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
from datetime import datetime

# Dashboard-Konfiguration
st.set_page_config(page_title="Alnatura Foodtrend-Dashboard", page_icon="🍔", layout="wide")
st.title("Alnatura Foodtrend-Dashboard")
st.markdown("Entdecke die neuesten Lebensmitteltrends in Deutschland")

# Sidebar-Konfiguration
with st.sidebar:
    st.header("Einstellungen")
    datenquelle = st.radio("Datenquelle auswählen", ["Beispieldaten", "Externe API"])
    lebensmittel_kategorien = {
        "Beliebte Küchen": ["Italienisches Essen", "Chinesisches Essen", "Deutsches Essen"],
        "Diät-Trends": ["Vegane Ernährung", "Keto Diät", "Trennkost Diät"],
        "Beliebte Zutaten": ["Avocado", "Quinoa", "Kurkuma"],
        "Desserts": ["Käsekuchen", "Tiramisu", "Eis"],
        "Getränke": ["Kaffee", "Bubble Tea", "Smoothie"]
    }
    ausgewählte_kategorie = st.selectbox("Lebensmittelkategorie auswählen", list(lebensmittel_kategorien.keys()))
    zeitraum_optionen = {"Letzter Monat": "1-m", "Letzte 3 Monate": "3-m", "Letztes Jahr": "12-m"}
    ausgewählter_zeitraum = st.selectbox("Zeitraum auswählen", list(zeitraum_optionen.keys()))

# Bundesländer mit ISO-Codes
bundeslaender = {
    "DE-BW": "Baden-Württemberg", "DE-BY": "Bayern", "DE-BE": "Berlin", "DE-BB": "Brandenburg",
    "DE-HB": "Bremen", "DE-HH": "Hamburg", "DE-HE": "Hessen", "DE-MV": "Mecklenburg-Vorpommern",
    "DE-NI": "Niedersachsen", "DE-NW": "Nordrhein-Westfalen", "DE-RP": "Rheinland-Pfalz", "DE-SL": "Saarland",
    "DE-SN": "Sachsen", "DE-ST": "Sachsen-Anhalt", "DE-SH": "Schleswig-Holstein", "DE-TH": "Thüringen"
}

# GeoJSON für Bundesländer laden
@st.cache_data(ttl=86400)
def load_geojson():
    url = "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/main/2_bundeslaender/4_niedrig.geo.json"
    geojson = requests.get(url).json()
    for f in geojson['features']:
        name = f['properties']['name']
        iso = next((k for k, v in bundeslaender.items() if v == name), None)
        if iso: f['id'] = iso
    return geojson

# Zufallsbasierte Beispieldaten generieren
def beispieldaten_generieren(keywords, zeitraum):
    tage = {"1-m": 30, "3-m": 90, "12-m": 52}
    index = pd.date_range(end=datetime.now(), periods=tage[zeitraum], freq='D' if 'm' in zeitraum else 'W')
    daten = {kw: np.clip(np.random.normal(50, 20, len(index)), 0, 100) for kw in keywords}
    interesse_zeit = pd.DataFrame(daten, index=index)
    interesse_region = pd.DataFrame({kw: np.random.randint(0, 100, len(bundeslaender)) for kw in keywords},
                                     index=pd.Index(bundeslaender.keys(), name='iso_alpha'))
    interesse_region['bundesland'] = interesse_region.index.map(bundeslaender.get)
    return interesse_zeit, interesse_region

# Daten von Open Food Facts API laden
@st.cache_data(ttl=3600)
def externe_api_daten_abrufen(suchbegriff):
    try:
        r = requests.get("https://world.openfoodfacts.org/cgi/search.pl", params={
            "search_terms": suchbegriff, "search_simple": 1,
            "action": "process", "json": 1, "page_size": 10
        }, headers={"User-Agent": "FoodTrendsDashboard"})
        daten = r.json().get("products", [])
        return [{
            "name": p.get("product_name", "Unbekannt"),
            "marke": p.get("brands", "Unbekannt"),
            "herkunft": p.get("countries", "Unbekannt"),
            "score": p.get("nutriscore_grade", "?"),
            "kategorien": p.get("categories", ""),
            "zutaten": p.get("ingredients_text", "Keine Info"),
            "bild": p.get("image_url", ""),
            "fett": p.get("nutriments", {}).get("fat_100g"),
            "zucker": p.get("nutriments", {}).get("sugars_100g")
        } for p in daten]
    except:
        return []

keywords = lebensmittel_kategorien[ausgewählte_kategorie]
zeitraum_kurz = zeitraum_optionen[ausgewählter_zeitraum]

if datenquelle == "Externe API":
    st.header("Lebensmittelinformationen aus externer API")
    suchbegriff = st.text_input("Lebensmittel suchen", value="Schokolade")
    if st.button("Suchen"):
        with st.spinner("Suche..."):
            produkte = externe_api_daten_abrufen(suchbegriff)
            if produkte:
                for p in produkte[:5]:
                    st.subheader(p["name"])
                    st.write(f"**Marke:** {p['marke']}, **Herkunft:** {p['herkunft']}, **Nutri-Score:** {p['score'].upper()}")
                    st.write(f"**Kategorien:** {p['kategorien']}")
                    st.write(f"**Zutaten:** {p['zutaten']}")
                    if p['bild']: st.image(p['bild'], width=150)

                vergleich_df = pd.DataFrame([p for p in produkte if p["fett"] is not None and p["zucker"] is not None])
                if not vergleich_df.empty:
                    st.subheader("Vergleich: Fett- und Zuckergehalt")
                    fig = px.scatter(vergleich_df, x="zucker", y="fett", text="name",
                                     hover_data=["marke"],
                                     labels={"zucker": "Zucker (g/100g)", "fett": "Fett (g/100g)"},
                                     title="Fett vs. Zucker je Produkt")
                    fig.update_traces(textposition='top center')
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown("*(Tipp: Produkte links unten im Diagramm haben wenig Zucker **und** wenig Fett – ideal für eine gesündere Wahl.)*")
            else:
                st.warning("Keine Ergebnisse gefunden.")
else:
    interesse_zeit, interesse_region = beispieldaten_generieren(keywords, zeitraum_kurz)
    tab1, tab2 = st.tabs(["Trend über Zeit", "Regionales Interesse"])

    with tab1:
        st.subheader("Interesse über Zeit")
        fig = px.line(interesse_zeit, x=interesse_zeit.index, y=keywords,
                      title="Trendverlauf", labels={"value": "Interesse", "variable": "Keyword"})
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Regionales Interesse")
        keyword = st.selectbox("Keyword auswählen", keywords)
        if keyword in interesse_region:
            geo = load_geojson()
            fig = px.choropleth(interesse_region, geojson=geo, locations=interesse_region.index,
                                featureidkey="id", color=keyword, hover_name="bundesland")
            fig.update_geos(fitbounds="locations", visible=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("""
    ### Über die Daten
    - **Interesse:** Relatives Interesse (0-100) basierend auf Zufallsdaten
    - **Zeitraum:** Ausgewählter Zeitraum simuliert
    - **Region:** Nur Deutschland
    """)

if st.sidebar.button("Cache leeren"):
    st.cache_data.clear()
    st.success("Cache geleert. Bitte Seite neu laden.")
