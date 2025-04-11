from aiohttp import web
import logging
from callers import get_next_n_available_agents
import os
from asyncio import Lock, sleep
players_per_user = os.environ['PLAYER_PER_USER']
players_per_user = 11
from callers import redis_client
from asyncio import create_task
from random import choice

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
            payload = eval(raw_data)  

            await socket_manager.emit(client_name, event, payload)
            return web.Response(text=f"Sent to {client_name}: {event} - {payload}")
        except Exception as e:
            log.exception("Emit failed")
            return web.Response(status=500, text=str(e))
        
    async def emit_enter_game(client_name: str, players:list):
        sleep_times = [
            0.1, 0.4, 1, 0.6, 0.3, 0.5, 0.9
        ]
        for player in players:
            data = {
                "telegram_id": player["telegram_id"],
                "cartella_number": 0,
                "bet_amount": 10,
                "is_agent": True,
            }
            await socket_manager.emit(client_name, "enter_new_game", data)
            await sleep(choice(sleep_times))

    async def emit_bingo_handler(request):
        data = await request.json()
        data['is_agent'] = True
        await socket_manager.emit(data['agent'], "bingo", data)
        return web.json_response({"msg": "received"})

        
    async def send_new(request):
        bet_amount = request.query.get("bet-amount")
        platform = request.query.get("platform")
        print("bet_amount", bet_amount, flush=True)
        print("platform", platform, flush=True)
        if not platform:
            return web.json_response({"error": "platform not provided"}, status=400)
        if not bet_amount:
            return web.json_response({"error": "bet-amount not provided"}, status=400)
        if not bet_amount.isdigit():
            return web.json_response({"error": "bet-amount must be a number"}, status=400)
        bet_amount = int(bet_amount)
        if bet_amount < 0:
            return web.json_response({"error": "bet-amount must be positive"}, status=400)
        players = await get_next_n_available_agents(bet_amount, 10, platform)
        create_task(emit_enter_game(platform, players))
        return web.json_response({"msg": "sent"})
    
    async def add_winner(request):
        data = await request.json()
        telegram_id = data.get("telegram_id")
        bet_amount = data.get("bet_amount")
        platform = data.get("platform")
        if not telegram_id:
            return web.json_response({"error": "telegram_id not provided"}, status=400)
        if not bet_amount:
            return web.json_response({"error": "bet_amount not provided"}, status=400)

        winners_key = f"{platform}:winners:{bet_amount}"
        await redis_client.rpush(winners_key, telegram_id)

        await redis_client.ltrim(winners_key, -100, -1)

        return web.json_response({"msg": "winner added"})
    
    async def send_more(request):
        data = await request.json()
        bet_amount = data.get("bet_amount")
        agent = data.get("agent")
        arr = data.get("arr")
        if not arr:
            return web.json_response({"error": "Agent Real Ratio not provided"}, status=400)
        if not bet_amount:
            return web.json_response({"error": "bet_amount not provided"}, status=400)
        if not agent:
            return web.json_response({"error": "agent not provided"}, status=400)
        print("arr", arr)
        players = await get_next_n_available_agents(bet_amount, 2, agent)
        create_task(emit_enter_game(agent, players))
        return web.json_response({"msg": "sent"})
      

    app.router.add_post("/emit", emit_event)
    app.router.add_post("/emit-bingo", emit_bingo_handler)
    app.router.add_post("/send-new", send_new)
    app.router.add_post("/add-winner", add_winner)
    app.router.add_post("/send-more", send_more)