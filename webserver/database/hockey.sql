PRAGMA foreign_keys=OFF;
BEGIN;

CREATE TABLE game(
    game_id         INTEGER     PRIMARY KEY     NOT NULL,
    scheduled_at    TIMESTAMP WITH TIME ZONE    NOT NULL,
    completed       INTEGER     DEFAULT 0,
    shootout        INTEGER     DEFAULT 0,
    rink            TEXT        NOT NULL,
    level           TEXT        NOT NULL,
    home_team_id    INTEGER     NOT NULL,
    away_team_id    INTEGER     NOT NULL,
    home_goals      INTEGER,
    away_goals      INTEGER,
    game_type       TEXT,
    scoresheet_html_url TEXT,
    scoresheet_pdf_url TEXT,
    did_notify_coming_soon BOOLEAN,
    created_at      TIMESTAMP WITH TIME ZONE,
    home_locker_room TEXT,
    away_locker_room TEXT,
);

CREATE TABLE game_reply(
    reply_id        SERIAL,
    game_id         INTEGER,
    team_id         INTEGER,
    user_id         INTEGER,
    is_goalie       BOOLEAN,
    response        TEXT,
    message         TEXT,
    modified_at     TIMESTAMP WITH TIME ZONE
);

-- Game chat messages
CREATE TABLE game_chat_message (
    message_id         SERIAL PRIMARY KEY,
    game_id            INTEGER NOT NULL REFERENCES game(game_id),
    team_id            INTEGER NOT NULL REFERENCES team(team_id),
    user_id            INTEGER NOT NULL REFERENCES users(user_id),
    parent_message_id  INTEGER REFERENCES game_chat_message(message_id),
    content            TEXT NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    edited_at          TIMESTAMP WITH TIME ZONE,
    is_deleted         BOOLEAN DEFAULT FALSE
);

-- Message reactions (emoji)
CREATE TABLE game_chat_reaction (
    reaction_id        SERIAL PRIMARY KEY,
    message_id         INTEGER NOT NULL REFERENCES game_chat_message(message_id),
    user_id            INTEGER NOT NULL REFERENCES users(user_id),
    emoji              TEXT NOT NULL,
    created_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (message_id, user_id, emoji)
);

-- Create indexes for common queries
CREATE INDEX idx_game_chat_message_game_team
    ON game_chat_message(game_id, team_id);

CREATE INDEX idx_game_chat_message_parent
    ON game_chat_message(parent_message_id)
    WHERE parent_message_id IS NOT NULL;

CREATE INDEX idx_game_chat_reaction_message
    ON game_chat_reaction(message_id);

CREATE TABLE team(
    team_id         SERIAL     PRIMARY KEY,
    external_id     INTEGER    DEFAULT 0,
    name            TEXT       NOT NULL
);

CREATE TABLE team_player(
    user_id         INTEGER,
    team_id         INTEGER,
    role            TEXT,
    number          INTEGER,
    pending_status  BOOLEAN,
    joined_at       TIMESTAMP WITH TIME ZONE
);

CREATE TABLE team_goalie(
    id              SERIAL     PRIMARY KEY,
    user_id         INTEGER,
    team_id         INTEGER,
    nickname        TEXT,
    phone_number    TEXT,
    order           INTEGER
);

CREATE TABLE users(
    user_id         SERIAL     PRIMARY KEY,

    external_id     TEXT,

    google_id       TEXT,
    activated       BOOL,

    _password       TEXT,
    salt            TEXT,

    password_reset_token    TEXT,
    password_reset_token_expire_at  TIMESTAMP WITH TIME ZONE;

    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,
    phone_number    TEXT,
    usa_hockey_number TEXT,

    created_at      TIMESTAMP WITH TIME ZONE,
    logged_in_at    TIMESTAMP WITH TIME ZONE,

    admin           BOOL
);

COMMIT;
