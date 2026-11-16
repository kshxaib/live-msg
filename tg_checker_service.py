import asyncio
from aiohttp import web
from opentele2.td import TDesktop
from opentele2.api import UseCurrentSession
from telethon import TelegramClient, errors
from telethon.sessions import MemorySession
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact

API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

client = None
guest_client = None

async def init_tg():
    global client, guest_client
    print("1. Connecting active Telethon client (acc_1)...")
    td = TDesktop(r"D:\Shoaib\tg-accounts\acc_1\tdata")
    client = await td.ToTelethon(session=MemorySession(), flag=UseCurrentSession, receive_updates=False)
    await client.connect()
    me = await client.get_me()
    print(f"   Connected as: {me.first_name} (+{me.phone})")

    print("2. Connecting MTProto probe client...")
    guest_client = TelegramClient(MemorySession(), API_ID, API_HASH)
    await guest_client.connect()
    print("   MTProto probe client online.")

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

async def check_ban_status(phone):
    global guest_client
    if not guest_client or not guest_client.is_connected():
        guest_client = TelegramClient(MemorySession(), API_ID, API_HASH)
        await guest_client.connect()
    try:
        res = await guest_client.send_code_request(phone, force_sms=False)
        return "OK", str(res.type)
    except errors.PhoneNumberBannedError:
        return "BANNED", "PHONE_NUMBER_BANNED"
    except errors.PhoneNumberInvalidError:
        return "INVALID", "PHONE_NUMBER_INVALID"
    except errors.FloodWaitError as e:
        return "FLOOD_WAIT", f"{e.seconds}s"
    except Exception as e:
        return "UNKNOWN", str(e)

async def check_handler(request):
    phone = request.query.get('phone', '').strip()
    if not phone:
        return web.json_response({"error": "Phone number required"}, status=400)
    
    if not phone.startswith('+'):
        phone = '+' + phone
    
    try:
        # STEP 1: Live MTProto Contact Check (Does active account exist?)
        contact = InputPhoneContact(client_id=0, phone=phone, first_name="Chk", last_name="")
        res = await client(ImportContactsRequest([contact]))
        
        if res.users:
            u = res.users[0]
            name = f"{u.first_name or ''} {u.last_name or ''}".strip()
            # Clean up contact in background
            asyncio.create_task(client(DeleteContactsRequest(id=[u.id])))
            
            return web.json_response({
                "status": "REGISTERED",
                "registered": True,
                "exists": True,
                "banned": False,
                "id": u.id,
                "name": name,
                "username": u.username or "",
                "phone": phone,
                "message": f"Account exists! (ID: {u.id}, Name: {name})"
            })
        
        # STEP 2: Live MTProto Auth Check (Is number banned or invalid or clean?)
        ban_status, detail = await check_ban_status(phone)
        
        if ban_status == "BANNED":
            return web.json_response({
                "status": "BANNED",
                "registered": False,
                "exists": False,
                "banned": True,
                "phone": phone,
                "error": detail,
                "message": "PHONE_NUMBER_BANNED! Number is banned on Telegram."
            })
        elif ban_status == "INVALID":
            return web.json_response({
                "status": "INVALID",
                "registered": False,
                "exists": False,
                "banned": False,
                "invalid": True,
                "phone": phone,
                "error": detail,
                "message": "PHONE_NUMBER_INVALID! Invalid number format."
            })
        else:
            # 100% CLEAN AND FRESH
            return web.json_response({
                "status": "CLEAN_FRESH",
                "registered": False,
                "exists": False,
                "banned": False,
                "phone": phone,
                "detail": detail,
                "message": "Clean & Fresh! No account exists & NOT banned."
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
