import os
from moviepy.editor import VideoFileClip
from pyAudioAnalysis import audioSegmentation as aS
import speech_recognition as sr

# Convertir .mp4 a .wav
video_clip = VideoFileClip("ruta/al/archivo.mp4")
audio_clip = video_clip.audio
audio_clip.write_audiofile("archivo_temp.wav")

# Probar con diferentes números de locutores
best_segmentation = None
best_score = float('inf')
for n_speakers in range(1, 10):  # Probar con 1 a 9 locutores
    segmentation = aS.speaker_diarization("archivo_temp.wav", n_speakers=n_speakers)
    score = aS.evaluate_segmentation(segmentation)  # Evaluar la calidad de la segmentación
    if score < best_score:
        best_score = score
        best_segmentation = segmentation

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
