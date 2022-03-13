PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

CREATE TABLE game(
    game_id         INTEGER     PRIMARY KEY     NOT NULL,
    scheduled_time  TEXT        NOT NULL,
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

CREATE TABLE team(
    --sqlite: team_id         INTEGER     PRIMARY KEY   AUTOINCREMENT,
    team_id         SERIAL     PRIMARY KEY,
    name            TEXT        NOT NULL
);

CREATE TABLE player(
    --sqlite: player_id         INTEGER     PRIMARY KEY   AUTOINCREMENT,
    player_id       SERIAL     PRIMARY KEY,
    name            TEXT        NOT NULL
);

CREATE TABLE player_team(
    player_id       INTEGER,
    team_id         INTEGER
);

-- sample data
-- insert into team (name) values ("Choking Hazards"), ("Pileons"), ("A-Team");
-- insert into player (name) values ("Jesse Boettcher"), ("Bill Stull"), ("Dave Christie");
-- insert into game (game_id, scheduled_time) values ("Jesse Boettcher"), ("Bill Stull"), ("Dave Christie");

COMMIT;
