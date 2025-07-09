import os
import wave
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter import font as tkFont
from moviepy import *
import speech_recognition as sr
import re
import json
import base64
from pathlib import Path

# Importación de componentes de LangChain
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

class MarkdownText(tk.Text):
    """Widget de texto personalizado que puede renderizar markdown básico"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.setup_markdown_tags()
        
    def setup_markdown_tags(self):
        """Configura los tags para diferentes estilos de markdown"""
        # Fuentes
        default_font = tkFont.nametofont("TkDefaultFont")
        bold_font = default_font.copy()
        bold_font.configure(weight="bold")
        italic_font = default_font.copy()
        italic_font.configure(slant="italic")
        code_font = tkFont.Font(family="Courier", size=default_font['size'])
        heading_font = default_font.copy()
        heading_font.configure(size=default_font['size'] + 4, weight="bold")
        
        # Configurar tags
        self.tag_configure("bold", font=bold_font)
        self.tag_configure("italic", font=italic_font)
        self.tag_configure("code", font=code_font, background="#f0f0f0", relief="solid", borderwidth=1)
        self.tag_configure("heading", font=heading_font, foreground="#2563eb")
        self.tag_configure("heading2", font=heading_font, foreground="#2563eb")
        self.tag_configure("heading3", font=heading_font, foreground="#2563eb")
        self.tag_configure("quote", foreground="#6b7280", lmargin1=20, lmargin2=20)
        self.tag_configure("list_item", lmargin1=20, lmargin2=40)
        self.tag_configure("link", foreground="#2563eb", underline=True)
        
    def insert_markdown(self, index, text):
        """Inserta texto con formato markdown"""
        self.config(state=tk.NORMAL)
        
        # Dividir el texto en líneas
        lines = text.split('\n')
        
        for line in lines:
            if line.strip():
                self.process_line(index, line)
            else:
                self.insert(index, '\n')
            index = self.index(tk.INSERT)
            
        self.config(state=tk.DISABLED)
        
    def process_line(self, index, line):
        """Procesa una línea individual aplicando formato markdown"""
        # Encabezados
        if line.startswith('### '):
            self.insert(index, line[4:] + '\n', "heading3")
        elif line.startswith('## '):
            self.insert(index, line[3:] + '\n', "heading2")
        elif line.startswith('# '):
            self.insert(index, line[2:] + '\n', "heading")
        # Citas
        elif line.startswith('> '):
            self.insert(index, line[2:] + '\n', "quote")
        # Listas
        elif line.strip().startswith('- ') or line.strip().startswith('* '):
            content = line.strip()[2:]
            # CAMBIO: Procesar inline markdown en listas
            self.process_inline_formatting(index, f"• {content}\n", tag="list_item")
        elif re.match(r'^\d+\. ', line.strip()):
            self.process_inline_formatting(index, line + '\n', tag="list_item")
        # Línea normal con formato inline
        else:
            self.process_inline_formatting(index, line + '\n')
    
    def process_inline_formatting(self, index, text, tag=None):
        """Procesa formato inline como negrita, cursiva, código"""
        patterns = [
            (r'\*\*(.*?)\*\*', 'bold'),
            (r'\*(.*?)\*', 'italic'),
            (r'`(.*?)`', 'code'),
        ]
        current_pos = 0
        while current_pos < len(text):
            next_match = None
            next_pos = len(text)
            next_tag = None
            for pattern, md_tag in patterns:
                match = re.search(pattern, text[current_pos:])
                if match:
                    match_start = current_pos + match.start()
                    if match_start < next_pos:
                        next_match = match
                        next_pos = match_start
                        next_tag = md_tag
            if next_match:
                # Insertar texto antes del match
                if next_pos > current_pos:
                    if tag:
                        self.insert(index, text[current_pos:next_pos], tag)
                    else:
                        self.insert(index, text[current_pos:next_pos])
                    index = self.index(tk.INSERT)
                # Insertar el texto formateado
                formatted_text = next_match.group(1)
                tags = (next_tag,)
                if tag:
                    tags = (tag, next_tag)
                self.insert(index, formatted_text, tags)
                index = self.index(tk.INSERT)
                current_pos = current_pos + next_match.end()
            else:
                # No hay más patrones, insertar el resto del texto
                if tag:
                    self.insert(index, text[current_pos:], tag)
                else:
                    self.insert(index, text[current_pos:])
                break

class TranscriptionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcriptor y Chat con IA")
        
        # Configurar tamaño de ventana para que se vea completa
        self.geometry("1300x750")  # Aumentado para acomodar la nueva sección
        self.minsize(1200, 750)    # Tamaño mínimo
        
        # Centrar la ventana si no está maximizada
        self.center_window()
        
        self.configure(bg='#f0f2f5')

        # Configurar estilos
        self.setup_styles()

        self.file_path = None
        self.cancelled = False
        self.conversion_in_progress = False
        self.chat_llm = None  # Inicializar como None
        
        # Archivo de configuración
        self.config_file = Path.home() / ".transcriptor_config.json"
        
        # Variables para el indicador de progreso mejorado
        self.transcription_start_time = None
        self.total_segments = 0
        self.current_segment = 0
        self.processed_segments = 0
        self.failed_segments = 0

        # Prompt y memoria (se inicializarán después de configurar la API)
        self.system_prompt = (
            "Eres un chatbot conversacional amigable que ayuda a resumir y "
            "responder preguntas sobre transcripciones. Usa markdown "
            "para formatear tus respuestas cuando sea apropiado: "
            "- Usa **texto** para negrita\n"
            "- Usa *texto* para cursiva\n"
            "- Usa `código` para código inline\n"
            "- Usa # para encabezados\n"
            "- Usa - para listas\n"
            "- Usa > para citas\n"
            "Responde de manera clara y bien estructurada."
        )
        
        self.conv_memory = ConversationBufferWindowMemory(
            k=5, memory_key="chat_history", return_messages=True
        )

        self.create_widgets()
        
        # Cargar configuración guardada
        self.load_config()
        
        # Mostrar mensaje de bienvenida
        self.show_welcome()
        
        # Forzar actualización de la interfaz
        self.update_idletasks()

    def save_config(self):
        """Guarda la configuración en un archivo JSON"""
        try:
            config = {}
            api_key = self.api_key_entry.get().strip()
            if api_key:
                # Codificar la API key para almacenamiento básico
                encoded_key = base64.b64encode(api_key.encode()).decode()
                config['api_key'] = encoded_key
            # Guardar el modelo IA (campo libre)
            config['model_name'] = self.model_var.get()
            # Crear el directorio si no existe
            self.config_file.parent.mkdir(exist_ok=True)
            # Guardar configuración
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            self.update_transcription_log("💾 Configuración guardada")
        except Exception as e:
            self.update_transcription_log(f"❌ Error al guardar configuración: {e}")

    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Cargar API key si existe
                if 'api_key' in config:
                    # Decodificar la API key
                    decoded_key = base64.b64decode(config['api_key'].encode()).decode()
                    self.api_key_entry.insert(0, decoded_key)
                    # Cargar modelo si existe
                    if 'model_name' in config:
                        self.model_var.set(config['model_name'])
                    # Intentar configurar automáticamente
                    self.auto_configure_api_key()
                    self.update_transcription_log("📂 Configuración cargada desde archivo")
                else:
                    self.update_transcription_log("📂 Archivo de configuración encontrado pero sin API key")
            else:
                self.update_transcription_log("📂 No se encontró archivo de configuración previo")
        except Exception as e:
            self.update_transcription_log(f"❌ Error al cargar configuración: {e}")

    def create_widgets(self):
        self.create_header()
        self.create_api_key_section()
        self.create_control_area()
        self.create_main_panel()
        self.create_signature_area()

    def create_header(self):
        header = tk.Frame(self, bg=self.colors['primary'], height=80)
        header.pack(fill=tk.X, pady=(0,10))
        header.pack_propagate(False)
        tk.Label(
            header, text="🎙️ Transcriptor y Chat con IA",
            font=('Segoe UI',24,'bold'), bg=self.colors['primary'], fg='white'
        ).pack(expand=True)
        tk.Label(
            header, text="Convierte audio a texto y chatea con inteligencia artificial",
            font=('Segoe UI',12), bg=self.colors['primary'], fg='#e0e7ff'
        ).pack()

    def create_api_key_section(self):
        """Crea la sección para configurar la API Key"""
        frame = tk.Frame(self, bg=self.colors['warning'], bd=2, relief='solid')
        frame.pack(fill=tk.X, padx=20, pady=(0,10))
        
        # Header de la sección
        header_frame = tk.Frame(frame, bg=self.colors['warning'])
        header_frame.pack(fill=tk.X, padx=10, pady=(5,0))
        
        tk.Label(
            header_frame, text="🔑 Configuración de API Key",
            font=('Segoe UI', 14, 'bold'), bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT)
        
        # Indicador de estado
        self.api_status_label = tk.Label(
            header_frame, text="❌ No configurada",
            font=('Segoe UI', 10, 'bold'), bg=self.colors['warning'], fg='white'
        )
        self.api_status_label.pack(side=tk.RIGHT)
        
        # Contenido de la sección
        content_frame = tk.Frame(frame, bg=self.colors['warning'])
        content_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Instrucciones
        instructions = tk.Label(
            content_frame, 
            text="Ingrese su API Key de GROQ para habilitar las funciones de IA:",
            font=('Segoe UI', 10), bg=self.colors['warning'], fg='white'
        )
        instructions.pack(anchor='w', pady=(0,5))
        
        # Input frame
        input_frame = tk.Frame(content_frame, bg=self.colors['warning'])
        input_frame.pack(fill=tk.X, pady=(0,5))
        
        # Campo de entrada para API Key
        tk.Label(
            input_frame, text="API Key:", font=('Segoe UI', 10, 'bold'),
            bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT, padx=(0,5))
        
        self.api_key_entry = tk.Entry(
            input_frame, font=('Segoe UI', 10), show="*", width=50,
            bg='white', fg=self.colors['text_primary']
        )
        self.api_key_entry.pack(side=tk.LEFT, padx=(0,10), ipady=3)
        self.api_key_entry.bind('<Return>', lambda e: self.configure_api_key())

        # Campo de texto para modelo IA
        model_frame = tk.Frame(input_frame, bg=self.colors['warning'])
        model_frame.pack(side=tk.LEFT, padx=(10,0))

        tk.Label(
            model_frame, text="Modelo IA:", font=('Segoe UI', 10, 'bold'),
            bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT)

        self.model_var = tk.StringVar()
        self.model_var.set("llama3-8b-8192")  # Sugerido por defecto

        self.model_entry = tk.Entry(
            model_frame, font=('Segoe UI', 10), width=22,
            bg='white', fg=self.colors['text_primary'], textvariable=self.model_var
        )
        self.model_entry.pack(side=tk.LEFT, padx=(5,0), ipady=3)

        # Etiqueta de sugerencia y link a modelos
        tk.Label(
            model_frame, text="(Sugerido: llama3-8b-8192)", font=('Segoe UI', 9, 'italic'),
            bg=self.colors['warning'], fg='#e0e7ff'
        ).pack(side=tk.LEFT, padx=(5,0))

        modelos_link = tk.Label(
            model_frame, text="Ver modelos disponibles", font=('Segoe UI', 9, 'underline'),
            bg=self.colors['warning'], fg='#e0f2fe', cursor="hand2"
        )
        modelos_link.pack(side=tk.LEFT, padx=(8,0))
        modelos_link.bind("<Button-1>", lambda e: self.open_modelos_link())

        # Botón para configurar
        self.configure_btn = ttk.Button(
            input_frame, text="🔧 Configurar API",
            style='Success.TButton', command=self.configure_api_key
        )
        self.configure_btn.pack(side=tk.LEFT, padx=(10,0))
        
        # Botón para mostrar/ocultar API Key
        self.show_api_btn = ttk.Button(
            input_frame, text="👁️ Mostrar",
            style='Secondary.TButton', command=self.toggle_api_key_visibility
        )
        self.show_api_btn.pack(side=tk.LEFT, padx=(0,10))
        
        # Botón para eliminar configuración
        self.clear_config_btn = ttk.Button(
            input_frame, text="🗑️ Eliminar",
            style='Danger.TButton', command=self.clear_config
        )
        self.clear_config_btn.pack(side=tk.LEFT)
        
        # Link para obtener API Key y manual
        info_frame = tk.Frame(content_frame, bg=self.colors['warning'])
        info_frame.pack(fill=tk.X)
        
        tk.Label(
            info_frame, text="💡 Obtenga su API Key gratuita en:",
            font=('Segoe UI', 9), bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT)
        
        link_label = tk.Label(
            info_frame, text="https://console.groq.com/keys",
            font=('Segoe UI', 9, 'underline'), bg=self.colors['warning'], fg='#e0f2fe',
            cursor="hand2"
        )
        link_label.pack(side=tk.LEFT, padx=(5,0))
        link_label.bind("<Button-1>", lambda e: self.open_groq_link())

        manual_label = tk.Label(
            info_frame, text=" | Manual de usuario",
            font=('Segoe UI', 9, 'underline'), bg=self.colors['warning'], fg='#e0f2fe',
            cursor="hand2"
        )
        manual_label.pack(side=tk.LEFT, padx=(5,0))
        manual_label.bind(
            "<Button-1>",
            lambda e: self.open_manual_link()
        )

    def open_modelos_link(self):
        import webbrowser
        webbrowser.open("https://console.groq.com/docs/models")

    def toggle_api_key_visibility(self):
        """Alterna la visibilidad de la API Key"""
        if self.api_key_entry.cget('show') == '*':
            self.api_key_entry.config(show='')
            self.show_api_btn.config(text='🙈 Ocultar')
        else:
            self.api_key_entry.config(show='*')
            self.show_api_btn.config(text='👁️ Mostrar')

    def open_groq_link(self):
        """Abre el enlace de GROQ en el navegador"""
        import webbrowser
        webbrowser.open("https://console.groq.com/keys")

    def open_manual_link(self):
        """Abre el enlace del manual de usuario en el navegador"""
        import webbrowser
        webbrowser.open("https://github.com/EstebanM007/Media/tree/main/STT_from_MP4_with_IA")

    def save_config(self):
        """Guarda la configuración en un archivo JSON"""
        try:
            config = {}
            api_key = self.api_key_entry.get().strip()
            if api_key:
                # Codificar la API key para almacenamiento básico
                encoded_key = base64.b64encode(api_key.encode()).decode()
                config['api_key'] = encoded_key
            # Guardar el modelo IA (campo libre)
            config['model_name'] = self.model_var.get()
            # Crear el directorio si no existe
            self.config_file.parent.mkdir(exist_ok=True)
            # Guardar configuración
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            self.update_transcription_log("💾 Configuración guardada")
        except Exception as e:
            self.update_transcription_log(f"❌ Error al guardar configuración: {e}")

    def load_config(self):
        """Carga la configuración desde el archivo JSON"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                # Cargar API key si existe
                if 'api_key' in config:
                    # Decodificar la API key
                    decoded_key = base64.b64decode(config['api_key'].encode()).decode()
                    self.api_key_entry.insert(0, decoded_key)
                    # Cargar modelo si existe
                    if 'model_name' in config:
                        self.model_var.set(config['model_name'])
                    # Intentar configurar automáticamente
                    self.auto_configure_api_key()
                    self.update_transcription_log("📂 Configuración cargada desde archivo")
                else:
                    self.update_transcription_log("📂 Archivo de configuración encontrado pero sin API key")
            else:
                self.update_transcription_log("📂 No se encontró archivo de configuración previo")
        except Exception as e:
            self.update_transcription_log(f"❌ Error al cargar configuración: {e}")

    def create_widgets(self):
        self.create_header()
        self.create_api_key_section()
        self.create_control_area()
        self.create_main_panel()
        self.create_signature_area()

    def create_header(self):
        header = tk.Frame(self, bg=self.colors['primary'], height=80)
        header.pack(fill=tk.X, pady=(0,10))
        header.pack_propagate(False)
        tk.Label(
            header, text="🎙️ Transcriptor y Chat con IA",
            font=('Segoe UI',24,'bold'), bg=self.colors['primary'], fg='white'
        ).pack(expand=True)
        tk.Label(
            header, text="Convierte audio a texto y chatea con inteligencia artificial",
            font=('Segoe UI',12), bg=self.colors['primary'], fg='#e0e7ff'
        ).pack()

    def create_api_key_section(self):
        """Crea la sección para configurar la API Key"""
        frame = tk.Frame(self, bg=self.colors['warning'], bd=2, relief='solid')
        frame.pack(fill=tk.X, padx=20, pady=(0,10))
        
        # Header de la sección
        header_frame = tk.Frame(frame, bg=self.colors['warning'])
        header_frame.pack(fill=tk.X, padx=10, pady=(5,0))
        
        tk.Label(
            header_frame, text="🔑 Configuración de API Key",
            font=('Segoe UI', 14, 'bold'), bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT)
        
        # Indicador de estado
        self.api_status_label = tk.Label(
            header_frame, text="❌ No configurada",
            font=('Segoe UI', 10, 'bold'), bg=self.colors['warning'], fg='white'
        )
        self.api_status_label.pack(side=tk.RIGHT)
        
        # Contenido de la sección
        content_frame = tk.Frame(frame, bg=self.colors['warning'])
        content_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Instrucciones
        instructions = tk.Label(
            content_frame, 
            text="Ingrese su API Key de GROQ para habilitar las funciones de IA:",
            font=('Segoe UI', 10), bg=self.colors['warning'], fg='white'
        )
        instructions.pack(anchor='w', pady=(0,5))
        
        # Input frame
        input_frame = tk.Frame(content_frame, bg=self.colors['warning'])
        input_frame.pack(fill=tk.X, pady=(0,5))
        
        # Campo de entrada para API Key
        tk.Label(
            input_frame, text="API Key:", font=('Segoe UI', 10, 'bold'),
            bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT, padx=(0,5))
        
        self.api_key_entry = tk.Entry(
            input_frame, font=('Segoe UI', 10), show="*", width=50,
            bg='white', fg=self.colors['text_primary']
        )
        self.api_key_entry.pack(side=tk.LEFT, padx=(0,10), ipady=3)
        self.api_key_entry.bind('<Return>', lambda e: self.configure_api_key())

        # Campo de texto para modelo IA
        model_frame = tk.Frame(input_frame, bg=self.colors['warning'])
        model_frame.pack(side=tk.LEFT, padx=(10,0))

        tk.Label(
            model_frame, text="Modelo IA:", font=('Segoe UI', 10, 'bold'),
            bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT)

        self.model_var = tk.StringVar()
        self.model_var.set("llama3-8b-8192")  # Sugerido por defecto

        self.model_entry = tk.Entry(
            model_frame, font=('Segoe UI', 10), width=22,
            bg='white', fg=self.colors['text_primary'], textvariable=self.model_var
        )
        self.model_entry.pack(side=tk.LEFT, padx=(5,0), ipady=3)

        # Etiqueta de sugerencia y link a modelos
        tk.Label(
            model_frame, text="(Sugerido: llama3-8b-8192)", font=('Segoe UI', 9, 'italic'),
            bg=self.colors['warning'], fg='#e0e7ff'
        ).pack(side=tk.LEFT, padx=(5,0))

        modelos_link = tk.Label(
            model_frame, text="Ver modelos disponibles", font=('Segoe UI', 9, 'underline'),
            bg=self.colors['warning'], fg='#e0f2fe', cursor="hand2"
        )
        modelos_link.pack(side=tk.LEFT, padx=(8,0))
        modelos_link.bind("<Button-1>", lambda e: self.open_modelos_link())

        # Botón para configurar
        self.configure_btn = ttk.Button(
            input_frame, text="🔧 Configurar API",
            style='Success.TButton', command=self.configure_api_key
        )
        self.configure_btn.pack(side=tk.LEFT, padx=(10,0))
        
        # Botón para mostrar/ocultar API Key
        self.show_api_btn = ttk.Button(
            input_frame, text="👁️ Mostrar",
            style='Secondary.TButton', command=self.toggle_api_key_visibility
        )
        self.show_api_btn.pack(side=tk.LEFT, padx=(0,10))
        
        # Botón para eliminar configuración
        self.clear_config_btn = ttk.Button(
            input_frame, text="🗑️ Eliminar",
            style='Danger.TButton', command=self.clear_config
        )
        self.clear_config_btn.pack(side=tk.LEFT)
        
        # Link para obtener API Key y manual
        info_frame = tk.Frame(content_frame, bg=self.colors['warning'])
        info_frame.pack(fill=tk.X)
        
        tk.Label(
            info_frame, text="💡 Obtenga su API Key gratuita en:",
            font=('Segoe UI', 9), bg=self.colors['warning'], fg='white'
        ).pack(side=tk.LEFT)
        
        link_label = tk.Label(
            info_frame, text="https://console.groq.com/keys",
            font=('Segoe UI', 9, 'underline'), bg=self.colors['warning'], fg='#e0f2fe',
            cursor="hand2"
        )
        link_label.pack(side=tk.LEFT, padx=(5,0))
        link_label.bind("<Button-1>", lambda e: self.open_groq_link())

        manual_label = tk.Label(
            info_frame, text=" | Manual de usuario",
            font=('Segoe UI', 9, 'underline'), bg=self.colors['warning'], fg='#e0f2fe',
            cursor="hand2"
        )
        manual_label.pack(side=tk.LEFT, padx=(5,0))
        manual_label.bind(
            "<Button-1>",
            lambda e: self.open_manual_link()
        )

    def open_modelos_link(self):
        import webbrowser
        webbrowser.open("https://console.groq.com/docs/models")

    def toggle_api_key_visibility(self):
        """Alterna la visibilidad de la API Key"""
        if self.api_key_entry.cget('show') == '*':
            self.api_key_entry.config(show='')
            self.show_api_btn.config(text='🙈 Ocultar')
        else:
            self.api_key_entry.config(show='*')
            self.show_api_btn.config(text='👁️ Mostrar')

    def open_groq_link(self):
        """Abre el enlace de GROQ en el navegador"""
        import webbrowser
        webbrowser.open("https://console.groq.com/keys")

    def open_manual_link(self):
        """Abre el enlace del manual de usuario en el navegador"""
        import webbrowser
        webbrowser.open("https://github.com/EstebanM007/Media/tree/main/STT_from_MP4_with_IA")

    def configure_api_key(self):
        """Configura la API Key de GROQ"""
        api_key = self.api_key_entry.get().strip()
        model_name = self.model_var.get().strip()
        
        if not api_key:
            messagebox.showerror("Error", "Por favor ingrese una API Key válida")
            return
        
        if not api_key.startswith('gsk_'):
            messagebox.showerror("Error", "La API Key debe comenzar con 'gsk_'")
            return
        
        if not model_name:
            messagebox.showerror("Error", "Por favor ingrese el nombre del modelo IA")
            return
        
        try:
            # Configurar la variable de entorno
            os.environ["GROQ_API_KEY"] = api_key
            
            # Inicializar el cliente de chat con el modelo seleccionado
            self.chat_llm = ChatGroq(
                groq_api_key=api_key,
                model_name=model_name
            )
            
            # Hacer una prueba básica
            test_response = self.chat_llm.invoke("Responde solo con 'OK' para confirmar conexión")
            
            # Si llegamos aquí, la configuración fue exitosa
            self.api_status_label.config(text="✅ Configurada", fg='#dcfce7')
            self.configure_btn.config(text="✅ Configurada", state=tk.DISABLED)
            
            # Habilitar controles que requieren IA (si existe el método)
            if hasattr(self, "enable_ai_features"):
                self.enable_ai_features()
            
            # Guardar configuración
            self.save_config()
            
            # Limpiar el chat y mostrar mensaje de éxito
            self.ia_chat_text.config(state=tk.NORMAL)
            self.ia_chat_text.delete(1.0, tk.END)
            self.ia_chat_text.config(state=tk.DISABLED)
            
            # ─── Mensaje de bienvenida (panel de chat) ────────────────────────────────────────
            self.update_ia_chat_markdown(
                f"# 🎙️ Transcriptor y Chat IA\n"
                f"**Convierte audio a texto y genera resúmenes con IA.**\n\n"
                f"**Autor:** Esteban Alberto Martínez Palacios (Estrategia Digital y GEN XXI)\n"
                f"**Modelo IA seleccionado:** `{model_name}`\n"
                "## 🛠️ Instrucciones de uso\n"
                "1. Selecciona un archivo de audio o video.\n"
                "2. Pulsa **Transcribir Audio**.\n"
                "3. Consulta el resultado en el panel derecho.\n\n"
                "## ℹ️ Notas importantes\n"
                "- ⚠️ Requiere conexión a Internet; la precisión depende de la claridad del audio.\n"
                "- ⚠️ Límite de petición: si se supera el tamaño máximo o créditos gratuitos, el resumen no funcionará.\n"
                "- ℹ️ Genera archivos WAV y TXT con la transcripción.\n"
                "- ℹ️ El audio se segmenta en fragmentos de 60 s para optimizar memoria; crea archivos temporales.\n"
                "- ⚠️ La IA solo recuerda los últimos 5 mensajes de contexto.\n\n"
                "## 💬 Chat IA\n"
                "- Usa el panel inferior izquierdo.\n"
                "- Mensajes editables (Ctrl+A para seleccionar todo).\n"
                "- Soporte Markdown: **negrita**, *cursiva*, `código`.\n\n"
                "## ✅ Estado de la aplicación\n"
                "- API Key configurada correctamente.\n"
                "- 🤖 Funciones de IA habilitadas.\n"
                "\n---\n"
                "✅ **Conexión establecida con GROQ**\n"
                "- 📝 Transcribir archivos de audio/video\n"
                "- 💬 Chatear sobre cualquier tema\n"
                "- 📊 Obtener resúmenes automáticos\n"
            )

            messagebox.showinfo("Éxito", "API Key configurada correctamente.\n¡Ya puedes usar todas las funciones!\n\nLa configuración se ha guardado automáticamente.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al configurar la API Key:\n{str(e)}")
            self.update_transcription_log(f"❌ Error al configurar API Key: {e}")

    def auto_configure_api_key(self):
        """Configura automáticamente la API key si es válida"""
        api_key = self.api_key_entry.get().strip()
        model_name = self.model_var.get().strip()
        if not api_key or not api_key.startswith('gsk_') or not model_name:
            return
        try:
            # Configurar la variable de entorno
            os.environ["GROQ_API_KEY"] = api_key
            
            # Inicializar el cliente de chat con el modelo seleccionado
            self.chat_llm = ChatGroq(
                groq_api_key=api_key,
                model_name=model_name
            )
            
            # Hacer una prueba básica (sin mostrar respuesta)
            test_response = self.chat_llm.invoke("Responde solo con 'OK' para confirmar conexión")
            
            # Si llegamos aquí, la configuración fue exitosa
            self.api_status_label.config(text="✅ Configurada", fg='#dcfce7')
            self.configure_btn.config(text="✅ Configurada")
            
            # Habilitar controles que requieren IA (si existe el método)
            if hasattr(self, "enable_ai_features"):
                self.enable_ai_features()
            
            # Actualizar estado de la interfaz
            self.update_auto_config_ui()
            
            self.update_transcription_log("✅ API Key configurada automáticamente")
            
        except Exception as e:
            self.update_transcription_log(f"❌ Error en configuración automática: {e}")
            # Resetear el estado si falla
            self.api_status_label.config(text="❌ No configurada", fg='white')
            self.configure_btn.config(text="🔧 Configurar API", state=tk.NORMAL)

    def update_auto_config_ui(self):
        """Actualiza la interfaz después de la configuración automática"""
        self.update_transcription_log("")  # línea en blanco para separar
        # Mensaje de bienvenida en el chat
        self.update_transcription_log("🎙️ Transcriptor y Chat con IA")
        self.update_transcription_log("Descripción: convierte audio a texto y genera un resumen con IA.")
        self.update_transcription_log("Autor: Esteban Alberto Martinez Palacios (Estrategia Digital y GEN XXI).")
        self.update_transcription_log("Uso:")
        self.update_transcription_log("  1) Seleccione un archivo de audio/video.")
        self.update_transcription_log("  2) Pulse 'Transcribir Audio'.")
        self.update_transcription_log("  3) Espere el resultado en el panel de la derecha.")
        self.update_transcription_log("  *MANUAL* https://github.com/EstebanM007/Media/tree/main/STT_from_MP4_with_IA")
        self.update_transcription_log("")  # línea en blanco para separar

        # Nota sobre límites y memoria
        self.update_transcription_log("⚠️ Nota[(REQUIERE CONEXION A INTERNET) LA TRANSCRIPCION NO ES PERFECTA Y DEPENDE MUCHO DE LA CLARIDAD DEL AUDIO]: Si la transcripción excede el tamaño máximo de petición o agota tus créditos gratuitos, el resumen/IA no funcionará. Además, la IA solo recuerda los últimos 5 mensajes enviados.")
        self.update_transcription_log("⚠️ Nota: El programa genera un arcivo WAV y un arichivo TXT con la transcripcion, al igual que muestra el registro de transcripción en el panel derecho.")
        self.update_transcription_log(" Nota: El programa divide el audio en segmentos de 60 segundos para evitar problemas de memoria y tamaño de petición, esto crea archivos temporales en el directorio actual.")

        self.update_transcription_log("")  # línea en blanco para separar

    def clear_config(self):
        """Elimina la configuración guardada"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
                self.update_transcription_log("🗑️ Configuración eliminada")
                messagebox.showinfo("Configuración", "La configuración ha sido eliminada.\nDeberá volver a configurar la API Key.")
            else:
                messagebox.showinfo("Configuración", "No hay configuración guardada para eliminar.")
        except Exception as e:
            self.update_transcription_log(f"❌ Error al eliminar configuración: {e}")
            messagebox.showerror("Error", f"No se pudo eliminar la configuración:\n{e}")
        
    def center_window(self):
        """Centra la ventana en la pantalla"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        pos_x = (self.winfo_screenwidth() // 2) - (width // 2)
        pos_y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{pos_x}+{pos_y}")
        
    def show_welcome(self):
        if self.chat_llm is None:  # Solo mostrar si no hay API configurada
            separator = "=" * 50
            self.update_transcription_log(separator)
            self.update_transcription_log("🔑 Configure su API Key de GROQ para comenzar") 
            self.update_transcription_log(separator)
            # Mostrar mensaje en el chat también
            self.update_ia_chat_markdown(
                "⚠️ **Mientras tanto, puedes escribir mensajes pero no obtendrás respuestas.**\n"
            )

    def setup_styles(self):
        self.colors = {
            'primary': '#2563eb', 'primary_hover': '#1d4ed8',
            'secondary': '#64748b', 'success': '#10b981',
            'danger': '#ef4444', 'background': '#f0f2f5',
            'surface': '#ffffff', 'accent': '#8b5cf6',
            'text_primary': '#1f2937', 'text_secondary': '#6b7280',
            'warning': "#125a0b"
        }
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure(
            'Primary.TButton', background=self.colors['primary'],
            foreground='white', borderwidth=0, padding=(20,10)
        )
        self.style.map(
            'Primary.TButton', background=[('active', self.colors['primary_hover'])]
        )
        self.style.configure(
            'Secondary.TButton', background=self.colors['surface'],
            foreground=self.colors['text_primary'], borderwidth=1, padding=(15,8)
        )
        self.style.configure(
            'Danger.TButton', background=self.colors['danger'],
            foreground='white', borderwidth=0, padding=(15,8)
        )
        self.style.map(
            'Danger.TButton', background=[('active', '#dc2626')]
        )
        self.style.configure(
            'Success.TButton', background=self.colors['success'],
            foreground='white', borderwidth=0, padding=(15,8)
        )
        self.style.map(
            'Success.TButton', background=[('active', '#059669')]
        )

    def create_control_area(self):
        frame = tk.Frame(self, bg=self.colors['surface'], bd=1, relief='solid')
        frame.pack(fill=tk.X, padx=20, pady=(0,10))
        inner = tk.Frame(frame, bg=self.colors['surface'])
        inner.pack(fill=tk.X, padx=20, pady=15)
        ttk.Button(
            inner, text="📁 Seleccionar Archivo",
            style='Primary.TButton', command=self.select_file
        ).pack(side=tk.LEFT)
        self.file_label = tk.Label(
            inner, text="No se ha seleccionado ningún archivo",
            bg=self.colors['surface'], fg=self.colors['text_secondary']
        )
        self.file_label.pack(side=tk.LEFT, padx=10)
        row = tk.Frame(inner, bg=self.colors['surface'])
        row.pack(fill=tk.X, pady=(10,0))
        self.transcribe_btn = ttk.Button(
            row, text="🎵 Transcribir Audio", style='Secondary.TButton',
            command=self.transcribe_audio, state=tk.DISABLED
        )
        self.transcribe_btn.pack(side=tk.LEFT)
        self.cancel_btn = ttk.Button(
            row, text="❌ Cancelar Proceso", style='Danger.TButton',
            command=self.cancel_process, state=tk.DISABLED
        )
        self.cancel_btn.pack(side=tk.RIGHT)

    def create_main_panel(self):
        # Usar PanedWindow para mejor control del espacio
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,10))
        
        # CAMBIO: usa tk.Frame en vez de ttk.Frame
        left = tk.Frame(paned, bg=self.colors['surface'])
        right = tk.Frame(paned, bg=self.colors['surface'])
        
        # Configurar el peso de los paneles (50-50)
        paned.add(left, weight=1)
        paned.add(right, weight=1)
        
        self.create_chat_panel(left)
        self.create_transcription_panel(right)

    def create_chat_panel(self, parent):
        frame = tk.Frame(parent, bg=self.colors['surface'], bd=1, relief='solid')
        frame.pack(fill=tk.BOTH, expand=True, padx=(0,10), pady=5)

        # Header del chat
        hdr = tk.Frame(frame, bg=self.colors['accent'], height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="🤖 Chat con IA (Markdown)", bg=self.colors['accent'], fg='white',
            font=('Segoe UI',14,'bold')
        ).pack(expand=True)

        # Input del chat SIEMPRE al fondo
        inp = tk.Frame(frame, bg=self.colors['surface'])
        inp.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0,10))

        self.ia_entry = tk.Entry(
            inp, font=('Segoe UI',11), bg='white', insertbackground=self.colors['primary'],
            state=tk.NORMAL, fg='#6b7280'
        )
        self.ia_entry.insert(0, "Escribe tu mensaje y presiona Enter...")
        def clear_placeholder(event):
            if self.ia_entry.get() == "Escribe tu mensaje y presiona Enter...":
                self.ia_entry.delete(0, tk.END)
                self.ia_entry.config(fg=self.colors['text_primary'])
        self.ia_entry.bind("<FocusIn>", clear_placeholder)

        def restore_placeholder(event):
            if not self.ia_entry.get():
                self.ia_entry.insert(0, "Escribe tu mensaje y presiona Enter...")
                self.ia_entry.config(fg='#6b7280')
        self.ia_entry.bind("<FocusOut>", restore_placeholder)

        self.ia_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self.ia_entry.bind('<Return>', lambda e: self.send_message())

        self.send_btn = ttk.Button(
            inp, text="➤ Enviar", style='Primary.TButton',
            command=self.send_message, state=tk.NORMAL
        )
        self.send_btn.pack(side=tk.RIGHT, padx=(5,0))

        # Frame para el chat y scrollbar (ocupa el resto)
        chat_frame = tk.Frame(frame)
        chat_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.ia_chat_text = MarkdownText(
            chat_frame, wrap=tk.WORD, font=('Segoe UI',11), bg='#f8fafc',
            bd=1, relief='solid', state=tk.DISABLED, height=20
        )
        scrollbar = tk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.ia_chat_text.yview)
        self.ia_chat_text.configure(yscrollcommand=scrollbar.set)
        self.ia_chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mensaje de bienvenida en el chat
        self.ia_chat_text.config(state=tk.NORMAL)
        welcome_msg = "¡Hola! 👋 Soy tu asistente de IA.\n\n"
        if self.chat_llm is None:
            welcome_msg += ("\n💡 **Para usar el chat:**\n\n"
            "⚠️ **Para configurar tu API Key de GROQ debes:**\n"
            "  1. Registrarte o iniciar sesión en https://app.groq.ai\n"
            "  2. Ir a tu perfil y seleccionar “API Keys”\n"
            "  3. Generar una nueva clave y copiarla\n"
            "  4. Pegarla en el campo en blaco y selecciona `Configurar API`\n\n"
            "  5. Ajusta el modelo de IA (Sugerido: llama3-8b-8192)\n\n"
            "  NOTA: Si ya lo tienes configurardo omite estos pasos\n\n"
            )
        else:
            welcome_msg += "✅ **API Key configurada correctamente**\n\n"
        self.ia_chat_text.insert_markdown(tk.END, welcome_msg)
        self.ia_chat_text.config(state=tk.DISABLED)

        self.ia_entry.bind("<KeyRelease>", lambda e: self.send_btn.config(
            state=tk.NORMAL if self.ia_entry.get().strip() else tk.DISABLED
        ))

    def create_transcription_panel(self, parent):
        frame = tk.Frame(parent, bg=self.colors['surface'], bd=1, relief='solid')
        frame.pack(fill=tk.BOTH, expand=True, padx=(10,0), pady=5)
        
        # Header con indicadores de progreso
        hdr = tk.Frame(frame, bg=self.colors['success'], height=70)  # Aumentado para acomodar indicadores
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        
        # Título
        title_frame = tk.Frame(hdr, bg=self.colors['success'])
        title_frame.pack(side=tk.LEFT, padx=10, pady=5)
        tk.Label(
            title_frame, text="📝 Registro de Transcripción", bg=self.colors['success'],
            fg='white', font=('Segoe UI',14,'bold')
        ).pack(anchor='w')
        
        # Crear frame para los indicadores de progreso
        progress_frame = tk.Frame(hdr, bg=self.colors['success'])
        progress_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Indicador principal de progreso
        self.progress_label = tk.Label(
            progress_frame, bg=self.colors['success'], fg='white',
            font=('Segoe UI', 9, 'bold')
        )
        self.progress_label.pack(anchor='e')
        
        # Indicador de estadísticas
        self.stats_label = tk.Label(
            progress_frame, bg=self.colors['success'], fg='#e0f2fe',
            font=('Segoe UI', 8)
        )
        self.stats_label.pack(anchor='e')
        
        # Indicador de tiempo
        self.time_label = tk.Label(
            progress_frame, bg=self.colors['success'], fg='#e0f2fe',
            font=('Segoe UI', 8)
        )
        self.time_label.pack(anchor='e')
        
        # Área de texto para transcripción
        self.transcription_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas',10), bg='#f8fafc',
            bd=1, relief='solid', height=22
        )
        self.transcription_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def create_signature_area(self):
        self.signature_frame = tk.Frame(self, bg='#ffffff', bd=1, relief='solid')
        self.signature_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0,10))
        line = tk.Frame(self.signature_frame, bg=self.colors['primary'], height=3)
        line.pack(fill=tk.X)
        cont = tk.Frame(self.signature_frame, bg='#ffffff')
        cont.pack(fill=tk.X, padx=20, pady=10)

    def reset_progress_indicators(self):
        """Reinicia los indicadores de progreso"""
        self.transcription_start_time = None
        self.total_segments = 0
        self.current_segment = 0
        self.processed_segments = 0
        self.failed_segments = 0
        self.progress_label.config(text="")
        self.stats_label.config(text="")
        self.time_label.config(text="")

    def update_progress_indicators(self, phase="", current=0, total=0, status=""):
        """Actualiza los indicadores de progreso con información detallada"""
        if phase == "start":
            self.transcription_start_time = time.time()
            self.total_segments = total
            self.current_segment = 0
            self.processed_segments = 0
            self.failed_segments = 0
            self.progress_label.config(text=f"🎯 Iniciando transcripción...")
            self.stats_label.config(text=f"Segmentos: {total}")
            self.time_label.config(text="⏱️ Tiempo: 00:00")
        
        elif phase == "processing":
            self.current_segment = current
            elapsed = time.time() - self.transcription_start_time if self.transcription_start_time else 0
            
            # Calcular progreso
            progress_percent = (current / total) * 100 if total > 0 else 0
            
            # Estimar tiempo restante
            if current > 0:
                time_per_segment = elapsed / current
                remaining_segments = total - current
                eta = time_per_segment * remaining_segments
                eta_str = f"ETA: {int(eta//60):02d}:{int(eta%60):02d}"
            else:
                eta_str = "ETA: --:--"
            
            # Actualizar labels
            self.progress_label.config(text=f"🔄 Procesando {current}/{total} ({progress_percent:.1f}%)")
            
            success_rate = (self.processed_segments / current) * 100 if current > 0 else 0
            self.stats_label.config(text=f"✅ {self.processed_segments} ❌ {self.failed_segments} ({success_rate:.1f}% éxito)")
            
            elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
            self.time_label.config(text=f"⏱️ {elapsed_str} | {eta_str}")
        
        elif phase == "segment_success":
            self.processed_segments += 1
        
        elif phase == "segment_failed":
            self.failed_segments += 1
        
        elif phase == "complete":
            elapsed = time.time() - self.transcription_start_time if self.transcription_start_time else 0
            elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
            success_rate = (self.processed_segments / self.total_segments) * 100 if self.total_segments > 0 else 0
            
            self.progress_label.config(text=f"✅ Completado - {self.total_segments} segmentos")
            self.stats_label.config(text=f"✅ {self.processed_segments} ❌ {self.failed_segments} ({success_rate:.1f}% éxito)")
            self.time_label.config(text=f"⏱️ Tiempo total: {elapsed_str}")
        
        elif phase == "cancelled":
            elapsed = time.time() - self.transcription_start_time if self.transcription_start_time else 0
            elapsed_str = f"{int(elapsed//60):02d}:{int(elapsed%60):02d}"
            
            self.progress_label.config(text=f"❌ Cancelado en {self.current_segment}/{self.total_segments}")
            self.stats_label.config(text=f"✅ {self.processed_segments} ❌ {self.failed_segments}")
            self.time_label.config(text=f"⏱️ Tiempo: {elapsed_str}")
        
        elif phase == "error":
            self.progress_label.config(text=f"❌ Error: {status}")
            self.stats_label.config(text="")
            self.time_label.config(text="")

    # Métodos de transcripción y chat
    def select_file(self):
        filetypes = [("Media Files", "*.mp4 *.ogg *.mp3 *.wav"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Seleccione un archivo", filetypes=filetypes)
        if path:
            self.file_path = path
            filename = os.path.basename(path)
            self.file_label.config(text=f"📄 {filename}", fg=self.colors['success'])
            # Solo habilitar transcripción si la API está configurada
            if self.chat_llm is not None:
                self.transcribe_btn.config(state=tk.NORMAL)
            else:
                self.transcribe_btn.config(state=tk.DISABLED)
                self.update_transcription_log("⚠️ Configure la API Key primero para habilitar la transcripción")
            self.update_transcription_log(f"Archivo seleccionado: {filename}")
            self.reset_progress_indicators()
        else:
            self.update_transcription_log("No se seleccionó ningún archivo.")

    def convert_to_wav(self, input_file):
        file_extension = os.path.splitext(input_file)[1].lower()
        self.update_transcription_log(f"Formato detectado: {file_extension}")
        output_wav = "archivo.wav"
        try:
            if file_extension == ".mp4":
                video_clip = VideoFileClip(input_file)
                audio_clip = video_clip.audio
                audio_clip.write_audiofile(output_wav)
                self.update_transcription_log("Conversión de video a WAV completada.")
            elif file_extension in [".ogg", ".mp3"]:
                audio_clip = AudioFileClip(input_file)
                audio_clip.write_audiofile(output_wav)
                self.update_transcription_log("Conversión de audio a WAV completada.")
            elif file_extension == ".wav":
                self.update_transcription_log("El archivo ya está en formato WAV; no se requiere conversión.")
                return input_file
            else:
                self.update_transcription_log("Formato no soportado. Use .mp4, .ogg, .mp3 o .wav.")
                return None
        except Exception as e:
            self.update_transcription_log(f"Error durante la conversión: {e}")
            return None
        return output_wav

    def divide_audio(self, filename, segment_length=60):
        segments = []
        try:
            audio = wave.open(filename, 'rb')
        except Exception as e:
            self.update_transcription_log(f"Error al abrir WAV: {e}")
            self.update_progress_indicators("error", status=f"Error al abrir WAV: {e}")
            return segments
        
        frame_rate = audio.getframerate()
        n_frames = audio.getnframes()
        duration = n_frames / frame_rate
        total_segments = int(duration // segment_length) + (1 if duration % segment_length > 0 else 0)
        
        self.update_transcription_log(f"Duración del audio: {duration:.1f} segundos")
        self.update_transcription_log(f"Se crearán {total_segments} segmentos de {segment_length} segundos")
        
        for start in range(0, int(duration), segment_length):
            if self.cancelled:
                break
            end = min(start + segment_length, duration)
            audio.setpos(int(start * frame_rate))
            frames = audio.readframes(int((end - start) * frame_rate))
            segment_filename = f"segment_{start}_{end}.wav"
            try:
                seg = wave.open(segment_filename, 'wb')
                seg.setnchannels(audio.getnchannels())
                seg.setsampwidth(audio.getsampwidth())
                seg.setframerate(frame_rate)
                seg.writeframes(frames)
                seg.close()
                segments.append(segment_filename)
                self.update_transcription_log(f"Segmento creado: {segment_filename}")
            except Exception as e:
                self.update_transcription_log(f"Error crear segmento {segment_filename}: {e}")
        
        audio.close()
        return segments

    def transcribe_segments(self, segments):
        recognizer = sr.Recognizer()
        full = ""
        total = len(segments)
        
        # Inicializar indicadores de progreso
        self.update_progress_indicators("start", total=total)
        
        for i, seg in enumerate(segments, 1):
            if self.cancelled:
                self.update_transcription_log("Transcripción cancelada.")
                self.update_progress_indicators("cancelled")
                break
            
            # Actualizar progreso
            self.update_progress_indicators("processing", current=i, total=total)
            
            with sr.AudioFile(seg) as source:
                audio_data = recognizer.record(source)
                try:
                    text = recognizer.recognize_google(audio_data, language="es-ES")
                    self.update_transcription_log(f"✅ {seg}: {text}")
                    full += text + "\n"
                    self.update_progress_indicators("segment_success")
                except sr.UnknownValueError:
                    self.update_transcription_log(f"❌ No entendí {seg}")
                    self.update_progress_indicators("segment_failed")
                except sr.RequestError as e:
                    self.update_transcription_log(f"❌ Error petición {seg}: {e}")
                    self.update_progress_indicators("segment_failed")
            
            try:
                os.remove(seg)
            except:
                pass
        
        if not self.cancelled:
            self.update_progress_indicators("complete")
        
        return full

    def _transcribe_audio(self):
        if not self.file_path:
            self.update_transcription_log("Seleccione un archivo primero.")
            return
        
        if self.chat_llm is None:
            self.update_transcription_log("❌ Configure la API Key primero.")
            messagebox.showerror("Error", "Debe configurar la API Key antes de transcribir")
            return
        
        self.cancelled = False
        self.cancel_btn.config(state=tk.NORMAL)
        self.transcribe_btn.config(state=tk.DISABLED)
        
        self.update_transcription_log("🔄 Iniciando conversión...")
        wav = self.convert_to_wav(self.file_path)
        if not wav:
            self.update_transcription_log("❌ Conversión fallida.")
            self.update_progress_indicators("error", status="Conversión fallida")
            self.cancel_btn.config(state=tk.DISABLED)
            self.transcribe_btn.config(state=tk.NORMAL)
            return
        
        self.update_transcription_log("📊 Dividiendo audio...")
        segs = self.divide_audio(wav)
        if not segs:
            self.update_transcription_log("❌ No se pudieron crear segmentos.")
            self.update_progress_indicators("error", status="No se pudieron crear segmentos")
            self.cancel_btn.config(state=tk.DISABLED)
            self.transcribe_btn.config(state=tk.NORMAL)
            return
        
        self.update_transcription_log("🎙️ Iniciando transcripción...")
        text = self.transcribe_segments(segs)
        
        if not self.cancelled:
            with open("transcripcion.txt","w",encoding="utf-8") as f:
                f.write(text)
            self.update_transcription_log("💾 Transcripción guardada en transcripcion.txt")
            self.update_transcription_log("🤖 Enviando a IA para generar resumen...")

            # Enviar el texto transcrito a la IA para generar un resumen
            try:
                resumen = self.get_chat_response(
                    "Eres un asistente experto en análisis de transcripciones. "
                    "Resume la siguiente transcripción de audio en español de forma clara y estructurada. "
                    "Incluye los puntos clave, temas principales, participantes (si los hay), y cualquier conclusión relevante. "
                    "Utiliza viñetas para los puntos importantes y, si es posible, separa por temas o secciones. "
                    "El resumen debe ser breve (máximo 10 líneas) y fácil de leer para alguien que no escuchó el audio. "
                    "Si el texto es muy largo, haz un resumen general y omite detalles irrelevantes.\n\n"
                    + text
                )
                self.update_ia_chat_markdown(
                    "\n## 📄 Resumen automático de la transcripción\n" + resumen +
                    "\n\n✅ **Transcripción y resumen generados con éxito.**"
                )
                self.update_transcription_log("🤖 Transcrito con éxito")
            except Exception as e:
                error_str = str(e).lower()
                if ("maximum context length" in error_str or 
                    "token limit" in error_str or 
                    "context length" in error_str or 
                    "too many tokens" in error_str):
                    user_msg = (
                        "❌ **La transcripción es demasiado larga para ser resumida por la IA.**\n"
                        "El servicio ha rechazado la petición por exceder el límite de tokens/contexto.\n"
                        "Puedes intentar con un archivo más corto o dividir el audio en partes más pequeñas."
                    )
                    self.update_ia_chat_markdown(f"\n{user_msg}\n")
                    self.update_transcription_log("❌ La transcripción es demasiado larga para el resumen automático de la IA (límite de tokens/contexto superado).")
                else:
                    error_msg = f"❌ Error al generar resumen automático: {e}"
                    self.update_ia_chat_markdown(
                        f"\n❌ **Error al generar resumen automático:** {e}\n"
                    )
                    self.update_transcription_log(error_msg)

        self.transcribe_btn.config(state=tk.NORMAL)

    def transcribe_audio(self):
        threading.Thread(target=self._transcribe_audio, daemon=True).start()

    def update_transcription_log(self, msg):
        self.transcription_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.transcription_text.see(tk.END)

    def get_chat_response(self, human_input):
        if self.chat_llm is None:
            raise Exception("API Key no configurada")
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{human_input}")
        ])
        chain = LLMChain(llm=self.chat_llm, prompt=prompt, memory=self.conv_memory)
        return chain.predict(human_input=human_input)

    def send_message(self):
        if self.chat_llm is None:
            self.update_ia_chat_markdown(
                "\n---\n"
                "### 👤 Usuario\n"
                "⚠️ **Sistema**: Debe configurar la API Key de GROQ primero para usar el chat.\n"
            )
            return

        msg = self.ia_entry.get().strip()
        if not msg:
            return
        self.update_ia_chat_markdown(
            f"\n---\n### 👤 Usuario\n{msg}\n"
        )
        self.ia_entry.delete(0, tk.END)
        threading.Thread(target=lambda: self._send_message(msg), daemon=True).start()

    def _send_message(self, msg):
        try:
            resp = self.get_chat_response(msg)
            self.update_ia_chat_markdown(
                f"\n---\n### 🤖 IA\n{resp}\n"
            )
        except Exception as e:
            self.update_ia_chat_markdown(
                f"\n---\n### 🤖 IA\n❌ **Error IA**: {e}\n"
            )

    def update_ia_chat_markdown(self, msg):
        """Actualiza el chat con formato markdown"""
        def _update():
            try:
                self.ia_chat_text.config(state=tk.NORMAL)
                self.ia_chat_text.insert_markdown(tk.END, msg)
                self.ia_chat_text.see(tk.END)
                self.ia_chat_text.config(state=tk.DISABLED)
            except Exception as e:
                # Fallback: insertar sin formato si hay error
                self.ia_chat_text.config(state=tk.NORMAL)
                self.ia_chat_text.insert(tk.END, msg)
                self.ia_chat_text.see(tk.END)
                self.ia_chat_text.config(state=tk.DISABLED)
        
        # Ejecutar en el hilo principal
        if threading.current_thread() != threading.main_thread():
            self.after(0, _update)
        else:
            _update()

    def update_ia_chat(self, msg):
        """Método de compatibilidad - ahora usa markdown"""
        self.update_ia_chat_markdown(msg)

    def update_progress(self, cur, tot):
        """Método de compatibilidad - ahora redirige a los nuevos indicadores"""
        self.update_progress_indicators("processing", current=cur, total=tot)

    def cancel_process(self):
        self.cancelled = True
        self.update_transcription_log("❌ Proceso cancelado por usuario.")
        self.update_progress_indicators("cancelled")

if __name__ == '__main__':
    app = TranscriptionApp()
    app.mainloop()