# Handles configuration options

import dataclasses
import pathlib
import tomllib
import typing
import importlib.resources

import slp2mp4
import slp2mp4.util as util

DEFAULT_CONFIG_FILE = importlib.resources.files(slp2mp4).joinpath("defaults.toml")
USER_CONFIG_FILE = pathlib.Path(".slp2mp4.toml").expanduser()


def _path(p):
    return pathlib.Path(p).expanduser()

def _parse_parallel(p):
    return 0 if (not isinstance(p, int) or p < 0) else p


CONSTRUCTORS = {
    "paths": {
        "ffmpeg": _path,
        "slippi_playback": _path,
        "ssbm_ini": _path,
    },
    "video": {
        "resolution": str,
        "bitrate": str,
        "backend": str,
    },
    "runtime": {
        "parallel": _parse_parallel,
    },
}


def _apply_constructors(conf: dict, constructors: dict):
    for k, constructor in constructors.items():
        if isinstance(constructor, typing.Callable):
            conf[k] = constructor(conf[k])
        elif isinstance(constructor, dict):
            _apply_constructors(conf[k], constructor)


def _load_configs(config_files: list[pathlib.Path]) -> dict:
    # TODO: Try open; skip if not found
    conf = {}
    for file in config_files:
        with open(file, "rb") as f:
            data = tomllib.load(f)
            util.update_dict(conf, data)
    _apply_constructors(conf, CONSTRUCTORS)
    return conf


def get_config():
    return _load_configs([DEFAULT_CONFIG_FILE, USER_CONFIG_FILE])
