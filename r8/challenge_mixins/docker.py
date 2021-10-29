import asyncio
import binascii
import re
import secrets
import shlex
import shutil
import time
from pathlib import Path
from typing import ClassVar, Optional

import r8


def docker_tagify(cid: str) -> str:
    """modify a challenge id so that it is an acceptable docker tag"""
    tag = "r8:" + re.sub(r"[^a-zA-Z0-9_.-]", "_", cid)
    if len(tag) > 128:
        tag = tag[:118] + hex(binascii.crc32(tag.encode()))
    return tag


class DockerError(RuntimeError):
    def __init__(self, reason, cmd=None, proc=None, stdout=None, stderr=None):
        super().__init__(reason)
        self.cmd = cmd
        self.proc = proc
        self.stdout = stdout
        self.stderr = stderr


class DockerChallenge(r8.Challenge):
    """Support for `docker run` in challenges"""
    dockerfile: ClassVar[Optional[Path]] = None
    docker_tag: ClassVar[Optional[str]] = None
    docker_args: tuple[str, ...] = (
        "--network", "none",
        #  --memory and --memory-swap are set to the same value, this prevents containers from using any swap.
        "--memory", "512m",
        "--memory-swap", "512m",
        "--kernel-memory", "128m",
        "--cpu-shares", "2",
        "--blkio-weight", "10",
        "--cap-drop", "all",
        "--user", "nobody",
    )
    docker_started: bool = False

    max_concurrent: ClassVar[asyncio.Semaphore] = asyncio.Semaphore(r8.settings.get("docker_max_concurrent", 5))
    timeout = r8.settings.get("docker_timeout", 10)
    debug = r8.settings.get("docker_debug", False)
    active_users: ClassVar[set[str]] = set()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.dockerfile and not self.docker_tag:
            raise RuntimeError(f"No dockerfile or docker tag attribute for {type(self).__name__}.")
        if not self.docker_tag:
            self.docker_tag = docker_tagify(self.id)

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

    async def _exec(self, *cmd) -> tuple[asyncio.subprocess.Process, bytes, bytes]:
        spin = asyncio.ensure_future(self.spin())
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
        except ValueError as e:
            raise DockerError(str(e), cmd) from e
        finally:
            spin.cancel()
        if self.debug:
            self.echo(
                f"\"{' '.join(shlex.quote(x) for x in cmd)}\" returned {proc.returncode}:" +
                (f"\n[stdout]\n{stdout.decode()}" if stdout else "") +
                (f"\n[stderr]\n{stderr.decode()}" if stderr else ""),
                err=True
            )
        if proc.returncode != 0:
            err = (
                f"Execution error (return code: {proc.returncode})\n"
                f"[command]\n"
                f"{shlex.join(cmd)}"
            )
            if stdout:
                err += (
                    f"\n[stdout]"
                    f"\n{stdout.decode(errors='backslashreplace').strip()}"
                )
            if stderr:
                err += (
                    f"\n[stderr]"
                    f"\n{stderr.decode(errors='backslashreplace').strip()}"
                )
            raise DockerError(err)
        return proc, stdout, stderr

    async def start(self):
        await super().start()
        if self.dockerfile:
            if shutil.which("docker") is None:
                self.echo("Docker not installed. Cannot build challenge.", err=True)
                return
            self.echo(f"Docker: Building {self.docker_tag}...")
            await self._exec(
                "docker", "build",
                "-t", self.docker_tag,
                str(self.dockerfile.absolute())
            )
            self.echo(f"Docker: {self.docker_tag} built.")
        else:
            _, stdout, _ = await self._exec("docker", "images", "-q", self.docker_tag)
            if not stdout:
                self.echo(f"Docker: Pulling {self.docker_tag}...")
                await self._exec("docker", "pull", self.docker_tag)
                self.echo(f"Docker: {self.docker_tag} pulled.")
        await self._exec("docker", "inspect", self.docker_tag)
        self.docker_started = True

    async def docker_run_unlimited(self, *args) -> str:
        """`docker run` without rate limits"""
        if not self.docker_started:
            raise DockerError("Docker service not started.")
        self.echo(f"Docker: run {' '.join(args)}")
        name = "r8_" + secrets.token_hex(8)
        start = time.time()

        cmd = [
            "docker", "run",
            "--rm",
            "--name", name,
            *self.docker_args,
            self.docker_tag,
            *args
        ]

        try:
            proc, stdout, stderr = await asyncio.wait_for(
                self._exec(*cmd),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            self.echo(f"Docker: Timeout. Killing...")
            try:
                await self._exec("docker", "kill", name)
            except DockerError as e:
                not_running = (
                    "No such container" in str(e)
                    or
                    "is not running" in str(e)
                )
                if not_running:
                    pass
                else:
                    self.echo(str(e), err=True)
                    raise
            else:
                self.echo(f"Docker: Killed.")
            raise DockerError("Process timed out.", cmd)
        else:
            self.echo(f"Docker: finished (time elapsed: {round(time.time() - start, 2)}s)")
            return stdout.strip().decode()

    async def docker_run(self, user: str, *args) -> str:
        if user in self.active_users:
            raise DockerError("Please wait for your previous request to complete.")
        else:
            self.active_users.add(user)
            try:
                async with self.max_concurrent:
                    return await self.docker_run_unlimited(*args)
            finally:
                self.active_users.remove(user)
