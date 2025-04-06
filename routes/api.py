from aiohttp import web
import logging
from callers import get_next_n_available_agents
import os
from asyncio import Lock, sleep
players_per_user = os.environ['PLAYER_PER_USER']
players_per_user = 11

nice_lock = Lock()
fast_lock = Lock()
zuse_lock = Lock()

locks = {
    "nice": nice_lock,
    "fast": fast_lock,
    "zuse": zuse_lock
}

log = logging.getLogger(__name__)

def setup_routes(app, socket_manager):
    async def emit_event(request):
        try:
            data = await request.post()
            client_name = data.get("client")
            event = data.get("event")
            raw_data = data.get("data", "{}")
            payload = eval(raw_data)  # ⚠️ Use json.loads() in production!

            await socket_manager.emit(client_name, event, payload)
            return web.Response(text=f"Sent to {client_name}: {event} - {payload}")
        except Exception as e:
            log.exception("Emit failed")
            return web.Response(status=500, text=str(e))
        
    async def emit_enter_game(client_name: str, players:list):
        for player in players:
            data = {
                "telegram_id": player["telegram_id"],
                "cartella_number": 0,
                "bet_amount": 10,
                "is_agent": True,
            }
            await socket_manager.emit(client_name, "enter_new_game", data)
            await sleep(0.5)

    async def emit_bingo_handler(request):
        data = await request.json()
        await socket_manager.emit(data['agent'], "bingo", data)
        return web.json_response({"msg": "received"})

        
    async def nice_callers(request):
        bet_amount = request.query.get("bet-amount", 10)
        players = await get_next_n_available_agents(bet_amount, int(players_per_user))
        await emit_enter_game("nice", players)
        return web.json_response({"msg": "sent"})
    

    app.router.add_post("/emit", emit_event)
    # app.router.add_get("/nice", nice_callers)
    app.router.add_post("/emit-bingo", emit_bingo_handler)
    app.router.add_post("/send-new", nice_callers)
