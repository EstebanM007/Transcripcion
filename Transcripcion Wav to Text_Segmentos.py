import os  # Libreria que interactua con el sistema operativo
import speech_recognition as sr
import wave

# Ruta del archivo .wav
filename = "archivo.wav"
output_file = "transcripcion_audio.txt"

# Inicializar el reconocedor
r = sr.Recognizer()

# Función para dividir el archivo de audio en segmentos
def divide_audio(filename, segment_length=60):
    audio = wave.open(filename, 'rb')
    frame_rate = audio.getframerate()
    n_frames = audio.getnframes()
    duration = n_frames / frame_rate
    segments = []

    for start in range(0, int(duration), segment_length):
        end = min(start + segment_length, duration)
        audio.setpos(int(start * frame_rate))
        frames = audio.readframes(int((end - start) * frame_rate))
        segment_filename = f"segment_{start}_{end}.wav"
        segment_audio = wave.open(segment_filename, 'wb')
        segment_audio.setnchannels(audio.getnchannels())
        segment_audio.setsampwidth(audio.getsampwidth())
        segment_audio.setframerate(frame_rate)
        segment_audio.writeframes(frames)
        segment_audio.close()
        segments.append(segment_filename)

    audio.close()
    return segments

# Dividir el archivo de audio en segmentos de 60 segundos
segments = divide_audio(filename)

# Transcribir cada segmento y guardar la transcripción
with open(output_file, "w", encoding="utf-8") as f:  # Especificar codificación UTF-8
    for segment in segments:
        with sr.AudioFile(segment) as source:
            audio = r.record(source)  # Leer el segmento de audio
            try:
                text = r.recognize_google(audio, language="es-ES")  # Transcribir el audio
                f.write(text + "\n")
                print(f"Transcripción del segmento {segment} completada")
            except sr.UnknownValueError:
                print(f"No se pudo entender el audio del segmento {segment}")
            except sr.RequestError as e:
                print(f"Error al solicitar resultados para el segmento {segment}; {0}".format(e))
        os.remove(segment)  # Eliminar el archivo de segmento temporal

print("Transcripción completa y guardada en", output_file)