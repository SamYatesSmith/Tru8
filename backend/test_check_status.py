import asyncio
from app.core.database import async_session
from sqlmodel import select
from app.models.check import Check
from datetime import datetime

async def check_status():
    check_id = 'c933cd27-0bf2-4c2e-9723-e05bea442a51'

    async with async_session() as session:
        result = await session.execute(
            select(Check).where(Check.id == check_id)
        )
        check = result.scalar_one_or_none()

        if check:
            print(f"Check ID: {check.id}")
            print(f"Status: {check.status}")
            print(f"User ID: {check.user_id}")
            print(f"Created at: {check.created_at}")
            print(f"Input type: {check.input_type}")
            print(f"Input content: {check.input_content[:100] if check.input_content else None}")
            print(f"Error message: {check.error_message}")
        else:
            print(f"No check found with ID: {check_id}")

if __name__ == "__main__":
    asyncio.run(check_status())