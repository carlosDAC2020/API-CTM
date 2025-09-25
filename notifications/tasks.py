from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from config import settings
import json

@shared_task(bind=True)
def send_email_task(self, recipient_list, subject, body, template_name=None, template_context=None, attachment_data=None, attachment_filename=None, attachment_mimetype=None):
    """
    Tarea de Celery para enviar un correo electrónico de forma asíncrona.
    """
    try:
        if template_name:
            # Si se proporciona una plantilla, renderizamos el cuerpo del correo desde ella
            html_content = render_to_string(template_name, json.loads(template_context or '{}'))
            message = EmailMessage(
                subject=subject,
                body=html_content, # El cuerpo es el HTML renderizado
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list
            )
            message.content_subtype = "html" # Indicamos que el contenido principal es HTML
        else:
            # Si no, enviamos un correo de texto plano
            message = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list
            )

        # Si hay datos de un adjunto, lo añadimos al mensaje
        if attachment_data and attachment_filename and attachment_mimetype:
            # attachment_data debe ser una lista de bytes, la decodificamos si es necesario
            message.attach(attachment_filename, bytes(attachment_data), attachment_mimetype)

        message.send()
        return f"Correo enviado exitosamente a {', '.join(recipient_list)}"

    except Exception as e:
        # Reintentar la tarea si falla, hasta 3 veces
        self.retry(exc=e, countdown=60, max_retries=3)
        return f"Error al enviar correo: {e}"