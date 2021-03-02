import sys
import os
from typing import Any, Optional, Text, Tuple
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))

def import_module_from_source(path: Text, name: Text) -> Any:

    # importlib.util.module_from_spec is supported from Python3.5
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 5):
        import imp
        module = imp.load_source(name, path)
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        loader = spec.loader
        if loader is None:
            return None
        loader.exec_module(module)  # type: ignore  # FIXME: typeshed issue?

    return module

def import_module_by_name(name: Text) -> Any:
    import importlib
    try:
        return importlib.import_module(name)
    except ImportError:
        return None

def resolve_bot_path(name: Text) -> Optional[Tuple[Path, Text]]:
    if os.path.isfile(name):
        bot_path = Path(name)
        bot_name = Path(bot_path).stem
        return (bot_path, bot_name)
    else:
        bot_name = name
        bot_path = Path(current_dir, 'bots', bot_name, bot_name + '.py')
        if os.path.isfile(bot_path):
            return (bot_path, bot_name)

    return None
