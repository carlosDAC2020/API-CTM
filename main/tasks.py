import os
import json
import time 
from celery import shared_task
from celery.result import AsyncResult
from celery.utils.log import get_task_logger

from django.conf import settings

# --- Dependencias de LangChain ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough,  RunnableLambda
from langchain.callbacks.base import BaseCallbackHandler

# --- NUEVO: Dependencias para la herramienta de búsqueda ---
from langchain_community.tools.tavily_search import TavilySearchResults

# flujos de busqueda 
from AI.pipelines.discovery import create_discovery_pipeline
from AI.pipelines.enrichment import create_enrichment_orchestrator

from AI.llm.llm import LlmService

# modelos de datos de logica principal 
from projects.models import Project, Research 



logger = get_task_logger(__name__)


# --- PASO 3: Callback Handler más inteligente ---
class CeleryCallbackHandler(BaseCallbackHandler):
    def __init__(self, task):
        self.task = task
        self.results = []

    def _update_state(self, status_message, progress):
        """
        Función auxiliar para llamar a self.task.update_state.
        Este es el método correcto para actualizar el estado desde dentro de un worker.
        """
        self.task.update_state(
            state='PROGRESS',
            meta={'status': status_message, 'step_results': self.results, 'progress': progress}
        )

    # --- MÉTODO ACTUALIZADO ---
    def on_chain_start(self, serialized, inputs, **kwargs):
        # kwargs['name'] contiene el valor de run_name que definimos
        run_name = kwargs.get('name')
        if run_name: # Solo registramos los pasos que hemos nombrado explícitamente
            log_entry = {'type': 'log', 'message': f"▶️ Iniciando paso: '{run_name}'..."}
            self.results.append(log_entry)
            self._update_state(f"Ejecutando '{run_name}'...", 10)

    # --- MÉTODO ACTUALIZADO ---
    def on_llm_start(self, serialized, prompts, **kwargs):
        run_name = kwargs.get('name')
        if run_name:
            log_entry = {'type': 'log', 'message': f"🤖 LLM procesando para: '{run_name}'..."}
            self.results.append(log_entry)
            self._update_state(f"LLM pensando en '{run_name}'...", 50)

    # --- MÉTODO ACTUALIZADO ---
    def on_tool_end(self, output: str, name: str, **kwargs):
        # 'name' aquí es el run_name de la herramienta
        run_name = name 
        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            data = output
            
        tool_entry = {
            'type': 'tool_result',
            # Guardamos tanto el nombre del paso como el tipo de herramienta
            'step_name': run_name,
            'tool': 'tavily_search_results_json', # Esto podría ser más dinámico si usas más herramientas
            'data': data
        }
        self.results.append(tool_entry)
        self._update_state(f"Herramienta '{run_name}' completada.", 75)


# ---  Registro de Flujos ---
def _create_poem_flow(llm:LlmService):
    """Define el flujo simple de generación de poemas."""
    prompt_tema = ChatPromptTemplate.from_template("Sugiere un tema interesante y poco común para un poema.")
    prompt_poema = ChatPromptTemplate.from_template("Escribe un poema corto sobre el siguiente tema: {tema}")
    

    llm = llm.get_general_llm()

    return (
        prompt_tema.with_config(run_name="Generando Prompt del Tema") | 
        llm.with_config(run_name="LLM Sugiriendo Tema")
        | RunnableLambda(lambda ai_message: ai_message.content).with_config(run_name="Extrayendo Contenido del Tema")
        | RunnableLambda(lambda tema_str: {"tema": tema_str}).with_config(run_name="Preparando Input para Poema")
        | prompt_poema.with_config(run_name="Generando Prompt del Poema")
        | llm.with_config(run_name="LLM Escribiendo Poema")
    ).with_config(run_name="Flujo de Creación de Poema")

def _create_web_search_flow(llm : LlmService):
    """NUEVO: Define un flujo que busca en la web y resume."""
    # 1. Herramienta de búsqueda
    search = TavilySearchResults(max_results=3)

    llm = llm.get_general_llm()

    # 2. Prompt que usará los resultados de la búsqueda
    prompt = ChatPromptTemplate.from_template(
        "Basado en estos resultados de búsqueda:\n\n---\n{context}\n---\n\n"
        "Por favor, responde la siguiente pregunta: {question}"
    )

    # 3. Construcción del flujo
    return (
        RunnablePassthrough.assign(
            context=RunnableLambda(lambda x: x["question"]).with_config(run_name="Extrayendo Pregunta") | search
        ).with_config(run_name="Paso de Búsqueda y Asignación de Contexto")
        | prompt.with_config(run_name="Construyendo Prompt Final con Contexto")
        | llm.with_config(run_name="LLM Respondiendo a la Pregunta")
    ).with_config(run_name="Flujo de Búsqueda y Resumen Web")

# Diccionario que mapea nombres de flujos a sus funciones de creación
FLOW_REGISTRY = {
    "poem_flow": _create_poem_flow,
    "web_search_flow": _create_web_search_flow,
    "discovery_opportunities_flow" : create_discovery_pipeline,
    "enrichment_opportunities_flow": create_enrichment_orchestrator
}


# --- Tarea de Celery Genérica ---
@shared_task(bind=True)
def run_langchain_flow(self, flow_name, flow_inputs=None, project_id=None):
    """
    Ejecuta un flujo de LangChain de forma genérica.
    :param flow_name: El nombre del flujo a ejecutar (debe estar en FLOW_REGISTRY).
    :param flow_inputs: Un diccionario con los inputs para el flujo (ej. {'question': '...'})
    """
    start_time = time.time()
    flow_inputs = flow_inputs or {}
    handler = CeleryCallbackHandler(task=self)

    research = None
    if project_id:
        try:
            project = Project.objects.get(id=project_id)
            # Creamos el registro de la investigación
            research = Research.objects.create(project=project, status='RUNNING')
            # --- CLAVE: Añadimos el ID de la investigación a los inputs del flujo ---
            flow_inputs['research_id'] = research.id
        except Project.DoesNotExist:
            # ... (manejo de error)
            return {'status': 'Error: Proyecto no encontrado.'}
    
    try:
        if flow_name not in FLOW_REGISTRY:
            raise ValueError(f"Flujo '{flow_name}' no encontrado.")

        # Inicializamos el LLM
        llm = LlmService(default_provider='gemini')
        
        # Obtenemos y creamos el flujo desde el registro
        create_flow_func = FLOW_REGISTRY[flow_name]
        chain = create_flow_func(llm)

        final_inputs = flow_inputs 
        
        # Invocamos la cadena con sus inputs y nuestro handler
        resultado = chain.invoke(final_inputs, config={"callbacks": [handler]})
        
        final_content = resultado.content if hasattr(resultado, 'content') else str(resultado)

        if research:
            # refrescamos los registros de la base de datos 
            research.refresh_from_db()
            # actualizamos el tiempo de ejecucion y los estados 
            research.execute_time = time.time() - start_time
            research.status = 'COMPLETED'
            research.save()

        return {
            'status': '¡Flujo completado!',
            'step_results': handler.results,
            'final_result': final_content,
            'progress': 100
        }
    except Exception as e:
        # en caso de fallar el reserch se coloca el estado correspondiente 
        if research:
            research.status = 'FAILED'
            research.save()

        logger.error(f"Error en flujo genérico: {e}", exc_info=True)
        error_message = f"Error: {type(e).__name__} - {e}"
        self.update_state(state='FAILURE', meta={'status': error_message, 'step_results': getattr(handler, 'results', [])})
        return {'status': error_message}