def start_bot():
    print("🤖 Bot Telegram en cours de démarrage... ")

    # Appelle ici les fonctions du bot que tu veux lancer
    # Exemple :
    from price_tracker import launch_price_check_loop
    launch_price_check_loop()

    # Tu peux aussi lancer d’autres tâches comme l’envoi automatique de récap
