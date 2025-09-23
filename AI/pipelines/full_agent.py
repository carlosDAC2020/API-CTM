# src/pipelines/full_agent.py
from langchain_core.runnables import RunnableLambda
from .discovery import create_discovery_pipeline
from .enrichment import create_enrichment_orchestrator as create_enrichment_pipeline
from ..utils.normalizers import flatten_opportunities

def create_full_agent_pipeline():
    """
    Crea y devuelve el pipeline COMPLETO y unificado, con nombres de pasos
    para la observabilidad y el streaming.
    """
    
    # Obtenemos los pipelines y les asignamos un nombre de alto nivel
    discovery_pipeline = create_discovery_pipeline().with_config({
        "run_name": "Stage 1: Discovery"
    })
    
    enrichment_pipeline = create_enrichment_pipeline().with_config({
        "run_name": "Stage 2: Enrichment"
    })

    # El aplanador final también puede tener un nombre
    final_formatter = RunnableLambda(flatten_opportunities).with_config({
        "run_name": "Formatting Final Output"
    })

    # Unimos los grandes bloques ya nombrados
    full_pipeline = (
        discovery_pipeline 
        | enrichment_pipeline 
        | final_formatter
    )
    
    return full_pipeline