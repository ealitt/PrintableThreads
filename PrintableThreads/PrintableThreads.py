"""Fusion entry points; toolbar events stay on Fusion's main thread."""
from . import commands
from .model import spec,preferences,target,solid
from .geometry import profile, backend, preview as preview_mesh
from .fusion_backend import ownership, selection, native, preview as preview_graphics
import adsk.core
import importlib
from pathlib import Path
import traceback

def run(context):
    try:
        commands.stop()
        for module in (spec,preferences,target,solid,profile,backend,preview_mesh,ownership,selection,native,preview_graphics):
            # Read source directly: Fusion can retain modules and bytecode after updates.
            exec(compile(Path(module.__file__).read_text(),module.__file__,'exec'),module.__dict__)
        exec(compile(Path(commands.__file__).read_text(),commands.__file__,'exec'),commands.__dict__)
        commands.start()
    except Exception:
        commands.stop()
        adsk.core.Application.get().userInterface.messageBox(traceback.format_exc(),'Printable Threads could not load')

def stop(context):
    commands.stop()
