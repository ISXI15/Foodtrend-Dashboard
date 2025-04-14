**1. Prototyp Foodtrend-Dashboard**

Dies ist eine interaktive Web-App, die mit [**Streamlit**](https://streamlit.io/) entwickelt wurde.
Sie analysiert und visualisiert Daten mithilfe von Plotly, Dash, Pandas und weiteren Tools.

_2. Schnellstart (lokal ausführen)_

_3. Voraussetzungen_

- **Python** 3.9 oder neuer installiert → [Download Python](https://www.python.org/downloads/)
- **Git** installiert → [Download Git](https://git-scm.com/downloads)
- **Visual Studio Code (VS Code)** → [Download VS Code](https://code.visualstudio.com/)

---

_4. Empfohlene VS Code Extensions_

Damit das Arbeiten am Projekt angenehm ist, bitte folgende Extensions in VS Code installieren:

- **Python** (von Microsoft)
- **Pylance** (für bessere IntelliSense)
- **Jupyter** (optional, für Notebooks)
- **Streamlit Runner** (optional, für Live Preview)

---

_5. Projekt klonen & starten_

```bash
# Repository klonen
git clone https://github.com/ISXI15/Foodtrend-Dashboard.git
cd Foodtrend-Dashboard

# Virtuelle Umgebung erstellen
python -m venv venv

# Umgebung aktivieren
# macOS/Linux:
source venv/bin/activate
# Windows (CMD):
venv\Scripts\activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Abhängigkeiten installieren
pip install -r requirements.txt

# App starten
streamlit run app.py
