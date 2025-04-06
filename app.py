import logging
from aiohttp import web
from socket_manager import SocketManager
from routes.api import setup_routes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

HTTP_SERVER_PORT = 8080
DEFAULT_SOCKET_URLS = {
    "nice": "http://nice-socket:7666",
    # Add more if needed
}

socket_manager = SocketManager()
for name, url in DEFAULT_SOCKET_URLS.items():
    socket_manager.add_connection(name, url)

async def on_startup(app):
    await socket_manager.connect_all()

async def on_cleanup(app):
    await socket_manager.disconnect_all()

def create_app():
    app = web.Application()
    setup_routes(app, socket_manager)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app

if __name__ == "__main__":
    web.run_app(create_app(), host='0.0.0.0', port=HTTP_SERVER_PORT)
