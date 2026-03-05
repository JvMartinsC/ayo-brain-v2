import os
import json
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
# 1. Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Evolution API
EVO_URL = os.environ.get("EVO_URL")
EVO_KEY = os.environ.get("EVO_KEY")

# 3. Google Sheets
SHEET_ID = os.environ.get("SPREADSHEET_ID")
try:
    creds_json = json.loads(os.environ.get("GOOGLE_CREDS"))
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    anamnese_tab = sheet.worksheet("Anamneses")
    estado_tab = sheet.worksheet("Estado_Conversa")
except Exception as e:
    print(f"Erro ao conectar na Planilha: {e}")

# --- LÓGICA DO WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # Verifica se é uma mensagem recebida
    if 'data' in data and 'message' in data['data']:
        try:
            # Captura dados da mensagem
            remote_jid = data['data']['key']['remoteJid']
            # Verifica se é áudio ou texto
            message_body = ""
            
            if 'conversation' in data['data']['message']:
                message_body = data['data']['message']['conversation']
            elif 'extendedTextMessage' in data['data']['message']:
                message_body = data['data']['message']['extendedTextMessage']['text']
            
            # Se for áudio, poderíamos processar aqui, mas vamos focar no fluxo inicial
            if not message_body:
                message_body = "[Mensagem de Áudio ou Mídia]"

            # 1. Instrução da Ayo
            prompt = (
                "Você é Ayo, a assistente da psicóloga Aline Machado. Sua voz é acolhedora, "
                "poética e focada em ancestralidade. Nunca use termos médicos frios. "
                "O objetivo é fazer uma anamnese fluida. Pergunte sobre o nome, história e motivação. "
                f"O paciente disse: {message_body}. Responda de forma breve e gentil."
            )
            
            response = model.generate_content(prompt)
            texto_resposta = response.text

            # 2. Envia a resposta de volta pelo WhatsApp
            send_url = f"{EVO_URL}/message/sendText/Ayo-Bot"
            headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
            payload = {
                "number": remote_jid.split('@')[0],
                "text": texto_resposta,
                "delay": 1200
            }
            requests.post(send_url, json=payload, headers=headers)

            return jsonify({"status": "success"}), 200

        except Exception as e:
            print(f"Erro no processamento: {e}")
            return jsonify({"status": "error"}), 500

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
