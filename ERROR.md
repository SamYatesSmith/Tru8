PS C:\Users\samya\projects\Tru8\backend> .\start-backend.bat
=======================================
   Tru8 Backend Startup Script
=======================================

[1/4] Checking Redis connection...
Redis is running
Ô£ô Redis is running
[2/4] Activating virtual environment...
Ô£ô Virtual environment activated
[3/4] Checking and installing dependencies...
This may take a few moments on first run...
Ô£ô Essential dependencies installed
[4/4] Starting services...

=======================================
 Starting Tru8 Backend Services  
=======================================

Ô£ô FastAPI will start on: http://localhost:8000
Ô£ô API docs available at: http://localhost:8000/api/docs
Ô£ô Celery worker will handle fact-checking tasks

Press Ctrl+C to stop all services

Starting Celery worker...
Celery logs: celery-worker.log
[Memory Safe] Using solo pool for Windows compatibility
Starting FastAPI server...
INFO:     Will watch for changes in these directories: ['C:\\Users\\samya\\projects\\Tru8\\backend\\app']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [36284] using StatReload
Process SpawnProcess-1:
Traceback (most recent call last):
  File "C:\Python313\Lib\multiprocessing\process.py", line 313, in _bootstrap
    self.run()
    ~~~~~~~~^^
  File "C:\Python313\Lib\multiprocessing\process.py", line 108, in run
    self._target(*self._args, **self._kwargs)
    ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\samya\projects\Tru8\backend\venv\Lib\site-packages\uvicorn\_subprocess.py", line 80, in subprocess_started
    target(sockets=sockets)
    ~~~~~~^^^^^^^^^^^^^^^^^
  File "C:\Users\samya\projects\Tru8\backend\venv\Lib\site-packages\uvicorn\server.py", line 67, in run
    return asyncio.run(self.serve(sockets=sockets))
           ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Python313\Lib\asyncio\runners.py", line 195, in run
    return runner.run(main)
           ~~~~~~~~~~^^^^^^
  File "C:\Python313\Lib\asyncio\runners.py", line 118, in run
    return self._loop.run_until_complete(task)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  File "C:\Python313\Lib\asyncio\base_events.py", line 725, in run_until_complete
    return future.result()
           ~~~~~~~~~~~~~^^
  File "C:\Users\samya\projects\Tru8\backend\venv\Lib\site-packages\uvicorn\server.py", line 71, in serve
    await self._serve(sockets)
  File "C:\Users\samya\projects\Tru8\backend\venv\Lib\site-packages\uvicorn\server.py", line 78, in _serve
    config.load()
    ~~~~~~~~~~~^^
  File "C:\Users\samya\projects\Tru8\backend\venv\Lib\site-packages\uvicorn\config.py", line 436, in load
    self.loaded_app = import_from_string(self.app)
                      ~~~~~~~~~~~~~~~~~~^^^^^^^^^^
  File "C:\Users\samya\projects\Tru8\backend\venv\Lib\site-packages\uvicorn\importer.py", line 22, in import_from_string
    raise exc from None
  File "C:\Users\samya\projects\Tru8\backend\venv\Lib\site-packages\uvicorn\importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "C:\Python313\Lib\importlib\__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 1026, in exec_module
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "C:\Users\samya\projects\Tru8\backend\main.py", line 11, in <module>
    from app.api.v1 import checks, users, auth, health, payments
  File "C:\Users\samya\projects\Tru8\backend\app\api\v1\__init__.py", line 4, in <module>
    from .checks import router as checks_router
  File "C:\Users\samya\projects\Tru8\backend\app\api\v1\checks.py", line 7, in <module>
    from xhtml2pdf import pisa
ModuleNotFoundError: No module named 'xhtml2pdf'