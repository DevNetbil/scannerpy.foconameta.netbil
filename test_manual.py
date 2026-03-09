"""
Script para testar a API FastAPI em execução
Execute este script em outro terminal enquanto a API estiver rodando
"""
import requests
import json

# URL base da API
BASE_URL = "http://localhost:8000"

def testar_api():
    print("=== Testando API Validador Gabarito ===\n")
    
    # 1. Testar endpoint raiz
    print("1. Testando endpoint raiz...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")
    except Exception as e:
        print(f"Erro: {e}\n")
    
    # 2. Testar health check
    print("2. Testando health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Resposta: {json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")
    except Exception as e:
        print(f"Erro: {e}\n")
    
    # 3. Criar um gabarito
    print("3. Criando gabarito...")
    gabarito_data = {
        "nome": "Prova de Matemática Básica",
        "disciplina": "Matemática",
        "questoes": [
            {"questao": 1, "resposta": "A", "valor": 2.0},
            {"questao": 2, "resposta": "B", "valor": 2.0},
            {"questao": 3, "resposta": "C", "valor": 1.0},
            {"questao": 4, "resposta": "D", "valor": 2.0},
            {"questao": 5, "resposta": "A", "valor": 3.0}
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/gabaritos", json=gabarito_data)
        print(f"Status: {response.status_code}")
        gabarito_criado = response.json()
        print(f"Gabarito criado: {json.dumps(gabarito_criado, indent=2, ensure_ascii=False)}\n")
        gabarito_id = gabarito_criado["id"]
    except Exception as e:
        print(f"Erro: {e}\n")
        return
    
    # 4. Listar gabaritos
    print("4. Listando gabaritos...")
    try:
        response = requests.get(f"{BASE_URL}/gabaritos")
        print(f"Status: {response.status_code}")
        gabaritos = response.json()
        print(f"Total de gabaritos: {len(gabaritos)}")
        for g in gabaritos:
            print(f"  - ID: {g['id']}, Nome: {g['nome']}, Disciplina: {g['disciplina']}")
        print()
    except Exception as e:
        print(f"Erro: {e}\n")
    
    # 5. Obter gabarito específico
    print(f"5. Obtendo gabarito ID {gabarito_id}...")
    try:
        response = requests.get(f"{BASE_URL}/gabaritos/{gabarito_id}")
        print(f"Status: {response.status_code}")
        gabarito = response.json()
        print(f"Gabarito obtido: {json.dumps(gabarito, indent=2, ensure_ascii=False)}\n")
    except Exception as e:
        print(f"Erro: {e}\n")
    
    # 6. Validar respostas
    print("6. Validando respostas...")
    validacao_data = {
        "gabarito_id": gabarito_id,
        "respostas": [
            {"questao": 1, "resposta": "A"},  # Correta
            {"questao": 2, "resposta": "C"},  # Incorreta
            {"questao": 3, "resposta": "C"},  # Correta
            {"questao": 4, "resposta": "D"},  # Correta
            {"questao": 5, "resposta": "B"}   # Incorreta
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/validar", json=validacao_data)
        print(f"Status: {response.status_code}")
        resultado = response.json()
        print(f"Resultado da validação:")
        print(f"  - Pontuação: {resultado['pontuacao_total']}/{resultado['pontuacao_maxima']}")
        print(f"  - Percentual: {resultado['percentual']}%")
        print(f"  - Acertos: {resultado['acertos']}/{resultado['total_questoes']}")
        print(f"  - Detalhes: {json.dumps(resultado['detalhes'], indent=2, ensure_ascii=False)}\n")
    except Exception as e:
        print(f"Erro: {e}\n")
    
    print("=== Testes concluídos! ===")
    print("Para mais testes, acesse:")
    print(f"- Documentação Swagger: {BASE_URL}/docs")
    print(f"- Documentação ReDoc: {BASE_URL}/redoc")

if __name__ == "__main__":
    testar_api()
