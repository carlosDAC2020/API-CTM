from typing import List, Optional
from pydantic import BaseModel, Field

# --- Modelo para la generación de Queries ---
class SearchQuery(BaseModel):
    idea: str = Field(description="La idea o el enfoque principal de la búsqueda.")
    international_query: str = Field(description="Query de búsqueda para oportunidades internacionales (en inglés).")
    national_query: str = Field(description="Query de búsqueda para oportunidades nacionales en Colombia (en español).")

class QueryList(BaseModel):
    queries: List[SearchQuery] = Field(description="Una lista de 5 pares de queries de búsqueda generadas.")

# --- esquema para validacion de fuentes ------------------------
class ScrutinyResult(BaseModel):
    is_relevant: bool = Field(description="Verdadero si la fuente parece ser una convocatoria, grant, o página de financiación directa. Falso si es una noticia, un blog, un directorio o un artículo académico.")
    
# --- Modelo para el paso de "Identification of Opportunities" ---
class FundingOpportunity(BaseModel):
    origin: str = Field(description="Nombre de la organización o convocatoria que ofrece la financiación.")
    description: str = Field(description="Un resumen conciso de la oportunidad de financiación.")
    financing_type: Optional[str] = Field(None, description="Tipo de financiación (ej. grant, inversión, subsidio).")
    main_requirements: Optional[List[str]] = Field(default_factory=list, description="Lista de los requisitos principales para aplicar.")
    application_deadline: Optional[str] = Field(None, description="Fecha límite para la postulación (formato YYYY-MM-DD).")
    opportunity_url: Optional[str] = Field(None, description="El enlace directo a la página específica de la convocatoria, si se encuentra.")

# --- Modelo para contener la lista de oportunidades ---
class FundingOpportunityList(BaseModel):
    opportunities: List[FundingOpportunity] = Field(description="Una lista de todas las oportunidades de financiación encontradas en la página.")

