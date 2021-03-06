import importlib
import importlib.abc
import importlib.util
import os
from pathlib import Path
from typing import Any, Optional, Tuple

current_dir = os.path.dirname(os.path.abspath(__file__))


def import_module_from_source(path: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if not isinstance(loader, importlib.abc.Loader):
        return None
    loader.exec_module(module)
    return module


def import_module_by_name(name: str) -> Any:
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def resolve_bot_path(name: str) -> Optional[Tuple[Path, str]]:
    if os.path.isfile(name):
        bot_path = Path(name)
        bot_name = Path(bot_path).stem
        return (bot_path, bot_name)
    else:
        bot_name = name
        bot_path = Path(current_dir, "bots", bot_name, bot_name + ".py")
        if os.path.isfile(bot_path):
            return (bot_path, bot_name)

    return None
