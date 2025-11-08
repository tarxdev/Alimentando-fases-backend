import os
import json 
from flask import jsonify # Usamos jsonify e request do Flask, mas o GCF injeta o objeto request
import google.generativeai as genai
from google.generativeai.errors import APIError

# =======================================================
# --- CONFIGURAÇÃO DE SEGURANÇA E IA --
# =======================================================

# 1. CARREGAMENTO SEGURO DA API KEY
# A chave de API DEVE ser carregada da variável de ambiente no GCF
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# 2. Define o "Personagem" do Chatbot (Sistema de Instrução)
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
        # Inicializa o modelo com a instrução do sistema
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
# FUNÇÃO DE PONTO DE ENTRADA DO GOOGLE CLOUD FUNCTIONS
# =======================================================

def nutrifases_api(request):
    """
    Trata as requisições HTTP para a API do chatbot.
    Esta é a função de ponto de entrada (entry point) para o Google Cloud Functions.
    O 'request' é um objeto compatível com Flask que o GCF fornece.
    """

    # --- Configuração de CORS (Crucial para o GitHub Pages) ---
    # Estes cabeçalhos garantem que seu frontend possa se comunicar com o GCF
    CORS_HEADERS = {
        'Access-Control-Allow-Origin': '*', # Permite acesso de qualquer origem
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '3600'
    }

    # 1. Resposta ao Preflight (Requisição OPTIONS)
    if request.method == 'OPTIONS':
        return ('', 204, CORS_HEADERS)

    # 2. Checagem de Configuração
    if not GOOGLE_API_KEY or not MODEL:
        return (jsonify({"error": "Erro de Configuração: API Key ou Modelo não está definido. Verifique a variável GOOGLE_API_KEY no GCF."}), 
                500, CORS_HEADERS)
        
    try:
        # Pega o JSON do objeto 'request' do GCF
        data = request.get_json(silent=True)
        if data is None:
             return (jsonify({"error": "Requisição inválida: O corpo da requisição não é um JSON válido."}), 400, CORS_HEADERS)

        history = data.get("history")
        
        if not history:
            return (jsonify({"error": "Nenhum histórico foi enviado."}), 400, CORS_HEADERS)

        # Envia o histórico de chat completo para a IA
        response = MODEL.generate_content(history)
        
        # Lógica de Navegação (a string que começa com ~)
        response_text = response.text
        if response_text.strip().startswith('~'):
            try:
                # Extrai o JSON da ação de navegação
                json_string = response_text.strip()[1:]
                action_data = json.loads(json_string)
                
                # Retorna o JSON da ação de navegação com status 200
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