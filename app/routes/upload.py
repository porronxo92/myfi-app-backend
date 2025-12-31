from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, status
from app.config import settings
from app.utils.security import get_current_user, check_rate_limit
from app.models import User
from app.utils.logger import get_logger, upload_logger, log_exception
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
    dependencies=[Depends(get_current_user), Depends(check_rate_limit)]
)

# Configurar Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)
logger.info("Gemini API configurada correctamente")


PROMPT_INGENIERO = """
# ROL
Eres un experto en procesamiento de datos financieros con conocimientos avanzados en extracción de información estructurada de documentos bancarios multiformato.

# OBJETIVO
Extraer y normalizar todas las transacciones bancarias de cualquier tipo de documento (PDF, Excel, CSV, TXT, imágenes) en un formato JSON estructurado compatible con el sistema de gestión financiera.

# CONTEXTO DEL SISTEMA
- Base de datos PostgreSQL con tablas: transactions, accounts, categories
- Las transacciones se clasifican en: income (ingreso), expense (gasto), transfer (transferencia)
- Cada transacción debe tener: fecha, descripción, cantidad, tipo y categoría
- El sistema soporta múltiples bancos y formatos de extracto

# INSTRUCCIONES DE PROCESAMIENTO

## 1. Análisis del Documento
- **Identifica el banco emisor**: Busca logos, encabezados, nombres de entidad
- **Detecta el tipo de cuenta**: Cuenta corriente, tarjeta de crédito, ahorro, inversión
- **Extrae metadatos**: Titular, periodo (mes/año), número de cuenta (si está visible)
- **Localiza todas las tablas de movimientos**: Pueden existir múltiples secciones

## 2. Extracción de Transacciones
Para cada transacción identificada, extrae:
- **Fecha**: Formato DD/MM/YYYY (normaliza cualquier formato encontrado: DD-MM-YY, DD/MM/AA, etc.)
- **Descripción**: Texto completo del concepto/descripción (limpia caracteres especiales innecesarios)
- **Cantidad**: Valor numérico (ver reglas de normalización)
- **Tipo de operación**: Determina si es cargo o abono según el contexto del documento
- **Origen**: Siempre debe ser "automatico"

## 2.1. Procesamiento de Descripciones (NLP)
Para cada transacción, genera DOS versiones de la descripción:

### **descripcion_original**
- Mantén el texto exacto como aparece en el extracto bancario
- Preserva códigos, referencias y formato original
- Útil para trazabilidad y auditoría

### **descripcion_nlp**
- **Transforma la descripción técnica en lenguaje natural y comprensible**
- Aplica estas reglas de normalización:

**Limpieza:**
- Elimina códigos técnicos innecesarios: `TRF-12345`, `REF:`, `ID:`, `CCC:`, etc.
- Elimina asteriscos, guiones bajos y caracteres especiales redundantes
- Normaliza mayúsculas: usa mayúscula inicial en sustantivos propios

**Contextualización:**
- Añade contexto cuando sea útil: "Pago" → "Pago de factura"
- Especifica el tipo de servicio si es obvio: "VODAFONE" → "Vodafone - Telefonía"
- Humaniza abreviaturas: "TPTE" → "Transporte", "GASOLINA" → "Repostaje"

**Criterios de calidad:**
- Máximo 80 caracteres
- Debe ser comprensible sin contexto técnico
- Mantén información relevante: ubicación si es significativa, nombre del comercio
- Elimina redundancias: "MERCADONA PZA.PADRE JOFRE, 12006" → "Mercadona"

## 3. Normalización de Importes
**CRÍTICO**: Aplica estas reglas en orden:
1. Elimina separadores de miles (puntos o espacios): `1.234,56` → `1234,56`
2. Convierte coma decimal a punto: `1234,56` → `1234.56`
3. **Convención de signos**:
   - **Gastos/Cargos**: números NEGATIVOS → `-150.50`
   - **Ingresos/Abonos**: números POSITIVOS → `2500.00`
4. Siempre incluye 2 decimales: `150` → `150.00`

## 4. Clasificación de Categorías
Analiza el texto de la descripción y asigna la categoría más apropiada:

**CATEGORÍAS DE GASTO** (type: "expense"):
- `Supermercado`: Mercadona, Carrefour, Lidl, Aldi, compras alimentación
- `Restaurantes`: Bares, cafeterías, comida a domicilio, Glovo, Uber Eats
- `Transporte`: Metro, autobús, taxi, Uber, Cabify, combustible
- `Coche`: Mantenimiento, ITV, seguro vehículo, parking
- `Bicicleta`: Reparaciones, accesorios bici
- `Compras Online`: Tiendas online generales, marketplace
- `Amazon`: Específicamente compras en Amazon
- `Alquiler`: Pago de alquiler vivienda, arrendamiento
- `Ocio/Deporte`: Gimnasio, cine, conciertos, deportes
- `Viajes`: Hoteles, vuelos, Booking, Airbnb
- `Salud/Cuidados`: Farmacia, médico, dentista, óptica
- `Gastos Fijos`: Luz, agua, gas, internet, teléfono, seguros
- `Inversión`: Aportaciones a fondos, compra acciones, planes pensiones
- `Bizum`: Transferencias Bizum salientes
- `Regalos`: Compras de regalos para terceros
- `Gastos Personales`: Peluquería, ropa, productos personales
- `Sin Categorizar`: Cuando no puedas determinar la categoría con certeza
- `Transferencia`: Transferencias entre cuentas propias o a terceros

**CATEGORÍAS DE INGRESO** (type: "income"):
- `Salario`: Nómina, pago de empresa empleadora
- `Freelance`: Pagos por trabajos independientes, facturas
- `Inversiones`: Dividendos, venta de acciones, rendimientos
- `Ingreso - Bizum`: Transferencias Bizum entrantes
- `Intereses`: Intereses bancarios, rendimientos cuenta
- `Ingreso`: Otros ingresos no clasificables en anteriores

## 5. Determinación del Método de Pago
Analiza la descripción e infiere el método:
- `tarjeta_credito`: Pagos con tarjeta (indica si es Visa, Mastercard si está visible)
- `tarjeta_debito`: Débito directo
- `transferencia`: Transferencias bancarias
- `domiciliacion`: Recibos domiciliados
- `bizum`: Operaciones Bizum
- `efectivo`: Retiradas de cajero, operaciones en efectivo
- `otro`: Cuando no se pueda determinar

# ESQUEMA JSON DE SALIDA
```json
{
  "banco": "string | null",
  "resumen_periodo": {
    "titular": "string | null",
    "mes": "string | null",
    "anio": "string | null",
    "periodo_completo": "string | null",
    "saldo_inicial": 0.00,
    "saldo_final": 0.00,
    "total_ingresos": 0.00,
    "total_gastos": 0.00, 
    "total_transacciones": 0 // balance total sumando gastos e ingresos
  },
  "transacciones": [
    {
      "fecha": "YYYY-MM-DD",
      "descripcion_original": "string",
      "descripcion_nlp": "string",
      "cantidad": 0.00, //siempre debe ser positivo
      "tipo": "expense | income",
      "categoria": "string",
      "origen": "string | null", // siempre debe ser automatico
      "notas": "string | null"
    }
  ],
  "metadatos": {
    "total_transacciones": 0,
    "formato_origen": "pdf | excel | csv | txt | imagen",
    "confianza_extraccion": "alta | media | baja",
    "advertencias": ["string"]
  }
}
```

# REGLAS CRÍTICAS

1. **SOLO JSON**: Devuelve únicamente el objeto JSON, sin texto adicional, sin markdown, sin explicaciones
2. **Normalización de fechas**: Siempre formato ISO `YYYY-MM-DD`
3. **Precisión decimal**: Siempre 2 decimales en cantidades
4. **Signos consistentes**: Gastos negativos, ingresos positivos
5. **Manejo de errores**: Si un campo no se puede extraer, usa `null` en lugar de inventar datos
6. **Campos obligatorios en transacciones**: `fecha`, `descripcion`, `cantidad`, `tipo`, `categoria`
7. **Array único**: Consolida todas las transacciones en un solo array `transacciones`, no separes por tipo
8. **Categorización inteligente**: Usa el contexto completo de la descripción para categorizar
9. **Preserva información**: Si hay datos adicionales relevantes, inclúyelos en `notas`
10. **Advertencias**: Si encuentras inconsistencias, datos ambiguos o problemas de extracción, documéntalos en `metadatos.advertencias`

# EJEMPLOS DE MAPEO

**Descripción original** → **Categoría**
- "MERCADONA MADRID" → Supermercado
- "UBER TRIP 12345" → Transporte  
- "NETFLIX SUSCRIPCION" → Gastos Fijos
- "NOMINA EMPRESA XYZ" → Salario
- "BIZUM DE JUAN PEREZ" → Ingreso - Bizum
- "AMAZON EU SARL" → Amazon
- "REINT. CAJERO AUTO. MADRID" → efectivo (retirada)

# VALIDACIONES FINALES

Antes de devolver el JSON:
- ✓ Todas las cantidades tienen 2 decimales
- ✓ Todas las fechas están en formato YYYY-MM-DD
- ✓ No hay campos obligatorios vacíos (excepto valores legítimamente null)
- ✓ **Cada transacción tiene descripcion_original Y descripcion_nlp**
- ✓ **Las descripciones NLP son naturales y comprensibles sin contexto técnico**
- ✓ Los signos son correctos: gastos negativos, ingresos positivos
- ✓ Todas las categorías existen en el catálogo definido
- ✓ El JSON es sintácticamente válido

**IMPORTANTE**: Si el documento contiene información ambigua o parcial, extrae lo máximo posible y documenta las limitaciones en `metadatos.advertencias`. Nunca inventes datos.

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
async def upload_document(fichero: UploadFile = File(...)):
    """
    Upload y procesamiento de documentos bancarios con Gemini AI
    
    Validaciones:
    - Extensión permitida: pdf, xlsx, csv, txt
    - Tamaño máximo: 10MB
    - Rate limiting: 100 req/min
    
    Seguridad:
    - Validación de tamaño antes de cargar en memoria
    - Limpieza automática de archivos temporales
    - Autenticación JWT requerida
    """
    upload_logger.info(f"Iniciando procesamiento de archivo: {fichero.filename}")
    
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

    temp_path = None
    try:
        # ... (Mantener creación de directorio y guardado temporal igual)
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
        
        # --- NUEVO: CÁLCULO DE COSTES POR LOGS ---
        # Contar tokens de entrada (Archivo + Prompt)
        count_response = model.count_tokens([uploaded_file, PROMPT_INGENIERO])
        input_tokens = count_response.total_tokens
        
        # Estimación de salida (Ratio aproximado para JSON bancarios: 1.5x entrada)
        est_output_tokens = int(input_tokens * 1.5)
        
        # Precios Nivel 1 (Tier 1) - Gemini 2.0 Flash
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
        # -----------------------------------------

        # 3. Generar respuesta
        upload_logger.info(f"Generando contenido con modelo {settings.LLM_MODEL}...")
        response = model.generate_content([uploaded_file, PROMPT_INGENIERO])
        
        # 4. Logs de consumo Real (Gemini devuelve los tokens usados en la respuesta)
        if hasattr(response, 'usage_metadata'):
            actual_in = response.usage_metadata.prompt_token_count
            actual_out = response.usage_metadata.candidates_token_count
            actual_cost = ((actual_in / 1_000_000) * 0.10) + ((actual_out / 1_000_000) * 0.40)
            upload_logger.info(f"COSTE REAL FINAL - In: {actual_in} | Out: {actual_out} | Coste: ${actual_cost:.6f}")

        # Limpiar y parsear JSON
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        parsed_data = json.loads(clean_json)
        
        upload_logger.info(f"JSON parseado correctamente - Gastos: {len(parsed_data.get('data', {}).get('gastos', []))}, Ingresos: {len(parsed_data.get('data', {}).get('ingresos', []))}")
        
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

