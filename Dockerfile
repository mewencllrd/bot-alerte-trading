# Utiliser l'image de base Python
FROM python:3.10-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier tous les fichiers dans l'image
COPY . /app

# Mettre à jour pip et installer les dépendances
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Exécuter le bot
CMD ["python", "main.py"]
