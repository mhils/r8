import abc
import asyncio
import functools
import inspect
import re
import time
import traceback
from pathlib import Path
from typing import Dict, Optional, Type, List, Set, Tuple, Union

import pkg_resources
from aiohttp import web

import r8


class Challenge:
    def __init_subclass__(cls, **kwargs):
        challenges.add_class(cls)  # register challenge plugin

    id: str
    """The challenge id, sometimes referred to as cid."""

    static_dir: Optional[Path] = None
    """Folder to serve static files from"""

    def __init__(self, cid: str) -> None:
        self.id = cid
        if not self.static_dir:
            self.static_dir = Path(inspect.getfile(type(self))).parent.absolute() / "static"

    # Overridable methods.
    @property
    @abc.abstractmethod
    def title(self) -> str:
        """The challenge name visible to the user."""
        pass

    async def description(self, user: str, solved: bool) -> str:
        """
        Challenge description visible to the user. Supports full HTML.
        There is no additional security layer, XSS is entirely possible.
        """
        return ""

    async def start(self) -> None:
        """Start the challenge, e.g. by starting a server."""
        pass

    async def stop(self) -> None:
        """Stop the challenge; we are shutting down or the challenge time is up."""
        pass

    async def visible(self, user: str) -> bool:
        """Determine if the challenge is visible for a given user."""
        return True

    def api_url(self, user: str, path: str) -> str:
        if path and not path.startswith("/"):
            path = "/" + path
        return r8.util.url_for(user, f"/api/challenges/{self.id}{path}")

    async def handle_get_request(self, user: str, request: web.Request) -> Union[str, web.StreamResponse]:
        """GET Requests to /api/challenges/cid land here."""
        if self.static_dir:
            filename = re.sub(
                "[^a-zA-Z0-9_.]",
                "",
                request.match_info["path"]
            )
            filepath = self.static_dir / filename
            if filepath.is_file():
                return web.FileResponse(filepath)
        return web.HTTPNotFound()

    async def handle_post_request(self, user: str, request: web.Request) -> Union[str, web.StreamResponse]:
        """POST Requests to /api/challenges/cid land here."""
        return web.HTTPNotFound()

    # Utility methods
    def log_and_create_flag(
        self,
        ip: r8.util.THasIP,
        user: Optional[str] = None,
        *,
        max_submissions: int = 1,
        flag: Optional[str] = None,
        challenge: Optional[str] = None,
    ) -> str:
        """
        Create a new flag that can be redeemed for this challenge and log its creation.

        If the challenge is currently inactive, an error message will be returned instead.

        If flag creation should not be logged (e.g. because it's done by the challenge
        automatically on startup), use r8.util.create_flag directly.
        """
        if not self.active:
            self.log(ip, "flag-inactive", uid=user)
            return "__flag__{challenge inactive}"

        if not challenge:
            challenge = self.id

        flag = r8.util.create_flag(challenge, max_submissions, flag)
        r8.log(ip, "flag-create", flag, uid=user, cid=challenge)
        return flag

    @property
    def active(self) -> bool:
        t_start, t_stop = self._active_times()
        return t_start <= time.time() <= t_stop

    @functools.lru_cache()
    def _active_times(self) -> Tuple[int, int]:
        with r8.db:
            return r8.db.execute("""
                SELECT CAST(strftime('%s', t_start) AS INT), CAST(strftime('%s', t_stop) AS INT) FROM challenges WHERE cid = ?
            """, (self.id,)).fetchone()

    def log(
        self,
        ip: r8.util.THasIP,
        type: str,
        data: Optional[str] = None,
        *,
        uid: Optional[str] = None
    ) -> None:
        """Log an event for the current challenge."""
        r8.log(ip, type, data, uid=uid, cid=self.id)

    def echo(self, message: str) -> None:
        """Print to console with the challenge's namespace added in front."""
        r8.echo(self.id, message)

    @property
    def args(self) -> str:
        """
        The raw string passed to the challenge as an argument between parentheses.
        For example, given a cid of "Challenge(foo bar)", .args would be "foo bar".
        """
        if "(" in self.id:
            return self.id.split("(", 1)[1].rsplit(")", 1)[0]
        else:
            return ""

    def get_data(self, key: str) -> Optional[str]:
        """
        Get persistent challenge data for a specific key.
        """
        # Could be extended to support key: Optional[str] and then return a list.
        with r8.db:
            return (r8.db.execute("""
                SELECT value FROM data WHERE cid = ? AND key = ?
            """, (self.id, key)).fetchone() or [None])[0]

    def set_data(self, key: str, value: str):
        """
        Set persistent challenge data for a specific key.
        """
        with r8.db:
            r8.db.execute(
                """INSERT OR REPLACE INTO data (cid, key, value) VALUES (?,?,?)""",
                (self.id, key, value)
            )


def get_challenges() -> List[str]:
    with r8.db:
        cursor = r8.db.execute("SELECT cid FROM challenges")
    return [row[0] for row in cursor.fetchall()]


def get_active_challenges() -> Set[str]:
    with r8.db:
        cursor = r8.db.execute(
            "SELECT cid FROM challenges WHERE datetime('now') BETWEEN t_start AND t_stop"
        )
    return {row[0] for row in cursor.fetchall()}


def class_name(cid: str) -> str:
    return cid.split("(", 1)[0]


class _Challenges:
    _classes: Dict[str, Type[Challenge]]
    """All challenges that have been loaded."""
    _instances: Dict[str, Challenge]
    """All challenge instances"""

    def __init__(self):
        self._classes = {}
        self._instances = {}

    def load(self):
        r8.echo("r8", "Loading challenges...")
        for entry_point in pkg_resources.iter_entry_points('r8.challenges'):
            entry_point.load()
        r8.echo("r8", f"Challenges loaded: {', '.join(self._classes)}")

        for cid in get_challenges():
            self._instances[cid] = self.make_instance(cid)

    def add_class(self, cls: Type[Challenge]) -> None:
        """Called by Challenge.__init_subclass__"""
        assert cls.__name__ not in self._classes
        self._classes[cls.__name__] = cls

    def make_instance(self, cid: str) -> Challenge:
        try:
            cls = self._classes[class_name(cid)]
        except KeyError:
            raise RuntimeError(f"Challenge definition not found: {class_name(cid)}")
        else:
            return cls(cid)

    def __getitem__(self, item):
        return self._instances[item]

    def __contains__(self, item):
        return item in self._instances

    async def start(self):
        await asyncio.gather(*[
            self._start(cid) for cid in self._instances
        ])

    async def _start(self, cid: str) -> None:
        inst = self[cid]
        if type(inst).start is not Challenge.start:
            r8.echo(cid, "Starting...")

        try:
            await inst.start()
        except Exception:
            r8.echo(cid, "Error on start.", err=True)
            traceback.print_exc()
            # if start failed, don't bother with stop.
            inst.stop = asyncio.coroutine(lambda: None)

    async def stop(self):
        await asyncio.gather(*[
            self._stop(cid) for cid in self._instances
        ])

    async def _stop(self, cid: str) -> None:
        inst = self[cid]
        try:
            await inst.stop()
        except Exception:
            r8.echo(cid, f"Error on stop.", err=True)
            traceback.print_exc()
        else:
            if type(inst).stop is not Challenge.stop:
                r8.echo(cid, "Stopped.")


challenges = _Challenges()
"""singleton object that tracks and manages all challenges."""
