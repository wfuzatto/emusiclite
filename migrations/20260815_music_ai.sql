-- eMusicLite IA v1 - aditiva, MySQL 5.7+, somente tabelas music_ai_*.
CREATE TABLE IF NOT EXISTS music_ai_migrations (
  version VARCHAR(40) NOT NULL,
  applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  external_subject_hash CHAR(64) NULL,
  display_name VARCHAR(190) NOT NULL,
  internal_code VARCHAR(80) NULL,
  user_type ENUM('CUSTOMER','SYSTEM') NOT NULL DEFAULT 'CUSTOMER',
  status ENUM('ACTIVE','DISABLED','SYSTEM') NOT NULL DEFAULT 'ACTIVE',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_music_user_subject (external_subject_hash),
  UNIQUE KEY uq_music_user_code (internal_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_tracks (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  owner_user_id BIGINT UNSIGNED NOT NULL,
  source ENUM('USER','AGENT') NOT NULL DEFAULT 'USER',
  title VARCHAR(200) NOT NULL DEFAULT 'Música em planejamento',
  description TEXT NULL,
  genre VARCHAR(120) NOT NULL,
  subgenre VARCHAR(120) NOT NULL DEFAULT '',
  mood VARCHAR(120) NOT NULL,
  theme VARCHAR(255) NOT NULL,
  language VARCHAR(40) NOT NULL DEFAULT 'Português',
  composition_type ENUM('INSTRUMENTAL','VOCAL') NOT NULL,
  desired_duration_seconds SMALLINT UNSIGNED NOT NULL,
  bpm SMALLINT UNSIGNED NULL,
  voice_type VARCHAR(120) NULL,
  instruments TEXT NULL,
  descriptive_references TEXT NULL,
  original_idea TEXT NOT NULL,
  status ENUM('PLANNING','QUEUED','GENERATING','COMPLETED','FAILED','DELETED') NOT NULL DEFAULT 'PLANNING',
  current_stage VARCHAR(120) NOT NULL DEFAULT 'Projeto criado',
  progress_percent TINYINT UNSIGNED NOT NULL DEFAULT 5,
  is_published TINYINT(1) NOT NULL DEFAULT 0,
  published_at DATETIME NULL,
  audio_media_id BIGINT UNSIGNED NULL,
  cover_media_id BIGINT UNSIGNED NULL,
  legacy_track_id INT NULL,
  generation_state LONGTEXT NULL,
  last_error VARCHAR(500) NULL,
  project_created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  plan_saved_at DATETIME NULL,
  lyrics_saved_at DATETIME NULL,
  prompt_saved_at DATETIME NULL,
  audio_generated_at DATETIME NULL,
  audio_validated_at DATETIME NULL,
  audio_uploaded_at DATETIME NULL,
  cover_generated_at DATETIME NULL,
  cover_uploaded_at DATETIME NULL,
  publication_completed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_music_tracks_owner (owner_user_id,updated_at),
  KEY idx_music_tracks_catalog (is_published,status,published_at),
  KEY idx_music_tracks_status (status,updated_at),
  CONSTRAINT fk_music_track_owner FOREIGN KEY (owner_user_id) REFERENCES music_ai_users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_track_plans (
  track_id BIGINT UNSIGNED NOT NULL,
  plan_json LONGTEXT NOT NULL,
  audio_prompt TEXT NOT NULL,
  cover_prompt TEXT NOT NULL,
  structure_json LONGTEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (track_id),
  CONSTRAINT fk_music_plan_track FOREIGN KEY (track_id) REFERENCES music_ai_tracks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_lyrics (
  track_id BIGINT UNSIGNED NOT NULL,
  concept_text TEXT NOT NULL,
  lyrics_text LONGTEXT NULL,
  language VARCHAR(40) NOT NULL,
  is_instrumental TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (track_id),
  CONSTRAINT fk_music_lyrics_track FOREIGN KEY (track_id) REFERENCES music_ai_tracks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_jobs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  track_id BIGINT UNSIGNED NOT NULL,
  agent_run_id BIGINT UNSIGNED NULL,
  job_type ENUM('PIPELINE','REGENERATE_AUDIO','REGENERATE_COVER') NOT NULL DEFAULT 'PIPELINE',
  operation_key VARCHAR(190) NOT NULL,
  status ENUM('PENDING','PROCESSING','COMPLETED','FAILED','CANCELLED') NOT NULL DEFAULT 'PENDING',
  priority SMALLINT NOT NULL DEFAULT 100,
  attempts SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  payload LONGTEXT NULL,
  result_data LONGTEXT NULL,
  locked_by VARCHAR(100) NULL,
  available_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at DATETIME NULL,
  heartbeat_at DATETIME NULL,
  finished_at DATETIME NULL,
  next_attempt_at DATETIME NULL,
  error_code VARCHAR(80) NULL,
  error_message VARCHAR(500) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_music_job_operation (operation_key),
  KEY idx_music_job_queue (status,available_at,priority,id),
  KEY idx_music_job_track (track_id,status),
  CONSTRAINT fk_music_job_track FOREIGN KEY (track_id) REFERENCES music_ai_tracks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_media (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  track_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  media_type ENUM('AUDIO','COVER','REFERENCE') NOT NULL,
  original_filename VARCHAR(255) NOT NULL,
  stored_filename VARCHAR(190) NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  file_size BIGINT UNSIGNED NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  checksum_sha256 CHAR(64) NOT NULL,
  duration_seconds DECIMAL(8,3) NULL,
  channels TINYINT UNSIGNED NULL,
  sample_rate INT UNSIGNED NULL,
  width INT UNSIGNED NULL,
  height INT UNSIGNED NULL,
  validation_json LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_music_track_media (track_id,media_type),
  KEY idx_music_media_owner (user_id,id),
  CONSTRAINT fk_music_media_track FOREIGN KEY (track_id) REFERENCES music_ai_tracks(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_agent_runs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_key VARCHAR(190) NOT NULL,
  trigger_type ENUM('DAILY','MANUAL') NOT NULL,
  scheduled_for DATE NULL,
  triggered_by BIGINT UNSIGNED NULL,
  owner_user_id BIGINT UNSIGNED NOT NULL,
  track_id BIGINT UNSIGNED NULL,
  status ENUM('QUEUED','RUNNING','RECOVERING','COMPLETED','FAILED') NOT NULL DEFAULT 'QUEUED',
  current_stage VARCHAR(190) NOT NULL DEFAULT 'Preparando ideia',
  progress_percent TINYINT UNSIGNED NOT NULL DEFAULT 0,
  attempts SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  recoveries SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  next_recovery_at DATETIME NULL,
  last_heartbeat_at DATETIME NULL,
  error_message VARCHAR(500) NULL,
  payload LONGTEXT NULL,
  started_at DATETIME NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_music_agent_run (run_key),
  KEY idx_music_agent_status (status,next_recovery_at),
  KEY idx_music_agent_track (track_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_workers (
  worker_id VARCHAR(100) NOT NULL,
  hostname VARCHAR(190) NOT NULL,
  process_id INT UNSIGNED NOT NULL,
  status ENUM('STARTING','IDLE','PROCESSING','STOPPED') NOT NULL,
  current_job_id BIGINT UNSIGNED NULL,
  current_track_id BIGINT UNSIGNED NULL,
  current_stage VARCHAR(190) NULL,
  health_json LONGTEXT NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  heartbeat_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  stopped_at DATETIME NULL,
  PRIMARY KEY (worker_id),
  KEY idx_music_worker_heartbeat (heartbeat_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_logs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NULL,
  track_id BIGINT UNSIGNED NULL,
  job_id BIGINT UNSIGNED NULL,
  operation VARCHAR(80) NOT NULL,
  status VARCHAR(30) NOT NULL,
  duration_ms INT UNSIGNED NULL,
  error_code VARCHAR(80) NULL,
  error_message VARCHAR(500) NULL,
  metadata LONGTEXT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_music_logs_created (created_at),
  KEY idx_music_logs_track (track_id),
  KEY idx_music_logs_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_settings (
  setting_key VARCHAR(100) NOT NULL,
  setting_value TEXT NOT NULL,
  description VARCHAR(255) NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (setting_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS music_ai_ingest_requests (
  request_id CHAR(36) NOT NULL,
  track_id BIGINT UNSIGNED NOT NULL,
  media_type ENUM('AUDIO','COVER') NOT NULL,
  media_id BIGINT UNSIGNED NULL,
  received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (request_id),
  KEY idx_music_ingest_received (received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO music_ai_users(external_subject_hash,display_name,internal_code,user_type,status)
SELECT NULL,'Agente Musical eMusic Lite','AGENTE-MUSICAL','SYSTEM','SYSTEM'
FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM music_ai_users WHERE internal_code='AGENTE-MUSICAL');

INSERT IGNORE INTO music_ai_settings(setting_key,setting_value,description) VALUES
('ai_enabled','1','Ativa a criação de músicas por IA'),
('max_active_tracks','3','Projetos incompletos por usuário'),
('max_generations_per_day','5','Projetos criados por usuário por dia'),
('daily_agent_enabled','1','Ativa a criação editorial diária'),
('daily_agent_time','04:30','Horário diário no fuso do worker; deve diferir do agente de livros'),
('daily_agent_duration_seconds','180','Duração alvo da música editorial'),
('daily_agent_genres','Pop,MPB,Eletrônica,Jazz,Lo-fi,Rock alternativo,Soul,Ambient','Gêneros permitidos'),
('daily_agent_composition_types','INSTRUMENTAL,VOCAL','Tipos de composição permitidos'),
('daily_agent_auto_publish','1','Publica somente após todas as validações'),
('worker_maintenance_seconds','30','Heartbeat e reconciliação'),
('worker_timeout_minutes','20','Recuperação de job sem heartbeat'),
('max_audio_mb','100','Limite de ingestão de áudio'),
('max_cover_mb','15','Limite de ingestão de capa');

INSERT IGNORE INTO music_ai_migrations(version) VALUES('20260815_music_ai_v1');
