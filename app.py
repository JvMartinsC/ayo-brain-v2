import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EVO_URL = os.environ.get("EVO_URL", "").rstrip('/')
EVO_KEY = os.environ.get("EVO_KEY")

def perguntar_ao_gemini(texto_usuario):
    # Mudança para o modelo 'latest' que resolve o erro 404 em chaves novas
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    payload = {"contents": [{"parts": [{"text": f"Você é Ayo, assistente da Aline Machado. Responda breve e gentil: {texto_usuario}"}]}]}
    
    try:
        response = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
        res_data = response.json()
        if response.status_code == 200:
            return res_data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Erro Google: {res_data}")
            return "Estou pensando... pode repetir?"
    except:
        return "Tive um erro de conexão."

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Log para você ver o que está chegando
    print(f"Recebido: {json.dumps(data)}")

    if data.get('data', {}).get('key', {}).get('fromMe'):
        return jsonify({"status": "ignored"}), 200

    try:
        # Pega o JID e a mensagem
        remote_jid = data['data']['key']['remoteJid']
        msg_content = data['data']['message']
        text = msg_content.get('conversation') or msg_content.get('extendedTextMessage', {}).get('text')

        if text:
            resposta = perguntar_ao_gemini(text)
            
            # ENVIO - Verifique se 'Ayo-Bot' é o nome da sua instância!
            send_url = f"{EVO_URL}/message/sendText/Ayo-Bot"
            payload = {
                "number": remote_jid.split('@')[0],
                "text": resposta
            }
            requests.post(send_url, json=payload, headers={"apikey": EVO_KEY})
            
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
