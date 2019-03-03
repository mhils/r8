import asyncio
import re
from typing import Tuple

import r8


class TcpServer(r8.Challenge):
    server: asyncio.AbstractServer = None
    address: Tuple[str, int] = ("", 8001)

    title = "2 * 3 * 7"

    challenge = b"What's the answer to life, the universe and everything?\n"
    response = r"42"
    fail = b"Not convinced!\n"

    async def description(self, user: str, solved: bool):
        return r8.util.media(self.api_url("tcp_server.svg"), f"""
            <p>
            There is an important question to be answered. 
            Connect to the TCP service at <code>{r8.util.get_host()}:{self.address[1]}</code>.
            </p>
        """)

    async def start(self):
        self.server = await asyncio.start_server(self.handle_connection, *self.address)
        self.echo(f"Running at {r8.util.format_address(self.address)}.")

    async def stop(self):
        self.echo("Stopping...")
        self.server.close()
        await self.server.wait_closed()

    @r8.util.connection_timeout
    @r8.util.tolerate_connection_error
    async def handle_connection(self, reader, writer):
        self.log(writer, "connected")

        writer.write(self.challenge)
        await writer.drain()

        code = await reader.readline()
        code = code.decode("ascii", "replace").strip()

        is_correct = re.search(self.response, code, re.IGNORECASE)

        if is_correct:
            flag = self.log_and_create_flag(writer)
            writer.write(flag.encode() + b"\n")
        else:
            self.log(writer, "fail", code)
            writer.write(self.fail)
        await writer.drain()
        writer.close()
