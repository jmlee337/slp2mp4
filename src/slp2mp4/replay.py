# Logic for interacting with a single slippi replay file

import dataclasses
import pathlib

_READY_GO_FRAMES = 124
_END_SCREEN_FRAMES = 114


@dataclasses.dataclass
class ReplayFile:
    slp_path: pathlib.Path

    def __post_init__(self):
        if not self.slp_path.exists():
            raise FileNotFoundError(f"slp not found: {self.slp_path}")

    def get_slp_filename(self):
        return str(self.slp_path.absolute())
