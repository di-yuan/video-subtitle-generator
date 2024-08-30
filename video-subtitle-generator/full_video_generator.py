from moviepy.editor import VideoFileClip
from openai import OpenAI
import argparse
import os


parser = argparse.ArgumentParser(description='Generate subtitles for a video')
parser.add_argument('--data_dir', type=str, default='local_data/')
parser.add_argument('--video_filename', type=str, default='test.MOV')
parser.add_argument('--srt_filename', type=str, default='test_full.srt')
args = parser.parse_args()

data_dir = args.data_dir
video_filename = args.video_filename
srt_filename = args.srt_filename
wav_filename = 'tmp.wav'

video = VideoFileClip(f'{data_dir}{video_filename}')
audio = video.audio
wav_filepath = f'{data_dir}{wav_filename}'
audio.write_audiofile(wav_filepath)
video.close()

wav_file = open(wav_filepath, 'rb')
client = OpenAI()

try:
    transcription = client.audio.transcriptions.create(
        model='whisper-1',
        file=wav_file,
        prompt='min_duration: 0.5, max_duration: 6',
        language='zh',
        response_format='srt'
    )
    with open(f'{data_dir}{srt_filename}', 'w') as srt_file:
        srt_file.write(transcription)
except Exception as e:
    print(e)
finally:
    wav_file.close()
    os.remove(wav_filepath)
