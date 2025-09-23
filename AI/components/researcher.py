# src/components/researcher.py

import feedparser
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import BraveSearch

# <-- ¡IMPORTANTE! Las importaciones ahora son relativas a la carpeta 'src'
from ..config import settings 

# --- SECCIÓN DE LÓGICA RSS ---

# Lista de URLs de RSS que quieres monitorear.
RSS_FEEDS = [
    "https://minciencias.gov.co/convocatorias/todas/rss.xml",
#    "https://www.innpulsacolombia.com/feed",
#    "https://www.grants.gov/rss/GG_NewOppRSS.jsp",
#    "https://www.nsf.gov/funding/rss/agencylist.xml"
]

def fetch_and_limit_rss_feeds(rss_urls: list[str], limit_per_feed: int = 5) -> list[dict]:
    """
    Lee una lista de feeds RSS y limita el número de entradas por cada uno.
    Esta función es independiente y será llamada una sola vez por el pipeline.
    """
    all_entries = []
    print(f"\n[Researcher] Leyendo {len(rss_urls)} fuentes RSS (límite: {limit_per_feed} por feed)...")
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            # Usamos slicing para tomar solo los primeros N elementos.
            for entry in feed.entries[:limit_per_feed]:
                all_entries.append({
                    "title": entry.get("title", "Sin título"),
                    "url": entry.get("link"),
                    "description": entry.get("summary", entry.get("description", ""))
                })
        except Exception as e:
            print(f"  -> ⚠️ Error al leer el feed RSS {url}: {e}")
            continue
    print(f"  -> Se encontraron {len(all_entries)} entradas en total en los feeds RSS.")
    return all_entries


# --- SECCIÓN DE LÓGICA DE BÚSQUEDA WEB ---

def create_research_chain():
    """
    Construye y devuelve una cadena que busca en la web (Tavily y Brave)
    para una ÚNICA query. Esta cadena está diseñada para ser usada con .map().
    
    NOTA: Esta cadena ya NO normaliza los resultados. Su única responsabilidad
    es obtener los datos brutos de la búsqueda. La normalización es
    responsabilidad del pipeline que la utiliza.
    """
    
    fallback_to_empty_list = RunnableLambda(lambda x: [])

    # NOTA: TavilySearchResults está obsoleto. Si actualizas, usa langchain_tavily
    tavily_tool = TavilySearchResults(
        max_results=settings.TAVILY_MAX_RESULTS
    ).with_retry(stop_after_attempt=3, wait_exponential_jitter=True).with_fallbacks([fallback_to_empty_list])

    brave_tool = BraveSearch.from_api_key(
        api_key=settings.BRAVE_SEARCH_API_KEY, 
        search_kwargs={"count": settings.BRAVE_SEARCH_COUNT}
    ).with_retry(stop_after_attempt=3, wait_exponential_jitter=True).with_fallbacks([fallback_to_empty_list])

    # Esta cadena toma una query y la busca en paralelo en ambas herramientas.
    parallel_search_step = RunnableParallel(
        tavily=tavily_tool, 
        #brave=brave_tool
    )
    
    return parallel_search_step