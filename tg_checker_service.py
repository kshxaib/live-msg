import asyncio
from aiohttp import web
from opentele2.td import TDesktop
from opentele2.api import UseCurrentSession
from telethon.sessions import MemorySession
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact

client = None

async def init_tg():
    global client
    print("Connecting Telethon client using acc_1...")
    td = TDesktop(r"D:\Shoaib\tg-accounts\acc_1\tdata")
    client = await td.ToTelethon(session=MemorySession(), flag=UseCurrentSession, receive_updates=False)
    await client.connect()
    me = await client.get_me()
    print(f"Connected to Telegram as: {me.first_name} (+{me.phone})")

@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        })
    resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp

async def check_handler(request):
    phone = request.query.get('phone', '').strip()
    if not phone:
        return web.json_response({"error": "Phone number required"}, status=400)
    
    if not phone.startswith('+'):
        phone = '+' + phone
    
    try:
        contact = InputPhoneContact(client_id=0, phone=phone, first_name="Chk", last_name="")
        res = await client(ImportContactsRequest([contact]))
        if res.users:
            u = res.users[0]
            name = f"{u.first_name or ''} {u.last_name or ''}".strip()
            # Clean up contact in background
            asyncio.create_task(client(DeleteContactsRequest(id=[u.id])))
            return web.json_response({
                "registered": True,
                "exists": True,
                "id": u.id,
                "name": name,
                "username": u.username or "",
                "phone": phone
            })
        else:
            return web.json_response({
                "registered": False,
                "exists": False,
                "phone": phone
            })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def health_handler(request):
    return web.json_response({"status": "ok", "service": "tg_checker"})

async def make_app():
    await init_tg()
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get('/check', check_handler)
    app.router.add_get('/health', health_handler)
    return app

if __name__ == '__main__':
    web.run_app(make_app(), host='127.0.0.1', port=5055)
