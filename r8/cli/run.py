import asyncio
import os
import signal

import click

import r8
from r8 import cars
from r8 import server
from r8 import util

_log_sql = print


@click.command("run")
@click.option("--debug", is_flag=True)
@util.with_database(echo=True)
def cli(debug) -> None:
    """Run the server."""
    print(cars.best_car())

    loop = asyncio.get_event_loop()

    if debug:
        r8.db.set_trace_callback(lambda msg: _log_sql(msg))
        loop.set_debug(True)

    r8.challenges.load()

    loop.run_until_complete(asyncio.gather(server.start(), r8.challenges.start()))
    r8.echo("r8", "Started.")

    if os.name != "nt":
        loop.add_signal_handler(signal.SIGTERM, loop.stop)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    r8.echo("r8", "Shutting down...")
    loop.run_until_complete(
        asyncio.gather(
            r8.challenges.stop(),
            server.stop(),
        )
    )
    r8.echo("r8", "Shut down.")
    loop.close()
