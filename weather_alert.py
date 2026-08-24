import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

# Récupérer les variables d'environnement (configurées dans GitHub Secrets)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
EMAIL_TO = os.getenv("EMAIL_TO")  # m.sainttjean@gmail.com
SMTP_USER = os.getenv("SMTP_USER")  # m.sainttjean@gmail.com
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Coordonnées de Saint-Jean-de-Luz (64500)
LAT = 43.3858
LON = -1.6606

def get_weather_forecast():
    """Récupère les prévisions météo via OpenWeatherMap."""
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={OPENWEATHER_API_KEY}&units=metric&lang=fr"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la requête API : {e}")
        return None

def check_wind_speed(forecast_data):
    """Vérifie si le vent dépasse 40 km/h dans les prochaines 24h."""
    if not forecast_data:
        return False, 0
    for item in forecast_data["list"]:
        wind_speed_kmh = item["wind"]["speed"] * 3.6  # Convertir de m/s à km/h
        if wind_speed_kmh > 40:
        # if wind_speed_kmh > 0:
            return True, wind_speed_kmh
    return False, 0

def send_email(wind_speed):
    """Envoie un email d'alerte via Gmail."""
    subject = "⚠️ Alerte vent fort à Saint-Jean-de-Luz"
    body = f"""
    Bonjour,

    Un vent de {wind_speed:.1f} km/h est prévu aujourd'hui à Saint-Jean-de-Luz.
    Prends tes précautions !

    Cordialement,
    Ton agent météo
    """
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())
        print(f"[{datetime.now()}] Email envoyé avec succès ! Vent : {wind_speed:.1f} km/h")
    except Exception as e:
        print(f"[{datetime.now()}] Erreur lors de l'envoi de l'email : {e}")

def main():
    print(f"[{datetime.now()}] Début de la vérification météo...")
    forecast = get_weather_forecast()
    if forecast:
        has_strong_wind, wind_speed = check_wind_speed(forecast)
        if has_strong_wind:
            send_email(wind_speed)
        else:
            print(f"[{datetime.now()}] Aucun vent fort détecté.")
    else:
        print(f"[{datetime.now()}] Impossible de récupérer les données météo.")

if __name__ == "__main__":
    main()
