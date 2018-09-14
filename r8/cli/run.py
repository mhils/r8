import asyncio
import signal

import click
import os

import r8
from r8 import cars
from r8 import server
from r8 import util


@click.command("run")
@util.database_path
@click.option('--debug', is_flag=True)
@click.option(
    "--static-dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, resolve_path=True),
    envvar="R8_STATIC",
    default=server.DEFAULT_STATIC_DIR
)
def cli(database, debug, static_dir) -> None:
    """Run the server."""
    print(cars.best_car())
    r8.echo("r8", f"Loading database ({database})...")
    r8.db = util.sqlite3_connect(database)

    loop = asyncio.get_event_loop()

    if debug:
        def log_sql(msg):
            if msg.startswith("SELECT cid FROM challenges"):
                return
            print(msg)

        r8.db.set_trace_callback(log_sql)
        loop.set_debug(True)

    r8.challenges.load()

    loop.run_until_complete(asyncio.gather(
        server.start(static_dir=static_dir),
        r8.challenges.start()
    ))

    if os.name != "nt":
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    r8.echo("r8", "Shutting down...")
    loop.run_until_complete(asyncio.gather(
        r8.challenges.stop(),
        server.stop(),
    ))
    r8.echo("r8", "Shut down.")
    loop.close()
