import os
import wave
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog
from moviepy import *
import speech_recognition as sr

# Importación de componentes de LangChain (basados en el ejemplo proporcionado)
from langchain.chains import LLMChain
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq

class TranscriptionApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Transcriptor y Chat con IA")
        self.geometry("1000x600")
        self.file_path = None
        self.cancelled = False
        self.conversion_in_progress = False

        # Configurar la clave API para Groq.
        if not os.environ.get("GROQ_API_KEY"):
            # Nota: Incluir la clave en el código no es seguro en producción.
<<<<<<< HEAD
            os.environ["GROQ_API_KEY"] = "Key_Secreta_Groq"
=======
            os.environ["GROQ_API_KEY"] = "Key_Secreta_Groq"
>>>>>>> 065e5ef0aed046e2b1d59266e61b1cf71bc50156

        # Inicializar el modelo de chat usando ChatGroq.
        try:
            groq_api_key = os.environ.get("GROQ_API_KEY")
            self.chat_llm = ChatGroq(groq_api_key=groq_api_key, model_name="llama3-8b-8192")
        except Exception as e:
            messagebox.showerror("Error", f"Error al inicializar el modelo de chat: {e}")
            self.destroy()
            return

        # Definir el prompt del sistema y configurar la memoria conversacional.
        self.system_prompt = ("Eres un chatbot conversacional amigable que ayuda a resumir y "
                              "responder preguntas sobre transcripciones.")
        self.conv_memory = ConversationBufferWindowMemory(k=5, memory_key="chat_history", return_messages=True)

        # --- Área de control superior ---
        self.control_frame = tk.Frame(self)
        self.control_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.select_button = tk.Button(self.control_frame, text="Seleccionar Archivo", width=20, command=self.select_file)
        self.select_button.pack(side=tk.LEFT, padx=5)

        self.file_label = tk.Label(self.control_frame, text="No se ha seleccionado ningún archivo", wraplength=600)
        self.file_label.pack(side=tk.LEFT, padx=5)

        self.transcribe_button = tk.Button(self.control_frame, text="Transcribir", width=20, command=self.transcribe_audio, state=tk.DISABLED)
        self.transcribe_button.pack(side=tk.LEFT, padx=5)

        # Botón para cancelar el proceso, ubicado en la parte superior derecha.
        self.cancel_button = tk.Button(self.control_frame, text="Cancelar Proceso", width=20, command=self.cancel_process, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)

        # --- Panel principal dividido en dos columnas ---
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(expand=1, fill=tk.BOTH, padx=10, pady=10)

        # Izquierda: Chat con IA
        self.left_frame = tk.Frame(self.paned)
        tk.Label(self.left_frame, text="Chat con IA", font=("Arial", 12, "bold")).pack(pady=5)
        self.ia_chat_text = scrolledtext.ScrolledText(self.left_frame, wrap=tk.WORD, width=50, height=25)
        self.ia_chat_text.pack(expand=1, fill=tk.BOTH, padx=5, pady=5)
        # Entrada y botón para enviar mensajes al chatbot.
        self.ia_input_frame = tk.Frame(self.left_frame)
        self.ia_input_frame.pack(fill=tk.X, padx=5, pady=5)
        self.ia_entry = tk.Entry(self.ia_input_frame)
        self.ia_entry.pack(side=tk.LEFT, expand=1, fill=tk.X, padx=(0,5))
        self.ia_send_button = tk.Button(self.ia_input_frame, text="Enviar", command=self.send_message)
        self.ia_send_button.pack(side=tk.LEFT)
        self.paned.add(self.left_frame)

        # Derecha: Registro de Transcripción y visualizador de progreso
        self.right_frame = tk.Frame(self.paned)
        # Frame para título y visualizador de progreso.
        title_frame = tk.Frame(self.right_frame)
        title_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Label(title_frame, text="Registro de Transcripción", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        self.progress_label = tk.Label(title_frame, text="")
        self.progress_label.pack(side=tk.RIGHT, padx=5)
        self.transcription_text = scrolledtext.ScrolledText(self.right_frame, wrap=tk.WORD, width=50, height=25)
        self.transcription_text.pack(expand=1, fill=tk.BOTH, padx=5, pady=5)
        self.paned.add(self.right_frame)

    # Actualiza el log en el panel derecho.
    def update_transcription_log(self, message):
        self.transcription_text.insert(tk.END, message + "\n")
        self.transcription_text.see(tk.END)
        self.update_idletasks()

    # Actualiza el chat de IA en el panel izquierdo.
    def update_ia_chat(self, message):
        self.ia_chat_text.insert(tk.END, message + "\n")
        self.ia_chat_text.see(tk.END)
        self.update_idletasks()

    # Actualiza el visualizador de progreso (para el proceso de transcripción o conversión).
    def update_progress(self, current, total):
        progress_percent = int((current / total) * 100)
        self.progress_label.config(text=f"Progreso: {current}/{total} ({progress_percent}%)")

    # Método para animar el progreso durante la conversión.
    def animate_conversion_progress(self):
        counter = 0
        while self.conversion_in_progress and not self.cancelled:
            dots = '.' * (counter % 4)
            self.progress_label.config(text=f"Conversión en progreso{dots}")
            counter += 1
            self.update_idletasks()
            time.sleep(0.5)
        if self.cancelled:
            self.progress_label.config(text="Conversión cancelada.")
        else:
            self.progress_label.config(text="Conversión completada.")

    # Retorna la respuesta del chatbot utilizando LLMChain y la memoria conversacional.
    def get_chat_response(self, user_input):
        prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{human_input}"),
            ]
        )
        chain = LLMChain(llm=self.chat_llm, prompt=prompt, verbose=False, memory=self.conv_memory)
        response = chain.predict(human_input=user_input)
        return response

    # Permite seleccionar un archivo local.
    def select_file(self):
        filetypes = [("Media Files", "*.mp4 *.ogg *.mp3 *.wav"), ("All files", "*.*")]
        path = filedialog.askopenfilename(title="Seleccione un archivo", filetypes=filetypes)
        if path:
            self.file_path = path
            self.file_label.config(text=f"Archivo seleccionado: {path}")
            self.transcribe_button.config(state=tk.NORMAL)
            self.update_transcription_log("Archivo seleccionado correctamente.")
        else:
            self.update_transcription_log("No se seleccionó ningún archivo.")

    # Convierte el archivo a WAV, si es necesario.
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
                output_wav = input_file
            else:
                self.update_transcription_log("Formato no soportado. Use un archivo .mp4, .ogg, .mp3 o .wav.")
                return None
        except Exception as e:
            self.update_transcription_log(f"Error durante la conversión: {e}")
            return None
        return output_wav

    # Divide el archivo WAV en segmentos (por defecto: 60 segundos).
    def divide_audio(self, filename, segment_length=60):
        segments = []
        try:
            audio = wave.open(filename, 'rb')
        except Exception as e:
            self.update_transcription_log(f"Error al abrir el archivo WAV: {e}")
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
                segment_audio = wave.open(segment_filename, 'wb')
                segment_audio.setnchannels(audio.getnchannels())
                segment_audio.setsampwidth(audio.getsampwidth())
                segment_audio.setframerate(frame_rate)
                segment_audio.writeframes(frames)
                segment_audio.close()
                segments.append(segment_filename)
                self.update_transcription_log(f"Segmento creado: {segment_filename}")
            except Exception as e:
                self.update_transcription_log(f"Error al crear el segmento {segment_filename}: {e}")

        audio.close()
        return segments

    # Transcribe cada segmento usando SpeechRecognition y actualiza el progreso.
    def transcribe_segments(self, segments):
        recognizer = sr.Recognizer()
        full_transcription = ""
        total = len(segments)
        for count, segment in enumerate(segments, start=1):
            if self.cancelled:
                self.update_transcription_log("Proceso cancelado durante la transcripción.")
                break
            with sr.AudioFile(segment) as source:
                audio_data = recognizer.record(source)
                try:
                    text = recognizer.recognize_google(audio_data, language="es-ES")
                    self.update_transcription_log(f"Segmento {segment} transcripto: {text}")
                    full_transcription += text + "\n"
                except sr.UnknownValueError:
                    self.update_transcription_log(f"No se pudo entender el audio del segmento {segment}")
                except sr.RequestError as e:
                    self.update_transcription_log(f"Error en la solicitud para {segment}: {e}")
            try:
                os.remove(segment)
            except Exception as e:
                self.update_transcription_log(f"Error al eliminar el segmento {segment}: {e}")
            self.update_progress(count, total)
        return full_transcription

    # Función interna (ejecutada en un hilo) que gestiona conversión, división, transcripción y resumen.
    def _transcribe_audio(self):
        if not self.file_path:
            self.update_transcription_log("Por favor, seleccione primero un archivo.")
            return

        # Reiniciamos la bandera de cancelación y habilitamos el botón Cancelar.
        self.cancelled = False
        self.cancel_button.config(state=tk.NORMAL)

        # CONVERSIÓN: Ejecutar la conversión con indicador de progreso
        self.update_transcription_log("Iniciando proceso de conversión...")
        self.conversion_in_progress = True
        anim_thread = threading.Thread(target=self.animate_conversion_progress, daemon=True)
        anim_thread.start()
        wav_file = self.convert_to_wav(self.file_path)
        self.conversion_in_progress = False

        if self.cancelled:
            self.update_transcription_log("Proceso cancelado durante la conversión.")
            self.cancel_button.config(state=tk.DISABLED)
            return

        if wav_file is None:
            self.update_transcription_log("Error en la conversión. Proceso abortado.")
            self.cancel_button.config(state=tk.DISABLED)
            return

        self.update_transcription_log("Conversión completada.")

        # DIVISIÓN: Dividir el audio en segmentos.
        segments = self.divide_audio(wav_file, segment_length=60)
        if not segments or self.cancelled:
            self.update_transcription_log("Proceso cancelado o no se pudieron dividir los segmentos.")
            self.cancel_button.config(state=tk.DISABLED)
            return

        # TRANSCRIPCIÓN: Transcribir cada segmento.
        transcription = self.transcribe_segments(segments)
        if self.cancelled:
            self.update_transcription_log("Proceso cancelado durante la transcripción.")
            self.cancel_button.config(state=tk.DISABLED)
            return

        output_text_file = "transcripcion_audio.txt"
        try:
            with open(output_text_file, "w", encoding="utf-8") as f:
                f.write(transcription)
            self.update_transcription_log("Transcripción completa y guardada en " + output_text_file)
        except Exception as e:
            self.update_transcription_log(f"Error al guardar la transcripción: {e}")

        # ENVÍO A LA IA: Solicitar resumen con la transcripción completa.
        summary_prompt = "Realiza un resumen de la siguiente transcripción:\n\n" + transcription
        try:
            summary = self.get_chat_response(summary_prompt)
            self.update_ia_chat("Resumen de la transcripción:\n" + summary)
        except Exception as e:
            self.update_ia_chat(f"Error al obtener resumen: {e}")

        self.cancel_button.config(state=tk.DISABLED)

    # Inicia la transcripción en un hilo para no bloquear la interfaz.
    def transcribe_audio(self):
        threading.Thread(target=self._transcribe_audio, daemon=True).start()

    # Envía un mensaje del usuario al chatbot en un hilo.
    def send_message(self):
        user_input = self.ia_entry.get().strip()
        if not user_input:
            return
        self.update_ia_chat("Usuario: " + user_input)
        self.ia_entry.delete(0, tk.END)
        threading.Thread(target=self._send_message, args=(user_input,), daemon=True).start()

    def _send_message(self, user_input):
        try:
            response = self.get_chat_response(user_input)
            self.update_ia_chat("IA: " + response)
        except Exception as e:
            self.update_ia_chat(f"Error al enviar mensaje a la IA: {e}")

    # Método para cancelar el proceso.
    def cancel_process(self):
        self.cancelled = True
        self.update_transcription_log("Proceso de transcripción cancelado por el usuario.")
        self.cancel_button.config(state=tk.DISABLED)

if __name__ == '__main__':
    app = TranscriptionApp()
    app.mainloop()
