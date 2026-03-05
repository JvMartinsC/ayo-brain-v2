import os
import json
import requests
from flask import Flask, request, jsonify
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
# 1. Gemini - FORÇANDO VERSÃO ESTÁVEL V1
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# O segredo está aqui: transport='rest' evita bugs de versão em alguns servidores
genai.configure(api_key=GEMINI_KEY, transport='rest')

# Forçamos o modelo flash sem o prefixo 'models/' para evitar erro de busca
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Evolution API
EVO_URL = os.environ.get("EVO_URL", "").rstrip('/')
EVO_KEY = os.environ.get("EVO_KEY")

# 3. Google Sheets
SHEET_ID = os.environ.get("SPREADSHEET_ID")
try:
    creds_json = json.loads(os.environ.get("GOOGLE_CREDS"))
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    try:
        anamnese_tab = sheet.worksheet("Anamneses")
        estado_tab = sheet.worksheet("Estado_Conversa")
    except:
        print("Aviso: Abas da planilha não encontradas. O bot seguirá sem salvar dados.")
except Exception as e:
    print(f"Erro ao conectar na Planilha: {e}")

# --- LÓGICA DO WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # 1. Segurança: Ignora mensagens do próprio bot
    if data.get('data', {}).get('key', {}).get('fromMe', False):
        return jsonify({"status": "ignored_self"}), 200

    # 2. Verifica se há mensagem
    if 'data' in data and 'message' in data['data']:
        try:
            remote_jid = data['data']['key']['remoteJid']
            message_body = ""
            msg_content = data['data']['message']
            
            # Extração de texto (simples ou estendido)
            if 'conversation' in msg_content:
                message_body = msg_content['conversation']
            elif 'extendedTextMessage' in msg_content:
                message_body = msg_content['extendedTextMessage']['text']
            
            if not message_body:
                return jsonify({"status": "no_text_content"}), 200

            # 3. Prompt da Ayo
            prompt = (
                "Você é Ayo, a assistente da psicóloga Aline Machado. Sua voz é acolhedora, "
                "poética e focada em ancestralidade. Nunca use termos médicos frios. "
                "O objetivo é fazer uma anamnese fluida. Pergunte sobre o nome, história e motivação. "
                f"O paciente disse: {message_body}. Responda de forma breve, gentil e preta."
            )
            
            # 4. Chamada ao Gemini (v1)
            response = model.generate_content(prompt)
            texto_resposta = response.text

            # 5. Envio para Evolution API
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
            # Se o erro for o 404 de modelo, ele aparecerá aqui no log
            print(f"Erro no processamento: {e}")
            return jsonify({"status": "error", "details": str(e)}), 500

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    # O Railway usa a porta 8080 por padrão
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
