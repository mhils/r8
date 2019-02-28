# We must import all submodules here so that they are loaded and plugins are registered.
from . import (
    basic,
    form_example,
    from_folder,
)
__all__ = [
    "basic",
    "form_example",
    "from_folder",
]
