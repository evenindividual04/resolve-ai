import asyncio
import httpx
from uuid import uuid4
from datetime import datetime, UTC

API_URL = "http://localhost:8000/events"

async def send_event(client: httpx.AsyncClient, workflow_id: str, user_id: str, message: str, outstanding: float):
    print(f"\n[{workflow_id}] Sending message: {message!r}")
    payload = {
        "event_id": f"evt-{uuid4().hex[:8]}",
        "workflow_id": workflow_id,
        "event_type": "user_message",
        "channel": "sms",
        "payload": {
            "user_id": user_id,
            "message": message,
            "outstanding_amount": outstanding,
        },
        "occurred_at": datetime.now(UTC).isoformat(),
        "idempotency_key": f"idem-{uuid4().hex}",
        "schema_version": "v1"
    }
    
    resp = await client.post(API_URL, json=payload, timeout=20.0)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Final Action: {data.get('final_action', 'Unknown')}")
        print(f"Intent Extracted: {data.get('trace', {}).get('llm_output', {}).get('intent', 'N/A')}")
        print(f"Model Used: {data.get('trace', {}).get('model_name', 'fallback')}")
    else:
        print(f"Error: {resp.text}")

async def main():
    async with httpx.AsyncClient() as client:
        print("=== Scenario 1: Hostile/Abusive User ===")
        # Will trigger ABUSIVE intent and result in an escalation
        await send_event(
            client, 
            workflow_id="real-wf-abusive", 
            user_id="user-adv-1", 
            message="This is harassment! I'm not paying a single cent to you scammers.", 
            outstanding=1200.0
        )
        
        await asyncio.sleep(2)
        
        print("\n=== Scenario 2: Hardship User ===")
        # Will trigger HARDSHIP intent and result in an escalation
        await send_event(
            client, 
            workflow_id="real-wf-hardship", 
            user_id="user-dist-1", 
            message="I just lost my job last week and can barely afford rent, let alone this loan.", 
            outstanding=5000.0
        )
        
        await asyncio.sleep(2)
        
        print("\n=== Scenario 3: Cooperative User (Payment Offer) ===")
        # Will trigger PAYMENT_OFFER and result in WAITING_FOR_PAYMENT
        await send_event(
            client, 
            workflow_id="real-wf-coop", 
            user_id="user-coop-1", 
            message="I know I'm late. I can do $400 by Friday if that works.", 
            outstanding=450.0
        )
        
        await asyncio.sleep(2)

        print("\n=== Scenario 4: Negotiation Attempt ===")
        # Offers 100 on a 1000 loan -> Should be rejected
        await send_event(
            client,
            workflow_id="real-wf-neg",
            user_id="user-neg-1",
            message="Can we settle this for $100? That's all I have.",
            outstanding=1000.0
        )
        
        print("\nAll real scenarios pushed through the API!")

if __name__ == "__main__":
    asyncio.run(main())
