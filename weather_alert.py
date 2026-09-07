import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

# ========== CONFIGURATION ==========
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
LAT = 43.3858  # Saint-Jean-de-Luz
LON = -1.6606
EMAIL_TO = os.getenv("EMAIL_TO")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Seuil de vent en km/h
WIND_THRESHOLD_KMH = 40

# Configuration pour api-maree.fr
MAREE_API_KEY = "12a849135b3fb84c577123cf6a758005"
MAREE_SITE = "saint-jean-de-luz"
MAREE_TZ = "Europe/Paris"

# Fuseau horaire de Paris
PARIS_TZ = timezone(timedelta(hours=2))

# ========== FONCTIONS POUR LA METEO ==========
def get_weather_forecast():
    """Récupère les prévisions météo sur 5 jours."""
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API météo : {e}")
        return None

def get_forecast_by_day(forecast_data):
    """Organise les prévisions par jour."""
    days = {}
    for item in forecast_data["list"]:
        dt = datetime.fromtimestamp(item["dt"], tz=PARIS_TZ)
        date_str = dt.strftime("%Y-%m-%d")
        if date_str not in days:
            days[date_str] = []
        days[date_str].append({
            "time": dt,
            "hour": dt.hour,
            "temp": item["main"]["temp"],
            "weather_desc": item["weather"][0]["description"],
            "weather_main": item["weather"][0]["main"],
            "rain_mm": item.get("rain", {}).get("3h", 0),
            "pop": item.get("pop", 0),
            "wind_speed_kmh": item["wind"]["speed"] * 3.6,
        })
    return days

# ========== FONCTIONS POUR LES MAREES (api-maree.fr) ==========
def get_tides(date):
    """Récupère les marées pour une date donnée via api-maree.fr."""
    date_str = date.strftime("%Y-%m-%d")
    url = f"https://api-maree.fr/tide-extrema?site={MAREE_SITE}&from={date_str}&to={date_str}&tz={MAREE_TZ}&key={MAREE_API_KEY}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Les données sont dans data[0]["extrema"]
            if "data" in data and len(data["data"]) > 0:
                # Filtre les marées pour la date demandée
                for day_data in data["data"]:
                    if day_data["date"] == date_str:
                        return day_data["extrema"]
                # Si aucune correspondance, retourne les premières données
                return data["data"][0]["extrema"] if data["data"] else []
            return []
        else:
            print(f"⚠️ Erreur API marées (code {response.status_code}) : {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erreur API marées : {e}")
        return None

def format_tides(tides_data):
    """Formate les données de marée pour l'email."""
    if not tides_data:
        return "Marées : Données non disponibles"

    pm = [t for t in tides_data if t.get("type") == "PM"]
    bm = [t for t in tides_data if t.get("type") == "BM"]
    # Tous les extrema ont le même coefficient pour une journée
    coefficient = tides_data[0].get("coef", "N/A") if tides_data else "N/A"

    pm_str = ", ".join([f"{t.get('time', 'N/A')} ({t.get('height', 'N/A'):.2f}m)" for t in pm])
    bm_str = ", ".join([f"{t.get('time', 'N/A')} ({t.get('height', 'N/A'):.2f}m)" for t in bm])

    return f"Marées : PM {pm_str} | BM {bm_str} | Coef: {coefficient}"

# ========== FONCTIONS DE RESUME ==========
def summarize_period(items, label):
    """Résumé pour une période (matin ou après-midi)."""
    if not items:
        return f"{label} : Aucune donnée"

    temps = [i["temp"] for i in items]
    min_temp = min(temps)
    max_temp = max(temps)

    # Météo dominante
    weather_counts = {}
    for i in items:
        w = i["weather_desc"].capitalize()
        weather_counts[w] = weather_counts.get(w, 0) + 1
    dominant_weather = max(weather_counts, key=weather_counts.get)

    # Pluie et probabilité
    total_rain = sum(i["rain_mm"] for i in items)
    max_pop = max(i["pop"] for i in items)

    # Vent max
    max_wind = max(i["wind_speed_kmh"] for i in items)

    # Icône
    if total_rain > 1.0:
        icon = "🌧️"
    elif "nuage" in dominant_weather.lower():
        icon = "☁️"
    elif "pluie" in dominant_weather.lower():
        icon = "🌧️"
    else:
        icon = "☀️"

    return (f"{icon} {label} : {dominant_weather} | "
            f"Temp: {min_temp:.0f}°C - {max_temp:.0f}°C | "
            f"Pluie: {total_rain:.1f}mm ({max_pop*100:.0f}% risque) | "
            f"Vent max: {max_wind:.0f} km/h")

def summarize_day(forecast_data, date, tides_data):
    """Résumé complet pour un jour donné."""
    date_str = date.strftime("%A %d %B %Y")
    day_items = forecast_data.get(date.strftime("%Y-%m-%d"), [])

    if not day_items:
        return f"### {date_str}\nAucune prévision disponible."

    # Sépare matin et après-midi
    morning = [i for i in day_items if i["hour"] < 12]
    afternoon = [i for i in day_items if i["hour"] >= 12]

    # Vent max de la journée
    max_wind = max(i["wind_speed_kmh"] for i in day_items)

    # Résumé du jour
    summary = f"### 📅 {date_str}\n"
    summary += summarize_period(morning, "🌅 Matin") + "\n"
    summary += summarize_period(afternoon, "🌆 Après-midi") + "\n"
    summary += f"💨 Vent max : {max_wind:.0f} km/h\n"

    # Ajoute les marées
    if tides_data:
        summary += format_tides(tides_data) + "\n"
    else:
        summary += "Marées : Données non disponibles\n"

    return summary

# ========== FONCTIONS D'ALERTE ==========
def check_wind_alert(forecast_data):
    """Vérifie si le vent dépasse le seuil sur les 2 prochains jours."""
    today = datetime.now(PARIS_TZ).date()
    tomorrow = today + timedelta(days=1)

    max_wind = 0
    max_wind_time = None

    for date_str, items in forecast_data.items():
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if date in (today, tomorrow):
            for item in items:
                if item["wind_speed_kmh"] > max_wind:
                    max_wind = item["wind_speed_kmh"]
                    max_wind_time = item["time"]

    return max_wind, max_wind_time

# ========== EMAIL ==========
def send_email(subject, body):
    """Envoie un email via SMTP."""
    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email envoyé à {EMAIL_TO}")
        return True
    except Exception as e:
        print(f"❌ Erreur envoi email : {e}")
        return False

# ========== MAIN ==========
def main():
    print(f"[{datetime.now(PARIS_TZ).strftime('%Y-%m-%d %H:%M')}] Début de la vérification météo...")

    # Récupère les données météo
    weather_data = get_weather_forecast()
    if not weather_data:
        print("❌ Impossible de récupérer les données météo.")
        return

    # Organise par jour
    forecast_by_day = get_forecast_by_day(weather_data)

    # Récupère les dates pour aujourd'hui et demain
    today = datetime.now(PARIS_TZ).date()
    tomorrow = today + timedelta(days=1)

    # Récupère les marées
    print(f"🔍 Récupération des marées pour {today} et {tomorrow}...")
    tides_today = get_tides(today)
    print(f"Marées aujourd'hui : {tides_today}")
    tides_tomorrow = get_tides(tomorrow)
    print(f"Marées demain : {tides_tomorrow}")

    # Crée le résumé pour les 2 jours
    summary = "🌊 PRÉVISIONS MÉTÉO ET MARÉES POUR SAINT-JEAN-DE-LUZ\n\n"
    summary += summarize_day(forecast_by_day, today, tides_today) + "\n"
    summary += summarize_day(forecast_by_day, tomorrow, tides_tomorrow)

    # Vérifie l'alerte vent
    max_wind, max_wind_time = check_wind_alert(forecast_by_day)
    print(f"💨 Vent maximum sur 2 jours : {max_wind:.1f} km/h (à {max_wind_time.strftime('%Y-%m-%d %H:%M')})")

    # Décision d'envoi
    if max_wind > WIND_THRESHOLD_KMH:
        subject = f"⚠️ ALERTE VENT FORT : {max_wind:.0f} km/h prévus à Saint-Jean-de-Luz"
        body = f"""
Bonjour,

⚠️⚠️ ALERTE VENT FORT ⚠️⚠️

{max_wind:.0f} km/h prévus le {max_wind_time.strftime('%d/%m à %H:%M')}.
Seuil d'alerte : {WIND_THRESHOLD_KMH} km/h

{summary}

---------------
Prévisions OpenWeatherMap + api-maree.fr
"""
    else:
        subject = f"🌤️ Résumé météo et marées - Saint-Jean-de-Luz (J et J+1)"
        body = f"""
Bonjour,

Voici les prévisions météo et marées pour Saint-Jean-de-Luz :

{summary}

💨 Vent maximum sur 2 jours : {max_wind:.0f} km/h (à {max_wind_time.strftime('%d/%m à %H:%M')})
✅ Aucune alerte vent fort (seuil : {WIND_THRESHOLD_KMH} km/h)

---------------
Prévisions OpenWeatherMap + api-maree.fr
"""
    send_email(subject, body)

if __name__ == "__main__":
    main()
