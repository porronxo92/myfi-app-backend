from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.utils.security import get_current_user, check_rate_limit, check_gemini_quota
from app.models import User
from app.services.category_service import CategoryService
from app.utils.logger import get_logger, upload_logger, log_exception
from typing import List
import google.generativeai as genai
import json
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile

# Logger para este módulo
logger = get_logger("app.routes.upload")

router = APIRouter(
    prefix="/api/upload",
    dependencies=[Depends(check_rate_limit), Depends(check_gemini_quota)]
)

# Configurar Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
logger.info("Gemini API configurada correctamente")


def build_extraction_prompt(expense_categories: List[str], income_categories: List[str]) -> str:
    """
    Genera el prompt de extracción con las categorías personalizadas del usuario.

    Args:
        expense_categories: Lista de nombres de categorías de gasto del usuario
        income_categories: Lista de nombres de categorías de ingreso del usuario

    Returns:
        Prompt completo para Gemini con las categorías inyectadas
    """
    # Formatear categorías como lista con viñetas
    expense_list = "\n".join([f"- `{cat}`" for cat in expense_categories]) if expense_categories else "- `Sin Categorizar`"
    income_list = "\n".join([f"- `{cat}`" for cat in income_categories]) if income_categories else "- `Ingreso`"

    return f"""
# ROL
Eres un experto en procesamiento de datos financieros con conocimientos avanzados en extracción de información estructurada de documentos bancarios multiformato (PDF, Excel, CSV, imágenes de extractos).

# OBJETIVO
Extraer y normalizar TODAS las transacciones bancarias del documento proporcionado en formato JSON estructurado, utilizando las categorías personalizadas del usuario.

# CONTEXTO DEL SISTEMA DE GESTIÓN FINANCIERA
- Sistema de finanzas personales con transacciones clasificadas en: **expense** (gasto) e **income** (ingreso)
- Cada usuario tiene sus propias categorías personalizadas (las que debes usar se listan abajo)
- Cada transacción requiere: fecha, descripción, cantidad, tipo y categoría
- El sistema soporta múltiples bancos españoles y formatos de extracto

# INSTRUCCIONES DE PROCESAMIENTO

## 1. Análisis del Documento
- **Identifica el banco emisor**: Busca logos, encabezados, nombres de entidad
- **Detecta el tipo de cuenta**: Cuenta corriente, tarjeta de crédito, ahorro
- **Extrae metadatos**: Titular (si visible), periodo (mes/año), número de cuenta parcial
- **Localiza TODAS las tablas de movimientos**: Pueden existir múltiples secciones

## 2. Extracción de Transacciones
Para CADA movimiento/transacción identificada, extrae:
- **Fecha**: Formato normalizado DD/MM/YYYY → convertir a YYYY-MM-DD
- **Descripción**: Texto completo del concepto
- **Cantidad**: Valor numérico (siempre POSITIVO en el JSON)
- **Tipo**: Determina si es gasto (`expense`) o ingreso (`income`) según el contexto
- **Origen**: Siempre `"automatico"`

## 3. Procesamiento de Descripciones (NLP)
Genera DOS versiones de cada descripción:

### **descripcion_original**
- Texto exacto como aparece en el extracto bancario
- Preserva códigos, referencias y formato original

### **descripcion_nlp**
- Transforma la descripción técnica en lenguaje natural y comprensible
- Reglas:
  - Elimina códigos técnicos innecesarios: `TRF-12345`, `REF:`, `ID:`, `CCC:`
  - Normaliza mayúsculas (solo inicial en nombres propios)
  - Humaniza abreviaturas: "TPTE" → "Transporte", "GASOLINA" → "Repostaje"
  - Máximo 80 caracteres
  - Elimina redundancias: "MERCADONA PZA.PADRE JOFRE, 12006" → "Mercadona"

## 4. Normalización de Importes
**CRÍTICO** - Aplica en orden:
1. Elimina separadores de miles (puntos o espacios): `1.234,56` → `1234,56`
2. Convierte coma decimal a punto: `1234,56` → `1234.56`
3. **El valor en el JSON siempre es POSITIVO** (el tipo indica si es gasto o ingreso)
4. Siempre incluye 2 decimales: `150` → `150.00`

## 5. Clasificación de Categorías
**IMPORTANTE**: Usa ÚNICAMENTE las categorías del usuario listadas abajo. Si ninguna categoría encaja con certeza, usa `"Sin Categorizar"` para gastos o `"Ingreso"` para ingresos.

### CATEGORÍAS DE GASTO (type: "expense"):
{expense_list}

### CATEGORÍAS DE INGRESO (type: "income"):
{income_list}

**Criterios de asignación:**
- Analiza el texto completo de la descripción para determinar la categoría más apropiada
- Busca palabras clave: nombres de comercios, conceptos bancarios, tipos de servicio
- Si hay ambigüedad, prioriza la categoría más general que aplique
- NUNCA inventes categorías que no estén en las listas anteriores

## 6. Determinación del Método de Pago
Infiere el método según la descripción:
- `tarjeta_credito`: Pagos con tarjeta de crédito
- `tarjeta_debito`: Débito directo, pagos con tarjeta débito
- `transferencia`: Transferencias bancarias
- `domiciliacion`: Recibos domiciliados, pagos recurrentes
- `bizum`: Operaciones Bizum
- `efectivo`: Retiradas de cajero, operaciones en efectivo
- `otro`: Cuando no se pueda determinar

# ESQUEMA JSON DE SALIDA (OBLIGATORIO)
```json
{{
  "banco": "string | null",
  "resumen_periodo": {{
    "titular": "string | null",
    "mes": "string | null",
    "anio": "string | null",
    "periodo_completo": "string | null",
    "saldo_inicial": 0.00,
    "saldo_final": 0.00,
    "total_ingresos": 0.00,
    "total_gastos": 0.00,
    "total_transacciones": 0
  }},
  "transacciones": [
    {{
      "fecha": "YYYY-MM-DD",
      "descripcion_original": "string",
      "descripcion_nlp": "string",
      "cantidad": 0.00,
      "tipo": "expense | income",
      "categoria": "string",
      "origen": "automatico",
      "notas": "string | null"
    }}
  ],
  "metadatos": {{
    "total_transacciones": 0,
    "formato_origen": "pdf | excel | csv | txt | imagen",
    "confianza_extraccion": "alta | media | baja",
    "advertencias": ["string"]
  }}
}}
```

# REGLAS CRÍTICAS

1. **SOLO JSON**: Devuelve ÚNICAMENTE el objeto JSON, sin texto adicional, sin markdown, sin explicaciones
2. **Normalización de fechas**: Siempre formato ISO `YYYY-MM-DD`
3. **Precisión decimal**: Siempre 2 decimales en cantidades
4. **Cantidades POSITIVAS**: El campo `cantidad` siempre es positivo; el `tipo` indica si es gasto/ingreso
5. **Manejo de errores**: Si un campo no se puede extraer, usa `null` (no inventes datos)
6. **Campos obligatorios**: `fecha`, `descripcion_original`, `descripcion_nlp`, `cantidad`, `tipo`, `categoria`, `origen`
7. **Array único**: Consolida TODAS las transacciones en el array `transacciones`
8. **Categorías válidas**: Usa SOLO las categorías proporcionadas arriba
9. **Advertencias**: Documenta inconsistencias o datos ambiguos en `metadatos.advertencias`
10. **No omitas transacciones**: Extrae TODOS los movimientos del documento, sin excepción

# VALIDACIONES FINALES

Antes de devolver el JSON, verifica:
- ✓ Todas las cantidades tienen 2 decimales y son positivas
- ✓ Todas las fechas están en formato YYYY-MM-DD
- ✓ Cada transacción tiene `descripcion_original` Y `descripcion_nlp`
- ✓ Las descripciones NLP son naturales y comprensibles
- ✓ TODAS las categorías existen en las listas proporcionadas
- ✓ El JSON es sintácticamente válido
- ✓ No hay campos obligatorios vacíos

**IMPORTANTE**: Si el documento contiene información ambigua o parcial, extrae lo máximo posible y documenta las limitaciones en `metadatos.advertencias`. NUNCA inventes datos.
"""


async def validate_file_size(file: UploadFile, max_size_mb: int):
    """
    Valida el tamaño del archivo leyéndolo en chunks
    para evitar cargar archivos grandes en memoria
    
    Args:
        file: Archivo a validar
        max_size_mb: Tamaño máximo permitido en MB
        
    Raises:
        HTTPException: Si el archivo excede el tamaño máximo
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    size = 0
    chunk_size = 8192  # 8KB chunks
    
    # Leer en chunks para no cargar todo en RAM
    while chunk := await file.read(chunk_size):
        size += len(chunk)
        if size > max_size_bytes:
            await file.seek(0)  # Reset para liberar memoria
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Archivo demasiado grande. Máximo permitido: {max_size_mb}MB"
            )
    
    # Reset para lectura posterior
    await file.seek(0)
    logger.info(f"Archivo validado: {size / (1024*1024):.2f}MB")


@router.post("/")
async def upload_document(
    fichero: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload y procesamiento de documentos bancarios con Gemini AI

    Validaciones:
    - Extensión permitida: pdf, xlsx, xls, csv, txt
    - Tamaño máximo: 2MB
    - Rate limiting: 100 req/min

    Seguridad:
    - Validación de tamaño antes de cargar en memoria
    - Limpieza automática de archivos temporales
    - Autenticación JWT requerida
    - Categorías personalizadas del usuario
    """
    upload_logger.info(f"Iniciando procesamiento de archivo: {fichero.filename} para usuario: {current_user.id}")

    # Validación 1: Extensión permitida
    if not fichero.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido")

    file_extension = fichero.filename.split('.')[-1].lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida. Permitidas: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Validación 2: Tamaño de archivo (antes de lectura completa)
    await validate_file_size(fichero, settings.MAX_FILE_SIZE_MB)

    # Obtener categorías del usuario para el prompt personalizado
    expense_categories = CategoryService.get_all_available_categories(db, current_user.id, category_type="expense")
    income_categories = CategoryService.get_all_available_categories(db, current_user.id, category_type="income")

    # Extraer nombres de categorías
    expense_names = [cat.name for cat in expense_categories] if expense_categories else ["Sin Categorizar"]
    income_names = [cat.name for cat in income_categories] if income_categories else ["Ingreso"]

    # Asegurar que siempre existan categorías por defecto
    if "Sin Categorizar" not in expense_names:
        expense_names.append("Sin Categorizar")
    if "Ingreso" not in income_names:
        income_names.append("Ingreso")

    # Generar prompt con las categorías del usuario
    prompt = build_extraction_prompt(expense_names, income_names)
    upload_logger.info(f"Prompt generado con {len(expense_names)} categorías de gasto y {len(income_names)} categorías de ingreso")

    temp_path = None
    try:
        # Crear directorio temporal y guardar archivo
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        with NamedTemporaryFile(delete=False, suffix=f".{fichero.filename.split('.')[-1]}", dir=temp_dir) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(fichero.file, temp_file)

        # 1. Subir a Google Generative AI
        upload_logger.info("Subiendo archivo a Gemini...")
        uploaded_file = genai.upload_file(path=temp_path)

        # 2. Inicializar modelo
        model = genai.GenerativeModel(model_name=settings.LLM_MODEL)

        # --- CÁLCULO DE COSTES POR LOGS ---
        # Contar tokens de entrada (Archivo + Prompt)
        count_response = model.count_tokens([uploaded_file, prompt])
        input_tokens = count_response.total_tokens

        # Estimación de salida (Ratio aproximado para JSON bancarios: 1.5x entrada)
        est_output_tokens = int(input_tokens * 1.5)

        # Precios Nivel 1 (Tier 1) - Gemini 2.5 Flash
        # Input: $0.10 / 1M tokens | Output: $0.40 / 1M tokens
        cost_in = (input_tokens / 1_000_000) * 0.10
        cost_out = (est_output_tokens / 1_000_000) * 0.40
        total_est_cost = cost_in + cost_out

        upload_logger.info(
            f"ESTIMACIÓN DE COSTE - Modelo: {settings.LLM_MODEL} | "
            f"Tokens Entrada: {input_tokens} | "
            f"Tokens Salida (est): {est_output_tokens} | "
            f"Coste Total Est: ${total_est_cost:.6f}"
        )

        # 3. Generar respuesta
        upload_logger.info(f"Generando contenido con modelo {settings.LLM_MODEL}...")
        response = model.generate_content([uploaded_file, prompt])

        # 4. Logs de consumo Real (Gemini devuelve los tokens usados en la respuesta)
        if hasattr(response, 'usage_metadata'):
            actual_in = response.usage_metadata.prompt_token_count
            actual_out = response.usage_metadata.candidates_token_count
            actual_cost = ((actual_in / 1_000_000) * 0.10) + ((actual_out / 1_000_000) * 0.40)
            upload_logger.info(f"COSTE REAL FINAL - In: {actual_in} | Out: {actual_out} | Coste: ${actual_cost:.6f}")

        # Limpiar y parsear JSON
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        parsed_data = json.loads(clean_json)

        # Log de resumen de extracción
        total_trans = len(parsed_data.get('transacciones', []))
        upload_logger.info(f"JSON parseado correctamente - Total transacciones: {total_trans}")

        return {
            "status": "success",
            "filename": fichero.filename,
            "data": parsed_data
        }

    except json.JSONDecodeError as e:
        upload_logger.error(f"Error al parsear JSON de Gemini: {str(e)}")
        log_exception(upload_logger, e, f"upload_document - {fichero.filename}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al parsear la respuesta del modelo: {str(e)}"
        )
    except Exception as e:
        upload_logger.error(f"Error al procesar archivo {fichero.filename}: {str(e)}")
        log_exception(upload_logger, e, f"upload_document - {fichero.filename}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )
    
    finally:
        # Limpiar archivos temporales
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
            upload_logger.info(f"Archivo temporal eliminado: {temp_path}")

