from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import openai
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re

router = APIRouter()

# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configurar Google Sheets
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")  # JSON das credenciais
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")  # ID da planilha

class ChatMessage(BaseModel):
    message: str
    conversation_history: list = []

@router.post("/chat")
async def chat_with_ai(chat_data: ChatMessage):
    try:
        # Prompt otimizado para conversa natural
        system_prompt = """Você é um consultor especialista em seguros de saúde da Vidda Seguros Saúde. 
        
        Conduza uma conversa natural e consultiva para coletar as seguintes informações:
        - Nome do cliente
        - Idade
        - Telefone
        - Email
        - Cidade/Estado/Bairro
        - Se o plano é somente para a pessoa, família ou empresa
        - Caso seja para família e empresa perguntar para quantas pessoas e as idades
        
        IMPORTANTE:
        - Seja natural, empático e consultivo
        - Faça UMA pergunta por vez
        - Use linguagem amigável e profissional
        - Quando tiver todas as informações, ofereça para buscar cotações reais
        - Não use scripts rígidos, seja conversacional
        - NÃO forneça sugestões de resposta, deixe o cliente responder livremente
        
        Responda sempre em português brasileiro."""

        # Preparar histórico da conversa
        messages = [{"role": "system", "content": system_prompt}]
        
        # Adicionar histórico
        for msg in chat_data.conversation_history:
            messages.append(msg)
        
        # Adicionar mensagem atual
        messages.append({"role": "user", "content": chat_data.message})

        # Chamar OpenAI
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=300,
            temperature=0.7
        )

        ai_response = response.choices[0].message.content

        # Verificar se está pronto para cotação
        ready_for_quote = check_if_ready_for_quote(messages)
        
        # Se estiver pronto, salvar no Google Sheets
        if ready_for_quote:
            await save_lead_to_sheets(messages)

        return {
            "response": ai_response,
            "suggestions": [],  # Sem sugestões conforme solicitado
            "ready_for_quote": ready_for_quote
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no chat: {str(e)}")

def check_if_ready_for_quote(messages):
    """Verifica se temos informações suficientes para cotação"""
    conversation = " ".join([msg["content"] for msg in messages if msg["role"] == "user"])
    
    # Verificar se temos as informações básicas
    has_name = any(word in conversation.lower() for word in ["nome", "chamo", "sou"])
    has_age = any(word in conversation.lower() for word in ["anos", "idade"]) or any(char.isdigit() for char in conversation)
    has_contact = any(word in conversation.lower() for word in ["telefone", "celular", "email", "@"])
    has_location = any(word in conversation.lower() for word in ["cidade", "estado", "bairro", "sp", "rj", "mg"])
    has_type = any(word in conversation.lower() for word in ["pessoa", "família", "empresa", "individual", "familiar"])
    
    return has_name and has_age and has_contact and has_location and has_type

async def save_lead_to_sheets(messages):
    """Salva o lead no Google Sheets"""
    try:
        # Extrair informações da conversa
        conversation = " ".join([msg["content"] for msg in messages if msg["role"] == "user"])
        
        lead_data = extract_lead_info(conversation)
        
        # Configurar Google Sheets
        if GOOGLE_SHEETS_CREDENTIALS and SPREADSHEET_ID:
            credentials_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
            credentials = Credentials.from_service_account_info(credentials_dict)
            gc = gspread.authorize(credentials)
            
            # Abrir planilha
            sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
            
            # Adicionar linha com dados do lead
            row = [
                datetime.now().strftime("%d/%m/%Y %H:%M"),  # Data/Hora
                lead_data.get("nome", ""),
                lead_data.get("idade", ""),
                lead_data.get("telefone", ""),
                lead_data.get("email", ""),
                lead_data.get("localizacao", ""),
                lead_data.get("tipo_plano", ""),
                lead_data.get("pessoas", ""),
                "Novo Lead",  # Status
                conversation[:500]  # Resumo da conversa (limitado)
            ]
            
            sheet.append_row(row)
            
    except Exception as e:
        print(f"Erro ao salvar no Google Sheets: {e}")

def extract_lead_info(conversation):
    """Extrai informações estruturadas da conversa"""
    lead_data = {}
    
    # Extrair nome (procurar padrões como "meu nome é", "me chamo", etc.)
    name_patterns = [
        r"(?:meu nome é|me chamo|sou o|sou a)\s+([A-Za-zÀ-ÿ\s]+)",
        r"nome:\s*([A-Za-zÀ-ÿ\s]+)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, conversation, re.IGNORECASE)
        if match:
            lead_data["nome"] = match.group(1).strip()
            break
    
    # Extrair idade
    age_match = re.search(r"(\d{1,2})\s*anos?", conversation, re.IGNORECASE)
    if age_match:
        lead_data["idade"] = age_match.group(1)
    
    # Extrair telefone
    phone_match = re.search(r"(\(?[0-9]{2}\)?[\s-]?[0-9]{4,5}[\s-]?[0-9]{4})", conversation)
    if phone_match:
        lead_data["telefone"] = phone_match.group(1)
    
    # Extrair email
    email_match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", conversation)
    if email_match:
        lead_data["email"] = email_match.group(1)
    
    # Extrair localização
    location_keywords = ["cidade", "estado", "bairro", "moro", "vivo"]
    for keyword in location_keywords:
        pattern = f"{keyword}[:\s]*([A-Za-zÀ-ÿ\s]+)"
        match = re.search(pattern, conversation, re.IGNORECASE)
        if match:
            lead_data["localizacao"] = match.group(1).strip()
            break
    
    # Extrair tipo de plano
    if "família" in conversation.lower():
        lead_data["tipo_plano"] = "Familiar"
    elif "empresa" in conversation.lower():
        lead_data["tipo_plano"] = "Empresarial"
    else:
        lead_data["tipo_plano"] = "Individual"
    
    # Extrair número de pessoas
    people_match = re.search(r"(\d+)\s*pessoas?", conversation, re.IGNORECASE)
    if people_match:
        lead_data["pessoas"] = people_match.group(1)
    
    return lead_data
