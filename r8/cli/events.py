import time

import click

import r8
from r8 import util


@click.command("events")
@util.with_database
@util.database_rows
@click.argument("query", nargs=-1)
def cli(rows, query):
    """
    Live view of events.

    Accepts an optional query argument to filter events,
    e.g. "WHERE type LIKE 'flag%'".
    """
    query = " ".join(query)

    def print_event(event):
        time, ip, uid, cid, type, data = event
        ip = ip.rjust(15)
        uid = (uid or "-").ljust(8)
        type = type.ljust(20)
        data = ((data or "-")[:20]).ljust(20)
        cid = cid or "-"
        print(time, ip, uid, type, data, cid)

    with r8.db:
        seen = max(r8.db.execute(f"SELECT COUNT(*) FROM events {query}").fetchone()[0] - rows, 0)
    while True:
        with r8.db:
            new = r8.db.execute(f"""
            SELECT time, ip, uid, cid, type, data
            FROM events
            {query}
            ORDER BY rowid
            LIMIT 100 OFFSET {seen}""").fetchall()
            seen += len(new)
            for e in new:
                print_event(e)
            time.sleep(0.5)
