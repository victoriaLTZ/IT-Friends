import uuid
import secrets
from datetime import datetime
from typing import Optional
import random

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, create_engine, Session, select
from fastapi import UploadFile, File
from fastapi.staticfiles import StaticFiles
import os
import shutil

ROSTER = [
    "Horti", "Clem", "Laure", "Margaux", "Eugé",
    "Antoine", "Ellis", "Sab", "Charles", "Vic",
]

TARGET_QUESTION_KEYS = [
    'favorite_book', 'favorite_quote', 'favorite_drink', 'borrowed_object',
    'phobia', 'hidden_talent', 'fun_fact_about_other', 'dream_trip',
    'impulse_purchase', 'looping_song', 'old_style', 'weird_sleep_spot',
]

TEAM_MEMBERSHIP = {
    "charles": "Pastis Pictures", "clem": "Pastis Pictures", "eugé": "Pastis Pictures",
    "ellis": "Studios Curaçao", "margaux": "Studios Curaçao", "laure": "Studios Curaçao",
    "antoine": "Metro-Goldwyn-Martini", "horti": "Metro-Goldwyn-Martini", "sab": "Metro-Goldwyn-Martini",
}

# ---------------------------------------------------------------------------
# Connexion à la base de données
# ---------------------------------------------------------------------------
import os as os_module
DATA_DIR = "/data" if os_module.path.exists("/data") else "."
DATABASE_URL = f"sqlite:///{DATA_DIR}/rallye.db"
engine = create_engine(DATABASE_URL, echo=True)


def generate_access_code():
    return secrets.token_hex(3).upper()  # ex: "A3F9D1"


# ---------------------------------------------------------------------------
# Modèles — équipes
# ---------------------------------------------------------------------------
class TeamPublic(SQLModel):
    id: str
    name: str
    color: str
    stage_index: int
    team_points: int

class Team(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    color: str = "#7A2048"
    stage_index: int = 0
    team_points: int = 0
    suspect_player_id: Optional[str] = Field(default=None, foreign_key="player.id")
    access_password: Optional[str] = None


class TeamCreate(SQLModel):
    name: str
    color: str = "#7A2048"


class AssignTeam(SQLModel):
    team_id: str


# ---------------------------------------------------------------------------
# Modèles — joueurs et profils
# ---------------------------------------------------------------------------
class Player(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    access_code: str = Field(default_factory=generate_access_code, index=True)
    avatar_config: Optional[str] = None  # JSON stocké en texte
    team_id: Optional[str] = Field(default=None, foreign_key="team.id")
    individual_points: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ProfileAnswer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: str = Field(foreign_key="player.id")
    question_key: str
    value: str
    about_player_id: Optional[str] = Field(default=None, foreign_key="player.id")
    about_player_name: Optional[str] = None


class PlayerCreate(SQLModel):
    name: str


class AnswerSubmit(SQLModel):
    question_key: str
    value: str
    about_player_id: Optional[str] = None
    about_player_name: Optional[str] = None

class AnswerAttempt(SQLModel):
    team_id: str
    answer: str

class AvatarUpdate(SQLModel):
    avatar_config: str


# ---------------------------------------------------------------------------
# Modèles — étapes du rallye
# ---------------------------------------------------------------------------
class Stage(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    code: str
    hint: Optional[str] = None
    order: int


class StageCreate(SQLModel):
    name: str
    code: str
    hint: Optional[str] = None
    order: int

# ---------------------------------------------------------------------------
# Modèles - controle du jeu / pages
# ---------------------------------------------------------------------------

class CodeSubmit(SQLModel):
    code: str

class GameState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phase: str = "locked"  # "locked" | "alert" | "playing"
    rally_finished: bool = False

class PhaseUpdate(SQLModel):
    phase: str

# ---------------------------------------------------------------------------
# Modèles - Trial
# ---------------------------------------------------------------------------

class TrialState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    active: bool = False
    revealed: bool = False

class TrialVote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    voter_player_id: str = Field(foreign_key="player.id")
    suspect_player_id: str = Field(foreign_key="player.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class VoteSubmit(SQLModel):
    voter_player_id: str
    suspect_player_id: str


class SuspectAssign(SQLModel):
    suspect_player_id: str

# ---------------------------------------------------------------------------
# Modèles — questions bonus (buzzer)
# ---------------------------------------------------------------------------
class BonusQuestion(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    prompt: str
    image_url: Optional[str] = None
    correct_answer: Optional[str] = None
    winner_team_id: Optional[str] = None
    active: bool = True



class Buzz(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bonus_id: str = Field(foreign_key="bonusquestion.id")
    team_id: str = Field(foreign_key="team.id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class TeamStationOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: str = Field(foreign_key="team.id")
    stage_id: str = Field(foreign_key="stage.id")
    position: int

class Clue(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    stage_id: str = Field(foreign_key="stage.id")
    team_id: str = Field(foreign_key="team.id")
    target_player_id: str = Field(foreign_key="player.id")
    text: str
    kind: str = "neutre"
    image_url : Optional[str] = None

class TeamStationOrderCreate(SQLModel):
    team_id: str
    stage_id: str
    position: int

class ClueCreate(SQLModel):
    stage_id: str
    team_id: str
    target_player_id: str
    text: str
    kind: str = "neutre"
    image_url:  Optional[str] = None

class BonusCreate(SQLModel):
    prompt: str
    image_url: Optional[str] = None
    correct_answer: Optional[str] = None


# ---------------------------------------------------------------------------
# Création des tables
# ---------------------------------------------------------------------------
SQLModel.metadata.create_all(engine)

def ensure_column(table: str, column: str, col_type: str = "TEXT"):
    with engine.connect() as conn:
        result = conn.exec_driver_sql(f"PRAGMA table_info({table})")
        existing_columns = [row[1] for row in result]
        if column not in existing_columns:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            conn.commit()

ensure_column("team", "suspect_player_id", "TEXT")
ensure_column("team", "clue_penalty", "INTEGER DEFAULT 0")
ensure_column("clue", "created_at", "TEXT")
ensure_column("bonusquestion", "image_url", "TEXT")
ensure_column("bonusquestion", "correct_answer", "TEXT")
ensure_column("bonusquestion", "winner_team_id", "TEXT")
ensure_column("gamestate", "rally_finished", "BOOLEAN DEFAULT 0")

# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = f"{DATA_DIR}/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# ---------------------------------------------------------------------------
# Gestion des connexions WebSocket
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Santé du serveur
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Le serveur du rallye tourne !"}


# ---------------------------------------------------------------------------
# Joueurs
# ---------------------------------------------------------------------------

def resolve_pending_answers_for(session: Session, player: Player):
    pending = session.exec(
        select(ProfileAnswer).where(
            ProfileAnswer.about_player_id == None,
            ProfileAnswer.about_player_name.ilike(player.name),
        )
    ).all()
    for a in pending:
        a.about_player_id = player.id
        session.add(a)
    if pending:
        session.commit()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/uploads/{filename}"}

@app.post("/api/players", response_model=Player)
def create_player(data: PlayerCreate):
    roster_lower = [n.lower() for n in ROSTER]
    if data.name.lower() not in roster_lower:
        raise HTTPException(status_code=400, detail=f"{data.name} n'est pas dans la liste des participants")

    with Session(engine) as session:
        existing = session.exec(
            select(Player).where(Player.name.ilike(data.name))
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"{data.name} a déjà un profil créé. Utilise ton code personnel pour le reprendre.")

        player = Player(name=data.name)

        team_name = TEAM_MEMBERSHIP.get(data.name.lower())
        if team_name:
            team = session.exec(select(Team).where(Team.name == team_name)).first()
            if team:
                player.team_id = team.id

        session.add(player)
        session.commit()
        session.refresh(player)
        resolve_pending_answers_for(session, player)
        return player

@app.post("/api/assign-teams-from-roster")
def assign_teams_from_roster():
    with Session(engine) as session:
        updated = []
        for name_lower, team_name in TEAM_MEMBERSHIP.items():
            player = session.exec(select(Player).where(Player.name.ilike(name_lower))).first()
            if not player:
                continue
            team = session.exec(select(Team).where(Team.name == team_name)).first()
            if not team:
                continue
            player.team_id = team.id
            session.add(player)
            updated.append({"player": player.name, "team": team.name})
        session.commit()
        return updated


@app.get("/api/players", response_model=list[Player])
def list_players():
    with Session(engine) as session:
        return session.exec(select(Player)).all()


@app.get("/api/players/{player_id}")
def get_player(player_id: str):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")
        answers = session.exec(
            select(ProfileAnswer).where(ProfileAnswer.player_id == player_id)
        ).all()
        return {
            "player": player,
            "answers": {a.question_key: a.value for a in answers},
        }


@app.get("/api/players/by-code/{access_code}")
def get_player_by_code(access_code: str):
    with Session(engine) as session:
        player = session.exec(
            select(Player).where(Player.access_code == access_code.upper())
        ).first()
        if not player:
            raise HTTPException(status_code=404, detail="Code invalide")
        answers = session.exec(
            select(ProfileAnswer).where(ProfileAnswer.player_id == player.id)
        ).all()
        return {
            "player": player,
            "answers": {a.question_key: a.value for a in answers},
        }

@app.get("/api/players/{player_id}/target-for-question/{question_key}")
def get_target_for_question(player_id: str, question_key: str):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")

        roster_lower = [n.lower() for n in ROSTER]
        if player.name.lower() not in roster_lower:
            raise HTTPException(status_code=400, detail="Ton prénom n'est pas reconnu")
        idx = roster_lower.index(player.name.lower())

        if question_key not in TARGET_QUESTION_KEYS:
            raise HTTPException(status_code=400, detail="Question inconnue")
        qpos = TARGET_QUESTION_KEYS.index(question_key)

        n = len(ROSTER)
        offset = (qpos % (n - 1)) + 1
        target_name = ROSTER[(idx + offset) % n]

        target_player = session.exec(
            select(Player).where(Player.name.ilike(target_name))
        ).first()

        return {
            "target_name": target_name,
            "target_id": target_player.id if target_player else None,
        }

@app.post("/api/players/{player_id}/answers")
def submit_answer(player_id: str, data: AnswerSubmit):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")

        about_id = data.about_player_id
        if not about_id and data.about_player_name:
            target = session.exec(
                select(Player).where(Player.name.ilike(data.about_player_name))
            ).first()
            if target:
                about_id = target.id

        existing = session.exec(
            select(ProfileAnswer).where(
                ProfileAnswer.player_id == player_id,
                ProfileAnswer.question_key == data.question_key,
            )
        ).first()

        if existing:
            existing.value = data.value
            existing.about_player_id = about_id
            existing.about_player_name = data.about_player_name
            session.add(existing)
        else:
            session.add(ProfileAnswer(
                player_id=player_id,
                question_key=data.question_key,
                value=data.value,
                about_player_id=about_id,
                about_player_name=data.about_player_name,
            ))

        session.commit()
        return {"saved": True, "question_key": data.question_key}
    
@app.post("/api/players/{player_id}/answers/bulk")
def submit_answers_bulk(player_id: str, data: list[AnswerSubmit]):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")

        for item in data:
            existing = session.exec(
                select(ProfileAnswer).where(
                    ProfileAnswer.player_id == player_id,
                    ProfileAnswer.question_key == item.question_key,
                )
            ).first()
            if existing:
                existing.value = item.value
                existing.about_player_id = item.about_player_id
                session.add(existing)
            else:
                session.add(ProfileAnswer(
                    player_id=player_id,
                    question_key=item.question_key,
                    value=item.value,
                    about_player_id=item.about_player_id,
                ))

        session.commit()
        return {"saved": len(data)}
    
@app.put("/api/players/{player_id}/avatar")
def update_avatar(player_id: str, data: AvatarUpdate):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")
        player.avatar_config = data.avatar_config
        session.add(player)
        session.commit()
        return {"saved": True}


@app.post("/api/players/{player_id}/team", response_model=Player)
def assign_team(player_id: str, data: AssignTeam):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")
        team = session.get(Team, data.team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Équipe introuvable")
        player.team_id = data.team_id
        session.add(player)
        session.commit()
        session.refresh(player)
        return player

@app.delete("/api/players/{player_id}")
def delete_player(player_id: str):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")

        answers = session.exec(
            select(ProfileAnswer).where(ProfileAnswer.player_id == player_id)
        ).all()
        for a in answers:
            session.delete(a)

        session.delete(player)
        session.commit()
        return {"deleted": True, "id": player_id}

# ---------------------------------------------------------------------------
# Équipes
# ---------------------------------------------------------------------------
@app.post("/api/teams", response_model=Team)
def create_team(data: TeamCreate):
    team = Team(**data.dict())
    with Session(engine) as session:
        session.add(team)
        session.commit()
        session.refresh(team)
        return team

@app.post("/api/draw-suspects")
def draw_suspects():
    with Session(engine) as session:
        teams = session.exec(select(Team)).all()
        if not teams:
            raise HTTPException(status_code=400, detail="Aucune équipe créée")

        results = []
        for team in teams:
            members = session.exec(select(Player).where(Player.team_id == team.id)).all()
            if not members:
                raise HTTPException(status_code=400, detail=f"L'équipe {team.name} n'a aucun membre")

            suspect = random.choice(members)
            team.suspect_player_id = suspect.id
            session.add(team)
            results.append({"team": team.name, "suspect": suspect.name})

        session.commit()
        return results


@app.put("/api/teams/{team_id}/suspect")
def set_team_suspect(team_id: str, data: SuspectAssign):
    with Session(engine) as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Équipe introuvable")
        player = session.get(Player, data.suspect_player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")
        team.suspect_player_id = data.suspect_player_id
        session.add(team)
        session.commit()
        return {"team": team.name, "suspect": player.name}

@app.get("/api/teams", response_model=list[TeamPublic])
def list_teams():
    with Session(engine) as session:
        return session.exec(select(Team)).all()

@app.delete("/api/players/{player_id}/team")
def remove_from_team(player_id: str):
    with Session(engine) as session:
        player = session.get(Player, player_id)
        if not player:
            raise HTTPException(status_code=404, detail="Joueur introuvable")
        player.team_id = None
        session.add(player)
        session.commit()
        return {"detached": True}

@app.delete("/api/teams/{team_id}")
def delete_team(team_id: str):
    with Session(engine) as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Équipe introuvable")

        players = session.exec(select(Player).where(Player.team_id == team_id)).all()
        for p in players:
            p.team_id = None
            session.add(p)

        orders = session.exec(select(TeamStationOrder).where(TeamStationOrder.team_id == team_id)).all()
        for o in orders:
            session.delete(o)

        clues = session.exec(select(Clue).where(Clue.team_id == team_id)).all()
        for c in clues:
            session.delete(c)

        buzzes = session.exec(select(Buzz).where(Buzz.team_id == team_id)).all()
        for b in buzzes:
            session.delete(b)

        session.delete(team)
        session.commit()
        return {"deleted": True, "id": team_id}

# ---------------------------------------------------------------------------
# Gestion des pages
# ---------------------------------------------------------------------------
def get_or_create_game_state(session: Session) -> GameState:
    state = session.exec(select(GameState)).first()
    if not state:
        state = GameState(phase="locked")
        session.add(state)
        session.commit()
        session.refresh(state)
    return state

@app.get("/api/game-state")
def get_game_state():
    with Session(engine) as session:
        state = get_or_create_game_state(session)
        return {"phase": state.phase}

@app.post("/api/game-state")
async def set_game_state(data: PhaseUpdate):
    if data.phase not in ["locked", "alert", "playing"]:
        raise HTTPException(status_code=400, detail="Phase invalide")
    with Session(engine) as session:
        state = get_or_create_game_state(session)
        state.phase = data.phase
        session.add(state)
        session.commit()

    await manager.broadcast({"event": "phase_changed", "phase": data.phase})
    return {"phase": data.phase}

# ---------------------------------------------------------------------------
# Étapes du rallye
# ---------------------------------------------------------------------------
@app.post("/api/stages", response_model=Stage)
def create_stage(data: StageCreate):
    stage = Stage(**data.dict())
    with Session(engine) as session:
        session.add(stage)
        session.commit()
        session.refresh(stage)
        return stage

@app.post("/api/stages/bulk", response_model=list[Stage])
def create_stages_bulk(data: list[StageCreate]):
    with Session(engine) as session:
        stages = [Stage(**s.dict()) for s in data]
        session.add_all(stages)
        session.commit()
        for s in stages:
            session.refresh(s)
        return stages
    
@app.get("/api/stages", response_model=list[Stage])
def list_stages():
    with Session(engine) as session:
        return session.exec(select(Stage).order_by(Stage.order)).all()


@app.put("/api/stages/{stage_id}", response_model=Stage)
def update_stage(stage_id: str, data: StageCreate):
    with Session(engine) as session:
        stage = session.get(Stage, stage_id)
        if not stage:
            raise HTTPException(status_code=404, detail="Étape introuvable")
        stage.name = data.name
        stage.code = data.code
        stage.hint = data.hint
        stage.order = data.order
        session.add(stage)
        session.commit()
        session.refresh(stage)
        return stage


@app.delete("/api/stages/{stage_id}")
def delete_stage(stage_id: str):
    with Session(engine) as session:
        stage = session.get(Stage, stage_id)
        if not stage:
            raise HTTPException(status_code=404, detail="Étape introuvable")
        session.delete(stage)
        session.commit()
        return {"deleted": True, "id": stage_id}

@app.post("/api/team-station-order/bulk")
def create_order_bulk(data: list[TeamStationOrderCreate]):
    with Session(engine) as session:
        entries = [TeamStationOrder(**d.dict()) for d in data]
        session.add_all(entries)
        session.commit()
        return {"created": len(entries)}

@app.get("/api/teams/{team_id}/current-station")
def get_current_station(team_id: str):
    with Session(engine) as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Équipe introuvable")

        order_entry = session.exec(
            select(TeamStationOrder).where(
                TeamStationOrder.team_id == team_id,
                TeamStationOrder.position == team.stage_index,
            )
        ).first()
        if not order_entry:
            return {"finished": True}

        station = session.get(Stage, order_entry.stage_id)
        return {"riddle": station.hint, "position": team.stage_index, "finished": False}


@app.post("/api/clues/bulk")
def create_clues_bulk(data: list[ClueCreate]):
    with Session(engine) as session:
        clues = [Clue(**d.dict()) for d in data]
        session.add_all(clues)
        session.commit()
        return {"created": len(clues)}

@app.get("/api/teams/{team_id}/clues")
def get_team_clues(team_id: str):
    with Session(engine) as session:
        clues = session.exec(select(Clue).where(Clue.team_id == team_id)).all()
        result = []
        for c in clues:
            target = session.get(Player, c.target_player_id)
            stage = session.get(Stage, c.stage_id)
            result.append({
                "station": stage.name,
                "target_player": target.name,
                "text": c.text,
                "kind": c.kind,
                "image_url": c.image_url,
            })
        return result
    
@app.post("/api/teams/{team_id}/submit-code")
async def submit_code(team_id: str, data: CodeSubmit):
    with Session(engine) as session:
        team = session.get(Team, team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Équipe introuvable")

        order_entry = session.exec(
            select(TeamStationOrder).where(
                TeamStationOrder.team_id == team_id,
                TeamStationOrder.position == team.stage_index,
            )
        ).first()
        if not order_entry:
            raise HTTPException(status_code=400, detail="Le parcours est déjà terminé pour cette équipe")

        station = session.get(Stage, order_entry.stage_id)
        if data.code.strip().upper() != station.code.strip().upper():
            return {"correct": False, "message": "Code incorrect"}

        team.stage_index += 1
        team.team_points += 10
        session.add(team)
        session.commit()
        session.refresh(team)

        # ... après team.stage_index += 1, team.team_points += 10, session.commit(), session.refresh(team)

        all_stations_count = session.exec(select(Stage)).all()
        if team.stage_index >= len(all_stations_count):
            state = get_or_create_game_state(session)
            if not state.rally_finished:
                state.rally_finished = True
                session.add(state)
                session.commit()

                all_teams = session.exec(select(Team)).all()
                standings = sorted(all_teams, key=lambda t: t.team_points, reverse=True)
                await manager.broadcast({
                    "event": "rally_finished",
                    "winner_team_id": team.id,
                    "standings": [{"name": t.name, "points": t.team_points, "color": t.color} for t in standings],
                })

        clue = session.exec(
            select(Clue).where(Clue.stage_id == station.id, Clue.team_id == team_id)
        ).first()
        clue_data = None
        if clue:
            target = session.get(Player, clue.target_player_id)
            clue_data = {"target_player": target.name, "text": clue.text, "kind": clue.kind}

        await manager.broadcast({
            "event": "team_advanced",
            "team_id": team.id,
            "stage_index": team.stage_index,
            "team_points": team.team_points,
        })

        return {"correct": True, "message": "Bravo, vous avancez !", "team": team, "clue": clue_data}

@app.post("/api/bonus/{bonus_id}/answer")
async def submit_bonus_answer(bonus_id: str, data: AnswerAttempt):
    with Session(engine) as session:
        bonus = session.get(BonusQuestion, bonus_id)
        if not bonus or not bonus.active:
            return {"correct": False, "already_resolved": True}

        given = data.answer.strip().lower()
        expected = (bonus.correct_answer or "").strip().lower()
        if not expected or given != expected:
            return {"correct": False}

        team = session.get(Team, data.team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Équipe introuvable")

        bonus.active = False
        bonus.winner_team_id = team.id
        session.add(bonus)

        team.team_points += 10
        session.add(team)
        session.commit()
        session.refresh(team)

    await manager.broadcast({
        "event": "bonus_won",
        "bonus_id": bonus_id,
        "team_id": team.id,
        "team_name": team.name,
        "team_points": team.team_points,
    })
    return {"correct": True, "team_points": team.team_points}

# ---------------------------------------------------------------------------
# Endpoints du procès ------ 
# ---------------------------------------------------------------------------

def get_or_create_trial_state(session: Session) -> TrialState:
    state = session.exec(select(TrialState)).first()
    if not state:
        state = TrialState(active=False, revealed=False)
        session.add(state)
        session.commit()
        session.refresh(state)
    return state


@app.get("/api/trial/suspects")
def get_trial_suspects():
    with Session(engine) as session:
        teams = session.exec(select(Team)).all()
        result = []
        for team in teams:
            if not team.suspect_player_id:
                continue
            suspect = session.get(Player, team.suspect_player_id)
            result.append({
                "suspect_id": suspect.id,
                "suspect_name": suspect.name,
                "team_name": team.name,
                "team_color": team.color,
            })
        return result


@app.post("/api/trial/start")
async def start_trial():
    with Session(engine) as session:
        state = get_or_create_trial_state(session)
        state.active = True
        state.revealed = False
        session.add(state)
        session.commit()

    await manager.broadcast({"event": "trial_started"})
    return {"started": True}


@app.post("/api/trial/vote")
async def submit_vote(data: VoteSubmit):
    with Session(engine) as session:
        state = get_or_create_trial_state(session)
        if not state.active:
            raise HTTPException(status_code=400, detail="Le vote n'est pas ouvert")

        teams = session.exec(select(Team)).all()
        suspect_ids = [t.suspect_player_id for t in teams if t.suspect_player_id]
        if data.voter_player_id in suspect_ids:
            raise HTTPException(status_code=403, detail="Les accusés ne peuvent pas voter")

        existing = session.exec(
            select(TrialVote).where(TrialVote.voter_player_id == data.voter_player_id)
        ).first()
        if existing:
            existing.suspect_player_id = data.suspect_player_id
            existing.timestamp = datetime.utcnow()
            session.add(existing)
        else:
            session.add(TrialVote(
                voter_player_id=data.voter_player_id,
                suspect_player_id=data.suspect_player_id,
            ))
        session.commit()

    await manager.broadcast({"event": "vote_cast"})
    return {"voted": True}


@app.get("/api/trial/results")
def get_trial_results():
    with Session(engine) as session:
        votes = session.exec(select(TrialVote)).all()
        tally = {}
        for v in votes:
            tally[v.suspect_player_id] = tally.get(v.suspect_player_id, 0) + 1

        suspects = get_trial_suspects()
        results = []
        for s in suspects:
            results.append({
                **s,
                "vote_count": tally.get(s["suspect_id"], 0),
            })
        results.sort(key=lambda r: r["vote_count"], reverse=True)
        return {"results": results, "total_votes": len(votes)}


@app.post("/api/trial/end")
async def end_trial():
    with Session(engine) as session:
        state = get_or_create_trial_state(session)
        state.active = False
        state.revealed = True
        session.add(state)
        session.commit()

    results = get_trial_results()
    await manager.broadcast({"event": "trial_ended", "results": results})
    return results

# ---------------------------------------------------------------------------
# Questions bonus (buzzer)
# ---------------------------------------------------------------------------
@app.post("/api/bonus", response_model=BonusQuestion)
async def start_bonus(data: BonusCreate):
    bonus = BonusQuestion(prompt=data.prompt, image_url=data.image_url, correct_answer=data.correct_answer, active=True)
    with Session(engine) as session:
        session.add(bonus)
        session.commit()
        session.refresh(bonus)

    await manager.broadcast({
        "event": "bonus_started",
        "bonus_id": bonus.id,
        "prompt": bonus.prompt,
        "image_url": bonus.image_url,
    })
    return bonus


@app.post("/api/bonus/{bonus_id}/end")
async def end_bonus(bonus_id: str):
    with Session(engine) as session:
        bonus = session.get(BonusQuestion, bonus_id)
        if not bonus:
            raise HTTPException(status_code=404, detail="Question introuvable")
        bonus.active = False
        session.add(bonus)
        session.commit()

    await manager.broadcast({"event": "bonus_ended", "bonus_id": bonus_id})
    return {"ended": True}

    
# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

from fastapi.responses import FileResponse

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path == "" or full_path == "/":
        full_path = "index.html"
    file_path = f"frontend/{full_path}"
    if os.path.exists(file_path) and not full_path.startswith("api"):
        return FileResponse(file_path)
    return FileResponse("frontend/index.html")