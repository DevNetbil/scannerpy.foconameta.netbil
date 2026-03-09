# API Validador Gabarito

Uma API FastAPI para validação de gabaritos de provas.

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
python main.py
```

A API estará disponível em: http://localhost:8000

## Documentação

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints

### 1. Health Check
- **GET** `/` - Endpoint raiz
- **GET** `/health` - Verificação de saúde

### 2. Gabaritos
- **POST** `/gabaritos` - Criar gabarito
- **GET** `/gabaritos` - Listar gabaritos
- **GET** `/gabaritos/{id}` - Obter gabarito específico
- **DELETE** `/gabaritos/{id}` - Deletar gabarito

### 3. Validação
- **POST** `/validar` - Validar respostas contra gabarito

## Exemplos de Uso

### Criar um Gabarito

```json
POST /gabaritos
{
  "nome": "Prova de Matemática",
  "disciplina": "Matemática",
  "questoes": [
    {
      "questao": 1,
      "resposta": "A",
      "valor": 2.0
    },
    {
      "questao": 2,
      "resposta": "B",
      "valor": 2.0
    },
    {
      "questao": 3,
      "resposta": "C",
      "valor": 1.0
    }
  ]
}
```

### Validar Respostas

```json
POST /validar
{
  "gabarito_id": 1,
  "respostas": [
    {
      "questao": 1,
      "resposta": "A"
    },
    {
      "questao": 2,
      "resposta": "C"
    },
    {
      "questao": 3,
      "resposta": "C"
    }
  ]
}
```

### Resposta da Validação

```json
{
  "gabarito_id": 1,
  "pontuacao_total": 3.0,
  "pontuacao_maxima": 5.0,
  "percentual": 60.0,
  "acertos": 2,
  "total_questoes": 3,
  "detalhes": [
    {
      "questao": 1,
      "resposta_dada": "A",
      "resposta_correta": "A",
      "correto": true,
      "pontos": 2.0
    },
    {
      "questao": 2,
      "resposta_dada": "C",
      "resposta_correta": "B",
      "correto": false,
      "pontos": 0.0
    },
    {
      "questao": 3,
      "resposta_dada": "C",
      "resposta_correta": "C",
      "correto": true,
      "pontos": 1.0
    }
  ]
}
```

## Características da API

### Segurança
- CORS configurado para desenvolvimento
- Validação de dados com Pydantic
- Tratamento de erros HTTP
- Logging de operações

### Funcionalidades
- Criação e gerenciamento de gabaritos
- Validação automática de respostas
- Cálculo de pontuação e percentual
- Relatório detalhado de acertos/erros
- Documentação automática (Swagger/ReDoc)

### Estrutura de Dados
- **Gabarito**: Nome, disciplina e lista de questões
- **Questão**: Número, resposta correta e valor em pontos
- **Validação**: Comparação automática e relatório de resultados

## Próximos Passos

Para produção, considere:

1. **Banco de Dados**: Integrar com PostgreSQL, MySQL ou MongoDB
2. **Autenticação**: Implementar JWT ou OAuth2
3. **Cache**: Redis para melhor performance
4. **Testes**: Adicionar testes unitários e de integração
5. **Deploy**: Containerização com Docker
6. **Monitoramento**: Logs estruturados e métricas
