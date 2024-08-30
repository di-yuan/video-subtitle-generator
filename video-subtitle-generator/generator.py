from moviepy.editor import VideoFileClip
from openai import OpenAI
import auditok
import datetime
import srt


data_dir = 'local_data/'
video_filename = 'test.MOV'
audio_filename = 'test.wav'

video = VideoFileClip(f'{data_dir}{video_filename}')
audio = video.audio
audio_filepath = f'{data_dir}{audio_filename}'
audio.write_audiofile(audio_filepath)

# split returns a generator of AudioRegion objects
# min_dur: minimum duration of a valid audio event in seconds
# max_dur: maximum duration of an event
# max_silence: maximum duration of tolerated continuous silence within an event
# energy_threshold: threshold of detection
audio_regions = auditok.split(
    audio_filepath,
    min_dur=0.2,
    max_dur=4,
    max_silence=2,
    energy_threshold=55
)

subtitles = []
client = OpenAI()
for index, region in enumerate(audio_regions):
    # Regions returned by `split` have 'start' and 'end' metadata fields
    print('Region {index}: {region.meta.start:.3f}s -- {region.meta.end:.3f}s'
          .format(index=index, region=region))

    # region's metadata can also be used with the `save` method
    # (no need to explicitly specify region's object and `format` arguments)
    filename = 'region_{meta.start:.3f}-{meta.end:.3f}.wav'
    filepath = region.save(f'{data_dir}{filename}')
    print('region saved as: {}'.format(filepath))

    audio_file = open(filepath, 'rb')
    transcription = client.audio.transcriptions.create(
        model='whisper-1',
        file=audio_file,
        prompt='only traditional chinese',
    )
    print(transcription.text)

    start_time = datetime.timedelta(seconds=region.meta.start)
    end_time = datetime.timedelta(seconds=region.meta.end)
    subtitles.append(srt.Subtitle(index+1, start=start_time, end=end_time,
                                  content=transcription.text))

srt_filename = 'test.srt'
with open(f'{data_dir}{srt_filename}', 'w') as srt_file:
    srt_file.write(srt.compose(subtitles))
