# We must import all submodules here so that they are loaded and plugins are registered.
from . import basic
from . import docker
from . import form_example
from . import from_folder
from . import tcp_server
from . import web_server

__all__ = [
    "basic",
    "docker",
    "form_example",
    "from_folder",
    "tcp_server",
    "web_server",
]
