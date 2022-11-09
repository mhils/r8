import functools
import shutil
import time
from math import ceil
from typing import Optional

import click

import r8
from r8 import util

try:
    from wcwidth import wcswidth
except ImportError:
    wcswidth = len


def min_distinguishable_column_width(elements: list[str]) -> int:
    elements = set(elements)
    if not elements:
        return 0

    n = max(len(x) for x in elements)
    while n > 0:
        if len({x[:n] for x in elements}) == len(elements):
            n -= 1
        else:
            break
    return n + 1


def format_untrusted_col(data: Optional[str], width: int) -> str:
    if data:
        data = r8.util.console_escape(data)[:width]
    else:
        data = "-"
    data = data
    while (curr_width := wcswidth(data)) > width:
        chars_to_remove = ceil((curr_width - width) / 2)
        data = data[:-chars_to_remove]
    if curr_width < width:
        return data + (" " * (width - curr_width))
    else:
        return data


@click.command("events")
@util.with_database()
@util.database_rows
@click.option("--watch/--no-watch", default=True)
@click.argument("query", nargs=-1)
def cli(rows, watch, query):
    """
    Live view of events.

    Accepts an optional query argument to filter events,
    e.g. "WHERE type LIKE 'flag%'".
    """
    query = " ".join(query)

    with r8.db:
        seen = max(
            r8.db.execute(f"SELECT COUNT(*) FROM events {query}").fetchone()[0] - rows,
            0,
        )
    while True:
        with r8.db:
            new = r8.db.execute(
                f"""
            SELECT time, ip, type, data, cid, uid
            FROM events
            {query}
            ORDER BY rowid
            LIMIT 100 OFFSET {seen}"""
            ).fetchall()
        seen += len(new)
        for t, ip, type, data, cid, uid in new:
            print(format_event(t, ip, type, data, cid, uid, r8.util.get_team(uid)))
        if not watch:
            break
        time.sleep(0.5)


@functools.cache
def get_widths():
    time_w = 19
    ip_w = 15
    uid_w = min_distinguishable_column_width(r8.util.get_users())
    uid_w = max(10, min(uid_w, 25))
    tid_w = min_distinguishable_column_width(r8.util.get_teams())
    tid_w = max(10, min(tid_w, 25))
    type_w = 20
    with r8.db:
        cids = [x[0] for x in r8.db.execute("SELECT cid FROM challenges").fetchall()]
    cid_w = min_distinguishable_column_width(cids)
    cid_w = max(15, min(cid_w, 25))
    return time_w, ip_w, tid_w, uid_w, type_w, cid_w


def format_event(
    time: str,
    ip: str,
    type: str,
    data: Optional[str],
    cid: Optional[str],
    uid: Optional[str],
    tid: Optional[str],
):
    # TODO: This is messy and could take some refactoring.
    time_w, ip_w, tid_w, uid_w, type_w, cid_w = get_widths()
    time = time[:time_w].ljust(time_w)
    ip = ip[:ip_w].rjust(ip_w)
    type = type[:type_w].ljust(type_w)

    cid = (cid or "-")[:cid_w]  # .ljust(cid_w)
    uid = format_untrusted_col(uid, uid_w)
    tid = format_untrusted_col(tid, uid_w)

    total_w, _ = shutil.get_terminal_size((200, 0))
    data_w = total_w - time_w - ip_w - type_w - cid_w - uid_w - tid_w - 6
    data_w = max(0, data_w)
    data = format_untrusted_col(data, data_w)

    return f"{time} {ip} {tid} {uid} {type} {data} {cid}"
