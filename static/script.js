let chunks = [];
let recorder;
let isRecording = false;
let isProcessing = false; // Variable para rastrear si se está procesando una pregunta

const recordButton = document.getElementById('recordButton');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const chatBox = document.getElementById('chat-box');

userInput.addEventListener('input', () => {
    sendButton.disabled = userInput.value.trim() === '' || isProcessing;
});

sendButton.addEventListener('click', () => {
    const message = userInput.value.trim();
    if (message && !isProcessing) {
        isProcessing = true; // Marcar que se está procesando una pregunta
        appendMessage('user', message);
        userInput.value = '';
        sendButton.disabled = true;
        processMessage(message);
    }
});

recordButton.addEventListener('click', () => {
    if (!isRecording) {
        // Comenzar a grabar
        chunks = [];
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                recorder = new MediaRecorder(stream);
                recorder.start();
                isRecording = true;
                recordButton.textContent = 'Detener';

                recorder.ondataavailable = e => {
                    chunks.push(e.data);
                    if (recorder.state == 'inactive') {
                        let blob = new Blob(chunks, { type: 'audio/wav' });
                        uploadAudio(blob);
                    }
                };
            }).catch(console.error);
    } else {
        // Detener la grabación
        recorder.stop();
        isRecording = false;
        recordButton.textContent = 'Grabar';
    }
});

function uploadAudio(blob) {
    let formData = new FormData();
    formData.append('audio', blob, 'input.wav');

    fetch('/transcribe', {
        method: 'POST',
        body: formData
    })
        .then(response => response.text())
        .then(text => {
            userInput.value = text; // Mostrar la transcripción en el cuadro de texto
            sendButton.disabled = false; // Habilitar el botón de enviar
        })
        .catch(console.error);
}

function appendMessage(sender, message) {
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    if (sender === 'user') {
        messageElement.classList.add('user-message');
    } else {
        messageElement.classList.add('bot-message');
    }
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function processMessage(message) {
    fetch('/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ question: message })
    })
        .then(response => response.json())
        .then(data => {
            appendMessage('bot', data.answer);
            isProcessing = false; // Marcar que se ha terminado de procesar la pregunta
            sendButton.disabled = userInput.value.trim() === ''; // Volver a habilitar el botón de envío si el cuadro de texto no está vacío
        })
        .catch(console.error);
}