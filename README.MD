# 🌊 AquaChile Virtual Assistant

## Descripción

Asistente virtual basado en IA diseñado para ayudar a los empleados de AquaChile con consultas sobre reglamentos, políticas empresariales y documentos oficiales.

## Características

- Responde preguntas sobre el Código de Conducta
- Proporciona información sobre políticas y procedimientos
- Aclara dudas sobre normativas internas
- Consulta reglamentos y documentos oficiales
- Interfaz de chat intuitiva
- Soporte multilingüe (Español e Inglés)

## Tecnologías Utilizadas

- Python
- Chainlit (interfaz de chat)
- LangChain (procesamiento de lenguaje natural)
- ChromaDB (base de datos vectorial)
- Modelos de IA

## Requisitos

- Python 3.11+
- Pip (gestor de paquetes de Python)
- Archivo .env con las claves API necesarias

## Instalación

1. Clonar el repositorio

    ```sh
    git clone [url-del-repositorio]
    ```

2. Instalar dependencias:

    ```sh
    pip install -r requirements.txt
    ```

## Uso

1. Iniciar la aplicación

    ```sh
    chainlit run app.py -w
    ```

2. Abrir el navegador en `http://localhost:8000`

## Estructura del proyecto

├── app.py            # Punto de entrada principal
├── agent.py          # Lógica del agente conversacional
├── utils/            # Utilidades y helpers
│   ├── models.py     # Definiciones de modelos
│   ├── prompts.py    # Templates de prompts
│   └── tools.py      # Herramientas auxiliares
└── .chainlit/        # Configuración de Chainlit
