import os
import json 
from flask import Flask, request, jsonify
import google.generativeai as genai
from google.generativeai.errors import APIError

# =======================================================
# --- CONFIGURAÇÃO DE SEGURANÇA E IA --
# =======================================================

# Carrega a chave da Vercel Environment Variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Define o "Personagem" do Chatbot (Sistema de Instrução)
SYSTEM_INSTRUCTION = (
    "Você é 'NutriFases', um assistente virtual especialista em nutrição "
    "do site 'Alimentando Fases'. Sua missão é tirar dúvidas sobre alimentação saudável, "
    "baseando-se no Guia Alimentar para a População Brasileira. "
    "Responda de forma acessível e encorajadora. Nunca se desvie do tema de nutrição. "
    "Você também é um especialista em navegação do site. Se o usuário pedir para ir para "
    "uma página (ex: 'Quero ir para receitas' ou 'Onde está o guia?'), você DEVE responder "
    "EXCLUSIVAMENTE com uma string de ação em formato JSON, começando com o caractere '~'. "
    "Exemplo de resposta de navegação: "
    "~{\"action\": \"navigate\", \"path\": \"#receitas\"}"
    "As páginas válidas são: '#receitas', '#fases-da-vida', '#guia-alimentar', '#contato', '#quem-somos'. "
    "Se a intenção não for navegar, apenas responda à pergunta sobre nutrição."
)


# Configura a API Key do Google AI e inicializa o modelo
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
        MODEL = None
else:
    print("AVISO: Variável de ambiente GOOGLE_API_KEY não definida.")

# =======================================================
# INSTÂNCIA PRINCIPAL DO FLASK (WSGI - PONTO DE ENTRADA)
# =======================================================

# 1. Cria a instância do Flask. O Vercel procurará por uma variável 'app'.
app = Flask(__name__)

# 2. Rota que o Vercel irá servir: /api/chat (o nome do arquivo 'chat.py' + a rota)
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat_entry_point():
    """
    Função de ponto de entrada chamada pelo Vercel. 
    Ela chama a lógica principal e garante que a variável 'request' seja o objeto Flask Request.
    """

    # --- Configuração de CORS (para o GitHub Pages) ---
    CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*', # Permitir todas as origens para funcionar com GitHub Pages
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600'
    }

    # Resposta ao Preflight (Requisição OPTIONS)
    if request.method == 'OPTIONS':
        return ('', 204, CORS_HEADERS)

    # Checagem de Configuração
    if not GOOGLE_API_KEY or not MODEL:
        return (jsonify({"error": "Erro de Configuração: API Key ou Modelo não está definido."}), 
                500, CORS_HEADERS)
        
    try:
        # Pega o JSON do objeto 'request' do Flask
        data = request.get_json(silent=True)
        if data is None:
             return (jsonify({"error": "Requisição inválida: O corpo da requisição não é um JSON válido."}), 400, CORS_HEADERS)

        history = data.get("history")
        
        if not history:
            return (jsonify({"error": "Nenhum histórico foi enviado."}), 400, CORS_HEADERS)

        # Envia o histórico de chat completo para a IA
        response = MODEL.generate_content(history)
        response_text = response.text
        
        # Lógica de Navegação (a string que começa com ~)
        if response_text.strip().startswith('~'):
            try:
                # Extrai o JSON da ação de navegação
                json_string = response_text.strip()[1:]
                action_data = json.loads(json_string)
                
                # Retorna o JSON da ação de navegação com status 200 e headers CORS
                return (jsonify(action_data), 200, CORS_HEADERS)
                
            except json.JSONDecodeError as json_error:
                # Se o JSON da IA estiver quebrado
                return (jsonify({
                    "response": f"Erro interno: Comando de navegação malformado. Detalhe: {str(json_error)}"
                }), 500, CORS_HEADERS)
        else:
            # Resposta de chat normal
            return (jsonify({
                "response": response_text
            }), 200, CORS_HEADERS)
        
    except APIError as api_e:
        # Erro específico da API do Gemini (ex: Key inválida, limite excedido)
        return (jsonify({"error": f"Erro da API Gemini: Limite ou chave inválida. Detalhe: {str(api_e)}"}), 
                500, CORS_HEADERS)
    except Exception as e:
        # Erro de processamento geral
        return (jsonify({"error": f"Erro interno ao processar a resposta: {str(e)}"}), 
                500, CORS_HEADERS)

# A Vercel procurará pela variável 'app' para rodar a função WSGI
# Não é necessário o bloco 'if __name__ == "__main__":'