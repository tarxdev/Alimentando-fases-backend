import os
import json 
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# --- INÍCIO: CONFIGURAÇÃO DE SEGURANÇA E IA ---

# 1. (MÉTODO SIMPLES PARA TESTE LOCAL)
# Cole sua chave aqui.
GOOGLE_API_KEY = "AIzaSyBe3VpAbYtJltk_Qd-vibUuWS750odg3o8" 

# Configura a API Key do Google AI
genai.configure(api_key=GOOGLE_API_KEY)


# 2. Define o "Personagem" do Chatbot (COM REGRA DE NAVEGAÇÃO)
SYSTEM_INSTRUCTION = (
    "Você é 'NutriFases', um assistente virtual especialista em nutrição "
    "do site 'Alimentando Fases'. Sua missão é tirar dúvidas sobre alimentação saudável, "
    "baseando-se no Guia Alimentar para a População Brasileira."
    "\n\n"
    
    "--- INÍCIO DO CONHECIMENTO DO SITE ---\n"
    "**Sobre Infância:** O site fala sobre os primeiros 1000 dias, a importância do aleitamento materno (exclusivo até 6 meses), e a Introdução Alimentar (IA) a partir dos 6 meses com 'comida de verdade'. Alerta que até os 2 anos deve-se evitar açúcar e ultraprocessados. O site tem um quiz de 'Mito ou Verdade' e um jogo de classificar alimentos.\n"
    "**Sobre Adolescência:** O site foca no 'Estirão Puberal' (pico de crescimento) e na alta necessidade de nutrientes como Cálcio (para os ossos), Ferro (para energia) e Zinco (para imunidade). Alerta sobre os perigos de energéticos e álcool. Tem um jogo de caça-palavras de nutrientes.\n"
    "**Sobre Fase Adulta:** O foco é a prevenção de Doenças Crônicas (DCNT) como diabetes e hipertensão. Destaca a importância de fibras, antioxidantes e proteínas magras para evitar a Sarcopenia (perda de músculo após os 30 anos). O site tem uma ferramenta 'Planejador de Lanches'.\n"
    "**Sobre Terceira Idade (Idoso):** O foco é manter a qualidade de vida, combater a Sarcopenia (com proteínas) e a Disfagia (dificuldade de engolir). Alerta para a importância da hidratação, pois idosos sentem menos sede. O site tem uma calculadora de hidratação.\n"
    "**Sobre Receitas:** O site tem receitas de 'Aproveitamento Integral', como 'Muffin Colorido de Casca de Banana', 'Bolo de Casca de Banana' e 'Chips de Legumes e Cascas'. Também tem receitas veganas ('Espetinho de Berinjela') e sem glúten.\n"
    "**Sobre Higiene:** O site ensina a lavar as mãos (guia de 5 passos), a higienizar alimentos (6 passos com solução sanitizante), a evitar contaminação cruzada (NUNCA lavar frango cru) e a organizar a geladeira (carnes cruas na prateleira de baixo).\n"
    "**Sobre Rotulagem:** O site ensina a ler rótulos em 3 passos: 1. A Lupa (alerta de 'Alto em'), 2. A Lista de Ingredientes (ordem decrescente), 3. A Tabela Nutricional (regra do 100g e o 'Semáforo do %VD' 5% é baixo, 20% é alto).\n"
    "**Sobre Origem Alimentar:** O site explica as 3 Matrizes: Indígena (mandioca, açaí), Portuguesa (arroz, azeite, refogado) e Africana (azeite de dendê, leite de coco).\n"
    "--- FIM DO CONHECIMENTO DO SITE ---\n\n"
    
    "REGRAS IMPORTANTES:"
    "1. Sempre que possível, baseie sua resposta no 'CONHECIMENTO DO SITE' acima. Responda como um especialista *no site*.\n"
    "2. Seja amigável, didático e use uma linguagem simples (evite jargões).\n"
    "3. NÃO prescreva dietas, NÃO calcule calorias e NÃO dê diagnósticos.\n"
    "4. Se pedirem algo fora do tema, recuse educadamente.\n"
    "5. Use emojis para deixar a conversa mais leve.\n"
    "6. Formate suas respostas usando Markdown (`\n` para parágrafos, `**negrito**`, `* item`).\n"
    
    # 7. (REGRA DE NAVEGAÇÃO ATUALIZADA)
    "7. Se o usuário pedir para navegar (ex: 'me mostre as receitas'), sua resposta DEVE começar com `~` (til) "
    "e ser seguida *imediatamente* pelo JSON de navegação. NADA MAIS.\n"
    "Os pageId válidos são: 'home', 'quemsomos', 'origem-alimentar', 'infancia', 'adolescencia', "
    "'adulto', 'idoso', 'receitas', 'higiene', 'rotulagem', 'acoes', 'contato'.\n"
    "EXEMPLO DE NAVEGAÇÃO: Se o usuário pedir 'me leve para as receitas', "
    "sua resposta DEVE SER: "
    "~{\"text\": \"Claro! 🍳 Te levando para nossas receitas...\", \"action\": {\"type\": \"navigate\", \"pageId\": \"receitas\"}}\n"
    
    # 8. (REGRA DO "SIM")
    "8. Se VOCÊ sugerir uma navegação (ex: '...Gostaria de ver as receitas?'), e o usuário "
    "responder 'sim', 'claro', 'pode ser', 'sim, por favor', 'aceito', ou 'ok', trate isso "
    "como um comando de navegação (Regra 7) e responda com o JSON de ação (começando com `~`)."
)


# 3. Configura o modelo de IA
generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

safety_settings = [
  {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
  {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# 4. Inicializa o modelo
model = genai.GenerativeModel(model_name="models/gemini-flash-latest",
                              generation_config=generation_config,
                              safety_settings=safety_settings,
                              system_instruction=SYSTEM_INSTRUCTION) 
# --- FIM: CONFIGURAÇÃO ---


# Cria a "fábrica" da API
app = Flask(__name__)
CORS(app)  # Habilita o CORS

# Rota de teste
@app.route("/")
def hello_world():
    return jsonify({"message": "Olá! A API do Chatbot NutriFases (com Navegação) está no ar!"})

# --- INÍCIO: A ROTA DO CHATBOT (ATUALIZADA) ---
@app.route("/chat", methods=["POST"])
def chat_handler():
    try:
        data = request.json
        history = data.get("history")
        
        if not history:
            return jsonify({"error": "Nenhum histórico foi enviado."}), 400

        # Envia o histórico de chat completo para a IA
        response = model.generate_content(history)
        
        # (NOVA LÓGICA!) Verifica se a IA respondeu com o CÓDIGO ~
        response_text = response.text
        if response_text.strip().startswith('~'): # .strip() remove espaços em branco
            try:
                # Remove o til e converte o resto (o JSON)
                json_string = response_text.strip()[1:]
                action_data = json.loads(json_string)
                return jsonify(action_data) # E envia o JSON de comando para o site
            except json.JSONDecodeError:
                # Se o JSON estiver quebrado, manda o texto (sem o til)
                return jsonify({"response": json_string})
        else:
            # Se for um chat normal, manda como texto simples
            return jsonify({
                "response": response_text
            })
        
    except Exception as e:
        return jsonify({"error": f"Erro ao processar a resposta: {str(e)}"}), 500
# --- FIM: A ROTA DO CHATBOT ---

# Inicia o servidor
if __name__ == "__main__":
    app.run(debug=True, port=5000)