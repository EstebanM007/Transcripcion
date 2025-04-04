import os
from moviepy.editor import VideoFileClip # Convertir .mp4 a .wav Versión 1.0.3
import speech_recognition as sr

# Convertir .mp4 a .wav
video_clip = VideoFileClip("audio.mp4")
audio_clip = video_clip.audio
audio_clip.write_audiofile("archivo_temp.wav")

# Transcribir el audio
filename = "archivo_temp.wav"
output_file = "transcripcion_audio.txt"
r = sr.Recognizer()

with sr.AudioFile(filename) as source:
    audio = r.record(source)  # Leer el archivo de audio
    try:
        text = r.recognize_google(audio, language="es-ES")  # Transcribir el audio
        with open(output_file, "w") as f:
            f.write(text)
        print("Transcripción completada y guardada en", output_file)
    except sr.UnknownValueError:
        print("No se pudo entender el audio")
    except sr.RequestError as e:
        print("Error al solicitar resultados; {0}".format(e))

# Eliminar el archivo temporal
os.remove(filename)
