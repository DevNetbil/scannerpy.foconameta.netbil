"""
Exemplos de testes para a API FastAPI
Para executar: pip install pytest httpx
Depois: pytest test_api.py
"""
import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_root_endpoint():
    """Testar endpoint raiz"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "timestamp" in data
    assert "message" in data

def test_health_check():
    """Testar health check"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_criar_gabarito():
    """Testar criação de gabarito"""
    gabarito_data = {
        "nome": "Teste de Matemática",
        "disciplina": "Matemática",
        "questoes": [
            {"questao": 1, "resposta": "A", "valor": 2.0},
            {"questao": 2, "resposta": "B", "valor": 2.0},
            {"questao": 3, "resposta": "C", "valor": 1.0}
        ]
    }
    
    response = client.post("/gabaritos", json=gabarito_data)
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == gabarito_data["nome"]
    assert data["disciplina"] == gabarito_data["disciplina"]
    assert len(data["questoes"]) == 3
    assert "id" in data
    assert "criado_em" in data

def test_listar_gabaritos():
    """Testar listagem de gabaritos"""
    # Primeiro criar um gabarito
    gabarito_data = {
        "nome": "Teste Lista",
        "disciplina": "Física",
        "questoes": [{"questao": 1, "resposta": "A", "valor": 1.0}]
    }
    client.post("/gabaritos", json=gabarito_data)
    
    # Depois listar
    response = client.get("/gabaritos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_obter_gabarito_existente():
    """Testar obtenção de gabarito específico"""
    # Criar gabarito
    gabarito_data = {
        "nome": "Teste Específico",
        "disciplina": "Química",
        "questoes": [{"questao": 1, "resposta": "A", "valor": 1.0}]
    }
    create_response = client.post("/gabaritos", json=gabarito_data)
    gabarito_id = create_response.json()["id"]
    
    # Obter gabarito
    response = client.get(f"/gabaritos/{gabarito_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == gabarito_id
    assert data["nome"] == gabarito_data["nome"]

def test_obter_gabarito_inexistente():
    """Testar obtenção de gabarito que não existe"""
    response = client.get("/gabaritos/99999")
    assert response.status_code == 404

def test_validar_respostas():
    """Testar validação de respostas"""
    # Criar gabarito
    gabarito_data = {
        "nome": "Teste Validação",
        "disciplina": "História",
        "questoes": [
            {"questao": 1, "resposta": "A", "valor": 2.0},
            {"questao": 2, "resposta": "B", "valor": 2.0},
            {"questao": 3, "resposta": "C", "valor": 1.0}
        ]
    }
    create_response = client.post("/gabaritos", json=gabarito_data)
    gabarito_id = create_response.json()["id"]
    
    # Validar respostas
    validacao_data = {
        "gabarito_id": gabarito_id,
        "respostas": [
            {"questao": 1, "resposta": "A"},  # Correta
            {"questao": 2, "resposta": "C"},  # Incorreta
            {"questao": 3, "resposta": "C"}   # Correta
        ]
    }
    
    response = client.post("/validar", json=validacao_data)
    assert response.status_code == 200
    data = response.json()
    
    assert data["gabarito_id"] == gabarito_id
    assert data["pontuacao_total"] == 3.0  # 2.0 + 1.0
    assert data["pontuacao_maxima"] == 5.0
    assert data["percentual"] == 60.0
    assert data["acertos"] == 2
    assert data["total_questoes"] == 3
    assert len(data["detalhes"]) == 3

def test_validar_gabarito_inexistente():
    """Testar validação com gabarito que não existe"""
    validacao_data = {
        "gabarito_id": 99999,
        "respostas": [{"questao": 1, "resposta": "A"}]
    }
    
    response = client.post("/validar", json=validacao_data)
    assert response.status_code == 404

def test_deletar_gabarito():
    """Testar deleção de gabarito"""
    # Criar gabarito
    gabarito_data = {
        "nome": "Teste Deletar",
        "disciplina": "Geografia",
        "questoes": [{"questao": 1, "resposta": "A", "valor": 1.0}]
    }
    create_response = client.post("/gabaritos", json=gabarito_data)
    gabarito_id = create_response.json()["id"]
    
    # Deletar gabarito
    response = client.delete(f"/gabaritos/{gabarito_id}")
    assert response.status_code == 204
    
    # Verificar se foi deletado
    get_response = client.get(f"/gabaritos/{gabarito_id}")
    assert get_response.status_code == 404

def test_deletar_gabarito_inexistente():
    """Testar deleção de gabarito que não existe"""
    response = client.delete("/gabaritos/99999")
    assert response.status_code == 404

if __name__ == "__main__":
    pytest.main([__file__])
