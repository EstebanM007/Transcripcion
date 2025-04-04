from moviepy.editor import VideoFileClip

# Cargar el archivo .mp4
video_clip = VideoFileClip("audio.mp4")

# Extraer el audio y guardarlo como .wav
audio_clip = video_clip.audio
audio_clip.write_audiofile("archivo.wav")
