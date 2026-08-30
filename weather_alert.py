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

# Fuseau horaire de Paris (UTC+2 en été, UTC+1 en hiver)
PARIS_TZ = timezone(timedelta(hours=2))

# Seuil de vent en km/h
WIND_THRESHOLD_KMH = 40

# ========== FONCTIONS ==========
def get_weather_forecast():
    """Récupère les prévisions météo sur 5 jours (tranches de 3h)."""
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur lors de la requête API : {e}")
        return None

def summarize_day(forecast_data):
    """Crée un résumé de la journée du jour (matin et soir)."""
    today = datetime.now(PARIS_TZ).date()
    day_items = []
    
    for item in forecast_data["list"]:
        dt = datetime.fromtimestamp(item["dt"], tz=PARIS_TZ)
        if dt.date() == today:
            day_items.append({
                "time": dt,
                "hour": dt.hour,
                "temp": item["main"]["temp"],
                "weather_desc": item["weather"][0]["description"],
                "weather_main": item["weather"][0]["main"],
                "rain_mm": item.get("rain", {}).get("3h", 0),
                "pop": item.get("pop", 0),  # Probabilité de précipitation
                "wind_speed_kmh": item["wind"]["speed"] * 3.6,
            })
    
    if not day_items:
        return "Aucune prévision disponible pour aujourd'hui."
    
    # Sépare les prévisions du matin (avant 12h) et du soir (après 12h)
    morning = [i for i in day_items if i["hour"] < 12]
    afternoon = [i for i in day_items if i["hour"] >= 12]
    
    def summarize_period(items, label):
        if not items:
            return f"{label} : Aucune donnée"
        
        temps = [i["temp"] for i in items]
        min_temp = min(temps)
        max_temp = max(temps)
        
        # Météo dominante (la plus fréquente)
        weather_counts = {}
        for i in items:
            w = i["weather_desc"].capitalize()
            weather_counts[w] = weather_counts.get(w, 0) + 1
        dominant_weather = max(weather_counts, key=weather_counts.get)
        
        # Pluie totale et probabilité max
        total_rain = sum(i["rain_mm"] for i in items)
        max_pop = max(i["pop"] for i in items)
        
        # Vent max
        max_wind = max(i["wind_speed_kmh"] for i in items)
        
        # Indicateur soleil/nuages/pluie
        if total_rain > 1.0:
            icon = "🌧️"
        elif "nuage" in dominant_weather.lower():
            icon = "☁️"
        else:
            icon = "☀️"
        
        return (f"{icon} {label} : {dominant_weather} "
                f"| Temp: {min_temp:.0f}°C - {max_temp:.0f}°C "
                f"| Pluie: {total_rain:.1f}mm ({max_pop*100:.0f}% risque) "
                f"| Vent max: {max_wind:.0f} km/h")
    
    summary = "📋 RÉSUMÉ DE LA JOURNÉE :\n"
    summary += summarize_period(morning, "🌅 Matin   ")
    summary += "\n" + summarize_period(afternoon, "🌆 Après-midi")
    
    return summary

def check_wind_alert(forecast_data):
    """Vérifie si le vent dépasse le seuil sur les prochaines 24h."""
    today = datetime.now(PARIS_TZ).date()
    max_wind = 0
    max_wind_time = None
    
    for item in forecast_data["list"]:
        dt = datetime.fromtimestamp(item["dt"], tz=PARIS_TZ)
        if dt.date() == today:
            wind_speed_kmh = item["wind"]["speed"] * 3.6
            if wind_speed_kmh > max_wind:
                max_wind = wind_speed_kmh
                max_wind_time = dt
    
    return max_wind, max_wind_time

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
    
    data = get_weather_forecast()
    if not data:
        print("❌ Impossible de récupérer les données météo.")
        return
    
    # Résumé de la journée
    day_summary = summarize_day(data)
    print(day_summary)
    
    # Vérification du vent
    max_wind, max_wind_time = check_wind_alert(data)
    print(f"💨 Vent maximum aujourd'hui : {max_wind:.1f} km/h (à {max_wind_time.strftime('%H:%M')})")
    
    # Décision d'envoi d'email
    if max_wind > WIND_THRESHOLD_KMH:
        subject = f"⚠️ Alerte vent fort : {max_wind:.0f} km/h prévus à Saint-Jean-de-Luz"
        body = f"""
Bonjour,

⚠️ ALERTE VENT FORT ⚠️

{day_summary}

💨 Vent maximum prévu : {max_wind:.0f} km/h à {max_wind_time.strftime('%H:%M')}
Seuil d'alerte : {WIND_THRESHOLD_KMH} km/h

---------------
Prévisions OpenWeatherMap pour Saint-Jean-de-Luz
        """
        send_email(subject, body)
    else:
        # Envoi du résumé quotidien même sans alerte
        subject = f"🌤️ Résumé météo du jour - Saint-Jean-de-Luz"
        body = f"""
{day_summary}

💨 Vent maximum prévu : {max_wind:.0f} km/h (à {max_wind_time.strftime('%H:%M')})
✅ Aucune alerte vent fort (seuil : {WIND_THRESHOLD_KMH} km/h)

---------------
Prévisions OpenWeatherMap
        """
        send_email(subject, body)
        print("ℹ️ Email de résumé envoyé (pas d'alerte).")

if __name__ == "__main__":
    main()
