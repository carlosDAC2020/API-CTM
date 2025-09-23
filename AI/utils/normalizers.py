# utils/normalizers.py
import json
import time
from typing import List, Dict, Any
from langchain_core.runnables import Runnable
from ..schemas.models import FundingOpportunityList

# --- Funciones que no cambian ---
def flatten_queries(query_list: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    flat_list = []
    for item in query_list:
        if item.get('international_query'):
            flat_list.append({"query": item['international_query']})
        if item.get('national_query'):
            flat_list.append({"query": item['national_query']})
    return flat_list

def combine_results(list_of_lists: List[List[Dict]]) -> List[Dict]:
    combined = []
    for sublist in list_of_lists:
        # Pequeña validación para evitar errores si un sublist no es una lista
        if isinstance(sublist, list):
            combined.extend(sublist)
    return combined

def normalize_search_results(raw_results: Dict[str, Any]) -> List[Dict[str, str]]:
    normalized = []
    for res in raw_results.get("tavily", []):
        normalized.append({
            "title": res.get("title", "Sin título"),
            "url": res.get("url"),
            "description": res.get("content")
        })
    brave_res_list = raw_results.get("brave", [])
    if isinstance(brave_res_list, str):
        try: brave_res_list = json.loads(brave_res_list)
        except json.JSONDecodeError: brave_res_list = []
    for res in brave_res_list:
        normalized.append({
            "title": res.get("title", "Sin título"),
            "url": res.get("link"),
            "description": res.get("snippet")
        })
    return normalized

def flatten_opportunities(list_of_opportunity_lists: List[FundingOpportunityList]) -> List[dict]:
    final_list = []
    for opportunity_list in list_of_opportunity_lists:
        # Nos aseguramos de que el objeto es del tipo esperado antes de acceder a sus atributos
        if isinstance(opportunity_list, FundingOpportunityList):
            for opportunity in opportunity_list.opportunities:
                final_list.append(opportunity.dict())
    return final_list