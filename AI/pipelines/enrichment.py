# src/pipelines/enrichment.py
import time
from typing import List, Dict
from langchain_core.runnables import RunnableLambda
from ..components.enricher import create_full_enrichment_pipeline
from ..schemas.models import FundingOpportunity

def create_enrichment_orchestrator():
    """Crea una cadena que toma una LISTA de oportunidades y las enriquece secuencialmente."""
    
    enrichment_worker_pipeline = create_full_enrichment_pipeline()

    def process_list_sequentially(opportunities_list: List[FundingOpportunity]) -> List[FundingOpportunity]:
        print(f"\n[Enrichment Stage] Iniciando enriquecimiento para {len(opportunities_list)} oportunidades...")
        enriched_opportunities = []
        
        for i, opportunity in enumerate(opportunities_list):
            print(f"--- Enriqueciendo {i+1}/{len(opportunities_list)}: {opportunity.origin} ---")
            try:
                # --- ¡MODIFICACIÓN CLAVE AQUÍ! ---
                # Creamos un nombre dinámico para la ejecución de cada item.
                # El frontend podrá mostrar "Enriqueciendo: Climate Change AI"...
                run_config = {
                    "run_name": f"Enriching Item: {opportunity.origin[:40]}" # Limitamos a 40 chars
                }
                
                # Pasamos la configuración directamente a la llamada .invoke()
                enriched_result = enrichment_worker_pipeline.invoke(
                    opportunity.dict(), # El worker espera un dict
                    config={"callbacks": run_config.get("callbacks"), **run_config}
                )
                
                enriched_opportunities.append(enriched_result)
            except Exception as e:
                print(f"  -> ❌ Error crítico durante el enriquecimiento: {e}")
                continue
            time.sleep(2)
            
        return enriched_opportunities

    return RunnableLambda(process_list_sequentially)