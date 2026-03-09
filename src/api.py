import math
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ultralytics import YOLO
from typing import List, Optional
from enum import Enum
import logging
import base64
import json
import os
from datetime import datetime
from pathlib import Path

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criação da instância FastAPI
app = FastAPI(
    title="API Validador Gabarito",
    description="API para validação de gabaritos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique domínios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Enums
class TipoEnsino(Enum):
    FUNDAMENTALI = 1
    FUNDAMENTALII = 2


class TipoGabarito(Enum):
    PORTMAT = 1
    CIENLING = 2


# Modelos Pydantic
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    message: str


class ImageRequest(BaseModel):
    imageBase64: str
    tipoEnsino: TipoEnsino
    tipoGabarito: TipoGabarito


class ImageResponse(BaseModel):
    message: str
    imageBase64: str
    tipo_ensino: str
    tipo_gabarito: str


# Armazenamento temporário (em produção, usar banco de dados)
gabaritos_db = {}
next_id = 1

# Endpoints


@app.get("/", response_model=HealthResponse)
async def root():
    """
    Endpoint raiz da API
    """
    try:
        return HealthResponse(
            status="success",
            timestamp=datetime.now(),
            message="API Validador Gabarito está funcionando!",
        )
    except Exception as e:
        logger.error(f"Erro no endpoint raiz: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Endpoint de verificação de saúde da API
    """
    try:
        return HealthResponse(
            status="healthy", timestamp=datetime.now(), message="Serviço operacional"
        )
    except Exception as e:
        logger.error(f"Erro no health check: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço indisponível",
        )


@app.post("/get-resposta-imagem")
async def get_resposta_imagem(request: ImageRequest):
    """
    Método para processar uma imagem e retornar respostas
    """
    try:
        images_dir = Path("imagens")
        images_dir.mkdir(exist_ok=True)
        output_path = images_dir / "img.jpeg"

        await save_base64_image(request.imageBase64, str(output_path))

        result_predict = YOLO("src/custom_train.pt").predict(
            source=str(output_path), save=True, line_width=2, save_txt=True
        )
        print(result_predict)

        logger.info(f"Imagem salva em: {output_path}")
        logger.info(
            f"Tipo de ensino: {request.tipoEnsino.name}, Tipo de gabarito: {request.tipoGabarito.name}"
        )

        grouped_boxes = group_boxes_by_vertical_axis(result_predict, tolerance=50)
        distance_info = calculate_distances_between_centers(
            grouped_boxes, max_boxes_per_group=30
        )

        result_json = map_result_to_json(grouped_boxes, distance_info, request)
        result_json["imageBase64"] = await image_to_base64(
            str(f"runs/detect/predict/img.jpg")
        )
        result = result_json

        if os.path.exists("runs"):
            import shutil

            shutil.rmtree("runs")
            logger.info(f"Arquivo temporário removido: runs")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar imagem",
        )


async def save_base64_image(base64_string, output_path):
    """
    Salva uma imagem base64 em um arquivo
    """
    try:
        # Remove o prefixo data:image se presente
        if base64_string.startswith("data:image"):
            base64_string = base64_string.split(",")[1]

        # Decodifica a imagem
        image_data = base64.b64decode(base64_string)

        # Cria o diretório pai se não existir
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Salva o arquivo
        with open(output_path, "wb") as output_file:
            output_file.write(image_data)

        logger.info(f"Imagem salva com sucesso em: {output_path}")

    except Exception as e:
        logger.error(f"Erro ao salvar imagem: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao salvar imagem: {str(e)}",
        )


async def image_to_base64(image_path):
    # Verifica se o arquivo existe
    if not Path(image_path).is_file():
        raise FileNotFoundError(f"File not found: {image_path}")

    # Lê a imagem e a converte para base64
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode("utf-8")

    return base64_string


def group_boxes_by_vertical_axis(results, tolerance=50, min_confidence=0.5):
    """
    Agrupa as detecções por eixo vertical com base na coordenada X do centro.

    Args:
        results: Resultados
        tolerance: Tolerância em pixels para considerar boxes no mesmo eixo vertical

    Returns:
        dict: Grupos de boxes organizados por eixo vertical
    """
    grouped_boxes = {}

    for result in results:
        if result.boxes is not None:
            boxes = result.boxes.xyxy.cpu().numpy()
            confidences = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()

            # Filtrar por confiança mínima
            valid_indices = confidences >= min_confidence
            boxes = boxes[valid_indices]
            confidences = confidences[valid_indices]
            classes = classes[valid_indices]

            box_info = []
            for i, (box, conf, cls) in enumerate(zip(boxes, confidences, classes)):
                x1, y1, x2, y2 = box
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                width = x2 - x1
                height = y2 - y1

                box_info.append(
                    {
                        "index": i,
                        "box": box,
                        "center_x": center_x,
                        "center_y": center_y,
                        "width": width,
                        "height": height,
                        "confidence": conf,
                        "class": cls,
                        "class_name": result.names[int(cls)],
                    }
                )

            # Remover duplicatas baseado em proximidade
            filtered_boxes = remove_duplicate_detections(box_info, overlap_threshold=0.5)

            groups = []
            for box in filtered_boxes:
                placed = False
                for group in groups:
                    if abs(group[0]["center_x"] - box["center_x"]) <= tolerance:
                        group.append(box)
                        placed = True
                        break

                if not placed:
                    groups.append([box])

            # Ordenar grupos
            for group in groups:
                group.sort(key=lambda x: x["center_y"])
            groups.sort(key=lambda x: x[0]["center_x"])

            grouped_boxes[f"image_{len(grouped_boxes)}"] = groups

    return grouped_boxes


def remove_duplicate_detections(box_info, overlap_threshold=0.5):
    """
    Remove detecções duplicadas baseado em sobreposição
    """
    filtered_boxes = []

    for box in box_info:
        is_duplicate = False
        for existing_box in filtered_boxes:
            # Calcular IoU (Intersection over Union)
            iou = calculate_iou(box["box"], existing_box["box"])
            if iou > overlap_threshold:
                # Manter a detecção com maior confiança
                if box["confidence"] > existing_box["confidence"]:
                    filtered_boxes.remove(existing_box)
                    filtered_boxes.append(box)
                is_duplicate = True
                break

        if not is_duplicate:
            filtered_boxes.append(box)

    return filtered_boxes


def calculate_iou(box1, box2):
    """
    Calcula Intersection over Union entre duas bounding boxes
    """
    x1_1, y1_1, x2_1, y2_1 = box1
    x1_2, y1_2, x2_2, y2_2 = box2

    # Coordenadas da interseção
    x1_inter = max(x1_1, x1_2)
    y1_inter = max(y1_1, y1_2)
    x2_inter = min(x2_1, x2_2)
    y2_inter = min(y2_1, y2_2)

    # Área da interseção
    if x2_inter <= x1_inter or y2_inter <= y1_inter:
        intersection = 0
    else:
        intersection = (x2_inter - x1_inter) * (y2_inter - y1_inter)

    # Áreas das caixas
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)

    # União
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0


def calculate_distances_between_centers(grouped_boxes, max_boxes_per_group=30):
    """
    Calcula distâncias entre os centros das detecções agrupadas verticalmente.

    Args:
        grouped_boxes: Grupos de boxes organizados por eixo vertical
        max_boxes_per_group: Número máximo de boxes por grupo a considerar

    Returns:
        dict: Informações sobre as distâncias calculadas
    """
    all_distances = []
    distance_analysis = {}

    for image_key, groups in grouped_boxes.items():
        image_analysis = {
            "groups": [],
            "total_groups": len(groups),
            "average_distance_per_group": [],
        }

        for group_idx, group in enumerate(groups):
            # Limitar número de boxes por grupo
            limited_group = group[:max_boxes_per_group]

            if len(limited_group) < 2:
                continue

            group_distances = []
            group_pairs = []

            # Calcular distâncias entre centros consecutivos no grupo
            for i in range(len(limited_group) - 1):
                box1 = limited_group[i]
                box2 = limited_group[i + 1]

                # Centros das boxes
                center1 = (box1["center_x"], box1["center_y"])
                center2 = (box2["center_x"], box2["center_y"])

                # Calcular distância euclidiana entre centros
                distance = math.sqrt(
                    (center2[0] - center1[0]) ** 2 + (center2[1] - center1[1]) ** 2
                )
                group_distances.append(distance)
                all_distances.append(distance)

                group_pairs.append(
                    {
                        "box_1_index": box1["index"],
                        "box_2_index": box2["index"],
                        "class_1": box1["class_name"],
                        "class_2": box2["class_name"],
                        "center_1": center1,
                        "center_2": center2,
                        "distance": distance,
                        "confidence_1": float(box1["confidence"]),
                        "confidence_2": float(box2["confidence"]),
                    }
                )

            # Análise do grupo
            if group_distances:
                group_analysis = {
                    "group_index": group_idx,
                    "total_boxes": len(limited_group),
                    "total_pairs": len(group_distances),
                    "average_distance": sum(group_distances) / len(group_distances),
                    "min_distance": min(group_distances),
                    "max_distance": max(group_distances),
                    "distances": group_distances,
                    "pairs": group_pairs,
                }

                image_analysis["groups"].append(group_analysis)
                image_analysis["average_distance_per_group"].append(
                    group_analysis["average_distance"]
                )

        distance_analysis[image_key] = image_analysis

    # Calcular estatísticas gerais
    if all_distances:
        overall_stats = {
            "total_distances": len(all_distances),
            "overall_average": sum(all_distances) / len(all_distances),
            "overall_min": min(all_distances),
            "overall_max": max(all_distances),
            "all_distances": all_distances,
        }
    else:
        overall_stats = {
            "total_distances": 0,
            "overall_average": 0,
            "overall_min": 0,
            "overall_max": 0,
            "all_distances": [],
        }

    return {"overall_stats": overall_stats, "by_image": distance_analysis}


def map_result_to_json(grouped_boxes, distance_info, request: ImageRequest):
    """
    Mapeia os resultados para um formato JSON
    """
    json_result = {
        "imageBase64": "",  # Placeholder para imagem em Base64
    }

    quantidade_blocos = 4
    distance_groups = distance_info["by_image"]["image_0"]["groups"]
    # print(distance_groups)

    if (
        request.tipoEnsino == TipoEnsino.FUNDAMENTALI
        and request.tipoGabarito == TipoGabarito.PORTMAT
    ):
        json_result["portugues"] = {}
        json_result["portugues"][f"bloco1"] = {}
        json_result["portugues"][f"bloco2"] = {}
        json_result["matematica"] = {}
        json_result["matematica"][f"bloco1"] = {}
        json_result["matematica"][f"bloco2"] = {}
    elif (
        request.tipoEnsino == TipoEnsino.FUNDAMENTALI
        and request.tipoGabarito == TipoGabarito.CIENLING
    ):
        json_result["ciencias_natureza"] = {}
        json_result["ciencias_natureza"][f"bloco1"] = {}
        json_result["ciencias_humanas"] = {}
        json_result["ciencias_humanas"][f"bloco1"] = {}
        json_result["linguagens"] = {}
        json_result["linguagens"][f"bloco1"] = {}
        json_result["linguagens"][f"bloco2"] = {}
    elif (
        request.tipoEnsino == TipoEnsino.FUNDAMENTALII
        and request.tipoGabarito == TipoGabarito.CIENLING
    ):
        json_result["ciencias_natureza"] = {}
        json_result["ciencias_natureza"][f"bloco1"] = {}
        json_result["ciencias_humanas"] = {}
        json_result["ciencias_humanas"][f"bloco1"] = {}
        json_result["linguagens"] = {}
        json_result["linguagens"][f"bloco1"] = {}
        json_result["linguagens"][f"bloco2"] = {}
    elif (
        request.tipoEnsino == TipoEnsino.FUNDAMENTALII
        and request.tipoGabarito == TipoGabarito.PORTMAT
    ):
        json_result["portugues"] = {}
        json_result["portugues"][f"bloco1"] = {}
        json_result["portugues"][f"bloco2"] = {}
        json_result["matematica"] = {}
        json_result["matematica"][f"bloco1"] = {}
        json_result["matematica"][f"bloco2"] = {}

    # Mostrar informações dos grupos
    for image_key, groups in grouped_boxes.items():
        for group_idx, group in enumerate(groups):
            # for group_idx, group in enumerate(groups[1:2]):
            # group_idx += 1  # Ajustar índice para começar de 1
            if (
                request.tipoEnsino == TipoEnsino.FUNDAMENTALI
                and request.tipoGabarito == TipoGabarito.PORTMAT
            ):
                quantidade_itens = 11
                item_atual = 0
                if group_idx < 2:
                    nome_bloco = "bloco" + str(group_idx + 1)
                    nome_disciplina = "portugues"
                else:
                    nome_bloco = "bloco" + str(group_idx - 1)
                    nome_disciplina = "matematica"

                actual_group = distance_groups[group_idx]
                final_pair = False
                while item_atual < quantidade_itens:
                    if final_pair == False:
                        for ip in range(len(actual_group["pairs"])):
                            par = actual_group["pairs"][ip]
                            if ip == 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_1"]
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 2}"
                                ] = par["class_2"]
                                item_atual += 2
                            elif ip > 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
                                item_atual += 1
                            elif par["distance"] > 105:
                                distance_calculated = int(par["distance"] // 105)
                                for id in range(distance_calculated):
                                    json_result[nome_disciplina][nome_bloco][
                                        f"q{item_atual + 1}"
                                    ] = ""
                                    item_atual += 1
                                    if id == distance_calculated - 1:
                                        item_atual += 1
                                        json_result[nome_disciplina][nome_bloco][
                                            f"q{item_atual}"
                                        ] = par["class_2"]
                                        final_pair = True
                    else:
                        for ip in range(quantidade_itens - item_atual):
                            json_result[nome_disciplina][nome_bloco][
                                f"q{item_atual + 1}"
                            ] = ""
                            item_atual += 1
                            if ip == quantidade_itens - item_atual:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
            elif (
                request.tipoEnsino == TipoEnsino.FUNDAMENTALI
                and request.tipoGabarito == TipoGabarito.CIENLING
            ):
                quantidade_itens = 0
                item_atual = 0
                if group_idx == 0:
                    quantidade_itens = 5
                    nome_bloco = "bloco1"
                    nome_disciplina = "ciencias_natureza"
                elif group_idx == 1:
                    quantidade_itens = 8
                    nome_bloco = "bloco1"
                    nome_disciplina = "ciencias_humanas"
                elif group_idx == 2:
                    quantidade_itens = 6
                    nome_bloco = "bloco1"
                    nome_disciplina = "linguagens"
                else:
                    quantidade_itens = 6
                    nome_bloco = "bloco2"
                    nome_disciplina = "linguagens"
                actual_group = distance_groups[group_idx]
                final_pair = False
                while item_atual < quantidade_itens:
                    if final_pair == False:
                        for ip in range(len(actual_group["pairs"])):
                            par = actual_group["pairs"][ip]
                            if ip == 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_1"]
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 2}"
                                ] = par["class_2"]
                                item_atual += 2
                            elif ip > 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
                                item_atual += 1
                            elif par["distance"] > 105:
                                distance_calculated = int(par["distance"] // 105)
                                for id in range(distance_calculated):
                                    json_result[nome_disciplina][nome_bloco][
                                        f"q{item_atual + 1}"
                                    ] = ""
                                    item_atual += 1
                                    if id == distance_calculated - 1:
                                        item_atual += 1
                                        json_result[nome_disciplina][nome_bloco][
                                            f"q{item_atual}"
                                        ] = par["class_2"]
                                        final_pair = True
                    else:
                        for ip in range(quantidade_itens - item_atual):
                            json_result[nome_disciplina][nome_bloco][
                                f"q{item_atual + 1}"
                            ] = ""
                            item_atual += 1
                            if ip == quantidade_itens - item_atual:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
            elif (
                request.tipoEnsino == TipoEnsino.FUNDAMENTALII
                and request.tipoGabarito == TipoGabarito.CIENLING
            ):
                quantidade_itens = 0
                item_atual = 0
                if group_idx == 0:
                    quantidade_itens = 8
                    nome_bloco = "bloco1"
                    nome_disciplina = "ciencias_natureza"
                elif group_idx == 1:
                    quantidade_itens = 8
                    nome_bloco = "bloco1"
                    nome_disciplina = "ciencias_humanas"
                elif group_idx == 2:
                    quantidade_itens = 9
                    nome_bloco = "bloco1"
                    nome_disciplina = "linguagens"
                else:
                    quantidade_itens = 9
                    nome_bloco = "bloco2"
                    nome_disciplina = "linguagens"
                actual_group = distance_groups[group_idx]
                final_pair = False
                while item_atual < quantidade_itens:
                    if final_pair == False:
                        for ip in range(len(actual_group["pairs"])):
                            par = actual_group["pairs"][ip]
                            if ip == 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_1"]
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 2}"
                                ] = par["class_2"]
                                item_atual += 2
                            elif ip > 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
                                item_atual += 1
                            elif par["distance"] > 105:
                                distance_calculated = int(par["distance"] // 105)
                                for id in range(distance_calculated):
                                    json_result[nome_disciplina][nome_bloco][
                                        f"q{item_atual + 1}"
                                    ] = ""
                                    item_atual += 1
                                    if id == distance_calculated - 1:
                                        item_atual += 1
                                        json_result[nome_disciplina][nome_bloco][
                                            f"q{item_atual}"
                                        ] = par["class_2"]
                                        final_pair = True
                    else:
                        for ip in range(quantidade_itens - item_atual):
                            json_result[nome_disciplina][nome_bloco][
                                f"q{item_atual + 1}"
                            ] = ""
                            item_atual += 1
                            if ip == quantidade_itens - item_atual:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
            elif (
                request.tipoEnsino == TipoEnsino.FUNDAMENTALII
                and request.tipoGabarito == TipoGabarito.PORTMAT
            ):
                quantidade_itens = 13
                item_atual = 0
                if group_idx == 0:
                    nome_bloco = "bloco1"
                    nome_disciplina = "portugues"
                elif group_idx == 1:
                    nome_bloco = "bloco2"
                    nome_disciplina = "portugues"
                elif group_idx == 2:
                    nome_bloco = "bloco1"
                    nome_disciplina = "matematica"
                else:
                    nome_bloco = "bloco2"
                    nome_disciplina = "matematica"
                actual_group = distance_groups[group_idx]
                final_pair = False
                while item_atual < quantidade_itens:
                    if final_pair == False:
                        for ip in range(len(actual_group["pairs"])):
                            par = actual_group["pairs"][ip]
                            if ip == 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_1"]
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 2}"
                                ] = par["class_2"]
                                item_atual += 2
                            elif ip > 0 and par["distance"] < 105:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
                                item_atual += 1
                            elif par["distance"] > 105:
                                distance_calculated = int(par["distance"] // 105)
                                for id in range(distance_calculated):
                                    json_result[nome_disciplina][nome_bloco][
                                        f"q{item_atual + 1}"
                                    ] = ""
                                    item_atual += 1
                                    if id == distance_calculated - 1:
                                        item_atual += 1
                                        json_result[nome_disciplina][nome_bloco][
                                            f"q{item_atual}"
                                        ] = par["class_2"]
                                        final_pair = True
                    else:
                        for ip in range(quantidade_itens - item_atual):
                            json_result[nome_disciplina][nome_bloco][
                                f"q{item_atual + 1}"
                            ] = ""
                            item_atual += 1
                            if ip == quantidade_itens - item_atual:
                                json_result[nome_disciplina][nome_bloco][
                                    f"q{item_atual + 1}"
                                ] = par["class_2"]
    print(json_result)
    return json_result


# Middleware para logging de requisições
@app.middleware("http")
async def log_requests(request, call_next):
    start_time = datetime.now()

    response = await call_next(request)

    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=80, reload=True, log_level="info")
