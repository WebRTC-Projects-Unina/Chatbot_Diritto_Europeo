import React, { useState, useEffect } from 'react';
import '../css/Chatbot.css';  // Importa il file CSS
import { io } from 'socket.io-client'; // Importa socket.io-client

const Chatbot = () => {
  const [userInput, setUserInput] = useState('');
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [disableSend, setDisableSend] = useState(false);
  const [socket, setSocket] = useState(null);  // Stato per gestire il socket
  const [chatId, setChatId] = useState(null);  // Stato per il chat_id
  const [chats, setChats] = useState([]);  // Stato per l'elenco delle chat

  // Stabilire la connessione al server Socket.IO
  useEffect(() => {
    const newSocket = io('http://127.0.0.1:5000');  // Assicurati che l'URL sia corretto
    setSocket(newSocket);

    // Recupera l'elenco delle chat esistenti dal backend
    const fetchChats = async () => {
      const response = await fetch('http://127.0.0.1:5000/get_chats');
      const data = await response.json();
      setChats(data);  // Salva le chat esistenti
    };
    fetchChats();

    // Crea una nuova chat o carica quella selezionata dal localStorage
    const storedChatId = localStorage.getItem('selectedChat');
    if (storedChatId) {
      setChatId(storedChatId);
      loadMessages(storedChatId);
    } else {
      const createChat = async () => {
        const response = await fetch('http://127.0.0.1:5000/create_chat', {
          method: 'POST',
        });
        const data = await response.json();
        setChatId(data.chat_id);
        localStorage.setItem('selectedChat', data.chat_id);  // Memorizza la chat nel localStorage
      };
      createChat();
    }

    return () => {
      newSocket.disconnect();
    };
  }, []);

  // Carica i messaggi di una chat selezionata
  const loadMessages = async (chatId) => {
    setConversation([]);  // Pulisci la conversazione
    const response = await fetch(`http://127.0.0.1:5000/get_messages/${chatId}`);
    const data = await response.json();
    setConversation(data);
  };

  // Gestire l'invio del messaggio
  const handleSubmit = (event) => {
    event.preventDefault();
    if (!userInput.trim()) return;

    // Aggiunge il messaggio dell'utente alla conversazione
    setConversation((prev) => [
      ...prev,
      { sender: 'user', text: userInput },
    ]);
    setLoading(true);
    setDisableSend(true);
    setUserInput('');

    // Aggiunge il messaggio di caricamento animato (puntino lampeggiante)
    setConversation((prev) => [...prev, { sender: 'bot', text: '⏳' }]);

    // Invia la domanda tramite WebSocket al server con il chat_id
    if (socket && chatId) {
      socket.emit('offer', { question: userInput, chat_id: chatId });
    }
  };

  // Gestire i messaggi ricevuti dal server tramite Socket.IO
  useEffect(() => {
    if (socket) {
      socket.on('message', (data) => {
        if (data === '[FINE]') {
          setLoading(false);
          setDisableSend(false);
          return;
        }

        // Aggiungere i dati (parola) alla conversazione
        setConversation((prev) => {
          return prev.map((msg, index, arr) => {
            if (index === arr.length - 1 && msg.sender === 'bot') {
              if (msg.text === '⏳') {
                return { ...msg, text: data };
              }
              return {
                ...msg,
                text: msg.text.endsWith(data) ? msg.text : msg.text + ' ' + data,
              };
            }
            return msg;
          });
        });
      });
    }

    // Pulizia quando il componente si smonta
    return () => {
      if (socket) {
        socket.off('message');
      }
    };
  }, [socket]);

  // Gestire la selezione di una chat
  const handleSelectChat = (chatId) => {
    setChatId(chatId);
    localStorage.setItem('selectedChat', chatId);  // Memorizza la chat nel localStorage
    loadMessages(chatId);
  };

  // Funzione per creare una nuova chat vuota
  const handleCreateChat = async () => {
    const response = await fetch('http://127.0.0.1:5000/create_chat', {
      method: 'POST',
    });
    const data = await response.json();
    setChats((prevChats) => [...prevChats, data]);  // Aggiungi la nuova chat alla lista
    handleSelectChat(data.chat_id);  // Seleziona subito la nuova chat
  };

  return (
    <div className="page-container">
      {/* Sidebar per la selezione della chat */}
      <div className="sidebar">
        <h2>Seleziona una chat</h2>
        <button onClick={handleCreateChat}>Crea una nuova chat</button>
        {chats.length > 0 ? (
          <ul>
            {chats.map((chat, index) => (
              <li
                key={index}
                onClick={() => handleSelectChat(chat.chat_id)}  // Passiamo il chat_id vero
                style={{ cursor: 'pointer', padding: '10px', borderBottom: '1px solid #ccc' }}
              >
                Chat{index} {/* Mostra chat0, chat1, chat2, ecc. */}
              </li>
            ))}
          </ul>
        ) : (
          <p>Nessuna chat disponibile</p>
        )}
    </div>
    {/* Container principale per la chat */}
      <div className="chatbox-container">
        <h1>Legal Chatbot</h1>

        <div className="chat-box">
          {conversation.map((entry, index) => (
            <div key={index} className={`chat-entry ${entry.sender}`}>
              <div className={entry.sender}>
                {entry.sender === 'user' ? 'Utente' : 'Bot'}:
              </div>
              <div className="message">
                {entry.text === '⏳' ? (
                  <span className="bot-typing">•</span> // Puntino lampeggiante
                ) : (
                  entry.text
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="input-group">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Fai una domanda..."
          />
          <button onClick={handleSubmit} disabled={loading || disableSend}>
            Invia
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;
