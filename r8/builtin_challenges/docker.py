import asyncio
import binascii
import re
import shlex
import secrets
import time
from pathlib import Path
from typing import ClassVar, Optional, Tuple

from aiohttp import web

import r8


def tagify(cid: str) -> str:
    """modify a challenge id so that it is an acceptable docker tag"""
    tag = "r8:" + re.sub(r"[^a-zA-Z0-9_.-]", "_", cid)
    if len(tag) > 128:
        tag = tag[:118] + hex(binascii.crc32(tag.encode()))
    return tag


class DockerChallenge(r8.Challenge):
    dockerfile: ClassVar[Optional[Path]] = None
    docker_tag: ClassVar[Optional[str]] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.dockerfile and not self.docker_tag:
            raise RuntimeError(f"No dockerfile or docker tag attribute for {type(self).__name__}.")
        if not self.docker_tag:
            self.docker_tag = tagify(self.id)

    async def spin(self):
        """progress indicator when building images"""
        try:
            while True:
                await asyncio.sleep(1)
                self.echo("/")
                await asyncio.sleep(1)
                self.echo("-")
                await asyncio.sleep(1)
                self.echo("\\")
                await asyncio.sleep(1)
                self.echo("-")
        except asyncio.CancelledError:
            pass

    async def _exec(self, *cmd) -> Tuple[asyncio.subprocess.Process, bytes, bytes]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"\"{' '.join(shlex.quote(x) for x in cmd)}\" returned {proc.returncode}:\n"
                f"[stdout]\n{stdout.decode()}\n"
                f"[stderr]\n{stderr.decode()}\n"
            )
        return proc, stdout, stderr

    async def start(self):
        if self.dockerfile:
            self.echo(f"Docker: Building {self.docker_tag}...")
            spin = asyncio.ensure_future(self.spin())
            await self._exec("docker", "build", "-t", self.docker_tag,
                             str(self.dockerfile.absolute()))
            spin.cancel()
            self.echo(f"Docker: {self.docker_tag} built.")
        await self._exec("docker", "inspect", self.docker_tag)

    async def docker_run(self, *args) -> str:
        self.echo(f"Docker: run {' '.join(args)}")
        name = "r8_" + secrets.token_hex(8)
        spin = asyncio.ensure_future(self.spin())
        start = time.time()
        try:
            proc, stdout, stderr = await asyncio.wait_for(self._exec(
                "docker", "run",
                "--rm",
                "--name", name,
                "--memory", "256m",
                "--memory-swap", "256m",
                "--kernel-memory", "128m",
                "--cpu-shares", "2",
                "--blkio-weight", "10",
                "--cap-drop", "all",
                self.docker_tag, *args),
                timeout=10
            )
        except asyncio.TimeoutError:
            self.echo(f"Docker: Timeout. Killing...")
            try:
                await self._exec("docker", "kill", name)
            except RuntimeError as e:
                if "No such container" not in str(e):
                    self.echo(str(e), err=True)
                    raise
            else:
                self.echo(f"Docker: Killed.")
            raise RuntimeError("Process timed out.")
        else:
            self.echo(f"Docker: finished (time elapsed: {round(time.time() - start, 2)}s)")
            return stdout.decode()
        finally:
            spin.cancel()


class DockerHelloWorld(DockerChallenge):
    title = "Hello World from Docker!"

    dockerfile = Path(__file__).parent / "docker-helloworld"

    async def description(self, user: str, solved: bool):
        return r8.util.media(
            None,
            r8.util.challenge_invoke_button(self.id, "docker run")
        )

    async def handle_post_request(self, user: str, request: web.Request):
        return web.json_response({
            "message": await self.docker_run("python", "-c", "raise RuntimeError()")
        })
