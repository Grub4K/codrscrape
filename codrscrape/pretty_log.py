import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Colorscheme:
    time: str = "\x1b[30;1m"
    levels: dict[int, str] = field(
        default_factory=lambda: {
            logging.DEBUG: "\x1b[96;1m",
            logging.INFO: "\x1b[34;1m",
            logging.WARNING: "\x1b[33;1m",
            logging.ERROR: "\x1b[31m",
            logging.CRITICAL: "\x1b[41m",
        },
    )
    name: str = "\x1b[35m"
    traceback: str = "\x1b[31m"
    reset: str = "\x1b[0m"

    def get_colors(self, levelno, /):
        return dict(
            time=self.time,
            name=self.name,
            traceback=self.traceback,
            reset=self.reset,
            level=self.levels.get(levelno, ""),
        )


class PrettyFormatter(logging.Formatter):
    LOG_FORMAT = " | ".join(
        [
            "{color[time]}{asctime}{color[reset]}",
            "{color[level]}{levelname:<8}{color[reset]}",
            "{color[name]}{name:<{name_length}}{color[reset]}",
            "{message}",
        ]
    )
    NO_COLOR = defaultdict(str)

    def __init__(
        self,
        /,
        *,
        name_length: int = 20,
        use_color: bool = True,
        colorscheme: Colorscheme | None = None,
    ):
        super().__init__(self.LOG_FORMAT, style="{")

        self.colorscheme = Colorscheme() if colorscheme is None else colorscheme

        self.use_color = use_color
        self.name_length = name_length

    def format(self, /, record: logging.LogRecord) -> str:
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        record.message = record.getMessage()

        if self.use_color:
            color = self.colorscheme.get_colors(record.levelno)
        else:
            color = self.NO_COLOR
        output = self.LOG_FORMAT.format(
            **vars(record), color=color, name_length=self.name_length
        )

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            if output[-1:] != "\n":
                output += "\n"
            if self.use_color:
                output += color["traceback"]
            output += record.exc_text
            if self.use_color:
                output += color["reset"]

        if record.stack_info:
            if output[-1:] != "\n":
                output += "\n"
            output += self.formatStack(record.stack_info)

        return output


def setup(
    colorscheme: Colorscheme | None = None,
    *,
    name_length: int = 20,
    file: bool = True,
    stream: bool = False,
    debug: bool = False,
):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    level = logging.DEBUG if debug else logging.INFO

    if not (file or stream):
        file = True

    if file:
        current_name = datetime.now().strftime("logs/%Y-%m-%d_%H-%M-%S.log")
        Path(current_name).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(current_name, mode="a", encoding="utf8")
        file_level = level
        file_handler.setLevel(file_level)
        logger.addHandler(file_handler)

        file_formatter = PrettyFormatter(use_color=False, name_length=name_length)
        file_handler.setFormatter(file_formatter)

    if not stream:
        return

    handler = logging.StreamHandler(sys.stderr)
    stream_level = level if not file else logging.INFO
    handler.setLevel(stream_level)
    logger.addHandler(handler)

    formatter = PrettyFormatter(
        name_length=name_length, use_color=True, colorscheme=colorscheme
    )
    handler.setFormatter(formatter)
