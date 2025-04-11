from moviepy.editor import VideoFileClip

# Cargar el archivo .mp4
video_clip = VideoFileClip(r"D:\38514603\Videos\Grabaciones de pantalla\Grabación de pantalla 2025-04-11 140938.mp4")

# Extraer el audio y guardarlo como .wav
audio_clip = video_clip.audio
audio_clip.write_audiofile("archivo.wav")
