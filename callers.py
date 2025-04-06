import aiohttp
import os

import redis.asyncio as redis



redis_client = redis.Redis(host="bagent-redis", decode_responses=True)

nice_api_url = os.environ['NICE_API_CALL']

async def refresh_all_agents_cache():
    async with aiohttp.ClientSession() as sess:
        async with sess.get(f"{nice_api_url}/get-agents") as res:
            agents = await res.json()

    ids = [str(agent['telegram_id']) for agent in agents]
    key = "nice:all-agents"
    await redis_client.delete(key)
    await redis_client.rpush(key, *ids)
    await redis_client.expire(key, 43200)


async def get_nice_availables(bet_amount:int):
    async with aiohttp.ClientSession() as sess:
        async with sess.get(f'{nice_api_url}/get-agents?bet_amount={bet_amount}') as res:
            agents = await res.json()
            return agents
    

async def get_next_n_available_agents(bet_amount: int, n: int):
    available = await get_nice_availables(bet_amount)
    if not available:
        return []

    available_map = {str(agent["telegram_id"]): agent for agent in available}
    reference_key = "nice:all-agents"
    index_key = f"nice:rotation-index:{bet_amount}"

    full_ids = await redis_client.lrange(reference_key, 0, -1)
    if not full_ids:
        await refresh_all_agents_cache()
        full_ids = await redis_client.lrange(reference_key, 0, -1)

        


    raw_index = await redis_client.get(index_key)
    start_index = int(raw_index) if raw_index else 0

    result = []
    total = len(full_ids)
    i = start_index
    tries = 0

    while len(result) < n and tries < total:
        uid = full_ids[i % total]
        if uid in available_map:
            result.append(available_map[uid])
        i += 1
        tries += 1

    await redis_client.set(index_key, i % total)
    return result

