from openai import OpenAI
from moviepy.editor import VideoFileClip
import auditok
import datetime
import srt

# video = VideoFileClip("./local_data/test.MOV")
# audio = video.audio
# audio.write_audiofile("./local_data/test.wav")

# split returns a generator of AudioRegion objects
audio_regions = auditok.split(
    "local_data/test.wav",
    min_dur=0.2,     # minimum duration of a valid audio event in seconds
    max_dur=4,       # maximum duration of an event
    max_silence=2, # maximum duration of tolerated continuous silence within an event
    energy_threshold=55 # threshold of detection
)

subtitles = []
client = OpenAI()
for i, r in enumerate(audio_regions):

    # Regions returned by `split` have 'start' and 'end' metadata fields
    print("Region {i}: {r.meta.start:.3f}s -- {r.meta.end:.3f}s".format(i=i, r=r))

    # play detection
    # r.play(progress_bar=True)

    # region's metadata can also be used with the `save` method
    # (no need to explicitly specify region's object and `format` arguments)
    filename = r.save("local_data/region_{meta.start:.3f}-{meta.end:.3f}.wav")
    print("region saved as: {}".format(filename))

    audio_file = open(filename, "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        prompt="only traditional chinese",
    )

    print(transcription.text)

    start_time = datetime.timedelta(seconds=r.meta.start)
    end_time = datetime.timedelta(seconds=r.meta.end)
    subtitles.append(srt.Subtitle(i+1, start=start_time, end=end_time, content=transcription.text))

srt_file = open("local_data/test.srt", "w")
srt_file.write(srt.compose(subtitles))
srt_file.close()
