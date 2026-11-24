import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.game_room import GameRoom
from app.models.restaurant_table import RestaurantTable

router = APIRouter(prefix="/games", tags=["Customer Games"])

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
GAME_TYPES = {"TIC_TAC_TOE": 9, "CONNECT_FOUR": 42}


class CreateRoomRequest(BaseModel):
    game_type: str
    player_id: UUID
    table_id: int = Field(gt=0)


class JoinRoomRequest(BaseModel):
    player_id: UUID
    table_id: int = Field(gt=0)


class GameMoveRequest(BaseModel):
    player_id: UUID
    position: int = Field(ge=0, le=41)


def validate_table(db: Session, table_id: int) -> None:
    if db.get(RestaurantTable, table_id) is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")


def get_room(db: Session, room_code: str, lock: bool = False) -> GameRoom:
    query = db.query(GameRoom).filter(
        GameRoom.room_code == room_code.upper()
    )
    if lock:
        query = query.with_for_update()

    room = query.first()
    if room is None:
        raise HTTPException(status_code=404, detail="Game room not found")
    return room


def player_role(room: GameRoom, player_id: UUID) -> str | None:
    visitor_id = str(player_id)
    if room.player_x_id == visitor_id:
        return "X"
    if room.player_o_id == visitor_id:
        return "O"
    return None


def room_response(room: GameRoom, player_id: UUID) -> dict:
    return {
        "room_code": room.room_code,
        "game_type": room.game_type,
        "board": room.board,
        "status": room.status,
        "current_turn": room.current_turn,
        "winner": room.winner,
        "player_role": player_role(room, player_id),
        "player_x_table_id": room.player_x_table_id,
        "player_o_table_id": room.player_o_table_id,
    }


def find_winner(board: list, game_type: str) -> str | None:
    if game_type == "TIC_TAC_TOE":
        lines = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        for first, second, third in lines:
            if board[first] and board[first] == board[second] == board[third]:
                return board[first]
        return None

    rows, columns = 6, 7
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

    for row in range(rows):
        for column in range(columns):
            token = board[row * columns + column]
            if token is None:
                continue

            for row_step, column_step in directions:
                end_row = row + 3 * row_step
                end_column = column + 3 * column_step
                if not (0 <= end_row < rows and 0 <= end_column < columns):
                    continue

                positions = [
                    (row + step * row_step) * columns
                    + column + step * column_step
                    for step in range(4)
                ]
                if all(board[position] == token for position in positions):
                    return token

    return None


@router.post("/rooms")
def create_game_room(
    payload: CreateRoomRequest,
    db: Session = Depends(get_db),
):
    game_type = payload.game_type.upper()
    if game_type not in GAME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Game type must be TIC_TAC_TOE or CONNECT_FOUR",
        )

    validate_table(db, payload.table_id)

    room_code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
    while db.query(GameRoom).filter(GameRoom.room_code == room_code).first():
        room_code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))

    room = GameRoom(
        room_code=room_code,
        game_type=game_type,
        board=[None] * GAME_TYPES[game_type],
        status="WAITING",
        current_turn="X",
        player_x_id=str(payload.player_id),
        player_x_table_id=payload.table_id,
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    return room_response(room, payload.player_id)


@router.post("/rooms/{room_code}/join")
def join_game_room(
    room_code: str,
    payload: JoinRoomRequest,
    db: Session = Depends(get_db),
):
    validate_table(db, payload.table_id)
    room = get_room(db, room_code, lock=True)
    visitor_id = str(payload.player_id)

    if room.player_x_id == visitor_id:
        return room_response(room, payload.player_id)

    if room.player_o_id == visitor_id:
        return room_response(room, payload.player_id)

    if room.status != "WAITING" or room.player_o_id is not None:
        raise HTTPException(status_code=409, detail="This game room is full")

    room.player_o_id = visitor_id
    room.player_o_table_id = payload.table_id
    room.status = "ACTIVE"
    db.commit()
    db.refresh(room)

    return room_response(room, payload.player_id)


@router.get("/rooms/{room_code}")
def get_game_room(
    room_code: str,
    player_id: UUID,
    db: Session = Depends(get_db),
):
    room = get_room(db, room_code)
    return room_response(room, player_id)


@router.post("/rooms/{room_code}/move")
def make_game_move(
    room_code: str,
    payload: GameMoveRequest,
    db: Session = Depends(get_db),
):
    room = get_room(db, room_code, lock=True)
    role = player_role(room, payload.player_id)

    if role is None:
        raise HTTPException(status_code=403, detail="You are not a player in this room")

    if room.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="This game is not active")

    if role != room.current_turn:
        raise HTTPException(status_code=409, detail="It is not your turn")

    board = list(room.board)

    if room.game_type == "TIC_TAC_TOE":
        if payload.position >= 9:
            raise HTTPException(status_code=400, detail="Invalid board position")
        if board[payload.position] is not None:
            raise HTTPException(status_code=409, detail="That square is already taken")
        board[payload.position] = role
    else:
        column = payload.position % 7
        available_row = None
        for row in range(5, -1, -1):
            index = row * 7 + column
            if board[index] is None:
                available_row = row
                break

        if available_row is None:
            raise HTTPException(status_code=409, detail="That column is full")

        board[available_row * 7 + column] = role

    room.board = board
    winner = find_winner(board, room.game_type)

    if winner:
        room.winner = winner
        room.status = "FINISHED"
        room.current_turn = None
    elif all(cell is not None for cell in board):
        room.status = "DRAW"
        room.current_turn = None
    else:
        room.current_turn = "O" if role == "X" else "X"

    db.commit()
    db.refresh(room)

    return room_response(room, payload.player_id)
