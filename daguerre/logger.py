import logging
import time
from pathlib import Path
import xdg.BaseDirectory


def set_up_logger(program):
    data_path = xdg.BaseDirectory.save_data_path(program)
    log_path = Path(data_path,
                    "log",
                    "%s_%s.log" % (time.strftime("%Y-%m-%d_%Hh%M"), program))
    if not log_path.parent.exists():
        log_path.parent.mkdir(parents=True)
    log = logging.getLogger(program)
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    log.addHandler(ch)

    fh = logging.FileHandler(log_path.as_posix())
    fh.setLevel(logging.DEBUG)
    log.addHandler(fh)
    return log


logger = set_up_logger("daguerre")
