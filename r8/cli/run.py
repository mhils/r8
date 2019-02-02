import asyncio
import signal

import click
import os

import r8
from r8 import cars
from r8 import server
from r8 import util


@click.command("run")
@click.option('--debug', is_flag=True)
@util.with_database(echo=True)
def cli(debug) -> None:
    """Run the server."""
    print(cars.best_car())

    loop = asyncio.get_event_loop()

    if debug:
        # TODO: We may want to do r8.settings["debug"] = debug at some point,
        # but for now we don't need it and don't introduce additional complexity.
        def log_sql(msg):
            if msg.startswith("SELECT cid FROM challenges"):
                return
            print(msg)

        r8.db.set_trace_callback(log_sql)
        loop.set_debug(True)

    r8.challenges.load()

    loop.run_until_complete(asyncio.gather(
        server.start(),
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
