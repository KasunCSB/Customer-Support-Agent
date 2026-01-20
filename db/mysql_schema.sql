-- MySQL schema for Customer Support Agent
-- Created to avoid deprecated display-width warnings and FK nullability errors
-- Use: run in a MySQL server where you have privileges to create the database and tables

CREATE DATABASE IF NOT EXISTS lankatel_demo
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
USE lankatel_demo;

-- Roles & permissions (simple RBAC)
CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(64) UNIQUE NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS permissions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  role_id INT NOT NULL,
  permission VARCHAR(128) NOT NULL,
  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Users (customers and human agents)
CREATE TABLE IF NOT EXISTS users (
  id CHAR(36) PRIMARY KEY,
  external_id VARCHAR(128),            -- telco account id if exists
  phone VARCHAR(32) UNIQUE,
  phone_normalized VARCHAR(32),
  email VARCHAR(256),
  display_name VARCHAR(256),
  role ENUM('customer','agent','admin') NOT NULL DEFAULT 'customer',
  metadata JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_phone_normalized (phone_normalized),
  INDEX idx_users_external_id (external_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Connectors (external systems)
CREATE TABLE IF NOT EXISTS connectors (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(128) UNIQUE NOT NULL,
  config JSON NOT NULL,
  enabled TINYINT(1) DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Services catalog (packages, VAS)
CREATE TABLE IF NOT EXISTS services (
  id CHAR(36) PRIMARY KEY,
  code VARCHAR(64) NOT NULL UNIQUE,     -- internal code used by agent
  name VARCHAR(256) NOT NULL,
  description TEXT,
  category VARCHAR(128),
  price DECIMAL(12,2),
  currency VARCHAR(8) DEFAULT 'LKR',
  metadata JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_services_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Action definitions (catalog of possible actions)
CREATE TABLE IF NOT EXISTS action_definitions (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(128) NOT NULL UNIQUE,     -- 'activate_service', 'create_ticket'
  description TEXT,
  params_schema JSON,                     -- JSON Schema for params (renamed from reserved word `schema`)
  requires_confirmation TINYINT(1) NOT NULL DEFAULT 1,
  requires_role VARCHAR(64),              -- e.g., 'admin'
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sessions (chat/voice)
CREATE TABLE IF NOT EXISTS sessions (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36),
  session_type ENUM('chat','voice') NOT NULL DEFAULT 'chat',
  started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_active_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  metadata JSON,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_sessions_user (user_id),
  INDEX idx_sessions_last_active (last_active_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- OTP / verification records
CREATE TABLE IF NOT EXISTS user_verifications (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36),
  phone VARCHAR(32) NOT NULL,
  otp_hash VARCHAR(128) NOT NULL,        -- e.g. bcrypt hash
  method ENUM('sms','voice','email') NOT NULL DEFAULT 'sms',
  purpose VARCHAR(64) NOT NULL,          -- 'login','confirm_action'
  attempts INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 5,
  is_verified TINYINT(1) NOT NULL DEFAULT 0,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_user_ver_phone (phone),
  INDEX idx_user_ver_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Subscriptions / activations
CREATE TABLE IF NOT EXISTS subscriptions (
  id CHAR(36) PRIMARY KEY,
  user_id CHAR(36) NOT NULL,
  service_id CHAR(36) NULL,                  -- allow NULL for ON DELETE SET NULL
  status ENUM('active','suspended','cancelled') NOT NULL DEFAULT 'active',
  activated_at TIMESTAMP NULL,
  deactivated_at TIMESTAMP NULL,
  expires_at TIMESTAMP NULL,
  external_ref VARCHAR(256),             -- provisioning system ID
  metadata JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL,
  INDEX idx_sub_user (user_id),
  INDEX idx_sub_service (service_id),
  INDEX idx_sub_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Actions (each requested operation)
CREATE TABLE IF NOT EXISTS actions (
  id CHAR(36) PRIMARY KEY,
  idempotency_key VARCHAR(128),
  session_id CHAR(36),
  user_id CHAR(36),
  action_name VARCHAR(128) NOT NULL,
  action_definition_id CHAR(36),
  params JSON,
  result JSON,
  status ENUM('pending','in_progress','completed','failed','requires_approval') NOT NULL DEFAULT 'pending',
  error TEXT,
  initiated_by ENUM('user','system','agent') DEFAULT 'user',
  initiated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP NULL,
  finished_at TIMESTAMP NULL,
  executed_by CHAR(36),
  connector_id CHAR(36),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (action_definition_id) REFERENCES action_definitions(id) ON DELETE SET NULL,
  FOREIGN KEY (executed_by) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_actions_user (user_id),
  INDEX idx_actions_session (session_id),
  INDEX idx_actions_name (action_name),
  INDEX idx_actions_status (status),
  UNIQUE KEY uq_actions_idempotency (idempotency_key, user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Action events (timeline)
CREATE TABLE IF NOT EXISTS action_events (
  id CHAR(36) PRIMARY KEY,
  action_id CHAR(36) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  payload JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE,
  INDEX idx_action_events_action (action_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Jobs queue (DB-backed queue)
CREATE TABLE IF NOT EXISTS jobs (
  id CHAR(36) PRIMARY KEY,
  action_id CHAR(36),
  job_type VARCHAR(128) NOT NULL,
  payload JSON,
  attempts INT NOT NULL DEFAULT 0,
  max_attempts INT NOT NULL DEFAULT 5,
  run_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  locked_until TIMESTAMP NULL,
  status ENUM('queued','running','failed','done') NOT NULL DEFAULT 'queued',
  last_error TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE SET NULL,
  INDEX idx_jobs_status (status),
  INDEX idx_jobs_run_at (run_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tickets (human escalation)
CREATE TABLE IF NOT EXISTS tickets (
  id CHAR(36) PRIMARY KEY,
  external_id VARCHAR(256),
  user_id CHAR(36),
  subject VARCHAR(512),
  description TEXT,
  priority ENUM('low','normal','high','urgent') DEFAULT 'normal',
  status ENUM('open','in_progress','resolved','closed') DEFAULT 'open',
  assigned_to CHAR(36),
  tags JSON,
  metadata JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_tickets_user (user_id),
  INDEX idx_tickets_status (status),
  INDEX idx_tickets_assigned (assigned_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Ticket events (history)
CREATE TABLE IF NOT EXISTS ticket_events (
  id CHAR(36) PRIMARY KEY,
  ticket_id CHAR(36) NOT NULL,
  event_type VARCHAR(128) NOT NULL,
  actor_id CHAR(36),
  payload JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
  FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_ticket_events_ticket (ticket_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Audit logs (append-only)
CREATE TABLE IF NOT EXISTS audit_logs (
  id CHAR(36) PRIMARY KEY,
  actor_id CHAR(36),
  actor_role VARCHAR(64),
  action VARCHAR(128) NOT NULL,
  target_type VARCHAR(64),
  target_id CHAR(36),
  request JSON,
  response JSON,
  severity ENUM('debug','info','warning','error') DEFAULT 'info',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_audit_actor (actor_id),
  INDEX idx_audit_target (target_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Attachments for tickets
CREATE TABLE IF NOT EXISTS attachments (
  id CHAR(36) PRIMARY KEY,
  ticket_id CHAR(36) NOT NULL,
  filename VARCHAR(512),
  content_type VARCHAR(128),
  storage_ref VARCHAR(1024),
  metadata JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Example: JSON virtual column index (for common JSON lookup)
-- Adds a generated column for service_code extracted from actions.params
ALTER TABLE actions
  ADD COLUMN service_code VARCHAR(64) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(params, '$.service_code'))) VIRTUAL;
CREATE INDEX idx_actions_service_code ON actions (service_code);

-- Optional: seed basic roles
INSERT IGNORE INTO roles (id, name) VALUES (NULL, 'customer'), (NULL, 'agent'), (NULL, 'admin');

-- End of schema

```