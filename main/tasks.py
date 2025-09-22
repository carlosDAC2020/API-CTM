# task_app/tasks.py
import os
from celery import shared_task
from celery.utils.log import get_task_logger

# --- Dependencias de LangChain ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.callbacks.base import BaseCallbackHandler

from django.conf import settings

logger = get_task_logger(__name__)

# --- Callback Handler Personalizado para LangChain (sin cambios) ---
class CeleryCallbackHandler(BaseCallbackHandler):
    def __init__(self, task):
        self.task = task
        self.results = []
    def on_chain_start(self, serialized, inputs, **kwargs):
        status_message = f"Iniciando cadena '{kwargs.get('name', 'desconocida')}'..."
        self.results.append(status_message)
        self.task.update_state(state='PROGRESS', meta={'status': status_message, 'step_results': self.results, 'progress': 10})
    def on_chain_end(self, outputs, **kwargs):
        status_message = "Cadena completada."
        self.results.append(status_message)
        self.task.update_state(state='PROGRESS', meta={'status': status_message, 'step_results': self.results, 'progress': 90})
    def on_llm_start(self, serialized, prompts, **kwargs):
        status_message = "LLM está pensando..."
        self.results.append(status_message)
        self.task.update_state(state='PROGRESS', meta={'status': status_message, 'step_results': self.results, 'progress': 50})

@shared_task(bind=True)
def run_langchain_flow(self):
    """
    Ejecuta un flujo de LangChain usando la API de Gemini.
    """
    handler = CeleryCallbackHandler(task=self)
    try:
        gemini_api_key = settings.GEMINI_API_KEY
        if not gemini_api_key:
            raise ValueError("La variable de entorno GEMINI_API_KEY no está configurada.")

        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", api_key=gemini_api_key, temperature=0.7)

        prompt_tema = ChatPromptTemplate.from_template("Sugiere un tema interesante y poco común para un poema.")
        prompt_poema = ChatPromptTemplate.from_template("Escribe un poema corto sobre el siguiente tema: {tema}")
        
        cadena = (
            prompt_tema 
            | llm 
            | (lambda ai_message: ai_message.content if hasattr(ai_message, 'content') else str(ai_message))
            | (lambda tema_str: {"tema": tema_str})
            | prompt_poema 
            | llm
        )
        
        resultado = cadena.invoke({}, config={"callbacks": [handler]})
        
        handler.results.append("Poema generado con éxito.")
        
        final_content = resultado.content if hasattr(resultado, 'content') else str(resultado)

        return {
            'status': '¡Flujo de LangChain completado!',
            'step_results': handler.results,
            'final_result': final_content,
            'progress': 100
        }
    except Exception as e:
        logger.error(f"Error en la tarea de Celery: {e}", exc_info=True)
        error_message = f"Error durante la ejecución: {type(e).__name__} - {e}"
        self.update_state(state='FAILURE', meta={'status': error_message, 'step_results': getattr(handler, 'results', [])})
        return {'status': error_message}