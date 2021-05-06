import asyncio
import re
from typing import Optional

import r8


class TcpServer(r8.Challenge):
    server: asyncio.AbstractServer = None
    address: tuple[str, int] = ("", 8001)

    title = "TCP Service Example"

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

        line: Optional[bytes]
        try:
            line = await asyncio.wait_for(reader.readline(), 0.5)
        except asyncio.TimeoutError:
            line = None
        else:
            if line.startswith(b"GET "):
                writer.write(b'HTTP/1.1 400 Bad Request\r\n'
                             b'\r\n'
                             b'<a href="https://en.wikipedia.org/wiki/Netcat">This is not an HTTP service.</a>')
                await writer.drain()
                writer.close()
                return

        writer.write(self.challenge)
        await writer.drain()

        if line is not None:
            code = line
        else:
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
