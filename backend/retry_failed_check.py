import asyncio
from app.core.database import async_session
from sqlmodel import select
from app.models.check import Check
from app.workers.pipeline import process_check

async def retry_check():
    check_id = '97d5fa17-0315-4dcb-83c3-ba4addb69bf9'

    async with async_session() as session:
        result = await session.execute(
            select(Check).where(Check.id == check_id)
        )
        check = result.scalar_one_or_none()

        if check:
            print(f"Found check: {check.id}")
            print(f"Status: {check.status}")
            print(f"User ID: {check.user_id}")

            # Parse input content
            import json
            input_data = json.loads(check.input_content)

            # Dispatch the task
            print("Dispatching task to Celery...")
            task = process_check.delay(
                check_id=check.id,
                user_id=check.user_id,
                input_data={
                    'input_type': check.input_type,
                    'content': input_data.get('content'),
                    'url': input_data.get('url'),
                    'file_path': input_data.get('file_path')
                }
            )

            print(f"Task dispatched with ID: {task.id}")

            # Wait for task to complete
            import time
            for i in range(10):
                time.sleep(2)
                print(f"Task state: {task.state}")
                if task.state in ['SUCCESS', 'FAILURE']:
                    print(f"Task result: {task.result}")
                    break
        else:
            print(f"No check found with ID: {check_id}")

if __name__ == "__main__":
    asyncio.run(retry_check())