import os
import json
# Importe apenas o que é essencial (não precisamos de toda a Flask)
from flask import jsonify 
import google.generativeai as genai
from google.generativeai.errors import APIError

# =======================================================
# --- CONFIGURAÇÃO DE SEGURANÇA E IA (MANTIDA) ---
# =======================================================

# Carrega a chave da Vercel Environment Variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") 

# A instrução do sistema (apenas para referência, deve ser a mesma)
SYSTEM_INSTRUCTION = (
    "Você é 'NutriFases', um assistente virtual especialista em nutrição "
    "do site 'Alimentando Fases'. Sua missão é tirar dúvidas sobre alimentação saudável... (Mantenha sua instrução completa aqui)..."
)

# Configura a API Key do Google AI
MODEL = None
if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        MODEL = genai.GenerativeModel(
            model='gemini-2.5-flash',
            system_instruction=SYSTEM_INSTRUCTION
        )
    except Exception as e:
        print(f"AVISO: Erro ao configurar a API Gemini: {e}")

# =======================================================
# FUNÇÃO DE PONTO DE ENTRADA DO VERCEL/FLASK (ADAPTADA)
# =======================================================

# Reutilizamos a lógica da API do Cloud Functions, mas o Vercel pode injetar o objeto request
def handler(request):
    """
    Trata a requisição HTTP. O Vercel nos envia a requisição como um objeto Request.
    """

    # --- Configuração de CORS para o GitHub Pages ---
    CORS_HEADERS = {
        'Access-Control-Allow-Origin': 'https://tanxdev.github.io', # Idealmente, restrinja ao seu domínio!
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600'
    }

    # 1. Resposta ao Preflight (Requisição OPTIONS)
    if request.method == 'OPTIONS':
        return ('', 204, CORS_HEADERS)

    # 2. Checagem de Configuração
    if not GOOGLE_API_KEY or not MODEL:
        return (jsonify({"error": "Erro de Configuração: API Key ou Modelo não está definido."}), 
                500, CORS_HEADERS)
        
    try:
        # Tenta pegar o JSON do corpo da requisição
        data = request.get_json(silent=True)
        if data is None:
             # Se for um POST sem JSON, retornamos erro
             return (jsonify({"error": "Requisição inválida: O corpo da requisição não é um JSON válido."}), 400, CORS_HEADERS)

        history = data.get("history")
        
        if not history:
            return (jsonify({"error": "Nenhum histórico foi enviado."}), 400, CORS_HEADERS)

        # Envia o histórico
        response = MODEL.generate_content(history)
        response_text = response.text
        
        # Lógica de Navegação (a string que começa com ~)
        if response_text.strip().startswith('~'):
            # ... (Lógica de JSON de Navegação idêntica ao app.py anterior)
            try:
                json_string = response_text.strip()[1:]
                action_data = json.loads(json_string)
                return (jsonify(action_data), 200, CORS_HEADERS)
            except json.JSONDecodeError:
                 return (jsonify({"response": f"Erro interno: Comando de navegação malformado."}), 500, CORS_HEADERS)
        
        else:
            # Resposta de chat normal
            return (jsonify({
                "response": response_text
            }), 200, CORS_HEADERS)
        
    except APIError as api_e:
        return (jsonify({"error": f"Erro da API Gemini: Limite ou chave inválida."}), 500, CORS_HEADERS)
    except Exception as e:
        return (jsonify({"error": f"Erro interno ao processar a resposta: {str(e)}"}), 500, CORS_HEADERS)

# Este é o ponto de entrada que o Vercel espera.
# Ele será o manipulador da função.
from http.server import BaseHTTPRequestHandler
from vercel_python import VercelRequestHandler
from vercel_python.handler import VercelRequest, VercelResponse

# Criar a instância Flask (mantemos para usar as funções jsonify e request.get_json)
from flask import Flask, request as flask_request
app = Flask(__name__)

# Função Wrapper que o Vercel usa (muito simplificada)
# Note que estamos chamando 'handler' (sua lógica principal) com o objeto de requisição Flask.
def chat_entry_point(request):
    # A função principal 'handler' precisa do objeto de requisição do Flask.
    # Usamos o contexto do Flask para que 'request' funcione como o objeto Flask Request.
    with app.app_context():
        # O Vercel Functions é inteligente o suficiente para injetar um objeto
        # de requisição Flask-compatível no contexto.
        return handler(flask_request)

# Define o manipulador para o Vercel
# O Vercel irá procurar por uma função com o mesmo nome do arquivo: chat
if __name__ != '__main__':
    # Esta é a função que o Vercel vai chamar.
    # Nós a definimos aqui para simplificar a estrutura da função principal.
    from vercel_python import VercelRequestHandler, VercelResponse
    def chat(req):
        return chat_entry_point(req)