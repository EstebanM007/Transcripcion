import os
import wave
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter import font as tkFont
from moviepy.editor import VideoFileClip, AudioFileClip
import speech_recognition as sr
import re

# Importación de componentes de LangChain
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

import os, sys
if getattr(sys, "frozen", False):
    # sys._MEIPASS es la carpeta temporal donde PyInstaller extrae los binarios
    os.environ["IMAGEIO_FFMPEG_EXE"] = os.path.join(sys._MEIPASS, "ffmpeg.exe")

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
            self.insert(index, f"• {content}\n", "list_item")
        elif re.match(r'^\d+\. ', line.strip()):
            self.insert(index, line + '\n', "list_item")
        # Línea normal con formato inline
        else:
            self.process_inline_formatting(index, line + '\n')
    
    def process_inline_formatting(self, index, text):
        """Procesa formato inline como negrita, cursiva, código"""
        # Patrones de markdown con expresiones regulares
        patterns = [
            (r'\*\*(.*?)\*\*', 'bold'),      # **texto** -> negrita
            (r'\*(.*?)\*', 'italic'),         # *texto* -> cursiva
            (r'`(.*?)`', 'code'),             # `texto` -> código
        ]
        
        current_pos = 0
        
        while current_pos < len(text):
            # Buscar el próximo patrón
            next_match = None
            next_pos = len(text)
            next_tag = None
            
            for pattern, tag in patterns:
                match = re.search(pattern, text[current_pos:])
                if match:
                    match_start = current_pos + match.start()
                    if match_start < next_pos:
                        next_match = match
                        next_pos = match_start
                        next_tag = tag
            
            if next_match:
                # Insertar texto antes del match
                if next_pos > current_pos:
                    self.insert(index, text[current_pos:next_pos])
                    index = self.index(tk.INSERT)
                
                # Insertar el texto formateado
                formatted_text = next_match.group(1)
                self.insert(index, formatted_text, next_tag)
                index = self.index(tk.INSERT)
                
                # Continuar después del match
                current_pos = current_pos + next_match.end()
            else:
                # No hay más patrones, insertar el resto del texto
                self.insert(index, text[current_pos:])
                break

class TranscriptionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcriptor y Chat con IA")
        self.geometry("1200x700")
        self.configure(bg='#f0f2f5')

        # Configurar estilos
        self.setup_styles()

        self.file_path = None
        self.cancelled = False
        self.conversion_in_progress = False

        # API Groq
        if not os.environ.get("GROQ_API_KEY"):
            os.environ["GROQ_API_KEY"] = "tu_clave_api_aqui"
        try:
            self.chat_llm = ChatGroq(
                groq_api_key=os.environ.get("GROQ_API_KEY"),
                model_name="llama3-8b-8192"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error al inicializar modelo de chat: {e}")
            self.destroy()
            return

        # Prompt y memoria
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
        # Mostrar mensaje de bienvenida al iniciar la app
        self.show_welcome()
        
    def show_welcome(self):
        separator = "=" * 50
        self.update_transcription_log(separator)
        self.update_transcription_log("🎙️ Transcriptor y Chat con IA")
        self.update_transcription_log("Descripción: convierte audio a texto y genera un resumen con IA.")
        self.update_transcription_log("Autor: Esteban Alberto Martinez Palacios (Estrategia Digital y GEN XXI).")
        self.update_transcription_log("Uso:")
        self.update_transcription_log("  1) Seleccione un archivo de audio/video.")
        self.update_transcription_log("  2) Pulse 'Transcribir Audio'.")
        self.update_transcription_log("  3) Espere el resultado en el panel de la derecha.")
        self.update_transcription_log("  *REPOSITORIO* https://github.com/EstebanM007/Media")
        self.update_transcription_log("")  # línea en blanco para separar

        # Nota sobre límites y memoria
        self.update_transcription_log("⚠️ Nota[(REQUIERE CONEXION A INTERNET) LA TRANSCRIPCION NO ES PERFECTA Y DEPENDE MUCHO DE LA CLARIDAD DEL AUDIO]: Si la transcripción excede el tamaño máximo de petición o agota tus créditos gratuitos, el resumen/IA no funcionará. Además, la IA solo recuerda los últimos 5 mensajes enviados.")
        self.update_transcription_log("⚠️ Nota: El programa genera un arcivo WAV y un arichivo TXT con la transcripcion, al igual que muestra el registro de transcripción en el panel derecho.")
        self.update_transcription_log(" Nota: El programa divide el audio en segmentos de 60 segundos para evitar problemas de memoria y tamaño de petición, esto crea archivos temporales en el directorio actual.")

        self.update_transcription_log("")  # línea en blanco para separar

        # Instrucciones de uso del chat
        self.update_transcription_log("💬 Para chatear con la IA en modo conversación, utiliza el panel inferior izquierdo.")
        self.update_transcription_log("(Maximiza la ventana para ver mejor el chat y poder chatear con la IA.)")
        self.update_transcription_log("Los mensajes en el chat son editables: puedes eliminar o modificar texto libremente.")
        self.update_transcription_log("Usa Ctrl+A para seleccionar todo el texto dentro del chat cuando lo necesites.")
        self.update_transcription_log("✨ NUEVO: El chat ahora soporta formato Markdown - la IA puede usar negrita, cursiva, código, etc.")
        self.update_transcription_log(separator)

    def setup_styles(self):
        self.colors = {
            'primary': '#2563eb', 'primary_hover': '#1d4ed8',
            'secondary': '#64748b', 'success': '#10b981',
            'danger': '#ef4444', 'background': '#f0f2f5',
            'surface': '#ffffff', 'accent': '#8b5cf6',
            'text_primary': '#1f2937', 'text_secondary': '#6b7280'
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

    def create_widgets(self):
        self.create_header()
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
        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0,10))
        left = ttk.Frame(paned)
        right = ttk.Frame(paned)
        paned.add(left, weight=1)
        paned.add(right, weight=1)
        self.create_chat_panel(left)
        self.create_transcription_panel(right)

    def create_chat_panel(self, parent):
        frame = tk.Frame(parent, bg=self.colors['surface'], bd=1, relief='solid')
        frame.pack(fill=tk.BOTH, expand=True, padx=(0,10), pady=5)
        hdr = tk.Frame(frame, bg=self.colors['accent'], height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="🤖 Chat con IA (Markdown)", bg=self.colors['accent'], fg='white',
            font=('Segoe UI',14,'bold')
        ).pack(expand=True)
        
        # Crear el frame del chat
        chat_frame = tk.Frame(frame)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Crear el widget de texto con markdown
        self.ia_chat_text = MarkdownText(
            chat_frame, wrap=tk.WORD, font=('Segoe UI',11), bg='#f8fafc',
            bd=1, relief='solid', state=tk.DISABLED
        )
        
        # Crear scrollbar
        scrollbar = tk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.ia_chat_text.yview)
        self.ia_chat_text.configure(yscrollcommand=scrollbar.set)
        
        # Empaquetar
        self.ia_chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Mensaje de bienvenida en el chat
        self.ia_chat_text.config(state=tk.NORMAL)
        welcome_msg = "¡Hola! 👋 Soy tu asistente de IA. Puedo ayudarte a:\n\n"
        welcome_msg += "• **Resumir** transcripciones de audio\n"
        welcome_msg += "• **Responder preguntas** sobre el contenido\n"
        welcome_msg += "• **Analizar** información de manera conversacional\n\n"
        welcome_msg += "Una vez que transcribas un audio, automáticamente te daré un resumen. "
        welcome_msg += "También puedes hacerme preguntas o pedirme que analice aspectos específicos del contenido.\n\n"
        welcome_msg += "*Tip: Mis respuestas incluyen formato markdown para mejor legibilidad.*"
        
        self.ia_chat_text.insert_markdown(tk.END, welcome_msg)
        self.ia_chat_text.config(state=tk.DISABLED)
        
        inp = tk.Frame(frame, bg=self.colors['surface'])
        inp.pack(fill=tk.X, padx=10, pady=(0,10))
        self.ia_entry = tk.Entry(
            inp, font=('Segoe UI',11), bg='white', insertbackground=self.colors['primary']
        )
        self.ia_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ia_entry.bind('<Return>', lambda e: self.send_message())
        ttk.Button(
            inp, text="➤ Enviar", style='Primary.TButton',
            command=self.send_message
        ).pack(side=tk.RIGHT)

    def create_transcription_panel(self, parent):
        frame = tk.Frame(parent, bg=self.colors['surface'], bd=1, relief='solid')
        frame.pack(fill=tk.BOTH, expand=True, padx=(10,0), pady=5)
        hdr = tk.Frame(frame, bg=self.colors['success'], height=40)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="📝 Registro de Transcripción", bg=self.colors['success'],
            fg='white', font=('Segoe UI',14,'bold')
        ).pack(side=tk.LEFT, padx=10)
        self.progress_label = tk.Label(hdr, bg=self.colors['success'], fg='white')
        self.progress_label.pack(side=tk.RIGHT, padx=10)
        self.transcription_text = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=('Consolas',10), bg='#f8fafc',
            bd=1, relief='solid'
        )
        self.transcription_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def create_signature_area(self):
        self.signature_frame = tk.Frame(self, bg='#ffffff', bd=1, relief='solid')
        self.signature_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0,10))
        line = tk.Frame(self.signature_frame, bg=self.colors['primary'], height=3)
        line.pack(fill=tk.X)
        cont = tk.Frame(self.signature_frame, bg='#ffffff')
        cont.pack(fill=tk.X, padx=20, pady=10)

    # Métodos de transcripción y chat
    def select_file(self):
        filetypes = [("Media Files", "*.mp4 *.ogg *.mp3 *.wav"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Seleccione un archivo", filetypes=filetypes)
        if path:
            self.file_path = path
            filename = os.path.basename(path)
            self.file_label.config(text=f"📄 {filename}", fg=self.colors['success'])
            self.transcribe_btn.config(state=tk.NORMAL)
            self.update_transcription_log(f"Archivo seleccionado: {filename}")
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
            return segments
        frame_rate = audio.getframerate()
        n_frames = audio.getnframes()
        duration = n_frames / frame_rate
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
        for i, seg in enumerate(segments, 1):
            if self.cancelled:
                self.update_transcription_log("Transcripción cancelada.")
                break
            with sr.AudioFile(seg) as source:
                audio_data = recognizer.record(source)
                try:
                    text = recognizer.recognize_google(audio_data, language="es-ES")
                    self.update_transcription_log(f"{seg}: {text}")
                    full += text + "\n"
                except sr.UnknownValueError:
                    self.update_transcription_log(f"No entendí {seg}")
                except sr.RequestError as e:
                    self.update_transcription_log(f"Error petición {seg}: {e}")
            try:
                os.remove(seg)
            except:
                pass
            self.update_progress(i, total)
        return full

    def _transcribe_audio(self):
        if not self.file_path:
            self.update_transcription_log("Seleccione un archivo primero.")
            return
        self.cancelled = False
        self.cancel_btn.config(state=tk.NORMAL)
        self.update_transcription_log("Iniciando conversión...")
        wav = self.convert_to_wav(self.file_path)
        if not wav:
            self.update_transcription_log("Conversión fallida.")
            return
        self.update_transcription_log("Dividiendo audio...")
        segs = self.divide_audio(wav)
        if not segs:
            return
        self.update_transcription_log("Iniciando transcripción...")
        text = self.transcribe_segments(segs)
        with open("transcripcion.txt","w",encoding="utf-8") as f:
            f.write(text)
        self.update_transcription_log("Transcripción guardada.")
        self.update_transcription_log("Enviando a IA resumen...")
        summary = self.get_chat_response("Resume el siguiente texto de manera clara y estructurada usando markdown cuando sea apropiado:\n\n" + text)
        self.update_ia_chat_markdown("\n\n---\n\n🤖 **Resumen Automático de la Transcripción:**\n\n" + summary)
        self.cancel_btn.config(state=tk.DISABLED)

    def transcribe_audio(self):
        threading.Thread(target=self._transcribe_audio, daemon=True).start()

    def update_transcription_log(self, msg):
        self.transcription_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.transcription_text.see(tk.END)

    def get_chat_response(self, human_input):
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template("{human_input}")
        ])
        chain = LLMChain(llm=self.chat_llm, prompt=prompt, memory=self.conv_memory)
        return chain.predict(human_input=human_input)

    def send_message(self):
        msg = self.ia_entry.get().strip()
        if not msg:
            return
        self.update_ia_chat_markdown(f"\n👤 **Usuario**: {msg}\n")
        self.ia_entry.delete(0,tk.END)
        threading.Thread(target=lambda: self._send_message(msg), daemon=True).start()

    def _send_message(self, msg):
        try:
            resp = self.get_chat_response(msg)
            self.update_ia_chat_markdown(f"\n🤖 **IA**: {resp}\n")
        except Exception as e:
            self.update_ia_chat_markdown(f"\n❌ **Error IA**: {e}\n")

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
        self.progress_label.config(text=f"{cur}/{tot}")

    def cancel_process(self):
        self.cancelled = True
        self.update_transcription_log("Proceso cancelado por usuario.")

if __name__ == '__main__':
    app = TranscriptionApp()
    app.mainloop()