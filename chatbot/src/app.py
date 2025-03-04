import time
import logging
from flask import Flask, request, send_from_directory, Response, jsonify
import uuid
from flask_socketio import SocketIO, emit
from transformers import AutoTokenizer, AutoModel, pipeline
from sentence_transformers import util
import os, torch
from fuzzywuzzy import fuzz
from pymongo import MongoClient
from flask_cors import CORS

# Carica il modello direttamente da Hugging Face
model_name = "tatore22/legal_bert_chatbot"
qa_pipeline = pipeline("text2text-generation", model=model_name)

# Carica il modello Legal-BERT
tokenizer = AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased")
legal_bert_model = AutoModel.from_pretrained("nlpaueb/legal-bert-base-uncased")
# Domande generiche comuni
generic_questions = ["cos'è", "cosa fa", "a cosa serve", "come funziona", "che cos'è", "puoi spiegare"]

# Configura il logging per debug
logging.basicConfig(level=logging.INFO)

# Connessione a MongoDB Atlas (sostituisci con le tue credenziali)
MONGO_URI = "-"
client = MongoClient(MONGO_URI)

# Seleziona il database e la collection
db = client["chatbotDB"]  # Sostituisci con il tuo database
collection = db["qa_collection"]
# Database per gestione chat multiple
chat_db = client["chatbot02"]
messages_collection = chat_db["messages"]

def is_relevant_fuzzy(query, candidate_question, threshold=75):
    """Verifica se la domanda candidata è sufficientemente simile alla query originale."""
    similarity_score = fuzz.partial_ratio(query.lower(), candidate_question.lower())
    return similarity_score >= threshold  # Restituisce True se supera la soglia

# Funzione per calcolare gli embedding con Legal-BERT
def compute_legal_bert_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    with torch.no_grad():
        outputs = legal_bert_model(**inputs)
        return outputs.last_hidden_state.mean(dim=1)  # Media sull'ultima dimensione per l'embedding

def get_topic_from_question(query_text):
    """Identifica il topic più vicino alla domanda dell'utente"""
    topics = collection.distinct("argomento")  # Estrae tutti gli argomenti nel database
    best_match = None
    highest_similarity = 0

    for topic in topics:
        # Confronto fuzzy tra la domanda e l'argomento
        similarity = fuzz.partial_ratio(query_text.lower(), topic.lower())
        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = topic

    return best_match if highest_similarity > 60 else None  # Usa una soglia di 60

def search_context_with_embeddings(query_text):
    """Cerca il contesto migliore combinando topic e embeddings"""
    topic = get_topic_from_question(query_text)
    query_embedding = compute_legal_bert_embedding(query_text)
    relevant_contexts = []

    query_filter = {"argomento": topic} if topic else {}

    for doc in collection.find(query_filter):
        question_embedding = compute_legal_bert_embedding(doc["domanda"])
        context_embedding = compute_legal_bert_embedding(doc["contesto"])

        question_similarity = util.pytorch_cos_sim(query_embedding, question_embedding).item()
        context_similarity = util.pytorch_cos_sim(query_embedding, context_embedding).item()

        combined_similarity = 0.7 * question_similarity + 0.3 * context_similarity

        if combined_similarity > 0.5 and is_relevant_fuzzy(query_text, doc["domanda"]):
            relevant_contexts.append((combined_similarity, f"Domanda: {doc['domanda']} Contesto: {doc['contesto']}"))

    relevant_contexts.sort(key=lambda x: x[0], reverse=True)
    return [context for _, context in relevant_contexts[:3]] if relevant_contexts else None

# Nuova funzione per generare la risposta parola per parola
def generate_response_stream(question, context, socket, chat_id):
    """Genera la risposta parola per parola per lo streaming tramite Socket.IO."""
    response = ""
    try:
        if len(context) > 1:
            for relevant_context in context:
                result = qa_pipeline(relevant_context, max_length=512, num_return_sequences=1, num_beams=5, early_stopping=True)
                if not result or 'generated_text' not in result[0]:
                    socket.emit('message', '⚠️ Errore nella generazione della risposta.')
                    return

                response += " " + result[0]['generated_text']

            for word in response.split():
                socket.emit('message', word)
                time.sleep(0.3)  # Simula un delay tra le parole per creare l'effetto di "streaming"

            socket.emit('message', '[FINE]')
        else:
            result = qa_pipeline(context, max_length=512, num_return_sequences=1, num_beams=5, early_stopping=True)
            if not result or 'generated_text' not in result[0]:
                socket.emit('message', '⚠️ Errore nella generazione della risposta.')
                return

            response = result[0]['generated_text']

            for word in response.split():
                socket.emit('message', word)
                time.sleep(0.3)

            socket.emit('message', '[FINE]')
    except Exception as e:
        socket.emit('message', f'⚠️ Errore nel server: {e}')
    
    # Inserisci il messaggio nel database
    messages_collection.insert_one({"chat_id": chat_id, "sender": "user", "text": question})
    messages_collection.insert_one({"chat_id": chat_id, "sender": "bot", "text": response})

# Inizializza l'app Flask
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173"])
CORS(app, origins=["http://localhost:5173"])  # Adjust with the URL of your frontend

@app.route("/create_chat", methods=["POST"])
def create_chat():
    """Crea una nuova chat e restituisce un chat_id univoco."""
    chat_id = str(uuid.uuid4())  # Genera un nuovo chat_id univoco
    return jsonify({"chat_id": chat_id})

@app.route("/get_chats", methods=["GET"])
def get_chats():
    """Recupera le chat esistenti dalla collection messages."""
    chats = messages_collection.distinct("chat_id")  # Ottieni tutti gli chat_id distinti
    return jsonify([{"chat_id": chat} for chat in chats])  # Restituisci un array di chat_id

@app.route("/get_messages/<chat_id>", methods=["GET"])
def get_messages(chat_id):
    """Recupera i messaggi di una chat specifica."""
    messages = list(messages_collection.find({"chat_id": chat_id}, {"_id": 0}).sort("timestamp", 1))  # Ordinato per timestamp crescente
    return jsonify(messages)

# Serve la pagina index.html da React
@app.route('/', methods=['GET'])
def home():
    return send_from_directory(os.path.join(app.root_path, 'build'), 'index.html')

@app.route("/stream", methods=["GET"])
def stream():
    question = request.args.get("question", "")
    chat_id = request.args.get("chat_id")  # Prendi il chat_id dalla richiesta
    context = search_context_with_embeddings(question)

    return Response(generate_response_stream(question, context, socketio, chat_id), content_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

# Gestione del WebRTC tramite Socket.IO
@socketio.on('offer')
def handle_offer(data):
    chat_id = data.get("chat_id")
    question = data['question']
    context = search_context_with_embeddings(question)
    generate_response_stream(question, context, socketio, chat_id)

@socketio.on('answer')
def handle_answer(data):
    print("Answer received:", data)

@socketio.on('ice-candidate')
def handle_ice_candidate(data):
    print("ICE candidate received:", data)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
