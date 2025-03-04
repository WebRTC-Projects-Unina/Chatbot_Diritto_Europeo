from pymongo import MongoClient
import json

# Connessione al database MongoDB Atlas
MONGO_URI="-"
client = MongoClient(MONGO_URI)

# Seleziona il database e la collection
db = client["chatbotDB"]
collection = db["qa_collection"]

# Carica il file JSON
with open("articles.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Inserisce direttamente i documenti
collection.insert_many(data["questions"])  # Assumendo che "questions" sia un array di oggetti

print("Dati importati con successo in MongoDB Atlas!")
