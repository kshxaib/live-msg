import os
import asyncio
from aiohttp import web
from opentele2.td import TDesktop
from opentele2.api import UseCurrentSession
from telethon import TelegramClient, errors
from telethon.sessions import MemorySession
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.functions.auth import SignInRequest
from telethon.tl.types import InputPhoneContact

API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

client = None
guest_client = None

async def init_tg():
    global client, guest_client
    print("1. Connecting active Telethon client (acc_1)...")
    acc_1_path = r"E:\Shoaib\tg-accounts\acc_1\tdata" if os.path.exists(r"E:\Shoaib\tg-accounts\acc_1\tdata") else r"D:\Shoaib\tg-accounts\acc_1\tdata"
    td = TDesktop(acc_1_path)
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

async def check_full_telegram(phone):
    global client, guest_client

    # STEP 1: Fast Contact Import (Detects user ID, name, username)
    try:
        contact = InputPhoneContact(client_id=0, phone=phone, first_name="Chk", last_name="")
        res = await client(ImportContactsRequest([contact]))
        if res.users:
            u = res.users[0]
            name = f"{u.first_name or ''} {u.last_name or ''}".strip()
            asyncio.create_task(client(DeleteContactsRequest(id=[u.id])))
            return {
                "status": "REGISTERED",
                "registered": True,
                "exists": True,
                "banned": False,
                "id": u.id,
                "name": name,
                "username": u.username or "",
                "phone": phone,
                "message": f"Account exists! (ID: {u.id}, Name: {name})"
            }
    except Exception as e:
        print("ImportContacts error:", e)

    # STEP 2: Probe Auth System (Handles Privacy-Hidden Numbers, Banned Numbers & Unoccupied Numbers)
    if not guest_client or not guest_client.is_connected():
        guest_client = TelegramClient(MemorySession(), API_ID, API_HASH)
        await guest_client.connect()

    try:
        sent = await guest_client.send_code_request(phone, force_sms=False)

        # Check 2a: If SentCodeType is SentCodeTypeApp, user HAS AN ACTIVE APP SESSION!
        type_name = type(sent.type).__name__
        if "SentCodeTypeApp" in type_name or "SentCodeTypeApp" in str(sent.type):
            return {
                "status": "REGISTERED",
                "registered": True,
                "exists": True,
                "banned": False,
                "phone": phone,
                "message": "Account exists! (Active Telegram app session detected)"
            }

        # Check 2b: Send a dummy code to query account occupancy
        try:
            await guest_client(SignInRequest(
                phone_number=phone,
                phone_code_hash=sent.phone_code_hash,
                phone_code="00000"
            ))
        except errors.PhoneNumberUnoccupiedError:
            # 100% FRESH & NOT REGISTERED
            return {
                "status": "CLEAN_FRESH",
                "registered": False,
                "exists": False,
                "banned": False,
                "phone": phone,
                "message": "Clean & Fresh! No account exists & NOT banned."
            }
        except (errors.PhoneCodeInvalidError, errors.SessionPasswordNeededError):
            # Code was invalid or 2FA active -> Account definitely EXISTS!
            return {
                "status": "REGISTERED",
                "registered": True,
                "exists": True,
                "banned": False,
                "phone": phone,
                "message": "Account exists on Telegram!"
            }
        except Exception:
            # Fallback
            return {
                "status": "REGISTERED",
                "registered": True,
                "exists": True,
                "banned": False,
                "phone": phone,
                "message": "Account exists on Telegram!"
            }

    except errors.PhoneNumberBannedError:
        return {
            "status": "BANNED",
            "registered": False,
            "exists": False,
            "banned": True,
            "phone": phone,
            "error": "PHONE_NUMBER_BANNED",
            "message": "PHONE_NUMBER_BANNED! Number is banned on Telegram."
        }
    except errors.PhoneNumberInvalidError:
        return {
            "status": "INVALID",
            "registered": False,
            "exists": False,
            "banned": False,
            "invalid": True,
            "phone": phone,
            "error": "PHONE_NUMBER_INVALID",
            "message": "PHONE_NUMBER_INVALID! Invalid number format."
        }
    except errors.FloodWaitError as e:
        return {
            "status": "FLOOD_WAIT",
            "registered": False,
            "exists": False,
            "banned": False,
            "phone": phone,
            "error": f"FLOOD_WAIT_{e.seconds}s",
            "message": f"Flood wait from Telegram ({e.seconds}s)."
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "registered": False,
            "exists": False,
            "banned": False,
            "phone": phone,
            "error": str(e),
            "message": f"Telegram check error: {e}"
        }

async def check_handler(request):
    phone = request.query.get('phone', '').strip()
    if not phone:
        return web.json_response({"error": "Phone number required"}, status=400)
    
    if not phone.startswith('+'):
        phone = '+' + phone
    
    result = await check_full_telegram(phone)
    return web.json_response(result)

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
