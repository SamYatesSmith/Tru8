
2025-11-06 13:39:06,212 INFO sqlalchemy.engine.Engine SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR ORDER BY "check".created_at DESC
 LIMIT $2::INTEGER OFFSET $3::INTEGER
2025-11-06 13:39:06,212 - sqlalchemy.engine.Engine - INFO - SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR ORDER BY "check".created_at DESC
 LIMIT $2::INTEGER OFFSET $3::INTEGER
2025-11-06 13:39:06,212 INFO sqlalchemy.engine.Engine [generated in 0.00049s] ('user_32YpX6nzyOe3gPadIBk2lwozNQH', 5, 0)
2025-11-06 13:39:06,212 - sqlalchemy.engine.Engine - INFO - [generated in 0.00049s] ('user_32YpX6nzyOe3gPadIBk2lwozNQH', 5, 0)
2025-11-06 13:39:06,216 INFO sqlalchemy.engine.Engine SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR
2025-11-06 13:39:06,216 - sqlalchemy.engine.Engine - INFO - SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR
2025-11-06 13:39:06,216 INFO sqlalchemy.engine.Engine [generated in 0.00043s] ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)
2025-11-06 13:39:06,216 - sqlalchemy.engine.Engine - INFO - [generated in 0.00043s] ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)
2025-11-06 13:39:06,218 INFO sqlalchemy.engine.Engine ROLLBACK
2025-11-06 13:39:06,218 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2025-11-06 13:39:06,218 INFO sqlalchemy.engine.Engine ROLLBACK
2025-11-06 13:39:06,218 - sqlalchemy.engine.Engine - INFO - ROLLBACK
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 533, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 784, in _prepare       
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 636, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 654, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 433, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg\protocol\protocol.pyx", line 166, in prepare
asyncpg.exceptions.UndefinedColumnError: column check.user_query does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1969, in _exec_single_context
    self.dialect.do_execute(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\default.py", line 922, in do_execute
    cursor.execute(statement, parameters)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 591, in execute        
    self._adapt_connection.await_(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 125, in await_only
    return current.driver.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 185, in greenlet_spawn      
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 569, in _prepare_and_execute
    self._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 520, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 808, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column check.user_query does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 419, in run_asgi        
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 84, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\applications.py", line 123, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\gzip.py", line 24, in __call__
    await responder(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\gzip.py", line 44, in __call__
    await self.app(scope, receive, self.send_with_gzip)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\cors.py", line 83, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 762, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 782, in app
    await route.handle(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 297, in handle
    await self.app(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 77, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 72, in app
    response = await func(request)
               ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 299, in app
    raise e
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 294, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 191, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\projects\Tru8\backend\app\api\v1\checks.py", line 274, in get_checks
    result = await session.execute(stmt)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\ext\asyncio\session.py", line 455, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 190, in greenlet_spawn      
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\session.py", line 2308, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\session.py", line 2190, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\context.py", line 293, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1416, in execute
    return meth(
           ^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\sql\elements.py", line 516, in _execute_on_connection        
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1639, in _execute_clauseelement        
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1848, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1988, in _exec_single_context
    self._handle_dbapi_exception(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 2343, in _handle_dbapi_exception       
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1969, in _exec_single_context
    self.dialect.do_execute(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\default.py", line 922, in do_execute
    cursor.execute(statement, parameters)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 591, in execute        
    self._adapt_connection.await_(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 125, in await_only
    return current.driver.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 185, in greenlet_spawn      
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 569, in _prepare_and_execute
    self._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 520, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 808, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column check.user_query does not exist
[SQL: SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR ORDER BY "check".created_at DESC
 LIMIT $2::INTEGER OFFSET $3::INTEGER]
[parameters: ('user_32YpX6nzyOe3gPadIBk2lwozNQH', 5, 0)]
(Background on this error at: https://sqlalche.me/e/20/f405)
2025-11-06 13:39:06,305 - httpcore.http11 - DEBUG - receive_response_headers.complete return_value=(b'HTTP/1.1', 200, b'OK', [(b'Date', b'Thu, 06 Nov 2025 13:39:06 GMT'), (b'Content-Type', b'application/json'), (b'Transfer-Encoding', b'chunked'), (b'Connection', b'keep-alive'), (b'Content-Encoding', b'gzip'), (b'CF-Ray', b'99a4feba3c9dcd16-LHR'), (b'CF-Cache-Status', b'DYNAMIC'), (b'clerk-api-version', b'2025-04-10'), (b'X-CFWorker', b'1'), (b'x-clerk-trace-id', b'0974842265a07b55ecf50034f1cbf071'), (b'x-cloud-trace-context', b'0974842265a07b55ecf50034f1cbf071'), (b'Set-Cookie', b'__cf_bm=uo31HUsE8JIJ4fUsYeg4_sOE3zBGGKIR2HwwvQcaje4-1762436346-1.0.1.1-LsIaS6oYfqD0dgfrmBxVURGSduSeBwFJnLn12kEXnoBbjXlOG.qrk3tYyOJ.7w0OrtcRcQCZR7YiuCscUPjfVhI4Xx_cNo2eseAsy4WKkDU; path=/; expires=Thu, 06-Nov-25 14:09:06 GMT; domain=.api.clerk.com; HttpOnly; Secure; SameSite=None'), (b'Vary', b'Accept-Encoding'), (b'Server', b'cloudflare')])
2025-11-06 13:39:06,305 - httpcore.http11 - DEBUG - receive_response_body.started request=<Request [b'GET']>
2025-11-06 13:39:06,305 - httpcore.http11 - DEBUG - receive_response_body.complete
2025-11-06 13:39:06,305 - httpcore.http11 - DEBUG - response_closed.started
2025-11-06 13:39:06,307 - httpcore.http11 - DEBUG - response_closed.complete
2025-11-06 13:39:06,307 - httpcore.connection - DEBUG - close.started
2025-11-06 13:39:06,307 - httpcore.connection - DEBUG - close.complete
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 533, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 784, in _prepare       
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 636, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 654, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 433, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg\protocol\protocol.pyx", line 166, in prepare
asyncpg.exceptions.UndefinedColumnError: column check.user_query does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1969, in _exec_single_context
    self.dialect.do_execute(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\default.py", line 922, in do_execute
    cursor.execute(statement, parameters)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 591, in execute        
    self._adapt_connection.await_(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 125, in await_only
    return current.driver.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 185, in greenlet_spawn      
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 569, in _prepare_and_execute
    self._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 520, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 808, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column check.user_query does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 419, in run_asgi        
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 84, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\applications.py", line 123, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\gzip.py", line 24, in __call__
    await responder(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\gzip.py", line 44, in __call__
    await self.app(scope, receive, self.send_with_gzip)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\cors.py", line 83, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 762, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 782, in app
    await route.handle(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 297, in handle
    await self.app(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 77, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 72, in app
    response = await func(request)
               ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 299, in app
    raise e
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 294, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 191, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\projects\Tru8\backend\app\api\v1\users.py", line 55, in get_profile
    checks_result = await session.execute(checks_stmt)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\ext\asyncio\session.py", line 455, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 190, in greenlet_spawn      
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\session.py", line 2308, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\session.py", line 2190, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\context.py", line 293, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1416, in execute
    return meth(
           ^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\sql\elements.py", line 516, in _execute_on_connection        
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1639, in _execute_clauseelement        
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1848, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1988, in _exec_single_context
    self._handle_dbapi_exception(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 2343, in _handle_dbapi_exception       
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1969, in _exec_single_context
    self.dialect.do_execute(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\default.py", line 922, in do_execute
    cursor.execute(statement, parameters)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 591, in execute        
    self._adapt_connection.await_(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 125, in await_only
    return current.driver.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 185, in greenlet_spawn      
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 569, in _prepare_and_execute
    self._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 520, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 808, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column check.user_query does not exist
[SQL: SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR]
[parameters: ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)]
(Background on this error at: https://sqlalche.me/e/20/f405)
2025-11-06 13:39:06,314 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2025-11-06 13:39:06,314 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2025-11-06 13:39:06,315 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2025-11-06 13:39:06,315 - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2025-11-06 13:39:06,315 INFO sqlalchemy.engine.Engine [cached since 0.1732s ago] ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)
2025-11-06 13:39:06,315 - sqlalchemy.engine.Engine - INFO - [cached since 0.1732s ago] ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)
2025-11-06 13:39:06,317 INFO sqlalchemy.engine.Engine SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR
2025-11-06 13:39:06,317 - sqlalchemy.engine.Engine - INFO - SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR
2025-11-06 13:39:06,318 INFO sqlalchemy.engine.Engine [cached since 0.1026s ago] ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)
2025-11-06 13:39:06,318 - sqlalchemy.engine.Engine - INFO - [cached since 0.1026s ago] ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)
2025-11-06 13:39:06,321 INFO sqlalchemy.engine.Engine ROLLBACK
2025-11-06 13:39:06,321 - sqlalchemy.engine.Engine - INFO - ROLLBACK
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 533, in _prepare_and_execute
    prepared_stmt, attributes = await adapt_connection._prepare(
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 784, in _prepare       
    prepared_stmt = await self._connection.prepare(
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 636, in prepare
    return await self._prepare(
           ^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 654, in _prepare
    stmt = await self._get_statement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\asyncpg\connection.py", line 433, in _get_statement
    statement = await self._protocol.prepare(
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "asyncpg\protocol\protocol.pyx", line 166, in prepare
asyncpg.exceptions.UndefinedColumnError: column check.user_query does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1969, in _exec_single_context
    self.dialect.do_execute(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\default.py", line 922, in do_execute
    cursor.execute(statement, parameters)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 591, in execute        
    self._adapt_connection.await_(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 125, in await_only
    return current.driver.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 185, in greenlet_spawn      
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 569, in _prepare_and_execute
    self._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 520, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 808, in _handle_exception
    raise translated_error from error
sqlalchemy.dialects.postgresql.asyncpg.AsyncAdapt_asyncpg_dbapi.ProgrammingError: <class 'asyncpg.exceptions.UndefinedColumnError'>: column check.user_query does not exist

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 419, in run_asgi        
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 84, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\applications.py", line 123, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\gzip.py", line 24, in __call__
    await responder(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\gzip.py", line 44, in __call__
    await self.app(scope, receive, self.send_with_gzip)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\cors.py", line 83, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 762, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 782, in app
    await route.handle(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 297, in handle
    await self.app(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 77, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 64, in wrapped_app
    raise exc
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\starlette\routing.py", line 72, in app
    response = await func(request)
               ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 299, in app
    raise e
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 294, in app
    raw_response = await run_endpoint_function(
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\fastapi\routing.py", line 191, in run_endpoint_function
    return await dependant.call(**values)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\projects\Tru8\backend\app\api\v1\users.py", line 55, in get_profile
    checks_result = await session.execute(checks_stmt)
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\ext\asyncio\session.py", line 455, in execute
    result = await greenlet_spawn(
             ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 190, in greenlet_spawn      
    result = context.throw(*sys.exc_info())
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\session.py", line 2308, in execute
    return self._execute_internal(
           ^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\session.py", line 2190, in _execute_internal
    result: Result[Any] = compile_state_cls.orm_execute_statement(
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\orm\context.py", line 293, in orm_execute_statement
    result = conn.execute(
             ^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1416, in execute
    return meth(
           ^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\sql\elements.py", line 516, in _execute_on_connection        
    return connection._execute_clauseelement(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1639, in _execute_clauseelement        
    ret = self._execute_context(
          ^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1848, in _execute_context
    return self._exec_single_context(
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1988, in _exec_single_context
    self._handle_dbapi_exception(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 2343, in _handle_dbapi_exception       
    raise sqlalchemy_exception.with_traceback(exc_info[2]) from e
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\base.py", line 1969, in _exec_single_context
    self.dialect.do_execute(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\engine\default.py", line 922, in do_execute
    cursor.execute(statement, parameters)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 591, in execute        
    self._adapt_connection.await_(
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 125, in await_only
    return current.driver.switch(awaitable)  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\util\_concurrency_py3k.py", line 185, in greenlet_spawn      
    value = await result
            ^^^^^^^^^^^^
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 569, in _prepare_and_execute
    self._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 520, in _handle_exception
    self._adapt_connection._handle_exception(error)
  File "C:\Users\james\AppData\Local\Programs\Python\Python312\Lib\site-packages\sqlalchemy\dialects\postgresql\asyncpg.py", line 808, in _handle_exception
    raise translated_error from error
sqlalchemy.exc.ProgrammingError: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError) <class 'asyncpg.exceptions.UndefinedColumnError'>: column check.user_query does not exist
[SQL: SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources
FROM "check"
WHERE "check".user_id = $1::VARCHAR]
[parameters: ('user_32YpX6nzyOe3gPadIBk2lwozNQH',)]
(Background on this error at: https://sqlalche.me/e/20/f405)
