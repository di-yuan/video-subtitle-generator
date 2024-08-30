from moviepy.editor import VideoFileClip
from openai import OpenAI
import argparse
import auditok
import datetime
import os
import srt


parser = argparse.ArgumentParser(description='Generate subtitles for a video')
parser.add_argument('--data_dir', type=str, default='local_data/')
parser.add_argument('--video_filename', type=str, default='test.MOV')
parser.add_argument('--srt_filename', type=str, default='test.srt')
parser.add_argument('--min_duration', type=float, default=0.5)
parser.add_argument('--max_duration', type=float, default=6)
parser.add_argument('--max_silence', type=float, default=2)
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

# min_dur: minimum duration of a valid audio event in seconds
# max_dur: maximum duration of an event
# max_silence: maximum duration of tolerated continuous silence within an event
# energy_threshold: threshold of detection
audio_regions = auditok.split(
    wav_filepath,
    min_dur=args.min_duration,
    max_dur=args.max_duration,
    max_silence=args.max_silence,
    energy_threshold=55
)
os.remove(wav_filepath)

subtitles = []
client = OpenAI()
for index, region in enumerate(audio_regions):
    # regions returned by `split` have 'start' and 'end' metadata fields
    print('region {index}: {region.meta.start:.3f}s -- {region.meta.end:.3f}s'
          .format(index=index, region=region))

    # region's metadata can also be used with the `save` method
    region_filename = 'region_{meta.start:.3f}-{meta.end:.3f}.wav'
    region_filepath = region.save(f'{data_dir}{region_filename}')

    region_file = open(region_filepath, 'rb')
    try:
        transcription = client.audio.transcriptions.create(
            model='whisper-1',
            file=region_file,
            prompt='only traditional chinese',
        )
    except Exception as e:
        print(e)
        continue
    finally:
        region_file.close()
        os.remove(region_filepath)
    print(transcription.text)

    start_time = datetime.timedelta(seconds=region.meta.start)
    end_time = datetime.timedelta(seconds=region.meta.end)
    subtitles.append(srt.Subtitle(index+1, start=start_time, end=end_time,
                                  content=transcription.text))

if subtitles:
    with open(f'{data_dir}{srt_filename}', 'w') as srt_file:
        srt_file.write(srt.compose(subtitles))
