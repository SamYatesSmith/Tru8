@echo off
echo Running Alembic migration...
echo.

echo Step 1: Generating migration...
alembic revision --autogenerate -m "Add stripe_customer_id to subscription"

echo.
echo Step 2: Applying migration...
alembic upgrade head

echo.
echo Migration complete!
pause
