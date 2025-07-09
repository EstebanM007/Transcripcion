# 🎙️ Transcriptor y Chat con IA

Una aplicación de escritorio que convierte archivos de audio y video a texto mediante reconocimiento de voz y permite interactuar con una IA conversacional para resumir y analizar las transcripciones.

## 📋 Características

- **Transcripción de Audio/Video**: Convierte archivos multimedia a texto
- **Chat con IA**: Interactúa con un chatbot inteligente basado en LLaMA
- **Formatos Soportados**: MP4, OGG, MP3, WAV
- **Procesamiento por Segmentos**: Divide el audio en fragmentos de 60 segundos
- **Interfaz Gráfica**: Aplicación moderna con Tkinter
- **Generación de Archivos**: Crea archivos WAV y TXT automáticamente

## 🚀 Instalación

### Requisitos Previos

- Python 3.8 o superior
- FFmpeg instalado en el sistema
- Conexión a Internet para peticiones a la IA

### Dependencias

```bash
pip install -r requirements.txt
```
- Se genero un `requirements.txt` con - `pip freeze > requirements.txt`
- Para instalar librerias utilice `pip install -r requirements.txt`

**requirements.txt:**
```
moviepy
SpeechRecognition
langchain
langchain-groq
langchain-core
tkinter
```

### Clonar Repositorio de Transcripcion (Herramientas Python)

```bash
# Clonar el repositorio
git clone [Transcripcion](https://github.com/EstebanM007/Transcripcion)
cd Entorno

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install moviepy SpeechRecognition langchain langchain-groq langchain-core

# Inicia la interfaz en la terminal
python Produccion.py
```

## 🔧 Configuración

### API Key de Groq

La aplicación utiliza la API de Groq para el chat con IA. La clave API está incluida en el código por defecto, pero puedes configurar la tuya propia:

```python
os.environ["GROQ_API_KEY"] = "tu_clave_api_aqui"
```

O establecer la variable de entorno:
```bash
export GROQ_API_KEY="tu_clave_api_aqui"
```

Puedes iniciar sesion de manera gratuita en [Groq](https://console.groq.com/home) y generar una key para estas aplicaciones

## 📖 Uso

### Ejecución desde Python

```bash
python Produccion.py
```

### Ejecución desde Ejecutable

1. Descargar el archivo [`TranscriptorIA.exe`](https://github.com/EstebanM007/Media)
2. Ejecutar directamente

### Flujo de Trabajo

1. **Seleccionar Archivo**: Haz clic en "📁 Seleccionar Archivo" y elige tu archivo multimedia
2. **Transcribir**: Presiona "🎵 Transcribir Audio" para iniciar el proceso
3. **Esperar Resultados**: El proceso se mostrará en tiempo real en el panel derecho
4. **Interactuar con IA**: Usa el chat inferior para hacer preguntas sobre la transcripción

### Archivos Generados

- `archivo.wav`: Archivo de audio convertido
- `transcripcion.txt`: Texto de la transcripción completa
- `segment_*.wav`: Archivos temporales de segmentos (se eliminan automáticamente), Si se cancela el proceso en medio de la transcripcion los segmentos no se eliminan.

## 🛠️ Pasos para generar el .exe de manera Exitosa

### Preparación del Entorno

```bash
# Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install moviepy SpeechRecognition langchain langchain-groq langchain-core pyinstaller
```

### Modificación del Código para generar el .exe

**Cambio requerido en el archivo fuente:**

```python
# Cambiar esta línea:
from moviepy.editor import VideoFileClip, AudioFileClip

# Por esta línea:
from moviepy import *
```

### Comando de Compilación Utilizado

```bash
pyinstaller --name TranscriptorIA --onefile --icon="ruta_al_icono.ico" Produccion.py
```

**Opciones del comando:**
- `--name TranscriptorIA`: Nombre del ejecutable
- `--onefile`: Genera un solo archivo ejecutable
- `--icon="ruta_al_icono.ico"`: Especifica el icono (opcional)

### Archivos Generados

- `dist/TranscriptorIA.exe`: Ejecutable final
- `build/`: Archivos temporales de compilación
- `TranscriptorIA.spec`: Especificación de PyInstaller

## 🎯 Funcionalidades Detalladas

### Panel de Transcripción

- **Registro en Tiempo Real**: Muestra el progreso de la conversión y transcripción
- **Información del Proceso**: Detalles sobre cada segmento procesado
- **Manejo de Errores**: Reporta problemas durante el proceso

### Chat con IA

- **Memoria Conversacional**: Recuerda los últimos 5 mensajes
- **Análisis de Transcripciones**: Genera resúmenes automáticos
- **Interacción Natural**: Responde preguntas sobre el contenido transcrito

### Procesamiento de Audio

- **Conversión Automática**: Convierte diferentes formatos a WAV
- **Segmentación Inteligente**: Divide archivos largos en segmentos manejables
- **Reconocimiento de Voz**: Utiliza Google Speech Recognition

## ⚠️ Limitaciones y Consideraciones

### Limitaciones Técnicas

- **Calidad del Audio**: La precisión depende de la claridad del audio original
- **Idioma**: Configurado para español (es-ES)
- **Conexión a Internet**: Requiere conexión para reconocimiento de voz y IA
- **Límites de API**: Sujeto a los límites de la API de Groq

### Rendimiento

- **Memoria**: Archivos muy grandes pueden requerir más memoria
- **Tiempo de Procesamiento**: Depende de la duración del archivo
- **Archivos Temporales**: Se crean archivos temporales durante el proceso

## 🔍 Solución de Problemas

### Errores Comunes

**Error de FFmpeg:**
```
Solución: Instalar FFmpeg y agregarlo al PATH del sistema
```

**Error de API:**
```
Solución: Verificar la clave API de Groq y la conexión a internet
```

**Error de Reconocimiento:**
```
Solución: Verificar la calidad del audio y la conexión a internet
```

### Archivos de Log

Los errores se muestran en el panel de transcripción con timestamp para facilitar el debugging.

## 👨‍💻 Información del Desarrollador

**Autor**: Esteban Alberto Martinez Palacios  
**Organización**: Estrategia Digital y GEN XXI  
**Descripción**: Aplicación para convertir audio a texto y generar resúmenes con IA


## Cambios y mejoras recientes

### 🆕 Selección de modelo IA flexible
- Ahora puedes **escribir el nombre de cualquier modelo IA** soportado por [GROQ](https://console.groq.com/docs/models) en el campo "Modelo IA".
- El campo sugiere `llama3-8b-8192` pero puedes usar cualquier modelo válido (ejemplo: `llama3-70b-8192`, `mixtral-8x7b-32768`, etc).
- El modelo IA se guarda y carga automáticamente junto con la API Key.

### 🆕 Formato de chat mejorado
- El chat con IA ahora muestra los mensajes con **separadores, encabezados y formato Markdown avanzado**.
- Los mensajes del usuario e IA aparecen claramente diferenciados y con formato enriquecido.
- El área de chat soporta **negrita, cursiva, listas, encabezados, código y enlaces** incluso dentro de listas.

### 🆕 Experiencia de usuario
- El campo de entrada del chat muestra un **placeholder** que desaparece al escribir y se restaura si queda vacío.
- El botón "Enviar" se desactiva si el campo está vacío.
- El campo "Modelo IA" permite cualquier texto, pero se recomienda consultar los [modelos disponibles](https://console.groq.com/docs/models).

### 🆕 Guardado y carga de configuración
- La configuración (API Key y modelo IA) se guarda en el archivo `.transcriptor_config.json` en la carpeta de usuario.
- Al iniciar la aplicación, la configuración se carga automáticamente y se intenta configurar la API Key y el modelo IA.

### 🆕 Mensajes de bienvenida y ayuda en el chat
- Al configurar la API Key correctamente, el chat muestra un mensaje de bienvenida con instrucciones, enlaces útiles y el modelo IA seleccionado.

---

## Ejemplo de uso del campo Modelo IA

- **Sugerido:** `llama3-8b-8192`
- **Otros ejemplos válidos:**  
  - `llama3-70b-8192`
  - `mixtral-8x7b-32768`
  - `gemma-7b-it`
- **Consulta la lista completa:** [Modelos disponibles en GROQ](https://console.groq.com/docs/models)

---

## Ejemplo de formato en el chat

```
---
### 👤 Usuario
¿Cuáles son los puntos clave de la transcripción?

---
### 🤖 IA
**Puntos clave:**
- **Primera Ley:** Un objeto en reposo permanece en reposo...
- **Segunda Ley:** La fuerza neta es igual a la masa...
- **Tercera Ley:** Para cada acción hay una reacción igual y opuesta.
```

---

## Notas adicionales

- Si introduces un modelo IA incorrecto, la aplicación mostrará un error al intentar configurar la API Key.
- El chat y la transcripción requieren conexión a Internet y una API Key válida de GROQ.
- Consulta el [manual de usuario](https://github.com/EstebanM007/Media/tree/main/STT_from_MP4_with_IA) para más detalles y ejemplos.

## 📝 Licencia

Utiliza un API del servicio Groq el cual limita la interaccion con IA (OpenSoruce).

## 📞 Soporte

Para reportar bugs o solicitar features, por favor abre un issue en el repositorio del proyecto.

---

*Desarrollado con ❤️ por EstebanM007*
