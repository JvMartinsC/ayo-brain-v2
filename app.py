import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIGURAÇÕES ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Ajuste automático da URL da Evolution para garantir o prefixo https://
EVO_URL = os.environ.get("EVO_URL", "")
if EVO_URL and not EVO_URL.startswith('http'):
    EVO_URL = f"https://{EVO_URL}"
EVO_URL = EVO_URL.rstrip('/')

EVO_KEY = os.environ.get("EVO_KEY")

# --- FUNÇÃO PARA FALAR COM O GEMINI ---
def perguntar_ao_gemini(texto_usuario):
    # Mudamos para o modelo 'gemini-pro' na v1beta, que é o mais compatível para APIs diretas
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    
    prompt_completo = (
        "Você é Ayo, a assistente da psicóloga Aline Machado. Sua voz é acolhedora, "
        "poética e focada em ancestralidade. Responda de forma breve e gentil. "
        f"O paciente disse: {texto_usuario}"
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt_completo}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        
        # Verifica se o Google devolveu a resposta corretamente
        if response.status_code == 200 and 'candidates' in response_data:
            return response_data['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"Erro Real na API do Google: {response_data}")
            return "Estou em um momento de silêncio interno, pode repetir em instantes?"
    except Exception as e:
        print(f"Erro de conexão no Gemini: {e}")
        return "Tive um pequeno tropeço nos pensamentos. Pode falar comigo novamente?"

# --- LÓGICA DO WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    # Segurança: Ignora mensagens que o próprio bot envia
    if data.get('data', {}).get('key', {}).get('fromMe', False):
        return jsonify({"status": "ignored_self"}), 200

    if 'data' in data and 'message' in data['data']:
        try:
            remote_jid = data['data']['key']['remoteJid']
            msg_content = data['data']['message']
            
            # Extração do texto (simples ou estendido)
            message_body = msg_content.get('conversation') or \
                           msg_content.get('extendedTextMessage', {}).get('text')
            
            if not message_body:
                return jsonify({"status": "no_text_content"}), 200

            # Chama o cérebro da Ayo
            resposta_ayo = perguntar_ao_gemini(message_body)

            # Envia para a Evolution API
            send_url = f"{EVO_URL}/message/sendText/Ayo-Bot"
            headers = {"apikey": EVO_KEY, "Content-Type": "application/json"}
            
            payload = {
                "number": remote_jid.split('@')[0],
                "text": resposta_ayo,
                "delay": 1200
            }
            
            res_evo = requests.post(send_url, json=payload, headers=headers)
            
            # Log de erro caso a Evolution recuse
            if res_evo.status_code not in [200, 201]:
                print(f"Erro ao enviar para Evolution: {res_evo.text}")

            return jsonify({"status": "success"}), 200

        except Exception as e:
            print(f"Erro Geral no Webhook: {e}")
            return jsonify({"status": "error"}), 500

    return jsonify({"status": "ignored"}), 200

if __name__ == "__main__":
    # O Railway usa a porta 8080 por padrão para containers Python
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
