"""Broker MQTT 3.1.1 mínimo para los tests: CONNECT, PUBLISH QoS 0/1 y PING."""

import asyncio
from dataclasses import dataclass, field
import ssl


@dataclass
class Message:
    topic: str
    payload: bytes
    qos: int
    retain: bool


@dataclass
class Broker:
    context: ssl.SSLContext | None = None
    users: dict[str, str] | None = None
    ack: bool = True
    port: int = 0
    messages: list[Message] = field(default_factory=list)
    sessions: list[tuple[str, bool]] = field(default_factory=list)
    _server: asyncio.Server | None = None
    _writers: set[asyncio.StreamWriter] = field(default_factory=set)

    @property
    def retained(self) -> dict[str, bytes]:
        return {m.topic: m.payload for m in self.messages if m.retain}

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", self.port)
        self.port = self._server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        self._server.close()
        self.drop()
        await self._server.wait_closed()

    def drop(self) -> None:
        for writer in list(self._writers):
            writer.close()

    async def _handle(self, reader, writer) -> None:
        self._writers.add(writer)
        try:
            # TLS aquí: un handshake fallido no llega al manejador de errores del loop.
            if self.context:
                await writer.start_tls(self.context)
            while True:
                first, body = await _packet(reader)
                kind = first >> 4
                if kind == 1:
                    writer.write(bytes([0x20, 2, 0, self._connect(body)]))
                elif kind == 3:
                    self._publish(first, body, writer)
                elif kind == 12:
                    writer.write(bytes([0xD0, 0]))
                elif kind == 14:
                    break
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, ssl.SSLError):
            pass
        finally:
            self._writers.discard(writer)
            writer.close()

    def _connect(self, body: bytes) -> int:
        _, i = _str(body, 0)
        flags = body[i + 1]
        client_id, i = _str(body, i + 4)
        user = password = b""
        if flags & 0x80:
            user, i = _str(body, i)
        if flags & 0x40:
            password, i = _str(body, i)
        self.sessions.append((client_id.decode(), bool(flags & 0x02)))
        if (
            self.users is not None
            and self.users.get(user.decode()) != password.decode()
        ):
            return 5
        return 0

    def _publish(self, first: int, body: bytes, writer) -> None:
        qos = (first >> 1) & 3
        topic, i = _str(body, 0)
        mid = body[i : i + 2] if qos else b""
        self.messages.append(
            Message(topic.decode(), body[i + len(mid) :], qos, bool(first & 1))
        )
        if qos == 1 and self.ack:
            writer.write(bytes([0x40, 2]) + mid)


async def _packet(reader) -> tuple[int, bytes]:
    first = (await reader.readexactly(1))[0]
    length, mult = 0, 1
    while True:
        byte = (await reader.readexactly(1))[0]
        length += (byte & 0x7F) * mult
        mult *= 128
        if byte < 0x80:
            return first, await reader.readexactly(length)


def _str(buf: bytes, i: int) -> tuple[bytes, int]:
    n = int.from_bytes(buf[i : i + 2])
    return buf[i + 2 : i + 2 + n], i + 2 + n
