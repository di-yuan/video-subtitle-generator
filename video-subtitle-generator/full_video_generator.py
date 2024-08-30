from moviepy.editor import VideoFileClip
from openai import OpenAI

data_dir = 'local_data/'
video_filename = 'test.MOV'
audio_filename = 'test.wav'

video = VideoFileClip(f'{data_dir}{video_filename}')
audio = video.audio
audio_filepath = f'{data_dir}{audio_filename}'
audio.write_audiofile(audio_filepath)

audio_file = open(audio_filepath, 'rb')
client = OpenAI()

try:
    transcription = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio_file,
        prompt='min_duration: 0.5, max_duration: 6',
        language='zh',
        response_format='srt'
    )
except Exception as e:
    print(e)

srt_filename = 'test_full.srt'
with open(f'{data_dir}{srt_filename}', 'w') as srt_file:
    srt_file.write(transcription)
