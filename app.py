import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EVO_URL = os.environ.get("EVO_URL", "").rstrip('/')
EVO_KEY = os.environ.get("EVO_KEY")

# --- FUNÇÃO PARA FALAR COM O GEMINI SEM DEPENDER DE BIBLIOTECA BUGADA ---
def perguntar_ao_gemini(texto_usuario):
    # Acessamos a versão v1 (estável) diretamente via URL
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    prompt_completo = (
        "Você é Ayo, a assistente da psicóloga Aline Machado. Sua voz é acolhedora, "
        "poética e focada em ancestralidade. Nunca use termos médicos frios. "
        f"O paciente disse: {texto_usuario}. Responda de forma breve e gentil."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_completo}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        
        if response.status_code != 200:
            print(f"Erro Real na API do Google: {response_data}")
            return "Estou em um momento de silêncio interno, pode repetir em instantes?"
            
        return response_data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return "Tive um pequeno tropeço. Pode falar comigo novamente?"

# --- LÓGICA DO WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # Evita que o bot responda a si mesmo
    if data.get('data', {}).get('key', {}).get('fromMe', False):
        return jsonify({"status": "ignored_self"}), 200

    if 'data' in data and 'message' in data['data']:
        try:
            remote_jid = data['data']['key']['remoteJid']
            msg_content = data['data']['message']
            
            # Pega o texto enviado
            message_body = msg_content.get('conversation') or \
                           msg_content.get('extendedTextMessage', {}).get('text')
            
            if not message_body:
                return jsonify({"status": "no_text"}), 200

            # Chama a Ayo
            resposta_texto = perguntar_ao_gemini(message_body)

            # Envia a resposta via Evolution API
            send_url = f"{EVO_URL}/message/sendText/Ayo-Bot"
            headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
            
            payload = {
                "number": remote_jid.split('@')[0],
                "text": resposta_texto,
                "delay": 1200
            }
            
            requests.post(send_url, json=payload, headers=headers)
            return jsonify({"status": "success"}), 200

        except Exception as e:
            print(f"Erro Geral: {e}")
            return jsonify({"status": "error"}), 500

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
