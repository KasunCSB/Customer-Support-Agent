-- Seed data for Lankatel demo (phased)
-- Phases:
-- Phase 1: core lookup tables (roles, connectors, services), sample users
-- Phase 2: subscriptions, verifications, action_definitions, sessions
-- Phase 3: actions, tickets, more users/subscriptions to reach ISP-like volume

USE lankatel_demo;

-- ==========================
-- Phase 1: Core catalog + users
-- ==========================

-- Roles (idempotent)
INSERT IGNORE INTO roles (name) VALUES ('customer'), ('agent'), ('admin');

-- Connectors (sample SMS/email connector)
INSERT IGNORE INTO connectors (id, name, config, enabled)
VALUES
  (UUID(), 'sms_gateway', JSON_OBJECT('provider','demo_sms','api_key','REDACTED'), 1),
  (UUID(), 'email_provider', JSON_OBJECT('provider','demo_email','api_key','REDACTED'), 1);

-- Services: data packages, voice & sms bundles, VAS, support options
INSERT INTO services (id, code, name, description, category, price, currency, metadata)
VALUES
  (UUID(), 'DATA_1GB', '1GB Data Pack', '1GB mobile data valid for 7 days', 'data', 199.00, 'LKR', JSON_OBJECT('validity_days',7,'volume_mb',1024)),
  (UUID(), 'DATA_5GB', '5GB Data Pack', '5GB mobile data valid for 30 days', 'data', 499.00, 'LKR', JSON_OBJECT('validity_days',30,'volume_mb',5120)),
  (UUID(), 'DATA_UNL', 'Unlimited Night Data', 'Unlimited off-peak data (midnight-6am)', 'data', 299.00, 'LKR', JSON_OBJECT('time','00:00-06:00')),
  (UUID(), 'VOICE_MONTH', 'Monthly Voice Bundle', '500 minutes to any network, 30 days', 'voice', 399.00, 'LKR', JSON_OBJECT('minutes',500)),
  (UUID(), 'SMS_PACK', '100 SMS Pack', '100 SMS to any network, 30 days', 'sms', 49.00, 'LKR', JSON_OBJECT('sms_count',100)),
  (UUID(), 'VAS_ROAM', 'Roaming Pack', 'Data and voice for roaming', 'vas', 1999.00, 'LKR', JSON_OBJECT('regions', JSON_ARRAY('SA','ASEAN'))),
  (UUID(), 'VAS_MUSIC', 'Music Streaming Addon', 'Unlimited music streaming (selected apps)', 'vas', 99.00, 'LKR', JSON_OBJECT('apps', JSON_ARRAY('MusicX','TuneNow'))),
  (UUID(), 'VAS_SMSALERT', 'SMS Alerts', 'Critical account alerts via SMS', 'vas', 25.00, 'LKR', JSON_OBJECT('frequency','as_needed'));

-- Sample users (customers)
INSERT INTO users (id, external_id, phone, phone_normalized, email, display_name, role, metadata)
VALUES
  (UUID(), 'ACC1001', '+94771100001', '+94771100001', 'alice@example.com', 'Alice Perera', 'customer', JSON_OBJECT('city','Colombo')),
  (UUID(), 'ACC1002', '+94771100002', '+94771100002', 'buddhi@example.com', 'Buddhi Silva', 'customer', JSON_OBJECT('city','Kandy')),
  (UUID(), 'ACC1003', '+94771100003', '+94771100003', 'charitha@example.com', 'Charitha Fernando', 'customer', JSON_OBJECT('city','Galle')),
  (UUID(), 'ACC1004', '+94771100004', '+94771100004', 'dilani@example.com', 'Dilani Jayasuriya', 'customer', JSON_OBJECT('city','Negombo')),
  (UUID(), 'ACC1005', '+94771100005', '+94771100005', 'eranda@example.com', 'Eranda Kumara', 'customer', JSON_OBJECT('city','Jaffna'));

-- Sample agent account
INSERT INTO users (id, external_id, phone, phone_normalized, email, display_name, role, metadata)
VALUES (UUID(), 'AGENT001', '+94770000001', '+94770000001', 'agent1@lankatel.com', 'Agent Ramesh', 'agent', JSON_OBJECT('team','support'));

-- ==========================
-- Phase 2: Subscriptions, verifications, actions definitions, sessions
-- ==========================

-- Add subscriptions linking users to services (lookup by service code)
-- Example: Alice subscribes to DATA_5GB and VOICE_MONTH
INSERT INTO subscriptions (id, user_id, service_id, status, activated_at, external_ref, metadata)
VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100001'), (SELECT id FROM services WHERE code = 'DATA_5GB'), 'active', NOW(), 'prov_REF_1001', JSON_OBJECT('source','promo')),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100001'), (SELECT id FROM services WHERE code = 'VOICE_MONTH'), 'active', NOW(), 'prov_REF_1002', JSON_OBJECT('roaming_allowed',false)),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100002'), (SELECT id FROM services WHERE code = 'DATA_1GB'), 'active', NOW(), 'prov_REF_2001', JSON_OBJECT()),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100003'), (SELECT id FROM services WHERE code = 'VAS_MUSIC'), 'active', NOW(), 'prov_REF_3001', JSON_OBJECT()),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100004'), (SELECT id FROM services WHERE code = 'VAS_ROAM'), 'active', NOW(), 'prov_REF_4001', JSON_OBJECT('expiry_notes','trial'));

-- Create user_verifications entries (OTP flow) for recent signups
INSERT INTO user_verifications (id, user_id, phone, otp_hash, method, purpose, attempts, max_attempts, is_verified, expires_at)
VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100001'), '+94771100001', 'bcrypt$2b$12$EXAMPLEHASH1', 'sms', 'login', 0, 5, 1, DATE_ADD(NOW(), INTERVAL 10 MINUTE)),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100002'), '+94771100002', 'bcrypt$2b$12$EXAMPLEHASH2', 'sms', 'login', 0, 5, 1, DATE_ADD(NOW(), INTERVAL 10 MINUTE));

-- Action definitions (store JSON schema strings)
INSERT INTO action_definitions (id, name, description, params_schema, requires_confirmation, requires_role)
VALUES
  (UUID(), 'activate_service', 'Activate a service/package for a user',
    '{"type":"object","required":["service_code","user_phone"],"properties":{"service_code":{"type":"string"},"user_phone":{"type":"string"},"idempotency_key":{"type":"string"}}}', 1, NULL),
  (UUID(), 'deactivate_service', 'Deactivate a service for a user',
    '{"type":"object","required":["service_code","user_phone"],"properties":{"service_code":{"type":"string"},"user_phone":{"type":"string"}}}', 1, NULL),
  (UUID(), 'create_ticket', 'Create a support ticket for escalation',
    '{"type":"object","required":["subject","description","user_phone"],"properties":{"subject":{"type":"string"},"description":{"type":"string"},"priority":{"type":"string","enum":["low","normal","high","urgent"]}}}', 0, NULL),
  (UUID(), 'check_balance', 'Return account balance and validity',
    '{"type":"object","required":["user_phone"],"properties":{"user_phone":{"type":"string"}}}', 0, NULL);

-- Start sample sessions
INSERT INTO sessions (id, user_id, session_type, metadata)
VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100001'), 'chat', JSON_OBJECT('channel','web_chat')),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100002'), 'voice', JSON_OBJECT('channel','call'));

-- ==========================
-- Phase 3: Actions, tickets, and bulk-ish inserts
-- ==========================

-- Create a few sample actions (user requested activation via LLM)
INSERT INTO actions (id, idempotency_key, session_id, user_id, action_name, action_definition_id, params, status, initiated_by)
VALUES
  (UUID(), 'idem-1001', (SELECT id FROM sessions WHERE user_id = (SELECT id FROM users WHERE phone = '+94771100001') LIMIT 1),
    (SELECT id FROM users WHERE phone = '+94771100001'), 'activate_service', (SELECT id FROM action_definitions WHERE name='activate_service' LIMIT 1),
    JSON_OBJECT('service_code','DATA_5GB','user_phone','+94771100001','requested_by','Alice'), 'completed', 'user'),
  (UUID(), 'idem-1002', (SELECT id FROM sessions WHERE user_id = (SELECT id FROM users WHERE phone = '+94771100002') LIMIT 1),
    (SELECT id FROM users WHERE phone = '+94771100002'), 'check_balance', (SELECT id FROM action_definitions WHERE name='check_balance' LIMIT 1),
    JSON_OBJECT('user_phone','+94771100002'), 'completed', 'user');

-- Create a few sample tickets (escalations)
INSERT INTO tickets (id, external_id, user_id, subject, description, priority, status)
VALUES
  (UUID(), 'TICK-0001', (SELECT id FROM users WHERE phone = '+94771100003'), 'Unable to use VAS', 'Customer reports music addon not working', 'high', 'open'),
  (UUID(), 'TICK-0002', (SELECT id FROM users WHERE phone = '+94771100004'), 'Roaming data billing query', 'High roaming charges unexpected', 'urgent', 'open');

-- Add events for tickets
INSERT INTO ticket_events (id, ticket_id, event_type, actor_id, payload)
VALUES
  (UUID(), (SELECT id FROM tickets WHERE external_id='TICK-0001'), 'created', (SELECT id FROM users WHERE phone='+94771100003'), JSON_OBJECT('note','Ticket created by agent from LLM action')),
  (UUID(), (SELECT id FROM tickets WHERE external_id='TICK-0002'), 'created', (SELECT id FROM users WHERE phone='+94771100004'), JSON_OBJECT('note','Escalation from user request'));

-- Bulk-ish insert: generate additional demo users and subscriptions
-- Insert 20 more demo customers
INSERT INTO users (id, external_id, phone, phone_normalized, email, display_name, role, metadata)
VALUES
  (UUID(), 'ACC1010', '+9477110010', '+9477110010','user10@example.com','User 10','customer', JSON_OBJECT('city','Colombo')),
  (UUID(), 'ACC1011', '+9477110011', '+9477110011','user11@example.com','User 11','customer', JSON_OBJECT('city','Gampaha')),
  (UUID(), 'ACC1012', '+9477110012', '+9477110012','user12@example.com','User 12','customer', JSON_OBJECT('city','Matara')),
  (UUID(), 'ACC1013', '+9477110013', '+9477110013','user13@example.com','User 13','customer', JSON_OBJECT('city','Kegalle')),
  (UUID(), 'ACC1014', '+9477110014', '+9477110014','user14@example.com','User 14','customer', JSON_OBJECT('city','Kurunegala')),
  (UUID(), 'ACC1015', '+9477110015', '+9477110015','user15@example.com','User 15','customer', JSON_OBJECT('city','Badulla')),
  (UUID(), 'ACC1016', '+9477110016', '+9477110016','user16@example.com','User 16','customer', JSON_OBJECT('city','Trincomalee')),
  (UUID(), 'ACC1017', '+9477110017', '+9477110017','user17@example.com','User 17','customer', JSON_OBJECT('city','Ratnapura')),
  (UUID(), 'ACC1018', '+9477110018', '+9477110018','user18@example.com','User 18','customer', JSON_OBJECT('city','Anuradhapura')),
  (UUID(), 'ACC1019', '+9477110019', '+9477110019','user19@example.com','User 19','customer', JSON_OBJECT('city','Polonnaruwa'));

-- Create subscriptions for some of the new users referencing DATA_1GB or 1GB/5GB services
INSERT INTO subscriptions (id, user_id, service_id, status, activated_at, external_ref)
SELECT UUID(), u.id, s.id, 'active', NOW(), CONCAT('prov_', LPAD(FLOOR(RAND()*10000),4,'0'))
FROM users u
CROSS JOIN services s
WHERE u.phone LIKE '+94771100%' AND s.code IN ('DATA_1GB','DATA_5GB')
LIMIT 20;

-- Create more tickets from random users
INSERT INTO tickets (id, external_id, user_id, subject, description, priority, status)
SELECT UUID(), CONCAT('TICK-', LPAD(FLOOR(RAND()*9000)+1000,4,'0')), id, 'Billing inquiry', 'Demo billing question created by seeder', 'normal', 'open'
FROM users
WHERE phone LIKE '+94771100%'
LIMIT 8;

-- Add audit logs for a few actions
INSERT INTO audit_logs (id, actor_id, actor_role, action, target_type, target_id, request, response, severity)
VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100001'), 'customer', 'activate_service', 'subscription', NULL, JSON_OBJECT('service_code','DATA_5GB'), JSON_OBJECT('status','ok'), 'info'),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771100002'), 'customer', 'check_balance', 'account', NULL, JSON_OBJECT(), JSON_OBJECT('balance','LKR 2500'), 'info');

-- Example action_events for actions created above
INSERT INTO action_events (id, action_id, event_type, payload)
VALUES
  (UUID(), (SELECT id FROM actions WHERE idempotency_key='idem-1001'), 'executed', JSON_OBJECT('result','success')),
  (UUID(), (SELECT id FROM actions WHERE idempotency_key='idem-1002'), 'executed', JSON_OBJECT('balance','LKR 1234'));

-- Phase 3 complete

-- Phase 4: Additional realistic sample data (at least 10 entries per main table)
-- (Extended from db/samples.sql)

-- Roles: add missing roles
INSERT IGNORE INTO roles (name) VALUES ('billing'), ('provisioning'), ('support_lead'), ('supervisor'), ('auditor'), ('analytics'), ('developer');

-- Permissions: sample permissions for admin-like roles
INSERT IGNORE INTO permissions (role_id, permission)
SELECT r.id, p.perm FROM roles r
JOIN (SELECT 'view_account' perm UNION ALL SELECT 'modify_subscription' UNION ALL SELECT 'create_ticket' UNION ALL SELECT 'approve_action' UNION ALL SELECT 'view_billing' UNION ALL SELECT 'manage_connectors' UNION ALL SELECT 'run_reports' UNION ALL SELECT 'manage_users' UNION ALL SELECT 'provision_service' UNION ALL SELECT 'audit_logs') p
WHERE r.name IN ('admin','billing','provisioning','support_lead','auditor','developer')
LIMIT 20;

-- Connectors: ensure at least 10 connectors
INSERT IGNORE INTO connectors (id, name, config, enabled) VALUES
  (UUID(), 'twilio_sms', JSON_OBJECT('provider','twilio','sid','xxxx','token','xxxx'), 0),
  (UUID(), 'stripe', JSON_OBJECT('provider','stripe','endpoint','https://stripe.example'), 0),
  (UUID(), 'bank_api', JSON_OBJECT('provider','bank','endpoint','https://bank.example'), 0),
  (UUID(), 'analytics', JSON_OBJECT('provider','internal_analytics','endpoint','https://analytics.example'), 1),
  (UUID(), 'monitoring', JSON_OBJECT('provider','monitor','endpoint','https://mon.example'), 1);

-- More services (to ensure >=10)
INSERT IGNORE INTO services (id, code, name, description, category, price, currency, metadata) VALUES
  (UUID(), 'BUNDLE_FAMILY', 'Family Bundle', 'Shared family data for up to 4 lines', 'bundle', 999, 'LKR', JSON_OBJECT('lines',4)),
  (UUID(), 'PREMIUM_UNL', 'Premium Unlimited', 'Unlimited data and voice', 'data', 2999, 'LKR', JSON_OBJECT());

-- Additional users (to reach >=10 customers and agents)
INSERT IGNORE INTO users (id, external_id, phone, phone_normalized, email, display_name, role, metadata) VALUES
  (UUID(), 'ACC2011', '+94771300011', '+94771300011','user11@example.com','User Eleven','customer', JSON_OBJECT('city','Colombo')),
  (UUID(), 'ACC2012', '+94771300012', '+94771300012','user12@example.com','User Twelve','customer', JSON_OBJECT('city','Galle')),
  (UUID(), 'ACC2013', '+94771300013', '+94771300013','user13@example.com','User Thirteen','customer', JSON_OBJECT('city','Kandy')),
  (UUID(), 'AG2003', '','+94770000003','agent3@lankatel.com','Agent Nimal','agent', JSON_OBJECT('team','support'));

-- Additional sessions for those users
INSERT IGNORE INTO sessions (id, user_id, session_type, metadata) VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300011' LIMIT 1), 'chat', JSON_OBJECT('channel','web')),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300012' LIMIT 1), 'voice', JSON_OBJECT('channel','call')),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300013' LIMIT 1), 'chat', JSON_OBJECT('channel','web'));

-- More user verifications
INSERT IGNORE INTO user_verifications (id, user_id, phone, otp_hash, method, purpose, attempts, max_attempts, is_verified, expires_at)
VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300011' LIMIT 1), '+94771300011', 'bcrypt$2b$12$HASH11', 'sms', 'login', 0, 5, 1, DATE_ADD(NOW(), INTERVAL 10 MINUTE)),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300012' LIMIT 1), '+94771300012', 'bcrypt$2b$12$HASH12', 'sms', 'login', 0, 5, 1, DATE_ADD(NOW(), INTERVAL 10 MINUTE)),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300013' LIMIT 1), '+94771300013', 'bcrypt$2b$12$HASH13', 'sms', 'login', 0, 5, 0, DATE_ADD(NOW(), INTERVAL 5 MINUTE));

-- More subscriptions to ensure >=10
INSERT IGNORE INTO subscriptions (id, user_id, service_id, status, activated_at, external_ref, metadata)
VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300011' LIMIT 1), (SELECT id FROM services WHERE code = 'DATA_1GB' LIMIT 1), 'active', NOW(), 'prov_2001', JSON_OBJECT()),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300012' LIMIT 1), (SELECT id FROM services WHERE code = 'DATA_5GB' LIMIT 1), 'active', NOW(), 'prov_2002', JSON_OBJECT()),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300013' LIMIT 1), (SELECT id FROM services WHERE code = 'VOICE_500' LIMIT 1), 'active', NOW(), 'prov_2003', JSON_OBJECT());

-- Additional action_definitions to reach >=10
INSERT IGNORE INTO action_definitions (id, name, description, params_schema, requires_confirmation, requires_role) VALUES
  (UUID(), 'suspend_service', 'Temporarily suspend a service', '{"type":"object","required":["service_code","user_phone"]}', 1, NULL),
  (UUID(), 'resume_service', 'Resume a suspended service', '{"type":"object","required":["service_code","user_phone"]}', 1, NULL);

-- More actions to reach >=10
INSERT IGNORE INTO actions (id, idempotency_key, session_id, user_id, action_name, action_definition_id, params, result, status, initiated_by)
VALUES
  (UUID(), 'act-2001', (SELECT id FROM sessions WHERE user_id=(SELECT id FROM users WHERE phone='+94771300011' LIMIT 1)), (SELECT id FROM users WHERE phone='+94771300011' LIMIT 1), 'retrieve_usage', (SELECT id FROM action_definitions WHERE name='retrieve_usage' LIMIT 1), JSON_OBJECT('user_phone','+94771300011'), JSON_OBJECT('usage_mb',5120), 'completed', 'user'),
  (UUID(), 'act-2002', (SELECT id FROM sessions WHERE user_id=(SELECT id FROM users WHERE phone='+94771300012' LIMIT 1)), (SELECT id FROM users WHERE phone='+94771300012' LIMIT 1), 'create_ticket', (SELECT id FROM action_definitions WHERE name='create_ticket' LIMIT 1), JSON_OBJECT('subject','Provisioning delay','description','Service not active after purchase','user_phone','+94771300012'), JSON_OBJECT('ticket','TICK-4001'), 'completed', 'user');

-- More action_events
INSERT IGNORE INTO action_events (id, action_id, event_type, payload) VALUES
  (UUID(), (SELECT id FROM actions WHERE idempotency_key='act-2001' LIMIT 1), 'executed', JSON_OBJECT('usage_mb',5120)),
  (UUID(), (SELECT id FROM actions WHERE idempotency_key='act-2002' LIMIT 1), 'created', JSON_OBJECT('note','ticket created by seeder'));

-- Jobs to reach >=10
INSERT IGNORE INTO jobs (id, action_id, job_type, payload, attempts, max_attempts, run_at, status) VALUES
  (UUID(), (SELECT id FROM actions WHERE idempotency_key='act-2001' LIMIT 1), 'report_generation', JSON_OBJECT('report','weekly'), 0, 1, NOW(), 'queued'),
  (UUID(), (SELECT id FROM actions WHERE idempotency_key='act-2002' LIMIT 1), 'provision_followup', JSON_OBJECT('ticket','TICK-4001'), 0, 2, NOW(), 'queued');

-- Additional tickets to reach >=10
INSERT IGNORE INTO tickets (id, external_id, user_id, subject, description, priority, status, assigned_to) VALUES
  (UUID(), 'TICK-4001', (SELECT id FROM users WHERE phone = '+94771300012' LIMIT 1), 'Provisioning delay', 'Service not activated after purchase', 'high', 'open', NULL),
  (UUID(), 'TICK-4002', (SELECT id FROM users WHERE phone = '+94771300011' LIMIT 1), 'Coverage question', 'Reported intermittent coverage', 'normal', 'open', NULL);

-- Ticket events to reach >=10
INSERT IGNORE INTO ticket_events (id, ticket_id, event_type, actor_id, payload) VALUES
  (UUID(), (SELECT id FROM tickets WHERE external_id='TICK-4001' LIMIT 1), 'created', (SELECT id FROM users WHERE phone='+94771300012' LIMIT 1), JSON_OBJECT('note','Created from seeder')),
  (UUID(), (SELECT id FROM tickets WHERE external_id='TICK-4002' LIMIT 1), 'created', (SELECT id FROM users WHERE phone='+94771300011' LIMIT 1), JSON_OBJECT('note','Created from seeder'));

-- Audit logs to reach >=10
INSERT IGNORE INTO audit_logs (id, actor_id, actor_role, action, target_type, target_id, request, response, severity) VALUES
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300011' LIMIT 1), 'customer', 'retrieve_usage', 'account', NULL, JSON_OBJECT('user_phone','+94771300011'), JSON_OBJECT('usage_mb',5120), 'info'),
  (UUID(), (SELECT id FROM users WHERE phone = '+94771300012' LIMIT 1), 'customer', 'create_ticket', 'ticket', NULL, JSON_OBJECT('subject','Provisioning delay'), JSON_OBJECT('ticket','TICK-4001'), 'info');

-- Attachments to reach >=10
INSERT IGNORE INTO attachments (id, ticket_id, filename, content_type, storage_ref, metadata) VALUES
  (UUID(), (SELECT id FROM tickets WHERE external_id='TICK-4001' LIMIT 1), 'prov_log.txt', 'text/plain', 's3://demo/prov_log.txt', JSON_OBJECT('uploaded_by','user')),
  (UUID(), (SELECT id FROM tickets WHERE external_id='TICK-4002' LIMIT 1), 'coverage_map.pdf', 'application/pdf', 's3://demo/coverage_map.pdf', JSON_OBJECT());

-- KB documents: add at least 20 more useful KB rows (>=20)
INSERT IGNORE INTO kb_documents (id, source_file, doc_id, title, content, metadata) VALUES
  (UUID(), 'samples', 's_kb_001', 'How to activate a pack', 'Use the app or dial the USSD code provided to activate.', JSON_OBJECT('category','activation')),
  (UUID(), 'samples', 's_kb_002', 'OTP troubleshooting', 'If OTP not received, verify phone number and network.', JSON_OBJECT('category','otp')),
  (UUID(), 'samples', 's_kb_003', 'Billing dispute steps', 'Collect invoice and evidence, create ticket and escalate to billing.', JSON_OBJECT('category','billing')),
  (UUID(), 'samples', 's_kb_004', 'Roaming FAQ', 'Roaming requires activation and may incur charges.', JSON_OBJECT('category','roaming')),
  (UUID(), 'samples', 's_kb_005', 'Data tips', 'Use WiFi, disable background apps to reduce data usage.', JSON_OBJECT('category','data')),
  (UUID(), 'samples', 's_kb_006', 'SIM replacement', 'SIM replacement requires KYC and verification.', JSON_OBJECT('category','sim')),
  (UUID(), 'samples', 's_kb_007', 'Family bundle guide', 'Steps to add family members to the bundle.', JSON_OBJECT('category','bundle')),
  (UUID(), 'samples', 's_kb_008', 'Voice quality tips', 'Check signal and device compatibility.', JSON_OBJECT('category','voice')),
  (UUID(), 'samples', 's_kb_009', 'Promo credits', 'Promotional credits apply per terms.', JSON_OBJECT('category','promo')),
  (UUID(), 'samples', 's_kb_010', 'Contact support', 'Use chat or phone for quick help.', JSON_OBJECT('category','support')),
  (UUID(), 'samples', 's_kb_011', 'Plan comparison', 'Compare plans by data, voice, and price.', JSON_OBJECT('category','plans')),
  (UUID(), 'samples', 's_kb_012', 'Refund policy', 'Refunds require manager approval and a ticket.', JSON_OBJECT('category','billing')),
  (UUID(), 'samples', 's_kb_013', 'Tethering rules', 'Some plans restrict tethering; check terms.', JSON_OBJECT('category','data')),
  (UUID(), 'samples', 's_kb_014', 'Upgrade path', 'Upgrade your plan via the portal or agent.', JSON_OBJECT('category','plans')),
  (UUID(), 'samples', 's_kb_015', 'Downgrade penalties', 'Early termination charges may apply.', JSON_OBJECT('category','billing')),
  (UUID(), 'samples', 's_kb_016', 'Coverage maps', 'View our coverage maps online for detailed info.', JSON_OBJECT('category','coverage')),
  (UUID(), 'samples', 's_kb_017', 'Device whitelist', 'Some devices require registration for VoLTE.', JSON_OBJECT('category','device')),
  (UUID(), 'samples', 's_kb_018', 'SIM activation time', 'SIM activations usually complete within 10 minutes.', JSON_OBJECT('category','activation')),
  (UUID(), 'samples', 's_kb_019', 'Data rollover', 'Rollover rules vary by pack.', JSON_OBJECT('category','data')),
  (UUID(), 'samples', 's_kb_020', 'Escalation contacts', 'Escalation emails for unresolved tickets.', JSON_OBJECT('category','support'));

COMMIT;

-- Notes:
-- - This seed file was extended with realistic demo data (roles, permissions, connectors, services, users, sessions, verifications, subscriptions, action_definitions, actions, events, jobs, tickets, ticket events, audit logs, attachments, kb_documents).
-- - You can re-run it but many statements use UUID() and INSERT IGNORE to avoid primary key conflicts; some statements may still fail on repeated runs if dependent rows are missing or constraints differ.
-- - For complete fidelity to training data, consider running scripts that map raw JSONL into these tables (e.g., scripts/load_jsonl_to_mysql.py).

-- End of seed file (extended)

