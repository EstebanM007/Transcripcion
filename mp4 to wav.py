from moviepy.editor import VideoFileClip, AudioFileClip
import os

# Ruta del archivo de entrada
input_file = r"D:\38514603\Videos\Grabaciones de pantalla\Grabación de pantalla 2025-05-08 181926.mp4"

# Detectar el formato del archivo de entrada
file_extension = os.path.splitext(input_file)[1].lower()  # Obtener la extensión del archivo
print(f"El archivo de entrada es de tipo: {file_extension}")

# Convertir el archivo al formato .wav
if file_extension in [".mp4"]:
    # Procesar archivos de video
    video_clip = VideoFileClip(input_file)
    audio_clip = video_clip.audio
    audio_clip.write_audiofile("archivo.wav")
    print("El archivo de video ha sido convertido a formato .wav y guardado como 'archivo.wav'")
elif file_extension in [".ogg", ".mp3"]:
    # Procesar archivos de audio
    audio_clip = AudioFileClip(input_file)
    audio_clip.write_audiofile("archivo.wav")
    print("El archivo de audio ha sido convertido a formato .wav y guardado como 'archivo.wav'")
else:
    print("Formato no soportado. Por favor, utiliza un archivo .mp4, .mp3 o .ogg.")
