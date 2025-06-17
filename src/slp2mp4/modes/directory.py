import argparse
from functools import cmp_to_key
import pathlib
import shutil
import sys
import tempfile
import multiprocessing
import queue
import os
import zipfile
import json
from pathvalidate import sanitize_filename

import slp2mp4.video as video
import slp2mp4.util as util
import slp2mp4.ffmpeg as ffmpeg

def _compare_context(a: dict, b: dict):
    if ('context' in a and 'startgg' in a['context']):
        aStartgg = a['context']['startgg']
    if ('context' in b and 'startgg' in b['context']):
        bStartgg = b['context']['startgg']
    if (aStartgg is None and bStartgg is None):
        if a['extraction_dir'] < b['extraction_dir']:
            return -1
        if a['extraction_dir'] > b['extraction_dir']:
            return 1
        return 0
    if (aStartgg is not None and bStartgg is None):
        return -1
    if (aStartgg is None and bStartgg is not None):
        return 1
    if (aStartgg['phase']['id'] != bStartgg['phase']['id']):
        return aStartgg['phase']['id'] - bStartgg['phase']['id']
    if (aStartgg['set']['ordinal'] is not None and bStartgg['set']['ordinal'] is not None):
        return aStartgg['set']['ordinal'] - bStartgg['set']['ordinal']
    return aStartgg['set']['round'] - bStartgg['set']['round']

def _get_inputs_and_outputs(in_dir: pathlib.Path, out_dir: pathlib.Path, zip_dirs: list):
    outputs = {}
    slps = [slp.resolve() for slp in sorted(in_dir.glob("*.slp"), key=util.natsort)]
    try:
        c_file = open(in_dir / "context.json")
    except FileNotFoundError:
        context = None
    else:
        with c_file:
            context = json.load(c_file)
    if (context is not None and 'startgg' in context):
        if ('players' in context):
            leftNames = " + ".join([player['name'] + " ⟮" + ", ".join(player['characters']) + "⟯" for player in context['players']['entrant1']])
            rightNames = " + ".join([player['name'] + " ⟮" + ", ".join(player['characters']) + "⟯" for player in context['players']['entrant2']])
        else:
            leftNames = ", ".join(context['scores'][0]['slots'][0]['displayNames'])
            rightNames = ", ".join(context['scores'][0]['slots'][1]['displayNames'])
        phase = context['startgg']['phase']['name']
        round = context['startgg']['set']['fullRoundText']
        tournament = context['startgg']['tournament']['name']
        output_file_name = sanitize_filename(f"""{leftNames} vs {rightNames} — {phase} {round} — {tournament}""") if context['startgg']['phase']['hasSiblings'] else sanitize_filename(f"""{leftNames} vs {rightNames} — {round} — {tournament}""")
    else:
        output_file_name = in_dir.stem
    name = f"""{out_dir.joinpath(output_file_name)}.mp4"""
    if len(slps) > 0 and not os.path.exists(name):
        outputs[name] = slps
    
    # Process .zip files recursively
    zip_metas = []
    for zip_file in in_dir.glob("*.zip"):
        zip_meta = {}
        zip_meta['extraction_dir'] = in_dir / zip_file.stem
        zip_meta['extraction_dir'].mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_file, 'r') as z:
            z.extractall(zip_meta['extraction_dir'])
        try:
            c = open(zip_meta['extraction_dir'] / "context.json")
        except FileNotFoundError:
            print(f"zip without context.json: {zip_file.name}")
        else:
            with c:
                zip_meta['context'] = json.load(c)
            zip_metas.append(zip_meta)

    for zip_meta in sorted(zip_metas, key=cmp_to_key(_compare_context)):
        zip_dirs.append(zip_meta['extraction_dir'])
        outputs.update(_get_inputs_and_outputs(zip_meta['extraction_dir'], out_dir, zip_dirs))

    # Procecss subdirs recursively exclude zip extraction dirs
    zip_dirs_list = [zip_meta['extraction_dir'] for zip_meta in zip_metas]
    zip_dirs_set = set(zip_dirs_list)
    for child in in_dir.iterdir():
        if child.is_dir() and child not in zip_dirs_set:
            outputs = outputs | _get_inputs_and_outputs(child, out_dir / child.stem, zip_dirs)
    
    return outputs


def _render(conf, args, slp_queue: multiprocessing.Queue, video_queue: multiprocessing.Queue):
    while True:
        data = slp_queue.get()
        if data is None:
            break
        key, path = data
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        if not args.dry_run:
            if not video.render(conf, path, pathlib.Path(tmp.name)):
                print(f"failed to render {path} for {key}")
                tmp.close()
                video_queue.put((key, {path: ""}))
                continue
        tmp.close()
        video_queue.put((key, {path: tmp.name}))

def _cleanup(tmpfiles: list[str]):
    for tmp in tmpfiles:
        if tmp:
            os.unlink(tmp)

def _concat(conf, args, video_queue: multiprocessing.Queue, inputs_and_outputs: dict):
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
        failed = False
        for tmp in tmpfiles:
            if not tmp:
                print(f"failed to create {key}", file=sys.stderr)
                _cleanup(tmpfiles)
                failed = True
                break
        if failed:
            continue

        output_file = key
        print(f"files to concat: {tmpfiles}")
        if not args.dry_run:
            Ffmpeg.concat_videos([pathlib.Path(t) for t in tmpfiles], output_file)
        _cleanup(tmpfiles)


def run(conf, args):
    path = args.path
    output_directory = args.output_directory
    if not args.dry_run:
        os.makedirs(output_directory, exist_ok=True)
    zip_dirs = []
    inputs_and_outputs = _get_inputs_and_outputs(path, output_directory, zip_dirs)

    parallel = conf["runtime"]["parallel"] or os.cpu_count() or 1
    slp_queue = multiprocessing.Queue()
    video_queue = multiprocessing.Queue()

    slp_pool = multiprocessing.Pool(
        parallel,
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

    for i in range(parallel):
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

    for zip_dir in zip_dirs:
        shutil.rmtree(zip_dir, ignore_errors=True)

    return [(out, inputs) for out, inputs in inputs_and_outputs.items()]


def register(subparser):
    parser = subparser.add_parser(
        "directory",
        help="render and combine .slp files in a directory to a video, recursively",
    )
    parser.add_argument("path", type=pathlib.Path)
    parser.set_defaults(run=run)
