from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from ..schemas.models import ScrutinyResult
from ..config import settings

from ..llm.llm import LlmService

def create_scrutinizer_chain(llm : LlmService):
    """
    Crea una cadena que actúa como un filtro.
    Toma un resultado de búsqueda y decide si vale la pena scrapear la página.
    """
    
    scrutinizer_prompt = ChatPromptTemplate.from_messages([
        ("system", 
         """Eres un analista de inteligencia encargado de pre-filtrar fuentes de información.
Tu única tarea es decidir si un enlace, basado en su título, URL y descripción, es una **fuente directa de financiación** (como una convocatoria, una página de 'grants', o un premio) o si es **contenido secundario** (como una noticia, un artículo de blog, un directorio de empresas, o un paper académico).
Responde únicamente con el formato JSON solicitado."""),
        ("human", 
         """Analiza la siguiente fuente y determina si es relevante para una extracción detallada:
- Título: {title}
- URL: {url}
- Descripción: {description}""")
    ])
    
    # Usamos el modelo más rápido y económico para esta tarea de clasificación simple.
    llm = llm.get_structured_llm()
    
    # Forzamos la salida al schema que definimos
    structured_llm = llm.with_structured_output(ScrutinyResult)
    chain_with_retry = (
        scrutinizer_prompt 
        | structured_llm.with_retry(
            stop_after_attempt=4,           # Intentará hasta 4 veces
            wait_exponential_jitter=True,   # Usa una espera variable para evitar colisiones
            #wait_exponential_max=10         # Esperará un máximo de 10 segundos entre intentos
        )
    )

    return chain_with_retry