# Legal Chatbot

Questo progetto è un chatbot basato su **React** per il frontend e **Flask** per il backend. Utilizza **MongoDB Atlas** come database per gestire le conversazioni e le risposte predefinite.

## Tecnologie utilizzate

### Frontend

- **React** (con Vite per la configurazione)
- **socket.io-client** per la comunicazione in tempo reale con il backend

### Backend

- **Flask**
- **Flask-SocketIO** per la comunicazione WebSocket
- **Transformers** (Hugging Face) per NLP
- **Sentence-Transformers** per il confronto tra frasi
- **FuzzyWuzzy** per il fuzzy matching
- **PyMongo** per la gestione del database
- **Flask-CORS** per la gestione della comunicazione tra frontend e backend

## Installazione e configurazione

### 1. Clonare il repository

```bash
git clone https://github.com/WebRTC-Projects-Unina/Chatbot_Diritto_Europeo.git
cd Chatbot_Diritto_Europeo

```

### 2. Configurare il database MongoDB Atlas

Per far funzionare l'applicazione, bisogna creare **due database** in **MongoDB Atlas**:

1. **chatbotDB** con la **collection** `qa_collection`
2. **chatbot02** con la **collection** `messages`

tramite il sito ufficiale:  https://www.mongodb.com/cloud/atlas

Recuperare la **chiave di connessione** e inserirla in `MONGO_URI` nei file:

- `convert_db.py`
- `chatbot/src/app.py`


### 3. Esegui lo script per popolare il database

```bash
python convert_db.py

```

Assicurati che nella sezione "Network Access" di MongoDB Atlas vengano consentite le richieste dal tuo indirizzo IP.

### 4. Installare le dipendenze

#### Backend

Assicurati di avere **Python 3.11.7** installato.

```bash

pip install -r requirements.txt

```

#### Frontend

Assicurati di avere **Node.js** installato.

```bash
npm install
```

### 5. Spostati nella cartella dell'applicazione

Prima di avviare l'applicazione

```bash
cd chatbot
```

### 6. Crea due terminali separati 

Nel primo terminale avvia il backend:

```bash
cd src
python app.py
```
Nel secondo terminale fai partire il frontend: 

```bash
npm run dev
```

Ora l'applicazione sarà disponibile all'indirizzo locale mostrato da Vite, nel terminale dedicato al frontend.



