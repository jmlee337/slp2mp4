# Logic for joining audio / video files

import pathlib
import tempfile
import subprocess
import time
import os
import glob

import slp2mp4.util as util


class FfmpegRunner:
    def __init__(self, config):
        self.ffmpeg_path = config["paths"]["ffmpeg"]

    # Assumes output file can handle no reencoding
    # Returns True if ffmpeg ran successfully, False otherwise
    def merge_audio_and_video(
        self,
        audio_file: pathlib.Path,
        video_file: pathlib.Path,
        output_file: pathlib.Path,
        reencode=False,
    ):
        #reencoded_audio_file = self.reencode_audio(audio_file)
        args = (
            (self.ffmpeg_path,),
            ("-y",),
            (
                "-i",
                audio_file,
            ),
            (
                "-i",
                video_file,
            ),
            (
                "-fflags",
                "+discardcorrupt"
            ),
            (
                "-c:v",
                "copy"
            ),
            (
                "-b:v",
                "7500k",    # TODO follow setting
            ),
            (
                "-ar",
                "48000",
            ),
            (
                "-c:a",
                "libopus",
            ),
            (
                "-ac",
                "2",
            ),
            (
                "-b:a",
                "128k"
            ),
            (
                "-avoid_negative_ts",
                "make_zero",
            ),
            ("-xerror",),
            (output_file,),
        )
        ffmpeg_args = util.flatten_arg_tuples(args)
        try:
            subprocess.run(ffmpeg_args, check=True)
        except subprocess.CalledProcessError as e:
            if e.returncode != 3199971767:
                raise e

    # Assumes all videos have the same encoding
    def concat_videos(self, videos: list[pathlib.Path], output_file: pathlib.Path):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as concat_file:
            print(concat_file)
            print(videos)
            
            files = ("\n").join(f"file '{video.resolve()}'" for video in videos)
            concat_file.write(files)
            concat_file.flush()
            # time.sleep(300)
            args = (
                (self.ffmpeg_path,),
                ("-y",),
                (
                    "-f",
                    "concat",
                ),
                (
                    "-safe",
                    "0",
                ),
                (
                    "-i",
                    concat_file.name,
                ),
                (
                    "-c",
                    "copy",
                ),
                ("-xerror",),
                (output_file,),
            )
            ffmpeg_args = util.flatten_arg_tuples(args)
            subprocess.run(ffmpeg_args, check=True)
