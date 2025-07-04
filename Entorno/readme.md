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

## 📝 Licencia

Utiliza un API del servicio Groq el cual limita la interaccion con IA (OpenSoruce).

## 📞 Soporte

Para reportar bugs o solicitar features, por favor abre un issue en el repositorio del proyecto.

---

*Desarrollado con ❤️ por EstebanM007*