import abc
import asyncio
import functools
import inspect
import json
import time
import traceback
from pathlib import Path
from typing import Any, ClassVar, Optional, Union

import pkg_resources
from aiohttp import web

import r8


class Challenge:
    id: str
    """The challenge id, sometimes referred to as cid."""

    static_dir: Optional[Path] = None
    """
    Directory that includes static files for the challenge.
    Will be served from :meth:`handle_get_request`.
    """

    tags: ClassVar[list[str]] = []
    """Tags for the challenge. This can be used to signal task category of difficulty."""

    flag: ClassVar[str] = None
    """If set, a static flag with the given value will be created on startup."""

    points: Optional[int] = None
    """Number of (hardcoded) points awarded for this challenge."""

    def __init__(self, cid: str) -> None:
        self.id = cid
        if self.static_dir is None:
            self.static_dir = Path(inspect.getfile(type(self))).parent.absolute() / "static"
        if self.flag:
            r8.util.create_flag(self.id, 999999, self.flag)

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

    async def visible(self, user: str) -> bool:
        """
        Determine if the challenge is visible for a given user.
        Defaults to `True`.
        """
        return True

    @property
    def active(self) -> bool:
        """`True` if the challenge is currently active, `False` otherwise (read-only)."""
        t_start, t_stop = self._active_times()
        return t_start <= time.time() <= t_stop

    @functools.lru_cache(maxsize=None)
    def _active_times(self) -> tuple[int, int]:
        with r8.db:
            return r8.db.execute("""
                SELECT CAST(strftime('%s', t_start) AS INT), CAST(strftime('%s', t_stop) AS INT) FROM challenges WHERE cid = ?
            """, (self.id,)).fetchone()

    @property
    def args(self) -> str:
        """
        The raw string passed to the challenge as an argument between parentheses.
        For example, given a cid of `"Challenge(foo bar)"`, this would be `"foo bar"`.
        """
        if "(" in self.id:
            return self.id.split("(", 1)[1].rsplit(")", 1)[0]
        else:
            return ""

    async def start(self) -> None:
        """
        Called when the challenge is started,
        can be used to start additional services for example.

        Note that challenge instances are always started immediately when running r8,
        independent of when the challenge will be active. This makes sure that there
        are no surprising startup errors.
        """
        pass

    async def stop(self) -> None:
        """
        Called when the challenge is stopped.

        Note that challenge instances will not be stopped on the challenge deadline,
        only flag generation and submission will be halted. This allows in-class
        demonstrations after the deadline.
        """
        pass

    def echo(self, message: str, err: bool = False) -> None:
        """Print to console with the challenge's namespace added in front."""
        r8.echo(self.id, message, err)

    def log(
            self,
            ip: r8.util.THasIP,
            type: str,
            data: Optional[str] = None,
            *,
            uid: Optional[str] = None
    ) -> None:
        """
        Log an event for the current challenge.
        See :func:`r8.log`.
        """
        r8.log(ip, type, data, uid=uid, cid=self.id)

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

        If the challenge is currently inactive, `__flag__{challenge inactive}` will be returned instead.

        If flag creation should not be logged (e.g. because it's done by the challenge
        automatically on startup), use :func:`r8.util.create_flag` directly.

        Args:
            ip: IP address which caused this flag to be created. Used for logging only.
            user: User who caused this flag to be created. Used for logging only.
            challenge: If given, override the challenge for which this flag is valid.
        """
        if not self.active:
            self.log(ip, "flag-inactive", uid=user)
            return "__flag__{challenge inactive}"

        if not challenge:
            challenge = self.id

        flag = r8.util.create_flag(challenge, max_submissions, flag)
        r8.log(ip, "flag-create", flag, uid=user, cid=challenge)
        return flag

    def api_url(self, path: str, absolute: bool = False, user: Optional[str] = None) -> str:
        """
        Construct a URL pointing to this challenge's API.

        Args:
            path: The request path relative to the API endpoint.
            absolute: If True, an absolute URL is constructed.
            user: If given, an authentication token will be included in the URL, making it possible to access the resource without additional authentication.
        """
        if not isinstance(absolute, bool):
            raise RuntimeError("api_url signature has changed.")
        if path and not path.startswith("/"):
            path = "/" + path  # don't use .lstrip() to make sure that "" returns in no trailing "/"
        return r8.util.url_for(f"/api/challenges/{self.id}{path}", absolute, user)

    async def handle_get_request(self, user: str, request: web.Request) -> Union[
        str, web.StreamResponse]:
        """
        HTTP GET requests to `/api/challenges/cid/*` land here.
        Serves static resources from :attr:`static_dir` by default.

        The request path can be accessed using `request.match_info["path"]`.
        """
        if self.static_dir:
            return r8.util.serve_static(self.static_dir, request.match_info["path"])
        else:
            return web.HTTPNotFound()

    async def handle_post_request(self, user: str, request: web.Request) \
            -> Union[str, web.StreamResponse]:
        """
        HTTP POST requests to `/api/challenges/cid/*` land here. Serves 404s by default.

        The request path can be accessed using `request.match_info["path"]`.
        """
        return web.HTTPNotFound()

    def get_data(self, key: str, *, cid: Optional[str] = None) -> Any:
        """
        Get persistent challenge data for a specific key.

        Args:
            cid: If given, override the challenge for which data should be accessed.
        """
        with r8.db:
            data = r8.db.execute("""
                SELECT value FROM data WHERE cid = ? AND key = ?
            """, (cid or self.id, key)).fetchone()
            if data:
                return json.loads(data[0])
            else:
                return None

    def set_data(self, key: str, value: Any, *, cid: Optional[str] = None):
        """
        Set persistent challenge data for a specific key.

        Args:
            cid: If given, override the challenge for which data should be modified.
        """
        with r8.db:
            r8.db.execute(
                """INSERT OR REPLACE INTO data (cid, key, value) VALUES (?,?,?)""",
                (cid or self.id, key, json.dumps(value))
            )

    def __init_subclass__(cls, **kwargs):
        challenges.add_class(cls)  # register challenge with r8 on init.


def get_challenges() -> list[str]:
    with r8.db:
        cursor = r8.db.execute("SELECT cid FROM challenges")
        return [row[0] for row in cursor.fetchall()]


def class_name(cid: str) -> str:
    return cid.split("(", 1)[0]


class _Challenges:
    _classes: dict[str, type[Challenge]]
    """All challenges that have been loaded."""
    _instances: dict[str, Challenge]
    """All challenge instances"""

    def __init__(self):
        self._classes = {}
        self._instances = {}

    def load(self):
        r8.echo("r8", "Loading challenges...")
        for entry_point in pkg_resources.iter_entry_points('r8.challenges'):
            entry_point.load()

        for cid in get_challenges():
            self._instances[cid] = self.make_instance(cid)

    def add_class(self, cls: type[Challenge]) -> None:
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
            inst.stop = lambda: asyncio.sleep(0)

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


challenges: _Challenges = _Challenges()
"""singleton object that tracks and manages all challenges."""
