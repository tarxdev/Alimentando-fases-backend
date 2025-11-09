import os
import json 
from flask import Flask, request, jsonify
import google.generativeai as genai
from google.generativeai.errors import APIError


# 1. CARREGAMENTO DE TESTE DA API KEY (HARDCODING TEMPORÁRIO)
GOOGLE_API_KEY = "AIzaSyBe3VpAbYtJltk_Qd-vibUuWS750odg3o8" 

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
    "Para qualquer outra pergunta, forneça uma resposta de nutrição. Se a página pedida não for válida, diga que não pode navegar até lá."
)

# Configuração de CORS (necessária para comunicação entre GitHub Pages e Vercel)
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
}

# Configura a API Key do Google AI e inicializa o modelo
MODEL = None
# A condição abaixo verifica se a chave foi substituída
if GOOGLE_API_KEY and GOOGLE_API_KEY != "SUA_CHAVE_SECRETA_COMPLETA_AQUI":
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
    # Se você esqueceu de substituir a string, esta mensagem aparece nos logs do Vercel
    print("ERRO CRÍTICO: Chave de API ausente ou não substituída no código.")


# 2. PONTO DE ENTRADA DO VERCEL/FLASK
# Cria a instância Flask
app = Flask(__name__)

# Manipulador da requisição principal (a lógica da API)
def handler(flask_request):
    # Trata a requisição OPTIONS (Pré-voo CORS)
    if flask_request.method == 'OPTIONS':
        return ('', 204, CORS_HEADERS)
    
    # 1. Checagem de Inicialização
    if not MODEL:
        return (jsonify({"error": "Erro de Configuração: O modelo Gemini não pôde ser inicializado. Verifique a chave API."}), 
                500, CORS_HEADERS)
    
    try:
        data = flask_request.get_json(silent=True)
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

# Define a função principal que o Vercel irá procurar (necessário para o Serverless)
# A rota Flask é definida para o Vercel.
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat():
    # O objeto 'request' é injetado pelo Flask
    return handler(request)

# Esta função é o ponto de entrada serverless para o Vercel (se necessário pelo vercel.json).
def chat_entry_point(request):
    # Chama a função 'chat' decorada acima
    return chat()