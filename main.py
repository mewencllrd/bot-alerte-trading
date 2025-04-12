print("✅ Bot lancé sur Railway")

from indicators import *  # utile pour charger les fonctions si besoin ailleurs

# ... (main bot fusionné ici)

if __name__ == "__main__":
    print("⏳ Initialisation du bot en cours...")

    from telegram_bot import start_bot
    start_bot()
