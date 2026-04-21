CREATE DATABASE IF NOT EXISTS ang_capital
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE ang_capital;

-- Ang Capital schema bootstrap
-- 管理员默认账号不会在这里写死插入，应用启动时会根据 .env 自动创建首个管理员。

CREATE TABLE IF NOT EXISTS research_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    category VARCHAR(120) NOT NULL DEFAULT 'General',
    analyst VARCHAR(120) NOT NULL DEFAULT 'Ang Capital',
    publish_date DATE NOT NULL,
    reading_time VARCHAR(60) NOT NULL DEFAULT '',
    cover_image VARCHAR(500) NULL,
    pdf_url VARCHAR(500) NULL,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_research_reports_title (title),
    INDEX idx_research_reports_slug (slug),
    INDEX idx_research_reports_status (status),
    INDEX idx_research_reports_publish_date (publish_date)
);

CREATE TABLE IF NOT EXISTS frontend_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    level VARCHAR(20) NOT NULL DEFAULT 'User',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_frontend_users_username (username),
    INDEX idx_frontend_users_email (email),
    INDEX idx_frontend_users_level (level)
);

CREATE TABLE IF NOT EXISTS admin_users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_admin_users_username (username),
    INDEX idx_admin_users_is_active (is_active)
);
