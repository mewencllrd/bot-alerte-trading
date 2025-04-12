import schedule
import time

def send_weekly_summary():
    print("📊 Envoi automatique du récapitulatif hebdomadaire...")

    # Ici, tu appelles ta fonction d'envoi de récap dans telegram_bot.py
    # Ex : send_telegram_summary()

# Planifie la tâche tous les dimanches à 22h
schedule.every().sunday.at("22:00").do(send_weekly_summary)

def start_scheduler():
    print("⏰ Scheduler activé (attente du dimanche 22h)...")
    while True:
        schedule.run_pending()
        time.sleep(60)
