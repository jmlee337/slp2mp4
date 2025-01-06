import argparse
import pathlib
import tempfile
import multiprocessing
import queue
import os
import zipfile

import slp2mp4.video as video
import slp2mp4.util as util
import slp2mp4.ffmpeg as ffmpeg



def _get_inputs_and_outputs(root: pathlib.Path, in_dir: pathlib.Path, out_dir: pathlib.Path):
    outputs = {}
    slps = [slp.resolve() for slp in sorted(in_dir.glob("*.slp"), key=util.natsort)]
    
    # Process .zip files in the directory
    for zip_file in in_dir.glob("*.zip"):
        extraction_dir = out_dir / zip_file.stem
        extraction_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_file, 'r') as z:
            z.extractall(extraction_dir)
        # Recursively process extracted files
        outputs.update(_get_inputs_and_outputs(root, extraction_dir, out_dir))
    
    root_name = pathlib.Path(root.resolve().name)
    relative_path = root_name.joinpath(in_dir.relative_to(root))
    name = f"""{out_dir.joinpath(("_").join(relative_path.parts))}.mp4"""

    if len(slps) > 0:
        outputs[name] = slps

    for child in in_dir.iterdir():
        if child.is_dir():
            outputs = outputs | _get_inputs_and_outputs(root, child, out_dir)
    
    return outputs


def _render(conf, args, slp_queue, video_queue):
    while True:
        data = slp_queue.get()
        if data is None:
            break
        key, path = data
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        if not args.dry_run:
            video.render(conf, path, pathlib.Path(tmp.name))
        tmp.close()
        video_queue.put((key, {path: tmp.name}))


def _concat(conf, args, video_queue, inputs_and_outputs):
    Ffmpeg = ffmpeg.FfmpegRunner(conf)
    outputs = {}
    while True:
        data = video_queue.get()
        if data is None:
            break
        key, tmpfile = data
        if key not in outputs:
            outputs[key] = {}
        outputs[key] = outputs[key] | tmpfile
        if len(outputs[key]) < len(inputs_and_outputs[key]):
            continue
        tmpfiles = [outputs[key][path] for path in inputs_and_outputs[key]]
        output_file = key
        print(f"files to concat: {tmpfiles}")
        if not args.dry_run:
            Ffmpeg.concat_videos([pathlib.Path(t) for t in tmpfiles], output_file)
        for tmp in tmpfiles:
            os.unlink(tmp)


def run(conf, args):
    path = args.path
    output_directory = args.output_directory
    if not args.dry_run:
        os.makedirs(output_directory, exist_ok=True)
    inputs_and_outputs = _get_inputs_and_outputs(path, path, output_directory)

    slp_queue = multiprocessing.Queue()
    video_queue = multiprocessing.Queue()

    slp_pool = multiprocessing.Pool(
        conf["runtime"]["parallel"],
        _render,
        (
            conf,
            args,
            slp_queue,
            video_queue,
        ),
    )
    video_pool = multiprocessing.Pool(
        1,
        _concat,
        (
            conf,
            args,
            video_queue,
            inputs_and_outputs,
        ),
    )

    for key, slps in inputs_and_outputs.items():
        for slp in slps:
            slp_queue.put(
                (
                    key,
                    slp,
                )
            )

    for i in range(conf["runtime"]["parallel"]):
        slp_queue.put(None)

    slp_queue.close()
    slp_queue.join_thread()

    slp_pool.close()
    slp_pool.join()

    video_queue.put(None)

    video_queue.close()
    video_queue.join_thread()

    video_pool.close()
    video_pool.join()

    return [(out, inputs) for out, inputs in inputs_and_outputs.items()]


def register(subparser):
    parser = subparser.add_parser(
        "directory",
        help="render and combine .slp files in a directory to a video, recursively",
    )
    parser.add_argument("path", type=pathlib.Path)
    parser.set_defaults(run=run)
