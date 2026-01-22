-- Clean, realistic schema and seed data for the ISP support agent
-- Target: MySQL 8.x (utf8mb4), safe to re-run on a fresh database
-- Creates tables for users, sessions, verifications, services, subscriptions,
-- tickets, actions, and audit logs. Seeds a small, coherent dataset.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS lankatel_demo
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE lankatel_demo;

-- Users (customers, agents, admins)
CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  external_id VARCHAR(64) UNIQUE,
  email VARCHAR(255) NOT NULL UNIQUE,
  phone_e164 VARCHAR(32) UNIQUE,
  display_name VARCHAR(255) NOT NULL,
  role ENUM('customer','agent','admin') NOT NULL DEFAULT 'customer',
  status ENUM('active','suspended') NOT NULL DEFAULT 'active',
  preferred_channel ENUM('email','phone') DEFAULT 'email',
  balance_lkr DECIMAL(10,2) NULL,
  connection_valid_until DATETIME NULL,
  metadata JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Email verification / OTP
CREATE TABLE IF NOT EXISTS verifications (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  channel ENUM('email') NOT NULL,
  destination VARCHAR(255) NOT NULL,
  purpose ENUM('login','recovery','verification') NOT NULL DEFAULT 'verification',
  code_hash CHAR(128) NOT NULL,
  expires_at DATETIME NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 5,
  verified_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_verifications_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_verifications_user (user_id),
  INDEX idx_verifications_destination (destination)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Auth sessions (hashed tokens)
CREATE TABLE IF NOT EXISTS sessions (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  token_hash CHAR(128) NOT NULL,
  user_agent VARCHAR(512),
  ip_address VARCHAR(64),
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_sessions_user (user_id),
  INDEX idx_sessions_token (token_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Service catalog
CREATE TABLE IF NOT EXISTS services (
  id CHAR(36) PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  category ENUM('data','voice','sms','bundle','vas') NOT NULL,
  price DECIMAL(10,2) NOT NULL,
  currency CHAR(3) NOT NULL DEFAULT 'LKR',
  validity_days INT NULL,
  metadata JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Customer subscriptions
CREATE TABLE IF NOT EXISTS subscriptions (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  service_id CHAR(36) NOT NULL,
  status ENUM('active','pending','suspended','cancelled','expired') NOT NULL DEFAULT 'active',
  activated_at DATETIME NULL,
  expires_at DATETIME NULL,
  external_ref VARCHAR(128) NULL,
  metadata JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_subscription_user_service (user_id, service_id),
  CONSTRAINT fk_subscriptions_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_subscriptions_service FOREIGN KEY (service_id) REFERENCES services(id),
  INDEX idx_subscriptions_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tickets for support issues
CREATE TABLE IF NOT EXISTS tickets (
  id CHAR(36) PRIMARY KEY,
  external_id VARCHAR(64) NOT NULL UNIQUE,
  user_id CHAR(36) NOT NULL,
  subject VARCHAR(255) NOT NULL,
  description TEXT,
  priority ENUM('low','normal','high','urgent') NOT NULL DEFAULT 'normal',
  status ENUM('open','in_progress','resolved','closed') NOT NULL DEFAULT 'open',
  assigned_to CHAR(36) NULL,
  metadata JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  closed_at DATETIME NULL,
  CONSTRAINT fk_tickets_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_tickets_assigned_to FOREIGN KEY (assigned_to) REFERENCES users(id),
  INDEX idx_tickets_status (status),
  INDEX idx_tickets_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Ticket event stream (status changes, notes)
CREATE TABLE IF NOT EXISTS ticket_events (
  id CHAR(36) PRIMARY KEY,
  ticket_id CHAR(36) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  actor_id CHAR(36) NULL,
  payload JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ticket_events_ticket FOREIGN KEY (ticket_id) REFERENCES tickets(id),
  CONSTRAINT fk_ticket_events_actor FOREIGN KEY (actor_id) REFERENCES users(id),
  INDEX idx_ticket_events_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Action executions (LLM/tool initiated)
CREATE TABLE IF NOT EXISTS actions (
  id CHAR(36) PRIMARY KEY,
  idempotency_key VARCHAR(128) NOT NULL UNIQUE,
  session_id CHAR(36) NULL,
  user_id CHAR(36) NOT NULL,
  action_name VARCHAR(64) NOT NULL,
  status ENUM('pending','confirmed','rejected','completed','failed') NOT NULL DEFAULT 'pending',
  requires_confirmation BOOLEAN NOT NULL DEFAULT 0,
  params JSON NULL,
  result JSON NULL,
  error TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  CONSTRAINT fk_actions_session FOREIGN KEY (session_id) REFERENCES sessions(id),
  CONSTRAINT fk_actions_user FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_actions_user (user_id),
  INDEX idx_actions_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Action event stream (state transitions, retries)
CREATE TABLE IF NOT EXISTS action_events (
  id CHAR(36) PRIMARY KEY,
  action_id CHAR(36) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  payload JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_action_events_action FOREIGN KEY (action_id) REFERENCES actions(id),
  INDEX idx_action_events_action (action_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audit log for compliance
CREATE TABLE IF NOT EXISTS audit_logs (
  id CHAR(36) PRIMARY KEY,
  actor_id CHAR(36) NULL,
  actor_role ENUM('customer','agent','admin','system') NOT NULL DEFAULT 'system',
  action VARCHAR(128) NOT NULL,
  target_type VARCHAR(64) NULL,
  target_id CHAR(36) NULL,
  request JSON NULL,
  response JSON NULL,
  severity ENUM('info','warn','error') NOT NULL DEFAULT 'info',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_logs_actor FOREIGN KEY (actor_id) REFERENCES users(id),
  INDEX idx_audit_actor (actor_id),
  INDEX idx_audit_target (target_type, target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- Seed data (idempotent; safe to re-run)
-- =============================================================================

-- Users
INSERT INTO users (id, external_id, email, phone_e164, display_name, role, status, preferred_channel, balance_lkr, connection_valid_until, metadata)
VALUES
  ('11111111-aaaa-4bbb-8888-000000000001', 'ACC1001', 'kasuncsb@gmail.com', '+94770011111', 'Anushka Perera', 'customer', 'active', 'email', 1250.75, DATE_ADD(NOW(), INTERVAL 365 DAY), JSON_OBJECT('city','Colombo')),
  ('11111111-aaaa-4bbb-8888-000000000002', 'ACC1002', 'maya@kasunc.uk', '+94770022222', 'Maya Fernando', 'customer', 'active', 'email', 420.00, DATE_ADD(NOW(), INTERVAL 180 DAY), JSON_OBJECT('city','Kandy')),
  ('11111111-aaaa-4bbb-8888-0000000000a1', 'AGENT001', 'agent.ramesh@kasunc.uk', '+94770033333', 'Agent Ramesh', 'agent', 'active', 'email', NULL, NULL, JSON_OBJECT('team','support')),
  ('11111111-aaaa-4bbb-8888-0000000000b1', 'OPSADMIN', 'ops.admin@kasunc.uk', '+94770044444', 'Ops Admin', 'admin', 'active', 'email', NULL, NULL, JSON_OBJECT('department','operations'))
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- Email verifications (sample: Anushka verified)
INSERT INTO verifications (id, user_id, channel, destination, purpose, code_hash, expires_at, attempts, max_attempts, verified_at, created_at)
VALUES
  ('22222222-aaaa-4bbb-8888-000000000001', '11111111-aaaa-4bbb-8888-000000000001', 'email', 'kasuncsb@gmail.com', 'verification', 'hash-otp-anushka', DATE_ADD(NOW(), INTERVAL 5 MINUTE), 1, 5, NOW(), NOW()),
  ('22222222-aaaa-4bbb-8888-000000000002', '11111111-aaaa-4bbb-8888-000000000002', 'email', 'maya@kasunc.uk', 'verification', 'hash-otp-maya', DATE_ADD(NOW(), INTERVAL 5 MINUTE), 0, 5, NULL, NOW())
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- Sessions
INSERT INTO sessions (id, user_id, token_hash, user_agent, ip_address, expires_at, revoked_at, created_at)
VALUES
  ('33333333-aaaa-4bbb-8888-000000000001', '11111111-aaaa-4bbb-8888-000000000001', 'hash-session-1', 'Mozilla/5.0', '203.0.113.10', DATE_ADD(NOW(), INTERVAL 7 DAY), NULL, NOW()),
  ('33333333-aaaa-4bbb-8888-000000000002', '11111111-aaaa-4bbb-8888-0000000000a1', 'hash-session-agent', 'Mozilla/5.0', '203.0.113.11', DATE_ADD(NOW(), INTERVAL 30 DAY), NULL, NOW())
ON DUPLICATE KEY UPDATE expires_at = VALUES(expires_at);

-- Services
INSERT INTO services (id, code, name, description, category, price, currency, validity_days, metadata)
VALUES
  ('44444444-aaaa-4bbb-8888-000000000001', 'DATA_5GB', '5GB Data Pack', '5GB mobile data valid for 30 days', 'data', 499.00, 'LKR', 30, JSON_OBJECT('volume_mb',5120)),
  ('44444444-aaaa-4bbb-8888-000000000002', 'DATA_UNL_NIGHT', 'Unlimited Night Data', 'Unlimited data from midnight to 6am', 'data', 299.00, 'LKR', 30, JSON_OBJECT('window','00:00-06:00')),
  ('44444444-aaaa-4bbb-8888-000000000003', 'VOICE_500', '500 Minute Voice Pack', '500 any-network minutes for 30 days', 'voice', 399.00, 'LKR', 30, JSON_OBJECT('minutes',500)),
  ('44444444-aaaa-4bbb-8888-000000000004', 'SMS_100', '100 SMS Pack', '100 SMS to any network for 30 days', 'sms', 49.00, 'LKR', 30, JSON_OBJECT('sms_count',100)),
  ('44444444-aaaa-4bbb-8888-000000000005', 'ROAM_REGIONAL', 'Regional Roaming Pack', 'Voice and data bundle for regional travel', 'vas', 1999.00, 'LKR', 15, JSON_OBJECT('regions', JSON_ARRAY('SA','ASEAN'))),
  ('44444444-aaaa-4bbb-8888-000000000006', 'BUNDLE_FAMILY', 'Family Bundle', 'Shared family data for up to 4 lines', 'bundle', 999.00, 'LKR', 30, JSON_OBJECT('lines',4,'shareable',true))
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- Subscriptions
INSERT INTO subscriptions (id, user_id, service_id, status, activated_at, expires_at, external_ref, metadata)
VALUES
  ('55555555-aaaa-4bbb-8888-000000000001', '11111111-aaaa-4bbb-8888-000000000001', '44444444-aaaa-4bbb-8888-000000000001', 'active', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY), 'prov-1001', JSON_OBJECT('channel','app')),
  ('55555555-aaaa-4bbb-8888-000000000002', '11111111-aaaa-4bbb-8888-000000000001', '44444444-aaaa-4bbb-8888-000000000003', 'active', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY), 'prov-1002', JSON_OBJECT('channel','web')),
  ('55555555-aaaa-4bbb-8888-000000000003', '11111111-aaaa-4bbb-8888-000000000002', '44444444-aaaa-4bbb-8888-000000000002', 'pending', NULL, NULL, 'prov-2001', JSON_OBJECT('note','awaiting verification'))
ON DUPLICATE KEY UPDATE status = VALUES(status), updated_at = CURRENT_TIMESTAMP;

-- Tickets
INSERT INTO tickets (id, external_id, user_id, subject, description, priority, status, assigned_to, metadata, created_at)
VALUES
  ('66666666-aaaa-4bbb-8888-000000000001', 'TICK-1001', '11111111-aaaa-4bbb-8888-000000000001', 'Billing dispute for DATA_5GB', 'Charged twice for the same pack on 2024-12-12.', 'high', 'open', '11111111-aaaa-4bbb-8888-0000000000a1', JSON_OBJECT('channel','chat'), NOW()),
  ('66666666-aaaa-4bbb-8888-000000000002', 'TICK-1002', '11111111-aaaa-4bbb-8888-000000000002', 'Coverage issue in Kandy', 'Intermittent coverage near Katugastota', 'normal', 'resolved', '11111111-aaaa-4bbb-8888-0000000000a1', JSON_OBJECT('channel','voice'), DATE_SUB(NOW(), INTERVAL 2 DAY))
ON DUPLICATE KEY UPDATE status = VALUES(status), updated_at = CURRENT_TIMESTAMP;

-- Ticket events
INSERT INTO ticket_events (id, ticket_id, event_type, actor_id, payload, created_at)
VALUES
  ('77777777-aaaa-4bbb-8888-000000000001', '66666666-aaaa-4bbb-8888-000000000001', 'created', '11111111-aaaa-4bbb-8888-000000000001', JSON_OBJECT('note','User reported double charge'), NOW()),
  ('77777777-aaaa-4bbb-8888-000000000002', '66666666-aaaa-4bbb-8888-000000000001', 'assigned', '11111111-aaaa-4bbb-8888-0000000000a1', JSON_OBJECT('team','support'), NOW()),
  ('77777777-aaaa-4bbb-8888-000000000003', '66666666-aaaa-4bbb-8888-000000000002', 'created', '11111111-aaaa-4bbb-8888-000000000002', JSON_OBJECT('note','User called voice line'), DATE_SUB(NOW(), INTERVAL 2 DAY)),
  ('77777777-aaaa-4bbb-8888-000000000004', '66666666-aaaa-4bbb-8888-000000000002', 'resolved', '11111111-aaaa-4bbb-8888-0000000000a1', JSON_OBJECT('resolution','Performed network reset'), DATE_SUB(NOW(), INTERVAL 1 DAY))
ON DUPLICATE KEY UPDATE created_at = VALUES(created_at);

-- Actions (tool executions)
INSERT INTO actions (id, idempotency_key, session_id, user_id, action_name, status, requires_confirmation, params, result, error, created_at, completed_at)
VALUES
  ('88888888-aaaa-4bbb-8888-000000000001', 'idem-create-ticket-1001', '33333333-aaaa-4bbb-8888-000000000001', '11111111-aaaa-4bbb-8888-000000000001', 'create_ticket', 'completed', 1, JSON_OBJECT('subject','Billing dispute for DATA_5GB','description','Charged twice','priority','high'), JSON_OBJECT('ticket_id','TICK-1001','status','open'), NULL, NOW(), NOW()),
  ('88888888-aaaa-4bbb-8888-000000000002', 'idem-activate-bundle-family', '33333333-aaaa-4bbb-8888-000000000001', '11111111-aaaa-4bbb-8888-000000000001', 'activate_service', 'pending', 1, JSON_OBJECT('service_code','BUNDLE_FAMILY','user_phone','+94770011111'), NULL, NULL, NOW(), NULL)
ON DUPLICATE KEY UPDATE status = VALUES(status), updated_at = CURRENT_TIMESTAMP;

-- Action events
INSERT INTO action_events (id, action_id, event_type, payload, created_at)
VALUES
  ('99999999-aaaa-4bbb-8888-000000000001', '88888888-aaaa-4bbb-8888-000000000001', 'confirmed', JSON_OBJECT('confirmed_by','user'), NOW()),
  ('99999999-aaaa-4bbb-8888-000000000002', '88888888-aaaa-4bbb-8888-000000000001', 'completed', JSON_OBJECT('ticket_id','TICK-1001'), NOW())
ON DUPLICATE KEY UPDATE created_at = VALUES(created_at);

-- Audit logs
INSERT INTO audit_logs (id, actor_id, actor_role, action, target_type, target_id, request, response, severity, created_at)
VALUES
  ('aaaaaaa1-aaaa-4bbb-8888-000000000001', '11111111-aaaa-4bbb-8888-0000000000a1', 'agent', 'create_ticket', 'ticket', '66666666-aaaa-4bbb-8888-000000000001', JSON_OBJECT('channel','chat'), JSON_OBJECT('status','open'), 'info', NOW()),
  ('aaaaaaa1-aaaa-4bbb-8888-000000000002', '11111111-aaaa-4bbb-8888-0000000000a1', 'agent', 'resolve_ticket', 'ticket', '66666666-aaaa-4bbb-8888-000000000002', JSON_OBJECT('resolution','network reset'), JSON_OBJECT('status','resolved'), 'info', DATE_SUB(NOW(), INTERVAL 1 DAY))
ON DUPLICATE KEY UPDATE created_at = VALUES(created_at);

-- Sample note: use password hashing and secure token hashing in the app; values here are placeholders for demo only.
