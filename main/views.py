# task_app/views.py
import json
import time
from celery.result import AsyncResult
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from .tasks import run_langchain_flow

class HomeView(TemplateView):
    template_name = "main/index.html"

@require_POST
def start_task_view(request):
    """
    Inicia una tarea de Celery genérica basada en el cuerpo de la petición.
    """
    try:
        data = json.loads(request.body)
        flow_name = data.get("flow")
        flow_inputs = data.get("inputs", {})

        if not flow_name:
            return JsonResponse({"error": "El nombre del flujo ('flow') es requerido."}, status=400)

        # Pasamos los argumentos a la tarea de Celery
        task = run_langchain_flow.apply_async(args=[flow_name, flow_inputs])
        
        return JsonResponse({"task_id": task.id})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Cuerpo de la petición JSON inválido."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def task_status_view(request, task_id):
    """
    Envía el estado de la tarea en tiempo real usando SSE.
    """
    def event_stream():
        while True:
            task_result = AsyncResult(task_id)
            response_data = {
                "state": task_result.state,
                "details": task_result.info if task_result.state != 'FAILURE' else str(task_result.info)
            }
            
            # Formato SSE: "data: <json_string>\n\n"
            yield f"data: {json.dumps(response_data)}\n\n"

            if task_result.ready():
                break
            
            time.sleep(1) # Espera 1 segundo antes de la siguiente verificación

    # Usamos StreamingHttpResponse para enviar el flujo de eventos
    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response['Cache-Control'] = 'no-cache' # Asegura que el navegador no cachee la respuesta
    return response