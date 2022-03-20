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
    game_type       TEXT ,   -- preseason vs Regular 2
    scoresheet_html_url TEXT,
    scoresheet_pdf_url TEXT
);

CREATE TABLE game_reply(
    reply_id        SERIAL,
    game_id         INTEGER,
    user_id         INTEGER,
    response        TEXT,
    message         TEXT,
    modified_at     TIMESTAMP WITH TIME ZONE
);

CREATE TABLE team(
    team_id         SERIAL     PRIMARY KEY,
    name            TEXT        NOT NULL
);

-- CREATE TABLE player(
--     player_id       SERIAL     PRIMARY KEY,
--     name            TEXT        NOT NULL
-- );

CREATE TABLE team_player(
    user_id         INTEGER,
    team_id         INTEGER,
    role            TEXT
    pending_status  BOOLEAN,
    joined_at       TIMESTAMP WITH TIME ZONE
);

CREATE TABLE users(
    user_id         SERIAL     PRIMARY KEY,

    external_id     TEXT,

    google_id       TEXT,
    activated       BOOL,

    _password       TEXT,

    first_name      TEXT,
    last_name       TEXT,
    email           TEXT,

    created_at      TIMESTAMP WITH TIME ZONE,
    logged_in_at    TIMESTAMP WITH TIME ZONE,

    admin           BOOL
);

-- sample data
-- insert into team (name) values ("Choking Hazards"), ("Pileons"), ("A-Team");
-- insert into player (name) values ("Jesse Boettcher"), ("Bill Stull"), ("Dave Christie");
-- insert into game (game_id, scheduled_time) values ("Jesse Boettcher"), ("Bill Stull"), ("Dave Christie");

COMMIT;
