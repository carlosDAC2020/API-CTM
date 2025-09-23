from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..config import settings
from ..schemas.models import QueryList

from ..llm.llm import LlmService

def create_query_generator_chain(llm : LlmService):
    """Construye y devuelve la cadena para generar queries de búsqueda."""
    
    system_prompt = """
    Actúa como un experto en la búsqueda de financiación para proyectos de innovación y tecnología. 
    Tu tarea es generar consultas de búsqueda (queries) estratégicas para encontrar oportunidades de financiación (grants, funding, convocatorias, etc.) basadas en la descripción de un proyecto que te proporcionará el usuario.
    Debes analizar el título, la descripción y las palabras clave del proyecto para crear 5 ideas de búsqueda diferentes y efectivas.
    Por cada idea, genera dos versiones de la query:
    1.  Una para búsquedas internacionales, en inglés.
    2.  Una para búsquedas a nivel nacional (Colombia), en español.
    Utiliza sinónimos y términos relacionados como "funding", "grants", "convocatorias", "financiación", "proyectos de investigación", "venture capital for green tech", etc.
    {format_instructions}
    """
    
    llm = llm.get_general_llm()
    
    parser = JsonOutputParser(pydantic_object=QueryList)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{project_details}"),
    ])
    
    return prompt_template | llm | parser