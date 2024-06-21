import pandas as pd
import sqlite3
import os
from langchain_community.llms import HuggingFaceEndpoint
from langchain.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from huggingface_hub import login

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from faster_whisper import WhisperModel
import os

# Reemplaza 'your_token_here' con tu token real
hf_token = "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"

# Configura la variable de entorno para el token
os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_token
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# Iniciar sesión utilizando el token
login(token=hf_token)

df = pd.read_csv("./pob_gto.csv", encoding='utf-8')

# Connect to a new SQLite database
con = sqlite3.connect('my_data.db')

# Write the DataFrame to the SQL database
df.to_sql('pob_gto', con, if_exists='replace', index=False)

db = SQLDatabase.from_uri("sqlite:///my_data.db")

# Define the repository ID for the Mistral 2b model
repo_id = "mistralai/Mistral-7B-Instruct-v0.2"

# Set up a Hugging Face Endpoint for Mistral 2b model
llm = HuggingFaceEndpoint(
    repo_id=repo_id,
    temperature=0.1,
    max_new_tokens=400
    #model_kwargs={"device": "cuda:0"}
)

db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'wav', 'mp3'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    audio_file = request.files['audio']
    if audio_file.filename == '' or not allowed_file(audio_file.filename):
        return jsonify({'error': 'Invalid file'}), 400

    filename = secure_filename(audio_file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_file.save(file_path)

    segments, info = model.transcribe(file_path, beam_size=5)
    os.remove(file_path)

    transcript = "\n".join(segment.text for segment in segments)
    return transcript

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    question = data.get('question')

    try:
        Question = db_chain.invoke(question)

        if isinstance(Question, dict):
            answer = Question.get('result') or Question.get('Answer', 'No se encontró una respuesta.')
        else:
            resultado_texto = str(Question)
            inicio_answer = resultado_texto.find("Answer:") + len("Answer:")
            answer = resultado_texto[inicio_answer:].strip()

            # Verificar si la respuesta es un mensaje de error
            if "OperationalError" in resultado_texto or "syntax error" in resultado_texto:
                answer = "No se pudo realizar esa consulta. Intente con otra."
    except Exception as e:
        # Manejo de errores generales
        answer = "No se pudo realizar esa consulta. Intente con otra."

    return jsonify({'answer': answer})

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host="0.0.0.0", port=5000)