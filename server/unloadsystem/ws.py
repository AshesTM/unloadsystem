"""WebSocket server-side minimal (RFC6455), stdlib. Testat anterior (27/27)."""
import asyncio
import base64
import hashlib
import os
import struct

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WS:
    def __init__(self, reader, writer, is_server=True):
        self.r, self.w, self.server = reader, writer, is_server
        self.closed = False
        self.lock = asyncio.Lock()

    async def recv(self):
        """('text',str) / ('binary',bytes) / ('close',None)."""
        while True:
            try:
                hdr = await self.r.readexactly(2)
            except (asyncio.IncompleteReadError, ConnectionError):
                return ("close", None)
            op = hdr[0] & 0x0F
            masked = hdr[1] & 0x80
            ln = hdr[1] & 0x7F
            try:
                if ln == 126:
                    ln = struct.unpack("!H", await self.r.readexactly(2))[0]
                elif ln == 127:
                    ln = struct.unpack("!Q", await self.r.readexactly(8))[0]
                mask = await self.r.readexactly(4) if masked else None
                data = await self.r.readexactly(ln) if ln else b""
            except (asyncio.IncompleteReadError, ConnectionError):
                return ("close", None)
            if masked:
                data = bytes(data[i] ^ mask[i % 4] for i in range(ln))
            if op == 0x8:
                return ("close", None)
            if op == 0x9:
                await self._send(0xA, data); continue
            if op == 0xA:
                continue
            if op == 0x1:
                return ("text", data.decode("utf-8", "replace"))
            if op == 0x2:
                return ("binary", data)

    async def send_text(self, s):
        await self._send(0x1, s.encode("utf-8"))

    async def send_bytes(self, b):
        await self._send(0x2, b)

    async def _send(self, op, data):
        if self.closed:
            return
        n = len(data)
        hdr = bytearray([0x80 | op])
        mbit = 0x00 if self.server else 0x80
        if n < 126:
            hdr.append(mbit | n)
        elif n < 65536:
            hdr.append(mbit | 126); hdr += struct.pack("!H", n)
        else:
            hdr.append(mbit | 127); hdr += struct.pack("!Q", n)
        if not self.server:
            mk = os.urandom(4)
            hdr += mk
            data = bytes(data[i] ^ mk[i % 4] for i in range(n))
        async with self.lock:
            try:
                self.w.write(bytes(hdr) + data)
                await self.w.drain()
            except (ConnectionError, RuntimeError):
                self.closed = True

    async def close(self):
        try:
            await self._send(0x8, b"")
            self.w.close()
        except Exception:
            pass
        self.closed = True


def accept_headers(key):
    accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
    return ("HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Accept: " + accept + "\r\n\r\n")
