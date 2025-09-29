
import time
from typing import List, Dict
from langchain_core.runnables import Runnable, RunnableLambda, RunnableParallel, RunnablePassthrough

from ..components.query_generator import create_query_generator_chain
from ..components.researcher import create_research_chain, fetch_and_limit_rss_feeds, RSS_FEEDS
from ..components.scrutinizer import create_scrutinizer_chain
from ..components.extractor import create_full_extraction_pipeline
from ..utils.normalizers import flatten_queries, combine_results, normalize_search_results
from ..schemas.models import FundingOpportunityList

from ..llm.llm import LlmService

# modelos de datos 
from projects.models import Research, ItemContext, Opportunity

def scrutinize_sequentially(search_results: List[Dict], scrutinizer_chain: Runnable, research_id: int) -> List[Dict]:
    """Evalúa los resultados de búsqueda uno por uno para encontrar fuentes relevantes."""
    
    if not search_results: return []

    print(f"\n[Discovery Stage] Escrutando {len(search_results)} resultados secuencialmente...")
    research_instance = Research.objects.get(id=research_id)
    research_instance.initial_results_count = len(search_results)
    research_instance.save()

    filtered_results = []

    for result in search_results:
        is_relevant = False
        try:
            print(f"  -> Escrutando: {result.get('title', 'Sin título')}")
            scrutiny_output = scrutinizer_chain.invoke(result)
            if scrutiny_output.is_relevant:
                print("    ✅ Relevante.")
                is_relevant = True
                filtered_results.append(result)
            else:
                print("    ❌ Descartado.")

            # Guardamos CADA item, marcando si es relevante o no
            ItemContext.objects.update_or_create(
                research=research_instance,
                url=result.get('url'),
                defaults={
                    'title': result.get('title', 'Sin Título'),
                    'description': result.get('content', ''),
                    'is_relevant': is_relevant
                }
            )
            time.sleep(4.1) # Pausa para respetar el límite de 15 RPM
        except Exception as e:
            print(f"    ⚠️ Error durante el escrutinio: {e}")
            continue
        
    # actualizamos metrica de relevancia
    research_instance.relevant_results_count = len(filtered_results)
    research_instance.save()
    
    return filtered_results

def extract_sequentially(relevant_results: List[Dict], extractor_chain: Runnable, research_id: int) -> List[Dict]:
    """Extrae información detallada de las fuentes relevantes, una por una."""
    if not relevant_results: return []

    research_instance = Research.objects.get(id=research_id)

    print(f"\n[Discovery Stage] Extrayendo de {len(relevant_results)} fuentes secuencialmente...")
    all_opportunities = []
    for result in relevant_results:
        try:
            # Obtenemos el ItemContext correspondiente al que estamos evluando 
            item_context = ItemContext.objects.get(research=research_instance, url=result.get('url'))
            print(f"  -> Extrayendo de: {result.get('url')}")
            opportunity_list = extractor_chain.invoke(result)
            for opp_data in opportunity_list.opportunities:
                # Guardamos la oportunidad en la DB, enlazada a su contexto
                Opportunity.objects.create(
                    research=research_instance,
                    source_context=item_context,
                    origin=opp_data.origin,
                    description=opp_data.description,
                    financing=opp_data.financing_type,
                    requirements=opp_data.main_requirements,
                    deadline = opp_data.application_deadline,
                    url_to = opp_data.opportunity_url
                )
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

    """
    # Paso 4: Unimos la búsqueda web y RSS en paralelo
    research_step = RunnableParallel(
        web_results=web_search_pipeline,
        rss_results=rss_fetcher_pipeline
    ).with_config({"run_name": "Performing Research (Web + RSS)"})
    
    # Paso 5: Nombramos los pasos secuenciales de análisis
    scrutinizer_step = RunnableLambda(
        lambda input_dict: scrutinize_sequentially(
            input_dict['combined_results'], 
            scrutinizer,
            input_dict['research_id']
        )
    ).with_config({"run_name": "Scrutinizing Results"})
    
    extractor_step = RunnableLambda(
        lambda input_dict: extract_sequentially(
            input_dict['relevant_results'],
            extractor,
            input_dict['research_id']
        )
    ).with_config({"run_name": "Extracting Opportunities"})

    # Paso 6: Ensamblamos el pipeline de descubrimiento final
    discovery_pipeline = (
        #query_generator.with_config({"run_name": "Generating Queries"})
        #| RunnableLambda(lambda x: x['queries'])
        #| research_step
        # Combinamos los resultados de las dos ramas de investigación
        #| RunnableLambda(lambda x: x['web_results'] + x['rss_results']).with_config({"run_name": "Combining All Sources"})
        #| scrutinizer_step
        #| extractor_step


        query_generator.with_config({"run_name": "Generating Queries"})
        | RunnableLambda(lambda x: x['queries'])
        | research_step
        # --- CLAVE: Preparamos el input para los siguientes pasos ---
        | RunnablePassthrough.assign(
            combined_results=lambda x: x['web_results'] + x['rss_results']
        ).with_config({"run_name": "Combining All Sources"})
        # Pasamos el research_id a través del pipeline
        | (lambda input_dict: {
            "combined_results": input_dict['combined_results'],
            "research_id": input_dict['research_id']
           })
        | RunnablePassthrough.assign(relevant_results=scrutinizer_step)
        | (lambda input_dict: {
            "relevant_results": input_dict['relevant_results'],
            "research_id": input_dict['research_id']
           })
        | extractor_step
    ).with_config({"run_name": "discovery_opportunities_flow"})
    """

    # Paso 1: Generar queries a partir del input inicial
    step1_query_gen = RunnablePassthrough.assign(
        queries=query_generator.with_config({"run_name": "Generating Queries"})
    )

    # Paso 2: Realizar la investigación en paralelo
    step2_research = RunnablePassthrough.assign(
        research_results=RunnableParallel(
            web_results=(lambda x: x['queries']['queries']) | web_search_pipeline,
            rss_results=rss_fetcher_pipeline
        )
    ).with_config({"run_name": "Performing Research (Web + RSS)"})

    # Paso 3: Combinar resultados y escrutinar
    step3_scrutinize = RunnablePassthrough.assign(
        relevant_results=(
            lambda x: scrutinize_sequentially(
                x['research_results']['web_results'] + x['research_results']['rss_results'],
                scrutinizer,
                x['research_id'] # <-- Pasamos el research_id que fluye por el Passthrough
            )
        )
    ).with_config({"run_name": "Scrutinizing Results"})

    # Paso 4: Extraer oportunidades de los resultados relevantes
    step4_extract = (
         RunnableLambda(
            lambda x: extract_sequentially(
                x['relevant_results'],
                extractor,
                x['research_id']
            )
        )
    ).with_config({"run_name": "Extracting Opportunities"})


    # --- Ensamblamos el pipeline final ---
    discovery_pipeline = (
        step1_query_gen
        | step2_research
        | step3_scrutinize
        | step4_extract
    ).with_config({"run_name": "discovery_opportunities_flow"})
    
    
    return discovery_pipeline