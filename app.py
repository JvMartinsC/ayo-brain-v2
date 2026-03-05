import os
import json
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
# 1. Gemini - Ajustado para evitar o erro 404
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

# Tenta pegar o modelo da variável ou usa o flash de forma estável
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
model = genai.GenerativeModel(model_name=MODEL_NAME)

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
    # Tenta acessar as abas, se não existirem o bot ainda funciona mas avisa no log
    try:
        anamnese_tab = sheet.worksheet("Anamneses")
        estado_tab = sheet.worksheet("Estado_Conversa")
    except:
        print("Aviso: Abas da planilha não encontradas. Verifique os nomes.")
except Exception as e:
    print(f"Erro ao conectar na Planilha: {e}")

# --- LÓGICA DO WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # Ignora mensagens enviadas pelo próprio bot para evitar loops
    if data.get('data', {}).get('key', {}).get('fromMe', False):
        return jsonify({"status": "ignored_self"}), 200

    # Verifica se é uma mensagem recebida
    if 'data' in data and 'message' in data['data']:
        try:
            # Captura dados da mensagem
            remote_jid = data['data']['key']['remoteJid']
            
            message_body = ""
            msg_content = data['data']['message']
            
            if 'conversation' in msg_content:
                message_body = msg_content['conversation']
            elif 'extendedTextMessage' in msg_content:
                message_body = msg_content['extendedTextMessage']['text']
            
            if not message_body:
                return jsonify({"status": "no_text_to_process"}), 200

            # 1. Instrução da Ayo
            prompt = (
                "Você é Ayo, a assistente da psicóloga Aline Machado. Sua voz é acolhedora, "
                "poética e focada em ancestralidade. Nunca use termos médicos frios. "
                "O objetivo é fazer uma anamnese fluida. Pergunte sobre o nome, história e motivação. "
                f"O paciente disse: {message_body}. Responda de forma breve e gentil."
            )
            
            # Geração da resposta
            response = model.generate_content(prompt)
            texto_resposta = response.text

            # 2. Envia a resposta de volta pelo WhatsApp via Evolution API
            # Removemos a barra final da URL se houver para evitar erro no path
            base_url = EVO_URL.rstrip('/')
            send_url = f"{base_url}/message/sendText/Ayo-Bot"
            
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
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.
