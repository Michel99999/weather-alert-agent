# 🌦️ Agent Météo - Alerte Vent Fort

Ce projet vérifie quotidiennement la météo pour **Saint-Jean-de-Luz (64500)** et envoie un email si un vent > 40 km/h est prévu.

## 📌 Configuration

### 1️⃣ Secrets GitHub
Pour que le script fonctionne, tu dois ajouter les **secrets** suivants dans ton dépôt GitHub :
1. Va dans **Settings > Secrets and variables > Actions**.
2. Ajoute les secrets suivants :
   Nom du secret          | Valeur à ajouter                          |
 |------------------------|-------------------------------------------|
 | `OPENWEATHER_API_KEY`  | `7e932054b27d6ea62a0d0dfdf0487cdc`        |
 | `EMAIL_TO`             | `m.sainttjean@gmail.com`                  |
 | `SMTP_USER`            | `m.sainttjean@gmail.com`                  |
 | `SMTP_PASSWORD`        | *(Ton App Password Gmail ou mot de passe)*|

⚠️ **Pour Gmail** :
- Si tu utilises la **2FA**, génère un **App Password** ici : [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords).
- Si tu n'utilises pas la 2FA, active l'option **"App moins sécurisées"** ici : [https://myaccount.google.com/lesssecureapps](https://myaccount.google.com/lesssecureapps).

### 2️⃣ Lancer manuellement
Tu peux lancer le workflow manuellement depuis l'onglet **Actions** de ton dépôt GitHub.

### 3️⃣ Vérifier les logs
- Va dans **Actions > Weather Alert** pour voir les logs d'exécution.
- Si une erreur survient, les détails seront affichés ici.

## 🔧 Personnalisation
- **Changer la localisation** : Modifie les coordonnées `LAT` et `LON` dans `weather_alert.py`.
- **Changer le seuil de vent** : Modifie la valeur `40` dans la fonction `check_wind_speed`.
- **Changer l'heure d'exécution** : Modifie la ligne `cron: '0 6 * * *'` dans `.github/workflows/weather_alert.yml`.

## 📧 Exemple d'email reçu