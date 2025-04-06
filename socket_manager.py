import asyncio
import socketio
import logging
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(raise_error_if_not_found=True))

log = logging.getLogger(__name__)

class SocketManager:
    def __init__(self):
        self.clients = {}

    def add_connection(self, name: str, url: str):
        client = socketio.AsyncClient(reconnection=True)
        self.clients[name] = {
            "url": url,
            "client": client,
            "connected": False,
        }

        @client.event
        async def connect():
            log.info(f"[{name}] Connected. SID: {client.sid}")
            self.clients[name]["connected"] = True
            await client.emit('client_hello', {'message': f'Hello from {name}!'})

        @client.event
        async def disconnect():
            log.warning(f"[{name}] Disconnected.")
            self.clients[name]["connected"] = False

        @client.event
        async def server_message(data):
            log.info(f"[{name}] Received message: {data}")

        return client

    async def connect_all(self):
        for name in self.clients:
            asyncio.create_task(self._connect_client(name))

    async def _connect_client(self, name: str):
        client = self.clients[name]['client']
        url = self.clients[name]['url']
        while True:
            if not client.connected:
                try:
                    log.info(f"[{name}] Connecting to {url}...")
                    await client.connect(url, transports=['websocket', 'polling'])
                except Exception as e:
                    log.error(f"[{name}] Connection error: {e}")
            await asyncio.sleep(5)

    async def emit(self, name: str, event: str, data: dict):
        client_info = self.clients.get(name)
        if not client_info:
            raise ValueError(f"No such connection '{name}'")

        client = client_info['client']
        if client.connected:
            if event == "bingo":
                res = await client.call(event, data)
                print("res", res, flush=True)
            else:
                await client.emit(event, data)
        else:
            raise ConnectionError(f"Client '{name}' is not connected.")

    async def disconnect_all(self):
        for name, info in self.clients.items():
            if info['client'].connected:
                await info['client'].disconnect()
