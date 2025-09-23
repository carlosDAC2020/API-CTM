from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import WebBaseLoader

from ..schemas.models import FundingOpportunityList
from ..config import settings

from ..llm.llm import LlmService

def scrape_content(item: dict) -> dict:
    """
    Toma un item con una URL, la scrapea, y devuelve el item con el contenido.
    Maneja errores de forma robusta.
    """
    try:
        loader = WebBaseLoader(item["url"])
        docs = loader.load()
        content = " ".join([doc.page_content for doc in docs])
        item["page_content"] = content[:10000] 
    except Exception as e:
        print(f"  -> ⚠️ Error al scrapear {item['url']}: {e}")
        item["page_content"] = "Error al cargar el contenido de la página."
    return item

def create_extractor_chain(llm : LlmService):
    """
    Crea una cadena que toma contenido de una página y extrae UNA LISTA de oportunidades.
    """
    
    # ¡PROMPT ACTUALIZADO!
    extractor_prompt = ChatPromptTemplate.from_messages([
        ("system", 
         """Eres un analista experto en identificar oportunidades de financiación.
Tu tarea es leer el contenido de una página web y extraer la información clave de TODAS las convocatorias, subvenciones o grants que encuentres.
Debes devolver una lista, incluso si encuentras una sola oportunidad o ninguna.
Si un dato específico (como la fecha límite o la URL de la convocatoria) no se encuentra en el texto, omite ese campo.
Como mínimo, cada oportunidad debe tener un origen y una descripción."""),
        ("human", "Aquí está el contenido de la página:\n\nCONTEXTO:\n{page_content}\n\nURL ORIGINAL:\n{url}")
    ])
    
    llm = llm.get_structured_llm()
    
    #  Usamos el modelo de lista para la salida estructurada
    structured_llm = llm.with_structured_output(FundingOpportunityList)
    
    extractor_chain = extractor_prompt | structured_llm
    
    return extractor_chain

def create_full_extraction_pipeline(llm : LlmService):
    """
    Encapsula el scraping y la extracción en un único pipeline.
    """
    extractor = create_extractor_chain(llm)
    scraper_runnable = RunnableLambda(scrape_content)
    return scraper_runnable | extractor