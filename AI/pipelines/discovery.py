# src/pipelines/discovery.py
import time
from typing import List, Dict
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel

from ..components.query_generator import create_query_generator_chain
from ..components.researcher import create_research_chain, fetch_and_limit_rss_feeds, RSS_FEEDS
from ..components.scrutinizer import create_scrutinizer_chain
from ..components.extractor import create_full_extraction_pipeline
from ..utils.normalizers import flatten_queries, combine_results, normalize_search_results
from ..schemas.models import FundingOpportunityList

from ..llm.llm import LlmService

# --- ¡AQUÍ VIVE LA LÓGICA DE ORQUESTACIÓN SECUENCIAL! ---

def scrutinize_sequentially(search_results: List[Dict], scrutinizer_chain: Runnable) -> List[Dict]:
    """Evalúa los resultados de búsqueda uno por uno para encontrar fuentes relevantes."""
    if not search_results: return []
    print(f"\n[Discovery Stage] Escrutando {len(search_results)} resultados secuencialmente...")
    filtered_results = []
    for result in search_results:
        try:
            print(f"  -> Escrutando: {result.get('title', 'Sin título')}")
            scrutiny_output = scrutinizer_chain.invoke(result)
            if scrutiny_output.is_relevant:
                print("    ✅ Relevante.")
                filtered_results.append(result)
            else:
                print("    ❌ Descartado.")
            time.sleep(4.1) # Pausa para respetar el límite de 15 RPM
        except Exception as e:
            print(f"    ⚠️ Error durante el escrutinio: {e}")
            continue
    return filtered_results

def extract_sequentially(relevant_results: List[Dict], extractor_chain: Runnable) -> List[Dict]:
    """Extrae información detallada de las fuentes relevantes, una por una."""
    if not relevant_results: return []
    print(f"\n[Discovery Stage] Extrayendo de {len(relevant_results)} fuentes secuencialmente...")
    all_opportunities = []
    for result in relevant_results:
        try:
            print(f"  -> Extrayendo de: {result.get('url')}")
            opportunity_list = extractor_chain.invoke(result)
            # La salida del extractor es FundingOpportunityList, accedemos a su contenido
            all_opportunities.extend(opportunity_list.opportunities)
        except Exception as e:
            print(f"    ⚠️ Error durante la extracción: {e}")
            continue
        time.sleep(2) # Pausa entre extracciones
    return all_opportunities

# --- FIN DE LA LÓGICA DE ORQUESTACIÓN ---

def create_discovery_pipeline(llm : LlmService):
    """
    Crea el pipeline de descubrimiento con el flujo de datos corregido y pasos nombrados.
    """
    query_generator = create_query_generator_chain(llm)
    web_researcher = create_research_chain()
    scrutinizer = create_scrutinizer_chain(llm)
    extractor = create_full_extraction_pipeline(llm)

    # --- LÓGICA DE PIPELINE CORREGIDA ---

    # Paso 1: Definimos una cadena que BUSCA y LUEGO NORMALIZA un resultado de búsqueda.
    # La salida de web_researcher es un dict {'tavily': ..., 'brave': ...}.
    # La entrada de normalize_search_results es exactamente ese dict. Encajan perfectamente.
    search_and_normalize_one = (
        web_researcher 
        | RunnableLambda(normalize_search_results)
    ).with_config({"run_name": "Search & Normalize One Query"})

    # Paso 2: Creamos el pipeline de búsqueda web.
    web_search_pipeline = (
        RunnableLambda(flatten_queries).with_config({"run_name": "Flattening Queries"})
        # Ahora mapeamos la cadena 'search_and_normalize_one'. 
        # Su salida será una lista de listas de resultados normalizados.
        | search_and_normalize_one.map()
        # combine_results ahora recibe la entrada correcta (una lista de listas) y funciona.
        | RunnableLambda(combine_results).with_config({"run_name": "Combining Web Results"})
    )

    # Paso 3: Creamos el pipeline de RSS (sin cambios)
    rss_fetcher_pipeline = RunnableLambda(
        lambda _: fetch_and_limit_rss_feeds(RSS_FEEDS, limit_per_feed=5)
    ).with_config({"run_name": "Fetching RSS Feeds"})

    # Paso 4: Unimos la búsqueda web y RSS en paralelo
    research_step = RunnableParallel(
        web_results=web_search_pipeline,
        rss_results=rss_fetcher_pipeline
    ).with_config({"run_name": "Performing Research (Web + RSS)"})
    
    # Paso 5: Nombramos los pasos secuenciales de análisis
    scrutinizer_step = RunnableLambda(
        lambda results: scrutinize_sequentially(results, scrutinizer)
    ).with_config({"run_name": "Scrutinizing Results"})
    
    extractor_step = RunnableLambda(
        lambda results: extract_sequentially(results, extractor)
    ).with_config({"run_name": "Extracting Opportunities"})

    # Paso 6: Ensamblamos el pipeline de descubrimiento final
    discovery_pipeline = (
        query_generator.with_config({"run_name": "Generating Queries"})
        | RunnableLambda(lambda x: x['queries'])
        | research_step
        # Combinamos los resultados de las dos ramas de investigación
        | RunnableLambda(lambda x: x['web_results'] + x['rss_results']).with_config({"run_name": "Combining All Sources"})
        | scrutinizer_step
        | extractor_step
    )
    
    return discovery_pipeline