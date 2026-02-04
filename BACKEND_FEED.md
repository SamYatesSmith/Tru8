FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:47:43,064 - ea1ef10d-310c-49aa-914e-b390595819c5 - sqlalchemy.engine.Engine - INFO - SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:47:43,064 INFO sqlalchemy.engine.Engine [cached since 378.7s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')
2026-02-04 13:47:43,064 - ea1ef10d-310c-49aa-914e-b390595819c5 - sqlalchemy.engine.Engine - INFO - [cached since 378.7s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')    
2026-02-04 13:47:43,066 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:47:43,066 - ea1ef10d-310c-49aa-914e-b390595819c5 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:47:43,067 INFO sqlalchemy.engine.Engine SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status = $2::VARCHAR
2026-02-04 13:47:43,067 - 9efd2703-098b-4012-af68-208762148321 - sqlalchemy.engine.Engine - INFO - SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status = $2::VARCHAR
2026-02-04 13:47:43,067 INFO sqlalchemy.engine.Engine [cached since 378.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active')
2026-02-04 13:47:43,067 - 9efd2703-098b-4012-af68-208762148321 - sqlalchemy.engine.Engine - INFO - [cached since 378.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active')
2026-02-04 13:47:43,069 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:47:43,069 - 9efd2703-098b-4012-af68-208762148321 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:47:43,527 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:47:43,527 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:47:43,527 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:47:43,527 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:47:43,528 INFO sqlalchemy.engine.Engine [cached since 379.2s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:47:43,528 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - [cached since 379.2s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:47:43,531 INFO sqlalchemy.engine.Engine SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:47:43,531 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:47:43,532 INFO sqlalchemy.engine.Engine [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,532 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,534 INFO sqlalchemy.engine.Engine SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".created_at >= $3::TIMESTAMP WITHOUT TIME ZONE
2026-02-04 13:47:43,534 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".created_at >= $3::TIMESTAMP WITHOUT TIME ZONE
2026-02-04 13:47:43,535 INFO sqlalchemy.engine.Engine [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed', datetime.datetime(2026, 2, 1, 0, 0))
2026-02-04 13:47:43,535 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed', datetime.datetime(2026, 2, 1, 0, 0))
2026-02-04 13:47:43,537 INFO sqlalchemy.engine.Engine SELECT coalesce(sum("check".raw_sources_count), $1::INTEGER) AS coalesce_1
FROM "check"
WHERE "check".user_id = $2::VARCHAR AND "check".status = $3::VARCHAR
2026-02-04 13:47:43,537 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - SELECT coalesce(sum("check".raw_sources_count), $1::INTEGER) AS coalesce_1
FROM "check"
WHERE "check".user_id = $2::VARCHAR AND "check".status = $3::VARCHAR
2026-02-04 13:47:43,537 INFO sqlalchemy.engine.Engine [cached since 379s ago] (0, 'user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,537 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - [cached since 379s ago] (0, 'user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,541 INFO sqlalchemy.engine.Engine SELECT avg(claim.confidence) AS avg_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:47:43,541 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - SELECT avg(claim.confidence) AS avg_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:47:43,542 INFO sqlalchemy.engine.Engine [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,542 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,546 INFO sqlalchemy.engine.Engine SELECT claim.verdict, count(claim.id) AS count_1 
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR GROUP BY claim.verdict
2026-02-04 13:47:43,546 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - SELECT claim.verdict, count(claim.id) AS count_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR GROUP BY claim.verdict
2026-02-04 13:47:43,547 INFO sqlalchemy.engine.Engine [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,547 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,550 INFO sqlalchemy.engine.Engine SELECT "check".article_domain, count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".article_domain IS NOT NULL GROUP BY "check".article_domain
2026-02-04 13:47:43,550 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - SELECT "check".article_domain, count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".article_domain IS NOT NULL GROUP BY "check".article_domain
2026-02-04 13:47:43,550 INFO sqlalchemy.engine.Engine [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,550 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - [cached since 379s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:47:43,552 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:47:43,552 - 73723013-b6d3-4fec-b13c-2e000600781d - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:47:53,177 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:47:53,177 - f7a1597b-fe3c-405a-96d3-a309cb6bfbb7 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:47:53,177 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:47:53,177 - f7a1597b-fe3c-405a-96d3-a309cb6bfbb7 - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:47:53,178 INFO sqlalchemy.engine.Engine [cached since 388.8s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:47:53,178 - f7a1597b-fe3c-405a-96d3-a309cb6bfbb7 - sqlalchemy.engine.Engine - INFO - [cached since 388.8s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:47:53,179 INFO sqlalchemy.engine.Engine SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:47:53,179 - f7a1597b-fe3c-405a-96d3-a309cb6bfbb7 - sqlalchemy.engine.Engine - INFO - SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:47:53,179 INFO sqlalchemy.engine.Engine [cached since 388.8s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')
2026-02-04 13:47:53,179 - f7a1597b-fe3c-405a-96d3-a309cb6bfbb7 - sqlalchemy.engine.Engine - INFO - [cached since 388.8s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')    
2026-02-04 13:47:53,180 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:47:53,180 - f7a1597b-fe3c-405a-96d3-a309cb6bfbb7 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:47:56,802 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:47:56,802 - 8869ebe6-5990-4f3a-ac53-73e182ebf266 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:47:56,802 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:47:56,802 - 8869ebe6-5990-4f3a-ac53-73e182ebf266 - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:47:56,802 INFO sqlalchemy.engine.Engine [cached since 392.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:47:56,802 - 8869ebe6-5990-4f3a-ac53-73e182ebf266 - sqlalchemy.engine.Engine - INFO - [cached since 392.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:47:56,805 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:47:56,805 - 8869ebe6-5990-4f3a-ac53-73e182ebf266 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:09,455 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:09,455 - 57cbe63a-cfdc-49a3-80bc-a7deea1f7eec - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:09,456 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:09,456 - 57cbe63a-cfdc-49a3-80bc-a7deea1f7eec - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:09,456 INFO sqlalchemy.engine.Engine [cached since 405.1s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:09,456 - 57cbe63a-cfdc-49a3-80bc-a7deea1f7eec - sqlalchemy.engine.Engine - INFO - [cached since 405.1s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:09,458 INFO sqlalchemy.engine.Engine SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:48:09,458 - 57cbe63a-cfdc-49a3-80bc-a7deea1f7eec - sqlalchemy.engine.Engine - INFO - SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:48:09,458 INFO sqlalchemy.engine.Engine [cached since 405.1s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')
2026-02-04 13:48:09,458 - 57cbe63a-cfdc-49a3-80bc-a7deea1f7eec - sqlalchemy.engine.Engine - INFO - [cached since 405.1s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')    
2026-02-04 13:48:09,459 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:09,459 - 57cbe63a-cfdc-49a3-80bc-a7deea1f7eec - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:10,829 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:10,829 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:10,831 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:10,831 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:10,831 INFO sqlalchemy.engine.Engine [cached since 406.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:10,831 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - [cached since 406.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:10,833 INFO sqlalchemy.engine.Engine SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:10,833 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:10,834 INFO sqlalchemy.engine.Engine [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,834 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,836 INFO sqlalchemy.engine.Engine SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".created_at >= $3::TIMESTAMP WITHOUT TIME ZONE
2026-02-04 13:48:10,836 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".created_at >= $3::TIMESTAMP WITHOUT TIME ZONE
2026-02-04 13:48:10,837 INFO sqlalchemy.engine.Engine [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed', datetime.datetime(2026, 2, 1, 0, 0))
2026-02-04 13:48:10,837 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed', datetime.datetime(2026, 2, 1, 0, 0))
2026-02-04 13:48:10,839 INFO sqlalchemy.engine.Engine SELECT coalesce(sum("check".raw_sources_count), $1::INTEGER) AS coalesce_1
FROM "check"
WHERE "check".user_id = $2::VARCHAR AND "check".status = $3::VARCHAR
2026-02-04 13:48:10,839 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - SELECT coalesce(sum("check".raw_sources_count), $1::INTEGER) AS coalesce_1
FROM "check"
WHERE "check".user_id = $2::VARCHAR AND "check".status = $3::VARCHAR
2026-02-04 13:48:10,840 INFO sqlalchemy.engine.Engine [cached since 406.3s ago] (0, 'user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,840 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - [cached since 406.3s ago] (0, 'user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,841 INFO sqlalchemy.engine.Engine SELECT avg(claim.confidence) AS avg_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:10,841 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - SELECT avg(claim.confidence) AS avg_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:10,842 INFO sqlalchemy.engine.Engine [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,842 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,846 INFO sqlalchemy.engine.Engine SELECT claim.verdict, count(claim.id) AS count_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR GROUP BY claim.verdict
2026-02-04 13:48:10,846 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - SELECT claim.verdict, count(claim.id) AS count_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR GROUP BY claim.verdict
2026-02-04 13:48:10,846 INFO sqlalchemy.engine.Engine [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,846 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,850 INFO sqlalchemy.engine.Engine SELECT "check".article_domain, count("check".id) AS count_1 
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".article_domain IS NOT NULL GROUP BY "check".article_domain
2026-02-04 13:48:10,850 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - SELECT "check".article_domain, count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".article_domain IS NOT NULL GROUP BY "check".article_domain
2026-02-04 13:48:10,850 INFO sqlalchemy.engine.Engine [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,850 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - [cached since 406.3s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:10,852 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:10,852 - 89064b1e-ad2a-43bf-89e4-3d1d580eafd5 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:20,566 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:20,566 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:20,567 INFO sqlalchemy.engine.Engine SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".article_excerpt, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources, "check".api_sources_used, "check".api_call_count, "check".api_coverage_percentage, "check".article_domain, "check".article_secondary_domains, "check".article_jurisdiction, "check".article_classification_confidence, "check".article_classification_source, "check".raw_sources_count
FROM "check"
WHERE "check".user_id = $1::VARCHAR ORDER BY "check".created_at DESC
 LIMIT $2::INTEGER OFFSET $3::INTEGER
2026-02-04 13:48:20,567 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".article_excerpt, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources, "check".api_sources_used, "check".api_call_count, "check".api_coverage_percentage, "check".article_domain, "check".article_secondary_domains, "check".article_jurisdiction, "check".article_classification_confidence, "check".article_classification_source, "check".raw_sources_count
FROM "check"
WHERE "check".user_id = $1::VARCHAR ORDER BY "check".created_at DESC
 LIMIT $2::INTEGER OFFSET $3::INTEGER
2026-02-04 13:48:20,567 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 20, 0)
2026-02-04 13:48:20,567 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 20, 0)
2026-02-04 13:48:20,574 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,574 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,576 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0', 1)
2026-02-04 13:48:20,576 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0', 1)
2026-02-04 13:48:20,579 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,579 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,579 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0',)
2026-02-04 13:48:20,579 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0',)
2026-02-04 13:48:20,582 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,582 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,582 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768', 1)
2026-02-04 13:48:20,582 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768', 1)
2026-02-04 13:48:20,583 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,583 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,584 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768',)
2026-02-04 13:48:20,584 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768',)
2026-02-04 13:48:20,585 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,585 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,585 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63', 1)
2026-02-04 13:48:20,585 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63', 1)
2026-02-04 13:48:20,586 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,586 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,587 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63',)
2026-02-04 13:48:20,587 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63',)
2026-02-04 13:48:20,587 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,587 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,588 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff', 1)
2026-02-04 13:48:20,588 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff', 1)
2026-02-04 13:48:20,590 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,590 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,590 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff',)
2026-02-04 13:48:20,590 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff',)
2026-02-04 13:48:20,593 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,593 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,593 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016', 1)
2026-02-04 13:48:20,593 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016', 1)
2026-02-04 13:48:20,595 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1 
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,595 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,595 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016',)
2026-02-04 13:48:20,595 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016',)
2026-02-04 13:48:20,596 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,596 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,596 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('f472c142-ffc2-4695-9131-ea30857e4395', 1)
2026-02-04 13:48:20,596 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('f472c142-ffc2-4695-9131-ea30857e4395', 1)
2026-02-04 13:48:20,598 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,598 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,598 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('f472c142-ffc2-4695-9131-ea30857e4395',)
2026-02-04 13:48:20,598 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('f472c142-ffc2-4695-9131-ea30857e4395',)
2026-02-04 13:48:20,599 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,599 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,600 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('ed1abe39-f39f-4db5-9f4d-1cb0b1e31207', 1)
2026-02-04 13:48:20,600 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('ed1abe39-f39f-4db5-9f4d-1cb0b1e31207', 1)
2026-02-04 13:48:20,600 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,600 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,601 INFO sqlalchemy.engine.Engine [cached since 416s ago] ('ed1abe39-f39f-4db5-9f4d-1cb0b1e31207',)
2026-02-04 13:48:20,601 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416s ago] ('ed1abe39-f39f-4db5-9f4d-1cb0b1e31207',)
2026-02-04 13:48:20,602 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,602 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,602 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('fe0da8c8-c517-48bd-96c8-1443214a2dec', 1)
2026-02-04 13:48:20,602 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('fe0da8c8-c517-48bd-96c8-1443214a2dec', 1)
2026-02-04 13:48:20,603 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,603 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,603 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('fe0da8c8-c517-48bd-96c8-1443214a2dec',)
2026-02-04 13:48:20,603 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('fe0da8c8-c517-48bd-96c8-1443214a2dec',)
2026-02-04 13:48:20,605 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,605 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,605 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('ae9b5ce7-d07b-41e9-853d-e5ccbd9b5889', 1)
2026-02-04 13:48:20,605 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('ae9b5ce7-d07b-41e9-853d-e5ccbd9b5889', 1)
2026-02-04 13:48:20,607 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,607 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,607 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('ae9b5ce7-d07b-41e9-853d-e5ccbd9b5889',)
2026-02-04 13:48:20,607 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('ae9b5ce7-d07b-41e9-853d-e5ccbd9b5889',)
2026-02-04 13:48:20,608 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,608 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,609 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('db990264-7db0-40ad-9dd2-f14d63b29df1', 1)
2026-02-04 13:48:20,609 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('db990264-7db0-40ad-9dd2-f14d63b29df1', 1)
2026-02-04 13:48:20,611 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1 
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,611 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,611 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('db990264-7db0-40ad-9dd2-f14d63b29df1',)
2026-02-04 13:48:20,611 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('db990264-7db0-40ad-9dd2-f14d63b29df1',)
2026-02-04 13:48:20,612 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,612 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,612 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('c7855c9f-a938-4241-9907-8a5ed43d85ee', 1)
2026-02-04 13:48:20,612 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('c7855c9f-a938-4241-9907-8a5ed43d85ee', 1)
2026-02-04 13:48:20,614 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,614 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,614 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('c7855c9f-a938-4241-9907-8a5ed43d85ee',)
2026-02-04 13:48:20,614 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('c7855c9f-a938-4241-9907-8a5ed43d85ee',)
2026-02-04 13:48:20,615 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,615 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,615 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('e15ee0a0-3115-4c04-bfb7-d3b90e44fd58', 1)
2026-02-04 13:48:20,615 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('e15ee0a0-3115-4c04-bfb7-d3b90e44fd58', 1)
2026-02-04 13:48:20,617 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,617 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,617 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('e15ee0a0-3115-4c04-bfb7-d3b90e44fd58',)
2026-02-04 13:48:20,617 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('e15ee0a0-3115-4c04-bfb7-d3b90e44fd58',)
2026-02-04 13:48:20,618 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,618 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,618 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('bbf0055d-c0a1-431b-b7f5-4187c787c88e', 1)
2026-02-04 13:48:20,618 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('bbf0055d-c0a1-431b-b7f5-4187c787c88e', 1)
2026-02-04 13:48:20,619 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,619 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,620 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('bbf0055d-c0a1-431b-b7f5-4187c787c88e',)
2026-02-04 13:48:20,620 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('bbf0055d-c0a1-431b-b7f5-4187c787c88e',)
2026-02-04 13:48:20,621 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,621 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,621 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('d8c5b1e8-d590-40b6-9c91-38a8447f0275', 1)
2026-02-04 13:48:20,621 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('d8c5b1e8-d590-40b6-9c91-38a8447f0275', 1)
2026-02-04 13:48:20,623 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,623 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,623 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('d8c5b1e8-d590-40b6-9c91-38a8447f0275',)
2026-02-04 13:48:20,623 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('d8c5b1e8-d590-40b6-9c91-38a8447f0275',)
2026-02-04 13:48:20,625 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,625 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,626 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('9f737dd6-ecc6-4727-bd15-53d83ba46b74', 1)
2026-02-04 13:48:20,626 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('9f737dd6-ecc6-4727-bd15-53d83ba46b74', 1)
2026-02-04 13:48:20,627 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,627 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,627 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('9f737dd6-ecc6-4727-bd15-53d83ba46b74',)
2026-02-04 13:48:20,627 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('9f737dd6-ecc6-4727-bd15-53d83ba46b74',)
2026-02-04 13:48:20,629 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,629 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,630 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('4aa4ddfe-eb5d-43cc-b47c-4f1015ce87de', 1)
2026-02-04 13:48:20,630 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('4aa4ddfe-eb5d-43cc-b47c-4f1015ce87de', 1)
2026-02-04 13:48:20,631 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,631 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,631 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('4aa4ddfe-eb5d-43cc-b47c-4f1015ce87de',)
2026-02-04 13:48:20,631 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('4aa4ddfe-eb5d-43cc-b47c-4f1015ce87de',)
2026-02-04 13:48:20,632 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,632 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,633 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('1840d808-23a0-47fb-a669-55fbe91c6ab3', 1)
2026-02-04 13:48:20,633 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('1840d808-23a0-47fb-a669-55fbe91c6ab3', 1)
2026-02-04 13:48:20,634 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,634 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,634 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('1840d808-23a0-47fb-a669-55fbe91c6ab3',)
2026-02-04 13:48:20,634 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('1840d808-23a0-47fb-a669-55fbe91c6ab3',)
2026-02-04 13:48:20,635 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,635 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,636 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('c26231b6-51d1-48b9-addc-7cfe032f9be4', 1)
2026-02-04 13:48:20,636 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('c26231b6-51d1-48b9-addc-7cfe032f9be4', 1)
2026-02-04 13:48:20,637 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,637 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,637 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('c26231b6-51d1-48b9-addc-7cfe032f9be4',)
2026-02-04 13:48:20,637 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('c26231b6-51d1-48b9-addc-7cfe032f9be4',)
2026-02-04 13:48:20,638 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,638 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,639 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('5c470a22-5bec-4360-acf0-8bd965bc18f6', 1)
2026-02-04 13:48:20,639 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('5c470a22-5bec-4360-acf0-8bd965bc18f6', 1)
2026-02-04 13:48:20,641 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1 
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,641 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,642 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('5c470a22-5bec-4360-acf0-8bd965bc18f6',)
2026-02-04 13:48:20,642 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('5c470a22-5bec-4360-acf0-8bd965bc18f6',)
2026-02-04 13:48:20,643 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,643 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:20,644 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('e26149bd-a07f-45c1-86fe-9ce47408710c', 1)
2026-02-04 13:48:20,644 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('e26149bd-a07f-45c1-86fe-9ce47408710c', 1)
2026-02-04 13:48:20,645 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,645 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:20,645 INFO sqlalchemy.engine.Engine [cached since 416.1s ago] ('e26149bd-a07f-45c1-86fe-9ce47408710c',)
2026-02-04 13:48:20,645 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - [cached since 416.1s ago] ('e26149bd-a07f-45c1-86fe-9ce47408710c',)
2026-02-04 13:48:20,648 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:20,648 - b374c935-635e-4b50-a118-603aff1ee173 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:26,972 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:26,972 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:26,974 INFO sqlalchemy.engine.Engine SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".article_excerpt, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources, "check".api_sources_used, "check".api_call_count, "check".api_coverage_percentage, "check".article_domain, "check".article_secondary_domains, "check".article_jurisdiction, "check".article_classification_confidence, "check".article_classification_source, "check".raw_sources_count
FROM "check"
WHERE "check".user_id = $1::VARCHAR ORDER BY "check".created_at DESC
 LIMIT $2::INTEGER OFFSET $3::INTEGER
2026-02-04 13:48:26,974 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".article_excerpt, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources, "check".api_sources_used, "check".api_call_count, "check".api_coverage_percentage, "check".article_domain, "check".article_secondary_domains, "check".article_jurisdiction, "check".article_classification_confidence, "check".article_classification_source, "check".raw_sources_count
FROM "check"
WHERE "check".user_id = $1::VARCHAR ORDER BY "check".created_at DESC
 LIMIT $2::INTEGER OFFSET $3::INTEGER
2026-02-04 13:48:26,974 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 5, 0)
2026-02-04 13:48:26,974 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 5, 0)
2026-02-04 13:48:26,979 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:26,979 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:26,980 INFO sqlalchemy.engine.Engine [cached since 422.4s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0', 1)
2026-02-04 13:48:26,980 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.4s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0', 1)
2026-02-04 13:48:26,982 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:26,982 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:26,983 INFO sqlalchemy.engine.Engine [cached since 422.4s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0',)
2026-02-04 13:48:26,983 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.4s ago] ('3f9fcad7-12f3-4754-b3a9-0002b4a289f0',)
2026-02-04 13:48:26,985 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:26,985 - 27ec5f6d-524f-49ea-8847-3207c105149d - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:26,985 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:26,985 - 27ec5f6d-524f-49ea-8847-3207c105149d - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:26,986 INFO sqlalchemy.engine.Engine [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:26,986 - 27ec5f6d-524f-49ea-8847-3207c105149d - sqlalchemy.engine.Engine - INFO - [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:26,988 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:26,988 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:26,988 INFO sqlalchemy.engine.Engine [cached since 422.4s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768', 1)
2026-02-04 13:48:26,988 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.4s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768', 1)
2026-02-04 13:48:26,989 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:26,989 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:26,989 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:26,989 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:26,990 INFO sqlalchemy.engine.Engine [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:26,990 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:26,990 INFO sqlalchemy.engine.Engine SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status = $2::VARCHAR
2026-02-04 13:48:26,990 - 27ec5f6d-524f-49ea-8847-3207c105149d - sqlalchemy.engine.Engine - INFO - SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status = $2::VARCHAR
2026-02-04 13:48:26,991 INFO sqlalchemy.engine.Engine [cached since 422.4s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active')
2026-02-04 13:48:26,991 - 27ec5f6d-524f-49ea-8847-3207c105149d - sqlalchemy.engine.Engine - INFO - [cached since 422.4s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active')
2026-02-04 13:48:26,992 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:26,992 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:26,992 INFO sqlalchemy.engine.Engine [cached since 422.4s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768',)
2026-02-04 13:48:26,992 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.4s ago] ('b35ba4cd-798f-42d1-bb46-f7caefece768',)
2026-02-04 13:48:26,993 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:26,993 - f89ff11d-a3f6-44f5-9da1-afb81c205337 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:26,994 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:26,994 - f89ff11d-a3f6-44f5-9da1-afb81c205337 - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:26,994 INFO sqlalchemy.engine.Engine [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:26,994 - f89ff11d-a3f6-44f5-9da1-afb81c205337 - sqlalchemy.engine.Engine - INFO - [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:26,997 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:26,997 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:26,997 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63', 1)
2026-02-04 13:48:26,997 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63', 1)
2026-02-04 13:48:26,998 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:26,998 - 27ec5f6d-524f-49ea-8847-3207c105149d - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:26,999 INFO sqlalchemy.engine.Engine SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".article_excerpt, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources, "check".api_sources_used, "check".api_call_count, "check".api_coverage_percentage, "check".article_domain, "check".article_secondary_domains, "check".article_jurisdiction, "check".article_classification_confidence, "check".article_classification_source, "check".raw_sources_count
FROM "check"
WHERE "check".user_id = $1::VARCHAR
2026-02-04 13:48:26,999 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - SELECT "check".id, "check".user_id, "check".input_type, "check".input_content, "check".input_url, "check".status, "check".credits_used, "check".processing_time_ms, "check".error_message, "check".created_at, "check".completed_at, "check".article_excerpt, "check".decision_trail, "check".transparency_score, "check".overall_summary, "check".credibility_score, "check".claims_supported, "check".claims_contradicted, "check".claims_uncertain, "check".user_query, "check".query_response, "check".query_confidence, "check".query_sources, "check".api_sources_used, "check".api_call_count, "check".api_coverage_percentage, "check".article_domain, "check".article_secondary_domains, "check".article_jurisdiction, "check".article_classification_confidence, "check".article_classification_source, "check".raw_sources_count
FROM "check"
WHERE "check".user_id = $1::VARCHAR
2026-02-04 13:48:27,000 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:27,000 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:27,001 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:27,001 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:27,001 INFO sqlalchemy.engine.Engine [cached since 422.4s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63',)
2026-02-04 13:48:27,001 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.4s ago] ('53dab0f5-bf21-4e29-b43f-f3c1400dba63',)
2026-02-04 13:48:27,002 INFO sqlalchemy.engine.Engine SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:48:27,002 - f89ff11d-a3f6-44f5-9da1-afb81c205337 - sqlalchemy.engine.Engine - INFO - SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:48:27,003 INFO sqlalchemy.engine.Engine [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')
2026-02-04 13:48:27,003 - f89ff11d-a3f6-44f5-9da1-afb81c205337 - sqlalchemy.engine.Engine - INFO - [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')    
2026-02-04 13:48:27,004 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:27,004 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:27,004 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff', 1)
2026-02-04 13:48:27,004 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff', 1)
2026-02-04 13:48:27,005 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:27,005 - f89ff11d-a3f6-44f5-9da1-afb81c205337 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:27,006 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:27,006 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:27,006 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff',)
2026-02-04 13:48:27,006 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('73d4e022-b220-4d2f-baad-b7f624c0c2ff',)
2026-02-04 13:48:27,007 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2026-02-04 13:48:27,007 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - BEGIN (implicit)
2026-02-04 13:48:27,007 INFO sqlalchemy.engine.Engine SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:27,007 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - SELECT "user".id, "user".email, "user".name, "user".credits, "user".total_credits_used, "user".push_token, "user".push_notifications_enabled, "user".platform, "user".device_id, "user".email_notifications_enabled, "user".email_check_completion, "user".email_check_failure, "user".email_weekly_digest, "user".email_marketing, "user".created_at, "user".updated_at
FROM "user"
WHERE "user".id = $1::VARCHAR
2026-02-04 13:48:27,007 INFO sqlalchemy.engine.Engine [cached since 422.7s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:27,007 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - [cached since 422.7s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31',)
2026-02-04 13:48:27,009 INFO sqlalchemy.engine.Engine SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:48:27,009 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - SELECT subscription.id, subscription.user_id, subscription.plan, subscription.status, subscription.credits_per_month, subscription.credits_remaining, subscription.current_period_start, subscription.current_period_end, subscription.stripe_subscription_id, subscription.stripe_customer_id, subscription.revenue_cat_id, subscription.created_at, subscription.updated_at
FROM subscription
WHERE subscription.user_id = $1::VARCHAR AND subscription.status IN ($2::VARCHAR, $3::VARCHAR)
2026-02-04 13:48:27,009 INFO sqlalchemy.engine.Engine [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')
2026-02-04 13:48:27,009 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - [cached since 422.6s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'active', 'trialing')    
2026-02-04 13:48:27,011 INFO sqlalchemy.engine.Engine SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:27,011 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT claim.id, claim.check_id, claim.text, claim.verdict, claim.confidence, claim.rationale, claim.position, claim.created_at, claim.temporal_markers, claim.time_reference, claim.is_time_sensitive, claim.claim_type, claim.is_verifiable, claim.verifiability_reason, claim.legal_metadata, claim.uncertainty_explanation, claim.confidence_breakdown, claim.abstention_reason, claim.min_requirements_met, claim.consensus_strength, claim.subject_context, claim.key_entities, claim.source_title, claim.source_url, claim.source_date, claim.current_verified_data, claim.rhetorical_context, claim.has_rhetorical_context, claim.rhetorical_style
FROM claim
WHERE claim.check_id = $1::VARCHAR ORDER BY claim.position
 LIMIT $2::INTEGER
2026-02-04 13:48:27,012 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016', 1)
2026-02-04 13:48:27,012 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016', 1)
2026-02-04 13:48:27,013 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:27,013 - 908e040a-7ab5-4faf-b11f-05bd2a1d033b - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:27,015 INFO sqlalchemy.engine.Engine SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:27,015 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - SELECT count(claim.id) AS count_1
FROM claim
WHERE claim.check_id = $1::VARCHAR
2026-02-04 13:48:27,015 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016',)
2026-02-04 13:48:27,015 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('523c9198-90ba-4ed0-b88a-cfcc8d851016',)
2026-02-04 13:48:27,016 INFO sqlalchemy.engine.Engine SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:27,016 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:27,016 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,016 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,017 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:27,017 - 079d8ed3-b786-4df7-a038-fce25a15f2b6 - sqlalchemy.engine.Engine - INFO - ROLLBACK
2026-02-04 13:48:27,018 INFO sqlalchemy.engine.Engine SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".created_at >= $3::TIMESTAMP WITHOUT TIME ZONE
2026-02-04 13:48:27,018 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - SELECT count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".created_at >= $3::TIMESTAMP WITHOUT TIME ZONE
2026-02-04 13:48:27,018 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed', datetime.datetime(2026, 2, 1, 0, 0))
2026-02-04 13:48:27,018 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed', datetime.datetime(2026, 2, 1, 0, 0))
2026-02-04 13:48:27,021 INFO sqlalchemy.engine.Engine SELECT coalesce(sum("check".raw_sources_count), $1::INTEGER) AS coalesce_1
FROM "check"
WHERE "check".user_id = $2::VARCHAR AND "check".status = $3::VARCHAR
2026-02-04 13:48:27,021 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - SELECT coalesce(sum("check".raw_sources_count), $1::INTEGER) AS coalesce_1
FROM "check"
WHERE "check".user_id = $2::VARCHAR AND "check".status = $3::VARCHAR
2026-02-04 13:48:27,021 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] (0, 'user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,021 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] (0, 'user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,022 INFO sqlalchemy.engine.Engine SELECT avg(claim.confidence) AS avg_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:27,022 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - SELECT avg(claim.confidence) AS avg_1 
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR
2026-02-04 13:48:27,023 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,023 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,027 INFO sqlalchemy.engine.Engine SELECT claim.verdict, count(claim.id) AS count_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR GROUP BY claim.verdict
2026-02-04 13:48:27,027 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - SELECT claim.verdict, count(claim.id) AS count_1
FROM claim JOIN "check" ON "check".id = claim.check_id
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR GROUP BY claim.verdict
2026-02-04 13:48:27,027 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,027 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,031 INFO sqlalchemy.engine.Engine SELECT "check".article_domain, count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".article_domain IS NOT NULL GROUP BY "check".article_domain
2026-02-04 13:48:27,031 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - SELECT "check".article_domain, count("check".id) AS count_1
FROM "check"
WHERE "check".user_id = $1::VARCHAR AND "check".status = $2::VARCHAR AND "check".article_domain IS NOT NULL GROUP BY "check".article_domain
2026-02-04 13:48:27,031 INFO sqlalchemy.engine.Engine [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,031 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - [cached since 422.5s ago] ('user_370wGIIYgMIRGmHcIR49sAqnR31', 'completed')
2026-02-04 13:48:27,032 INFO sqlalchemy.engine.Engine ROLLBACK
2026-02-04 13:48:27,032 - 6513d9b4-28b1-43d2-a6db-2f7d9d178b43 - sqlalchemy.engine.Engine - INFO - ROLLBACK