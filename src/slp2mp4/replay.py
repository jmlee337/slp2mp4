# Logic for interacting with a single slippi replay file

import dataclasses
import pathlib

import peppi_py

_READY_GO_FRAMES = 124
_END_SCREEN_FRAMES = 114


@dataclasses.dataclass
class ReplayFile:
    slp_path: pathlib.Path
    slp_data: peppi_py.Game = dataclasses.field(init=False)

    def __post_init__(self):
        if not self.slp_path.exists():
            raise FileNotFoundError(f"slp not found: {self.slp_path}")
        try:
            self.slp_data = peppi_py.read_slippi(str(self.slp_path), skip_frames=True)
        except Exception as e:
            print(f"failed to parse {self.slp_path}:")
            print(e)
            raise

    def get_slp_filename(self):
        return str(self.slp_path.absolute())

    def get_expected_number_of_frames(self):
        gameplay_frames = _READY_GO_FRAMES + self.slp_data.metadata["lastFrame"]
        end_frames = (
            _END_SCREEN_FRAMES if (self.slp_data.end.lras_initiator is None) else 0
        )
        return gameplay_frames + end_frames
