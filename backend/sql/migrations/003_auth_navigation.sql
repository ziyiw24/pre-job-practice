-- 用户会话、门店邀请及三 Tab 查询所需字段。
ALTER TABLE store_members ADD COLUMN status ENUM('active','disabled') NOT NULL DEFAULT 'active' AFTER role;
ALTER TABLE training_courses ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at;
ALTER TABLE training_assignments ADD COLUMN assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER due_at;
ALTER TABLE training_assignments ADD COLUMN completed_at DATETIME NULL AFTER assigned_at;
CREATE INDEX idx_course_store_status ON training_courses(store_id,status);
CREATE INDEX idx_assignment_employee_status ON training_assignments(employee_user_id,status);

CREATE TABLE user_sessions (
  id CHAR(36) PRIMARY KEY,
  user_id BIGINT UNSIGNED NOT NULL,
  refresh_token_hash CHAR(64) NOT NULL UNIQUE,
  device_id VARCHAR(128) NULL,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_session_user(user_id),
  FOREIGN KEY(user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE store_invites (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  store_id BIGINT UNSIGNED NOT NULL,
  invite_code_hash CHAR(64) NOT NULL UNIQUE,
  role ENUM('manager','employee') NOT NULL DEFAULT 'employee',
  expires_at DATETIME NOT NULL,
  max_uses INT NOT NULL DEFAULT 1,
  used_count INT NOT NULL DEFAULT 0,
  created_by BIGINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_invite_store(store_id),
  FOREIGN KEY(store_id) REFERENCES stores(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user_preferences (
  user_id BIGINT UNSIGNED PRIMARY KEY,
  active_store_id BIGINT UNSIGNED NULL,
  active_role ENUM('owner','manager','employee') NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(active_store_id) REFERENCES stores(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
