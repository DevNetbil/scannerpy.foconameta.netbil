"""
Script para testar o endpoint de processamento de imagem
"""
import requests
import base64
import json

# URL da API
BASE_URL = "http://localhost:8000"

def criar_imagem_teste_base64():
    """
    Cria uma imagem simples em base64 para teste
    """
    # Imagem PNG 1x1 pixel transparente
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    return base64.b64encode(png_data).decode('utf-8')

def testar_processamento_imagem():
    """
    Testa o endpoint de processamento de imagem
    """
    print("=== Testando Processamento de Imagem ===\n")
    
    # Dados de teste
    request_data = {
        "imageBase64": criar_imagem_teste_base64(),
        "tipoEnsino": 1,  # FUNDAMENTALI
        "tipoGabarito": 1  # PORTMAT
    }
    
    try:
        print("Enviando requisição...")
        response = requests.post(f"{BASE_URL}/get-resposta-imagem", json=request_data)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Sucesso!")
            print(f"📝 Mensagem: {result['message']}")
            print(f"📁 Caminho: {result['path']}")
            print(f"🎓 Tipo de Ensino: {result['tipo_ensino']}")
            print(f"📋 Tipo de Gabarito: {result['tipo_gabarito']}")
        else:
            print("❌ Erro!")
            print(f"Resposta: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro de conexão! Certifique-se de que a API está rodando em http://localhost:8000")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def testar_com_imagem_real():
    """
    Exemplo de como testar com uma imagem real (se você tiver uma)
    """
    print("\n=== Exemplo com Imagem Real ===")
    print("Para testar com uma imagem real, substitua o código abaixo:")
    print("""
    # Ler arquivo de imagem
    with open("caminho/para/sua/imagem.jpg", "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
    
    request_data = {
        "imageBase64": image_base64,
        "tipoEnsino": 2,  # FUNDAMENTALII
        "tipoGabarito": 2  # CIENLING
    }
    """)

if __name__ == "__main__":
    testar_processamento_imagem()
    testar_com_imagem_real()
