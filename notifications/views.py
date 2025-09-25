from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .tasks import send_email_task

def test_sender_view(request):
    """Renderiza el frontend de prueba para enviar correos."""
    return render(request, 'notifications/test_sender.html')

@require_POST
def send_notification_view(request):
    """
    Vista de API para encolar una tarea de envío de correo.
    Maneja datos de formulario, incluyendo archivos adjuntos.
    """
    try:
        # Obtenemos los datos del formulario (request.POST)
        recipients = request.POST.get('recipients')
        subject = request.POST.get('subject', 'Sin Asunto')
        body = request.POST.get('body', '')
        template_name = request.POST.get('template_name') # Ej: "notifications/generic_notification.html"
        template_context = request.POST.get('template_context', '{}') # Un string JSON

        if not recipients:
            return JsonResponse({'error': 'El campo "recipients" es requerido.'}, status=400)
        
        recipient_list = [email.strip() for email in recipients.split(',')]
        
        # Manejo del archivo adjunto (request.FILES)
        attachment_data = None
        attachment_filename = None
        attachment_mimetype = None

        if 'attachment' in request.FILES:
            uploaded_file = request.FILES['attachment']
            attachment_filename = uploaded_file.name
            attachment_mimetype = uploaded_file.content_type
            # Leemos el contenido del archivo en memoria como bytes
            attachment_data = uploaded_file.read()

        # Encolamos la tarea de Celery con todos los argumentos
        task = send_email_task.apply_async(args=[
            recipient_list,
            subject,
            body,
            template_name or None,
            template_context,
            attachment_data,
            attachment_filename,
            attachment_mimetype
        ])

        return JsonResponse({'status': 'Correo encolado', 'task_id': task.id})

    except Exception as e:
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)