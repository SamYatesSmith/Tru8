import asyncio
from app.workers.pipeline import process_check

# Test dispatching a task
task = process_check.delay(
    check_id='test-check-id',
    user_id='test-user-id',
    input_data={
        'input_type': 'text',
        'content': 'Test content',
        'url': None,
        'file_path': None
    }
)

print(f"Task dispatched with ID: {task.id}")
print(f"Task state: {task.state}")
print(f"Task info: {task.info}")

# Wait a bit for task to be picked up
import time
time.sleep(2)

print(f"Task state after waiting: {task.state}")
print(f"Task info after waiting: {task.info}")