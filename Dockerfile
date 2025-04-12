# Utilisation de l'image Python officielle comme base
FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier tous les fichiers dans le conteneur
COPY . /app

# Installer les dépendances
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Exécuter le bot
CMD ["python", "main.py"]
