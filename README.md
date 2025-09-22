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

```
                  +-------------------------+
                  |  Cliente (Navegador)    |
                  +-------------------------+
                          |      ^
      (1) Iniciar Tarea   |      | (4) Stream de Estado (SSE)
        (POST /start-task)|      |
                          v      |
                  +-------------------------+
                  |   Servidor Web (Django) |
                  +-------------------------+
                          |      ^
      (2) Enviar Tarea    |      | (3) Leer Estado de Tarea
        a la cola         |      |
                          v      |
                  +-------------------------+      +--------------------------+
                  |     Broker (Redis)      |<---->| Backend Resultados (Redis)|
                  +-------------------------+      +--------------------------+
                          |                                   ^
      (2.1) Worker        |                                   | (3.1) Actualizar
        recoge tarea      |                                   |     Progreso
                          v                                   |
                  +-------------------------+      +--------------------------+
                  |      Worker (Celery)    |----->|  Base de Datos (PostgreSQL)|
                  +-------------------------+      +--------------------------+
                          |                                (Opcional: persistir
  (2.2) Ejecuta flujo     |                                   resultados finales)
  de LangChain e interactúa
  con APIs externas (ej. Gemini)
```

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