# Logic to orchestrate making a video file from a slippi replay

import pathlib
import shutil
import tempfile

import slp2mp4.ffmpeg as ffmpeg
import slp2mp4.replay as replay
import slp2mp4.dolphin.runner as dolphin_runner


# Returns True if the render succeeded, False otherwise
# output_path must be a container that requires no reencoding, e.g. mkv
def render(conf, slp_path: pathlib.Path, output_path: pathlib.Path):
    Ffmpeg = ffmpeg.FfmpegRunner(conf)
    Dolphin = dolphin_runner.DolphinRunner(conf)
    with tempfile.TemporaryDirectory() as tmpdir_str:
        tmpdir = pathlib.Path(tmpdir_str)
        try:
            r = replay.ReplayFile(slp_path)
        except:
            return False
        tries = 0
        while (True):
            try:
                audio_file, video_file = Dolphin.run_dolphin(r, tmpdir)
                break
            except:
                tries += 1
                if tries < 3:
                    print(f"dolphin retry #{tries} for {slp_path}")
                    shutil.rmtree(tmpdir, ignore_errors=True)
                else:
                    return False

        try:
            Ffmpeg.merge_audio_and_video(
                audio_file,
                video_file,
                output_path,
                conf["video"]["reencode_when_merging_audio_and_video"],
            )
            return True
        except:
            return False
