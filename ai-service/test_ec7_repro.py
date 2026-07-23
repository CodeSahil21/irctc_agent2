# -*- coding: utf-8 -*-
import sys, asyncio, re, random
sys.stdout.reconfigure(encoding="utf-8")
import httpx

BASE  = "http://localhost:8000/api/v1/agent"
EMAIL = "x-user-email@test.com"

async def turn(c, msg, conv, resume=False, resume_val=None):
    body = {"message": msg, "conversation_id": conv, "user_email": EMAIL}
    if resume:
        body["resume"] = True
        body["resume_value"] = resume_val
    r = await c.post(BASE, json=body, timeout=90)
    r.raise_for_status()
    return r.json()

async def main():
    async with httpx.AsyncClient() as c:
        conv = f"ec7-{random.randint(1000,9999)}"

        # Add saved passenger
        r = await turn(c, "Add passenger Deepak, 40, Male to my list", conv)
        if r.get("confirmation_required") or r.get("interrupted"):
            r = await turn(c, "", conv, resume=True, resume_val=True)
        print(f"Saved: {r['message'][:80]}")

        # Book using saved passenger
        r = await turn(c, "Book Paschim Express from BCT to NDLS on 2026-08-09 in SL", conv)
        print(f"T2 reply:")
        print(r['message'])
        print(f"\nT2 interrupted: {r.get('confirmation_required') or r.get('interrupted')}")

asyncio.run(main())
