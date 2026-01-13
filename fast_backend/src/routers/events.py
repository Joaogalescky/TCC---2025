import asyncio

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix='/events', tags=['events'])

clients = []


@router.get('/elections')
async def election_updates():
    async def event_generator():
        queue = asyncio.Queue()
        clients.append(queue)
        try:
            while True:
                data = await queue.get()
                yield {'data': data}
        finally:
            clients.remove(queue)

    return EventSourceResponse(event_generator())


async def notify_election_change():
    for queue in clients:
        await queue.put('update')
