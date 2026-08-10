"""Config schema, defaults, and JSON load/save for the Wingspan automation app."""

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json

import platformdirs

APP_NAME = "WingspanAutomation"

CONFIG_DIR = Path(platformdirs.user_config_dir(APP_NAME))
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.json"

LOG_DIR = Path(platformdirs.user_log_dir(APP_NAME))
LOG_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_PATH = LOG_DIR / "wingspan_automation.log"

# Kept relative to the project directory rather than user config, since they're
# just working directories for this run, not user-editable settings.
SCREENSHOT_DIR = "screenshots"
BIRD_JSON = "birds.json"

SCHEMA_VERSION = 1


@dataclass
class WindowConfig:
    x_offset: int
    y_offset: int
    width: int
    height: int
    dead_height: int


@dataclass
class ButtonConfig:
    x: float
    y: float
    delay: float


@dataclass
class RegionConfig:
    name: str
    x: float
    y: float
    w: float
    h: float
    color: tuple[int, int, int]


@dataclass
class TunablesConfig:
    screenshots_to_keep: int
    bird_match_minimum_ratio: float
    window_ready_delay: float
    grid_spacing_px: int


@dataclass
class RunOptions:
    automa: bool
    continue_on_match: bool


@dataclass
class AppConfig:
    window: WindowConfig
    buttons: dict[str, ButtonConfig]
    starting_birds: list[RegionConfig]
    tray_birds: list[RegionConfig]
    eor_goals: list[RegionConfig]
    bird_points: dict[str, int]
    no_goal_points: int
    point_threshold: int
    tunables: TunablesConfig
    alert_sound_macos: str
    alert_sound_windows: str | None
    run_options: RunOptions

    @classmethod
    def default(cls) -> "AppConfig":
        """Reproduces the exact values that were hardcoded in wingspan_automation.py."""
        window_w = 1280
        window_h = 828
        dead_height = 30
        button_h = window_h + dead_height  # buttons were calibrated against this taller reference

        def button(x_px, y_px, delay):
            return ButtonConfig(x=x_px / window_w, y=y_px / button_h, delay=delay)

        def region(name, x_px, y_px, w_px, h_px, color):
            return RegionConfig(name=name, x=x_px / window_w, y=y_px / window_h,
                                 w=w_px / window_w, h=h_px / window_h, color=color)

        return cls(
            window=WindowConfig(x_offset=6, y_offset=43, width=window_w, height=window_h,
                                 dead_height=dead_height),
            buttons={
                'settingsButton': button(56, 110, 0.6),
                'menuButton': button(634, 545, 2.0),
                'playButton': button(345, 465, 0.4),
                'customGameButton': button(328, 688, 0.4),
                'automaButton': button(630, 688, 0.4),
                'forwardArrowButton': button(1198, 844, 6.0),
                'forwardArrowButtonShort': button(1198, 844, 0.5),
                'middleButton': button(640, 510, 0.2),
                'wetlandHabitatButton': button(60, 600, 0.4),
                'firstBird': button(316, 400, 0.3),
                'secondBird': button(480, 400, 0.3),
                'thirdBird': button(630, 400, 0.3),
                'fourthBird': button(790, 400, 0.3),
                'fifthBird': button(950, 400, 0.3),
                'firstBonusCard': button(510, 400, 0.3),
                'secondBonusCard': button(740, 400, 0.3),
            },
            starting_birds=[
                region('bird 1', 260, 265, 104, 44, (255, 0, 0)),
                region('bird 2', 436, 265, 104, 44, (0, 255, 0)),
                region('bird 3', 590, 265, 104, 44, (0, 0, 255)),
                region('bird 4', 744, 265, 104, 44, (255, 255, 0)),
                region('bird 5', 911, 265, 104, 44, (255, 0, 255)),
            ],
            tray_birds=[
                region('tray bird 1', 700, 580, 104, 44, (255, 0, 0)),
                region('tray bird 2', 833, 580, 104, 44, (0, 255, 0)),
                region('tray bird 3', 970, 580, 104, 44, (0, 0, 255)),
            ],
            eor_goals=[
                region('eor1', 995, 62, 60, 65, (0, 255, 255)),
                region('eor2', 1061, 45, 60, 65, (255, 128, 0)),
                region('eor3', 1124, 45, 60, 65, (128, 0, 255)),
                region('eor4', 1185, 45, 60, 65, (255, 128, 128)),
            ],
            bird_points={
                "Canvasback": 2,
                "Savi's Warbler": 2,
                "Northern Shoveler": 2,
                "Purple Gallinule": 2,
                "Spotted Sandpiper": 2,
                "Wilson's Snipe": 2,
                "Kelp Gull": 1,
                "Brolga": 1,
                "Dorian's Jackdaw": 1,
                "Nightingale": 1,
                "Green Pheasant": 1,
                "Gray Catbird": 1,
                "Northern Mockingbird": 1,
                "Bluethroat": 1,
            },
            no_goal_points=100,
            point_threshold=103,
            tunables=TunablesConfig(
                screenshots_to_keep=3,
                bird_match_minimum_ratio=0.6,
                window_ready_delay=0.2,
                grid_spacing_px=100,
            ),
            alert_sound_macos='/System/Library/Sounds/Glass.aiff',
            alert_sound_windows=None,
            run_options=RunOptions(automa=True, continue_on_match=True),
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data['schema_version'] = SCHEMA_VERSION
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        return cls(
            window=WindowConfig(**data['window']),
            buttons={name: ButtonConfig(**b) for name, b in data['buttons'].items()},
            starting_birds=[RegionConfig(**r) for r in data['starting_birds']],
            tray_birds=[RegionConfig(**r) for r in data['tray_birds']],
            eor_goals=[RegionConfig(**r) for r in data['eor_goals']],
            bird_points=data['bird_points'],
            no_goal_points=data['no_goal_points'],
            point_threshold=data['point_threshold'],
            tunables=TunablesConfig(**data['tunables']),
            alert_sound_macos=data['alert_sound_macos'],
            alert_sound_windows=data.get('alert_sound_windows'),
            run_options=RunOptions(**data['run_options']),
        )

    def save(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG_PATH) -> "AppConfig":
        if not path.exists():
            cfg = cls.default()
            cfg.save(path)
            return cfg
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
