from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import requests
import os
import json
from typing import List, Optional

router = APIRouter()

# Configurações da API Trindade
TRINDADE_API_URL = os.getenv("TRINDADE_API_URL", "https://api.trindadetecnologia.com.br" )
TRINDADE_API_KEY = os.getenv("TRINDADE_API_KEY")

class CotacaoRequest(BaseModel):
    nome: str
    idade: int
    telefone: str
    email: str
    cidade: str
    estado: str
    tipo_plano: str  # individual, familiar, empresarial
    pessoas: Optional[int] = 1
    idades_dependentes: Optional[List[int]] = []

class PlanoSaude(BaseModel):
    operadora: str
    nome_plano: str
    preco_mensal: float
    cobertura: str
    rede_credenciada: str
    carencia: str

@router.post("/cotacao")
async def buscar_cotacoes(dados: CotacaoRequest):
    """Busca cotações reais na API da Trindade"""
    try:
        # Preparar dados para API da Trindade
        payload = {
            "nome": dados.nome,
            "idade": dados.idade,
            "telefone": dados.telefone,
            "email": dados.email,
            "cidade": dados.cidade,
            "estado": dados.estado,
            "tipo_cobertura": dados.tipo_plano,
            "qtd_pessoas": dados.pessoas,
            "idades_dependentes": dados.idades_dependentes or []
        }

        # Headers para API da Trindade
        headers = {
            "Authorization": f"Bearer {TRINDADE_API_KEY}",
            "Content-Type": "application/json"
        }

        # Fazer requisição para API da Trindade
        if TRINDADE_API_KEY:
            response = requests.post(
                f"{TRINDADE_API_URL}/cotacao",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                cotacoes_reais = response.json()
                return {
                    "success": True,
                    "cotacoes": format_cotacoes_trindade(cotacoes_reais),
                    "fonte": "API Trindade"
                }
        
        # Fallback: cotações simuladas se API não disponível
        cotacoes_simuladas = gerar_cotacoes_simuladas(dados)
        return {
            "success": True,
            "cotacoes": cotacoes_simuladas,
            "fonte": "Simulação"
        }

    except Exception as e:
        # Em caso de erro, retornar cotações simuladas
        cotacoes_simuladas = gerar_cotacoes_simuladas(dados)
        return {
            "success": True,
            "cotacoes": cotacoes_simuladas,
            "fonte": "Simulação (erro na API)"
        }

def format_cotacoes_trindade(dados_api):
    """Formata dados da API Trindade para o frontend"""
    cotacoes = []
    
    for item in dados_api.get("planos", []):
        cotacao = {
            "operadora": item.get("operadora", ""),
            "nome_plano": item.get("nome_plano", ""),
            "preco_mensal": float(item.get("valor_mensal", 0)),
            "cobertura": item.get("tipo_cobertura", ""),
            "rede_credenciada": item.get("rede_credenciada", ""),
            "carencia": item.get("carencia", ""),
            "beneficios": item.get("beneficios", []),
            "link_contratacao": item.get("link", "")
        }
        cotacoes.append(cotacao)
    
    return cotacoes

def gerar_cotacoes_simuladas(dados: CotacaoRequest):
    """Gera cotações simuladas baseadas no perfil"""
    
    # Fator de idade para cálculo
    fator_idade = 1.0
    if dados.idade > 50:
        fator_idade = 1.8
    elif dados.idade > 35:
        fator_idade = 1.4
    elif dados.idade > 25:
        fator_idade = 1.2

    # Fator família
    fator_familia = dados.pessoas if dados.pessoas > 1 else 1

    cotacoes = [
        {
            "operadora": "Amil",
            "nome_plano": "Amil Fácil",
            "preco_mensal": round(180 * fator_idade * fator_familia, 2),
            "cobertura": "Nacional",
            "rede_credenciada": "Ampla rede credenciada",
            "carencia": "180 dias",
            "beneficios": ["Consultas", "Exames", "Internações", "Urgência/Emergência"],
            "link_contratacao": "https://viddasegurossaude.com.br/contato"
        },
        {
            "operadora": "Bradesco Saúde",
            "nome_plano": "Bradesco Efetivo",
            "preco_mensal": round(220 * fator_idade * fator_familia, 2 ),
            "cobertura": "Nacional",
            "rede_credenciada": "Rede própria + credenciados",
            "carencia": "180 dias",
            "beneficios": ["Consultas", "Exames", "Internações", "Telemedicina"],
            "link_contratacao": "https://viddasegurossaude.com.br/contato"
        },
        {
            "operadora": "SulAmérica",
            "nome_plano": "SulAmérica Clássico",
            "preco_mensal": round(280 * fator_idade * fator_familia, 2 ),
            "cobertura": "Nacional",
            "rede_credenciada": "Hospitais de referência",
            "carencia": "180 dias",
            "beneficios": ["Consultas", "Exames", "Internações", "Medicina preventiva"],
            "link_contratacao": "https://viddasegurossaude.com.br/contato"
        },
        {
            "operadora": "Unimed",
            "nome_plano": "Unimed Essencial",
            "preco_mensal": round(320 * fator_idade * fator_familia, 2 ),
            "cobertura": "Regional",
            "rede_credenciada": "Cooperativas Unimed",
            "carencia": "180 dias",
            "beneficios": ["Consultas", "Exames", "Internações", "Programa de saúde"],
            "link_contratacao": "https://viddasegurossaude.com.br/contato"
        }
    ]

    return cotacoes

@router.post("/lead" )
async def registrar_interesse(dados: dict):
    """Registra interesse do cliente em um plano"""
    try:
        # Aqui você pode integrar com seu CRM
        # Por enquanto, apenas retorna sucesso
        
        return {
            "success": True,
            "message": "Interesse registrado! Nossa equipe entrará em contato em breve.",
            "protocolo": f"VID{dados.get('timestamp', '000000')}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao registrar interesse: {str(e)}")
