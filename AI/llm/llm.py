import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Carga las variables de entorno desde un archivo .env (opcional pero recomendado)
load_dotenv()

class LlmService:
    """
    Una clase de servicio para gestionar y proveer acceso a diferentes
    modelos de lenguaje (LLMs) de múltiples proveedores como Google (Gemini)
    y OpenAI (GPT).

    Esta clase permite configurar varios proveedores y obtener instancias
    de modelos para tareas generales o estructuradas.
    """

    def __init__(self, default_provider='gemini'):
        """
        Inicializa el servicio de LLMs.

        Args:
            default_provider (str): El proveedor a utilizar por defecto ('gemini' u 'openai').
        """
        self.default_provider = default_provider
        self._providers = {}

        # Inicializa los proveedores disponibles
        self._initialize_providers()

    def _initialize_providers(self):
        """
        Carga las configuraciones de los proveedores de LLM basadas en las
        variables de entorno.
        """
        # Configuración para Google Gemini
        if os.getenv("GEMINI_API_KEY"):
            self._providers['gemini'] = {
                'general_llm': None,
                'structured_llm': None,
                'config': {
                    'api_key': os.getenv("GEMINI_API_KEY"),
                    'model': os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                }
            }

        # Configuración para OpenAI
        if os.getenv("OPENAI_API_KEY"):
            self._providers['openai'] = {
                'general_llm': None,
                'structured_llm': None,
                'config': {
                    'api_key': os.getenv("OPENAI_API_KEY"),
                    'model': os.getenv("OPENAI_MODEL", "gpt-4o"),
                }
            }

    def _get_gemini_general_llm(self):
        """Crea y devuelve una instancia de Gemini para tareas generales."""
        if self._providers['gemini']['general_llm'] is None:
            config = self._providers['gemini']['config']
            self._providers['gemini']['general_llm'] = ChatGoogleGenerativeAI(
                model=config['model'],
                api_key=config['api_key'],
                temperature=0.5
            )
        return self._providers['gemini']['general_llm']

    def _get_gemini_structured_llm(self):
        """Crea y devuelve una instancia de Gemini optimizada para tareas estructuradas."""
        if self._providers['gemini']['structured_llm'] is None:
            config = self._providers['gemini']['config']
            self._providers['gemini']['structured_llm'] = ChatGoogleGenerativeAI(
                model=config['model'],
                api_key=config['api_key'],
                temperature=0.1  # Temperatura baja para respuestas más predecibles
            )
        return self._providers['gemini']['structured_llm']

    def _get_openai_general_llm(self):
        """Crea y devuelve una instancia de OpenAI para tareas generales."""
        if self._providers['openai']['general_llm'] is None:
            config = self._providers['openai']['config']
            self._providers['openai']['general_llm'] = ChatOpenAI(
                model=config['model'],
                api_key=config['api_key'],
                temperature=0.7
            )
        return self._providers['openai']['general_llm']

    def _get_openai_structured_llm(self):
        """Crea y devuelve una instancia de OpenAI optimizada para tareas estructuradas."""
        if self._providers['openai']['structured_llm'] is None:
            config = self._providers['openai']['config']
            self._providers['openai']['structured_llm'] = ChatOpenAI(
                model=config['model'],
                api_key=config['api_key'],
                temperature=0.1  # Temperatura baja para respuestas más predecibles
            )
        return self._providers['openai']['structured_llm']

    def get_general_llm(self, provider=None):
        """
        Obtiene un modelo de lenguaje para propósitos generales del proveedor especificado.

        Args:
            provider (str, optional): 'gemini' u 'openai'. Si no se especifica,
                                      se usa el proveedor por defecto.

        Returns:
            Una instancia de un modelo de lenguaje de LangChain.
        """
        provider_to_use = provider or self.default_provider
        if provider_to_use not in self._providers:
            raise ValueError(f"Proveedor '{provider_to_use}' no configurado o no soportado.")

        if provider_to_use == 'gemini':
            return self._get_gemini_general_llm()
        elif provider_to_use == 'openai':
            return self._get_openai_general_llm()

    def get_structured_llm(self, provider=None):
        """
        Obtiene un modelo de lenguaje optimizado para tareas estructuradas (ej. extracción de datos).

        Args:
            provider (str, optional): 'gemini' u 'openai'. Si no se especifica,
                                      se usa el proveedor por defecto.

        Returns:
            Una instancia de un modelo de lenguaje de LangChain con baja temperatura.
        """
        provider_to_use = provider or self.default_provider
        if provider_to_use not in self._providers:
            raise ValueError(f"Proveedor '{provider_to_use}' no configurado o no soportado.")

        if provider_to_use == 'gemini':
            return self._get_gemini_structured_llm()
        elif provider_to_use == 'openai':
            return self._get_openai_structured_llm()

# --- Ejemplo de Uso ---

# 1. Configura tus variables de entorno en un archivo .env
#    GEMINI_API_KEY="tu_api_key_de_gemini"
#    OPENAI_API_KEY="tu_api_key_de_openai"
#    GEMINI_MODEL="gemini-1.5-flash"
#    OPENAI_MODEL="gpt-4o"

"""

# 2. Crea una instancia del servicio
llm_service = LlmService(default_provider='gemini')

# 3. Obtén un modelo para una tarea general (usará Gemini por defecto)
try:
    general_llm = llm_service.get_general_llm()
    response = general_llm.invoke("Hola, ¿cómo estás?")
    print("Respuesta de Gemini (general):", response.content)

    # 4. Obtén un modelo para una tarea estructurada de un proveedor específico (OpenAI)
    structured_llm_openai = llm_service.get_structured_llm(provider='openai')
    response_structured = structured_llm_openai.invoke("Extrae el nombre y la edad de: 'Juan Pérez tiene 30 años'")
    print("\nRespuesta de OpenAI (estructurada):", response_structured.content)

except ValueError as e:
    print(e)
except Exception as e:
    print(f"Ocurrió un error inesperado: {e}")
"""
