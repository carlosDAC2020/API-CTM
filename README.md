# Plataforma Asíncrona para Flujos de Agentes de IA

Este proyecto es una plataforma backend robusta y escalable, diseñada para la **ejecución asíncrona de flujos complejos de agentes de IA** construidos con LangChain. Su arquitectura genérica permite a los desarrolladores integrar y ejecutar fácilmente diferentes tareas de IA (desde simples generadores de texto hasta complejos agentes con herramientas como búsqueda web), mientras se ofrece **feedback en tiempo real al cliente** sobre el progreso de cada tarea.

## ✨ Características Principales

-   **Ejecución Asíncrona**: Utiliza **Celery y Redis** para delegar tareas pesadas y de larga duración a procesos en segundo plano (*workers*), asegurando que la aplicación principal nunca se bloquee y pueda manejar múltiples peticiones simultáneamente.
-   **Arquitectura Genérica de Flujos**: El sistema no está atado a una tarea específica. A través de un "Registro de Flujos", se pueden añadir nuevos agentes y cadenas de LangChain simplemente definiendo una función y registrándola, sin necesidad de modificar la lógica central de ejecución.
-   **Feedback en Tiempo Real**: Implementa **Server-Sent Events (SSE)** para establecer un canal de comunicación unidireccional y persistente entre el servidor Django y el cliente. Esto permite enviar actualizaciones detalladas del estado y los resultados intermedios de cada paso del flujo a medida que ocurren.
-   **Escalabilidad y Aislamiento**: Toda la aplicación está orquestada con **Docker Compose**, definiendo servicios separados para el servidor web (Django), los workers (Celery), el broker de mensajes (Redis) y la base de datos (PostgreSQL). Esto facilita el despliegue y la escalabilidad horizontal.
-   **Extensible**: Diseñado desde cero para ser fácil de extender. Añadir un nuevo y complejo flujo de IA es tan simple como escribir la lógica del flujo y registrarlo en el sistema.

## 🏗️ Arquitectura del Sistema

El flujo de comunicación y ejecución sigue el siguiente patrón:

![Diagrama](/docs/diagrama%20de%20ejeucion.png)

1.  El **Cliente** envía una petición POST a Django para iniciar un flujo específico.
2.  **Django** crea una tarea en Celery y la envía al broker **Redis**. Inmediatamente, devuelve un `task_id` al cliente.
3.  El **Worker de Celery** recoge la tarea, la ejecuta y actualiza su estado y resultados intermedios en el backend de resultados (también Redis).
4.  El **Cliente**, al recibir el `task_id`, establece una conexión SSE con Django, que a su vez consulta el estado de la tarea en Redis y transmite las actualizaciones en tiempo real.

## 🛠️ Stack Tecnológico

-   **Backend**: Django
-   **Tareas Asíncronas**: Celery
-   **Broker de Mensajes y Caché**: Redis
-   **Base de Datos**: PostgreSQL
-   **Orquestación de Contenedores**: Docker & Docker Compose
-   **Framework de IA**: LangChain
-   **Frontend**: HTML, CSS y JavaScript vainilla para la demostración.

## 🚀 Puesta en Marcha

Sigue estos pasos para levantar el entorno de desarrollo local.

### Prerrequisitos

-   Tener [Docker](https://www.docker.com/get-started) y Docker Compose instalados.

### 1. Clonar el Repositorio

```bash
git clone https://github.com/carlosDAC2020/API-CTM.git
cd API-CTM
```

### 2. Configurar Variables de Entorno

Crea un archivo llamado `.env` en la raíz del proyecto. Puedes copiar el archivo `env.example` (si existe) o usar la siguiente plantilla. Rellena tus claves de API.

```dotenv
# Clave secreta de Django (puedes generar una con python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
SECRET_KEY=tu_secret_key_aqui

# Configuración de la Base de Datos PostgreSQL
POSTGRES_DB=django_db
POSTGRES_USER=django_user
POSTGRES_PASSWORD=supersecretpassword
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Claves de APIs para los flujos de LangChain
GEMINI_API_KEY=tu_api_key_de_gemini
TAVILY_API_KEY=tu_api_key_de_tavily
```

### 3. Construir y Levantar los Contenedores

Este comando construirá las imágenes de Docker para el backend y el worker, y levantará todos los servicios.

```bash
docker-compose up --build -d
```
*(Usa `-d` para ejecutar en segundo plano)*.

### 4. Ejecutar las Migraciones de la Base de Datos

Una vez que los contenedores estén en ejecución, abre una nueva terminal y ejecuta las migraciones iniciales de Django para crear las tablas en la base de datos PostgreSQL.

```bash
docker-compose exec backend python manage.py migrate
```

### 5. Acceder a la Aplicación

¡Listo! Abre tu navegador y visita **`http://localhost:8000`**.

## 🧩 Cómo Añadir Nuevos Flujos de IA

La arquitectura está diseñada para ser fácilmente extensible. Para añadir un nuevo flujo:

1.  **Define el Flujo**: Ve al archivo `main/tasks.py` y crea una nueva función que construya y devuelva tu cadena de LangChain. Por ejemplo: `_create_mi_nuevo_flujo(llm)`.
2.  **Regístralo**: Añade la función al diccionario `FLOW_REGISTRY` con un nombre único.
    ```python
    FLOW_REGISTRY = {
        "poem_flow": _create_poem_flow,
        "web_search_flow": _create_web_search_flow,
        "mi_nuevo_flujo": _create_mi_nuevo_flujo, # <-- Tu nuevo flujo
    }
    ```
3.  **Actualiza el Frontend (Opcional)**: Añade la nueva opción al selector en `index.html` para que los usuarios puedan ejecutarlo.


---

## 🔌 Guía de uso 

Esta sección documenta los endpoints de la API necesarios para interactuar con la plataforma de ejecución de flujos.

La comunicación se basa en dos endpoints principales: uno para iniciar una tarea y otro para recibir sus actualizaciones en tiempo real.

### Endpoint 1: Iniciar un Flujo de Trabajo

Este endpoint crea una nueva tarea asíncrona y la pone en la cola para su ejecución.

*   **URL**: `/start-task/`
*   **Método**: `POST`
*   **Content-Type**: `application/json`
*   **Protección CSRF**: Sí. La petición debe incluir la cabecera `X-CSRFToken`.

#### Cuerpo de la Petición (Request Body)

El cuerpo de la petición es un objeto JSON que especifica qué flujo ejecutar y qué parámetros proporcionarle.

```json
{
  "flow": "nombre_del_flujo",
  "inputs": {
    "parametro_1": "valor_1",
    "parametro_2": "valor_2"
  }
}
```

*   `flow` (string, **requerido**): El nombre identificador del flujo que se desea ejecutar.
*   `inputs` (objeto, **opcional**): Un objeto JSON que contiene los parámetros necesarios para ese flujo específico. Si un flujo no requiere inputs, se puede enviar un objeto vacío `{}`.

#### Flujos Disponibles(ejemplos) y sus Inputs

| `nombre_del_flujo` | Descripción                                 | `inputs` Requeridos                                     |
|--------------------|---------------------------------------------|---------------------------------------------------------|
| `poem_flow`        | Genera un poema sobre un tema aleatorio.    | Objeto vacío: `{}`                                      |
| `web_search_flow`  | Busca en la web y resume la respuesta.      | `{ "question": "Tu pregunta aquí..." }`                 |
| *... (añadir más flujos aquí a medida que se creen)* | | |


#### Respuesta Exitosa (Código 200 OK)

Si la tarea se crea correctamente, la API devolverá un objeto JSON con el ID único de la tarea. Este ID es crucial para el siguiente paso.

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

#### Respuestas de Error

*   **Código 400 (Bad Request)**: El cuerpo de la petición es inválido, no es un JSON, o falta el campo `flow`.
*   **Código 403 (Forbidden)**: Falta el token CSRF o es incorrecto.
*   **Código 500 (Internal Server Error)**: Ocurrió un error inesperado al crear la tarea.

### Endpoint 2: Recibir Estado de la Tarea (Server-Sent Events)

Una vez que tienes el `task_id` del endpoint anterior, debes abrir una conexión de tipo Server-Sent Events (SSE) a este endpoint para recibir las actualizaciones en tiempo real.

*   **URL**: `/task-status/<task_id>/`
*   **Método**: `GET`
*   **Content-Type**: `text/event-stream`

#### Cómo Consumirlo en JavaScript

Debes usar la clase `EventSource` para suscribirte a las actualizaciones.

```javascript
// Obtén el task_id de la respuesta del endpoint /start-task/
const taskId = 'a1b2c3d4-e5f6-7890-1234-567890abcdef';
const eventSource = new EventSource(`/task-status/${taskId}/`);

eventSource.onmessage = function(event) {
    // Parsea los datos JSON que llegan en cada evento
    const data = JSON.parse(event.data);
    console.log("Nueva actualización:", data);

    // Aquí va tu lógica para actualizar la UI con la nueva información
    // updateTaskUI(taskId, data);

    // Si la tarea ha terminado, cierra la conexión para ahorrar recursos
    if (data.state === 'SUCCESS' || data.state === 'FAILURE') {
        eventSource.close();
    }
};

eventSource.onerror = function(error) {
    console.error("Error en la conexión SSE:", error);
    eventSource.close();
};
```

#### Formato de los Datos Recibidos

Cada mensaje recibido a través del `EventSource` será un objeto JSON con la siguiente estructura:

```json
{
  "state": "ESTADO_ACTUAL",
  "details": { ... }
}
```

*   `state` (string): El estado general de la tarea. Puede ser:
    *   `PENDING`: La tarea está en la cola, esperando ser procesada.
    *   `PROGRESS`: La tarea está siendo ejecutada por un worker.
    *   `SUCCESS`: La tarea finalizó con éxito.
    *   `FAILURE`: La tarea falló.

*   `details` (objeto): Contiene la información detallada del estado `PROGRESS`, `SUCCESS` o `FAILURE`.

##### Estructura del objeto `details`

```json
{
    "status": "Mensaje de estado actual, ej: 'Ejecutando LLM...'",
    "progress": 80, // Un número del 0 al 100
    "step_results": [
        // Una lista de los pasos completados hasta ahora
        {
            "type": "log",
            "message": "▶️ Iniciando paso: 'Generando Prompt del Tema'..."
        },
        {
            "type": "tool_result",
            "step_name": "Búsqueda en la Web (Tavily)",
            "tool": "tavily_search_results_json",
            "data": [
                {
                    "url": "https://example.com",
                    "content": "Contenido encontrado en la web..."
                }
            ]
        }
    ],
    "final_result": "El resultado final de la cadena cuando state es 'SUCCESS'"
}
```

*   `step_results` (array): Una lista ordenada de los eventos ocurridos durante la ejecución. Cada objeto en el array tiene un `type` que te permite renderizarlo de forma diferente:
    *   `type: "log"`: Un simple mensaje de progreso. Muestra el `message`.
    *   `type: "tool_result"`: El resultado de la ejecución de una herramienta. Muestra el `step_name` como título y el contenido de `data` (que suele ser un objeto o lista de objetos JSON).


### 📬 Módulo de Notificaciones Asíncronas

El proyecto incluye un módulo de notificaciones robusto y desacoplado, encapsulado en la aplicación Django `notifications`. Su propósito es gestionar el envío de correos electrónicos de forma asíncrona, asegurando que las operaciones de notificación no afecten el rendimiento de la aplicación principal ni la experiencia del usuario.

#### Arquitectura del Servicio de Notificaciones

Este servicio sigue una arquitectura basada en tareas en segundo plano, integrándose perfectamente con el ecosistema de Celery y Redis ya establecido.