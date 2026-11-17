-- テーブル定義（26_テーブル設計書_ぽけっと手当.xlsx の 01〜04・09）
-- IF NOT EXISTS：すでにテーブルがあれば何もしない

-- 01 補助金マスタ
CREATE TABLE IF NOT EXISTS subsidy (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    name               VARCHAR(100) NOT NULL,
    amount             VARCHAR(100) NOT NULL,
    difficulty         VARCHAR(10)  NOT NULL,              -- easy / normal / hard
    deadline           DATE,                               -- NULL＝随時
    official_url       VARCHAR(500) NOT NULL,
    category           VARCHAR(20)  NOT NULL,
    target_area        VARCHAR(2)   NOT NULL DEFAULT '00', -- 00＝全国、01〜47＝都道府県
    single_parent_only BOOLEAN      NOT NULL DEFAULT 0,
    child_required     BOOLEAN      NOT NULL DEFAULT 1,
    income_max         SMALLINT,                           -- NULL＝年収の条件なし
    updated_at         DATETIME     NOT NULL
);

-- 02 会員
CREATE TABLE IF NOT EXISTS member (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    email           VARCHAR(254) NOT NULL UNIQUE COLLATE NOCASE,  -- 大文字・小文字を区別しない
    password_hash   VARCHAR(256) NOT NULL,
    prefecture      VARCHAR(2)   NOT NULL DEFAULT '',
    children_count  SMALLINT,
    income          SMALLINT,
    is_single       BOOLEAN,
    notify_deadline BOOLEAN      NOT NULL DEFAULT 1,
    agree_partner   BOOLEAN      NOT NULL DEFAULT 0,
    signup_trigger  VARCHAR(30)  NOT NULL DEFAULT '',
    created_at      DATETIME     NOT NULL
);

-- 03 お気に入り
CREATE TABLE IF NOT EXISTS favorite (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id  INTEGER NOT NULL REFERENCES member(id) ON DELETE CASCADE,   -- 退会したら一緒に消える
    subsidy_id INTEGER NOT NULL REFERENCES subsidy(id) ON DELETE CASCADE,
    created_at DATE    NOT NULL
);

-- 04 診断ログ
CREATE TABLE IF NOT EXISTS diagnosis_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id       VARCHAR(36) NOT NULL,
    member_id      INTEGER REFERENCES member(id) ON DELETE SET NULL,      -- 退会したら NULL になる
    created_at     DATETIME    NOT NULL,
    prefecture     VARCHAR(2)  NOT NULL,
    children_count SMALLINT    NOT NULL,
    income         SMALLINT    NOT NULL,
    is_single      BOOLEAN     NOT NULL,
    subsidy_ids    TEXT        NOT NULL                    -- 該当した補助金IDをカンマ区切りで
);

-- 09 管理者
CREATE TABLE IF NOT EXISTS admin_user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      VARCHAR(30)  NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    created_at    DATETIME     NOT NULL
);

-- 10 退会理由（任意・個人を特定する情報は保存しない）
CREATE TABLE IF NOT EXISTS withdrawal_feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    reason     VARCHAR(100) NOT NULL,
    created_at DATETIME     NOT NULL
);

-- 11 公式サイトへのクリック
CREATE TABLE IF NOT EXISTS official_click (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id   VARCHAR(36) NOT NULL,
    member_id  INTEGER REFERENCES member(id) ON DELETE SET NULL,
    subsidy_id INTEGER NOT NULL REFERENCES subsidy(id) ON DELETE CASCADE,
    created_at DATETIME    NOT NULL
);
