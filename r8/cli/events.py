import time
from typing import List, Optional

import click

import r8
from r8 import util


def min_distinguishable_column_width(elements: List[str]) -> int:
    elements = set(elements)
    if not elements:
        return 0

    n = max(len(x) for x in elements)
    while n > 0:
        if len(set(x[:n] for x in elements)) == len(elements):
            n -= 1
        else:
            break
    return n + 1


@click.command("events")
@util.with_database()
@util.database_rows
@click.option("--watch/--no-watch", default=True)
@click.option("--teams/--no-teams", default=False, help="Show team.")
@click.argument("query", nargs=-1)
def cli(rows, watch, teams, query):
    """
    Live view of events.

    Accepts an optional query argument to filter events,
    e.g. "WHERE type LIKE 'flag%'".
    """
    query = " ".join(query)

    time_w = 19
    ip_w = 15
    uid_w = min_distinguishable_column_width(r8.util.get_users())
    uid_w = max(10, min(uid_w, 25))
    tid_w = min_distinguishable_column_width(r8.util.get_teams())
    tid_w = max(10, min(tid_w, 25))
    type_w = 20
    with r8.db:
        cids = [x[0] for x in
                r8.db.execute("SELECT cid FROM challenges").fetchall()]
    cid_w = min_distinguishable_column_width(cids)
    cid_w = max(10, min(uid_w, 25))

    def print_event(
            time: str,
            ip: str,
            type: str,
            data: Optional[str],
            cid: Optional[str],
            uid: Optional[str]
    ):
        # TODO: This is messy and could take some refactoring.
        time = time[:time_w].ljust(time_w)
        ip = ip[:ip_w].rjust(ip_w)
        type = type[:type_w].ljust(type_w)

        if teams:
            tid = (r8.util.get_team(uid) or "-")[:tid_w].ljust(tid_w)
        cid = (cid or "-")[:cid_w].ljust(cid_w)
        uid = (uid or "-")[:uid_w].ljust(uid_w)

        total_w, _ = click.get_terminal_size()
        data_w = total_w - time_w - ip_w - type_w - cid_w - uid_w - 5
        if teams:
            data_w -= tid_w + 1
        data_w = max(0, data_w)
        if data:
            data = r8.util.console_escape(data)
        else:
            data = "-"
        data = data[:data_w].ljust(data_w)
        if teams:
            print(time, ip, tid, uid, type, data, cid)
        else:
            print(time, ip, uid, type, data, cid)

    with r8.db:
        seen = max(r8.db.execute(f"SELECT COUNT(*) FROM events {query}").fetchone()[0] - rows, 0)
    while True:
        with r8.db:
            new = r8.db.execute(f"""
            SELECT time, ip, type, data, cid, uid
            FROM events
            {query}
            ORDER BY rowid
            LIMIT 100 OFFSET {seen}""").fetchall()
        seen += len(new)
        for e in new:
            print_event(*e)
        if not watch:
            break
        time.sleep(0.5)
