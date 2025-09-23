import time
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.tools.tavily_search import TavilySearchResults

from ..schemas.models import FundingOpportunity # ¡Importamos el schema de salida!
from ..config import settings

from ..llm.llm import LlmService

# --- PASO 1: Lógica para obtener el contenido de la mejor fuente ---
def get_best_content(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Toma una oportunidad, busca la mejor URL si es necesario, la scrapea,
    y devuelve la oportunidad original junto con el contenido de la página.
    """
    content = "No se pudo cargar contenido relevante."
    target_url = opportunity.get("opportunity_url")

    # Si no hay una URL, intentamos encontrar una
    if not target_url:
        print(f"  ->  URL no encontrada para '{opportunity.get('origin')}'. Buscando en la web...")
        try:
            search_tool = TavilySearchResults(max_results=1)
            query = f"funding opportunity official page {opportunity.get('origin')} {opportunity.get('description', '')[:100]}"
            search_results = search_tool.invoke(query)
            if search_results and search_results[0].get("url"):
                target_url = search_results[0]["url"]
                print(f"  -> URL encontrada: {target_url}")
                # Actualizamos la URL en la oportunidad original para el siguiente paso
                opportunity["opportunity_url"] = target_url
        except Exception as e:
            print(f"  -> ⚠️ Error durante la búsqueda: {e}")

    # Si tenemos una URL (original o encontrada), la scrapeamos
    if target_url:
        try:
            print(f"  -> Scrapeando: {target_url}")
            loader = WebBaseLoader(target_url)
            docs = loader.load()
            content = " ".join([doc.page_content for doc in docs])
            # Limitamos el contenido para no exceder los límites de tokens del LLM
            opportunity["page_content"] = content[:15000]
        except Exception as e:
            print(f"  -> ⚠️ Error al scrapear {target_url}: {e}")
            opportunity["page_content"] = "Error al cargar el contenido de la página."
    else:
        opportunity["page_content"] = "No se pudo encontrar una URL para scrapear."

    return opportunity


# --- PASO 2: Lógica del LLM para refinar la información ---
def create_deep_dive_chain(llm : LlmService):
    """
    Crea una cadena que usa un LLM para analizar el contenido de una página
    y refinar los detalles de una oportunidad de financiación.
    """
    refinement_prompt = ChatPromptTemplate.from_messages([
        ("system",
        """Eres un analista de investigación experto y meticuloso.
        Tu tarea es tomar una oportunidad de financiación preliminar y, basándote en el contenido detallado de su página web, verificar, completar y refinar la información.
        - Corrige cualquier dato incorrecto en la oportunidad original.
        - Completa los campos que estén vacíos (como `application_deadline` o `main_requirements`) si encuentras la información en el texto.
        - Mejora la `description` para que sea más precisa y concisa.
        - Asegúrate de que `opportunity_url` sea el enlace más directo y relevante.
        - Si la página menciona múltiples convocatorias, enfócate únicamente en la que más se parezca a la oportunidad original.
        - Responde únicamente con el formato JSON solicitado."""),
        ("human",
        """Aquí está la información que debes analizar:

        **1. Oportunidad Preliminar (Datos Originales):**
        ```json
        {original_opportunity}
        {page_content}
        Ahora, por favor, refina la oportunidad basándote en el contenido de la página.""")
    ])

    llm = llm.get_structured_llm()

    # Forzamos la salida al schema de una ÚNICA oportunidad
    structured_llm = llm.with_structured_output(FundingOpportunity)

    # Creamos la cadena que alimenta el prompt y llama al LLM
    chain = (
        RunnablePassthrough.assign(
            original_opportunity=RunnableLambda(lambda x: x) # Pasamos la oportunidad completa
        )
        | refinement_prompt
        | structured_llm
    )

    return chain

# --- PASO 3: Pipeline completo que une la obtención de datos y el refinamiento ---
def create_full_enrichment_pipeline():
    """
    Encapsula la búsqueda de fuente, el scraping y el refinamiento en un único pipeline.
    """
    content_scrapper = RunnableLambda(get_best_content)
    refinement_chain = create_deep_dive_chain()

    # El pipeline toma una oportunidad, le añade el 'page_content' y luego lo pasa todo a la cadena de refinamiento.
    full_pipeline = content_scrapper | refinement_chain

    return full_pipeline