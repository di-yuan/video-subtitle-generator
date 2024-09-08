from moviepy.editor import VideoFileClip
from openai import OpenAI
from srt import Subtitle
from srt import compose
from srt import parse as parse_srt
from srt import sort_and_reindex
import argparse
import datetime
import os


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate subtitles for a video')
    parser.add_argument('--data_dir', type=str, default='local_data/')
    parser.add_argument('--video_filename', type=str, default='test.MOV')
    parser.add_argument('--srt_filename', type=str, default='test_full.srt')
    parser.add_argument(
        '-mt', '--merged_threshold', type=float, default=0.5,
        help='threshold(seconds) for merging subtitles')
    parser.add_argument(
        '-md', '--max_duration', type=float, default=2,
        help='max duration(seconds) of each subtitle')
    parser.add_argument(
        '-ml', '--max_length', type=int, default=17,
        help='max number of characters of each subtitle')
    parser.add_argument(
        '--fake', action='store_true', help='use local srt file')
    return parser.parse_args()


def merge_subtitle(start: Subtitle, end: Subtitle) -> Subtitle:
    return Subtitle(
        index=start.index,
        start=start.start,
        end=end.end,
        content=start.content + end.content
    )


if __name__ == '__main__':
    args = parse_args()

    data_dir = args.data_dir
    video_filename = args.video_filename
    srt_filename = args.srt_filename
    fake_post = args.fake
    wav_filename = 'tmp.wav'

    video = VideoFileClip(f'{data_dir}{video_filename}')
    audio = video.audio
    wav_filepath = f'{data_dir}{wav_filename}'
    audio.write_audiofile(wav_filepath)
    video.close()

    if fake_post:  # use local srt file
        if not os.path.exists(f'{data_dir}{srt_filename}'):
            raise FileNotFoundError(f'{data_dir}{srt_filename} not found')
        transcription = open(f'{data_dir}{srt_filename}', 'r').read()
    else:  # post to OpenAI API
        wav_file = open(wav_filepath, 'rb')
        client = OpenAI()
        try:
            print('Transcribing...')
            transcription = client.audio.transcriptions.create(
                model='whisper-1',
                file=wav_file,
                language='zh',
                response_format='srt'
            )
        except Exception as e:
            print(e)
        finally:
            wav_file.close()
            os.remove(wav_filepath)

    subtitles = [subtitle for subtitle in parse_srt(transcription)]

    # merge subtitles
    MAX_SUBTITLE_LENGTH = args.max_length
    MERGED_THRESHOLD = datetime.timedelta(seconds=args.merged_threshold)
    MAX_SUBTITLE_DURATION = datetime.timedelta(seconds=args.max_duration)

    merged_subtitles = []
    current_srt = subtitles[0]
    for next_srt in subtitles[1:]:
        if (
            next_srt.start - current_srt.end < MERGED_THRESHOLD and
            current_srt.end - current_srt.start < MAX_SUBTITLE_DURATION and
            len(current_srt.content + next_srt.content) < MAX_SUBTITLE_LENGTH
        ):
            current_srt = merge_subtitle(current_srt, next_srt)
        else:
            merged_subtitles.append(current_srt)
            current_srt = next_srt
    merged_subtitles.append(current_srt)  # the last subtitle
    sorted_subtitles = sort_and_reindex(merged_subtitles)

    # write to srt file
    composed_srt = compose(sorted_subtitles)
    with open(f'{data_dir}{srt_filename}', 'w') as srt_file:
        srt_file.write(composed_srt)
        print(composed_srt)
    print(f'{data_dir}{srt_filename} generated')
