from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.game_invitation import GameInvitation, GamePlayerPresence
from app.models.game_room import GameRoom
from app.models.restaurant_table import RestaurantTable

router = APIRouter(prefix="/games", tags=["Customer Game Invitations"])

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
GAME_TYPES = {"TIC_TAC_TOE": 9, "CONNECT_FOUR": 42}
PRESENCE_SECONDS = 90
INVITATION_SECONDS = 120


class PresenceRequest(BaseModel):
    visitor_id: UUID
    table_id: int = Field(gt=0)


class InvitationRequest(BaseModel):
    sender_id: UUID
    receiver_id: UUID
    table_id: int = Field(gt=0)
    game_type: str


def validate_table(db: Session, table_id: int) -> None:
    if db.get(RestaurantTable, table_id) is None:
        raise HTTPException(status_code=404, detail="Restaurant table not found")


def get_active_presence(db: Session, visitor_id: str):
    cutoff = datetime.now(UTC) - timedelta(seconds=PRESENCE_SECONDS)
    return (
        db.query(GamePlayerPresence)
        .filter(
            GamePlayerPresence.visitor_id == visitor_id,
            GamePlayerPresence.last_seen >= cutoff,
        )
        .with_for_update()
        .first()
    )


def make_room_code(db: Session) -> str:
    import secrets

    for _ in range(10):
        code = "".join(secrets.choice(ROOM_ALPHABET) for _ in range(6))
        exists = (
            db.query(GameRoom.id)
            .filter(GameRoom.room_code == code)
            .first()
        )
        if exists is None:
            return code

    raise HTTPException(status_code=503, detail="Could not create a game room")


def invitation_response(invitation: GameInvitation) -> dict:
    return {
        "id": invitation.id,
        "sender_id": invitation.sender_id,
        "receiver_id": invitation.receiver_id,
        "sender_table_id": invitation.sender_table_id,
        "receiver_table_id": invitation.receiver_table_id,
        "game_type": invitation.game_type,
        "status": invitation.status,
        "room_code": invitation.room_code,
        "created_at": invitation.created_at,
        "expires_at": invitation.expires_at,
    }


@router.post("/presence")
def update_game_presence(
    payload: PresenceRequest,
    db: Session = Depends(get_db),
):
    validate_table(db, payload.table_id)

    now = datetime.now(UTC)
    statement = insert(GamePlayerPresence).values(
        visitor_id=str(payload.visitor_id),
        table_id=payload.table_id,
        last_seen=now,
    )
    statement = statement.on_conflict_do_update(
        index_elements=["visitor_id"],
        set_={"table_id": payload.table_id, "last_seen": now},
    )
    db.execute(statement)
    db.commit()

    return {
        "visitor_id": str(payload.visitor_id),
        "table_id": payload.table_id,
        "status": "ONLINE",
    }


@router.get("/players")
def list_game_players(
    visitor_id: UUID,
    db: Session = Depends(get_db),
):
    cutoff = datetime.now(UTC) - timedelta(seconds=PRESENCE_SECONDS)

    players = (
        db.query(GamePlayerPresence, RestaurantTable.name)
        .join(RestaurantTable, RestaurantTable.id == GamePlayerPresence.table_id)
        .filter(
            GamePlayerPresence.last_seen >= cutoff,
            GamePlayerPresence.visitor_id != str(visitor_id),
        )
        .order_by(GamePlayerPresence.last_seen.desc())
        .all()
    )

    return {
        "players": [
            {
                "visitor_id": presence.visitor_id,
                "table_id": presence.table_id,
                "table_name": table_name,
                "last_seen": presence.last_seen,
            }
            for presence, table_name in players
        ]
    }


@router.post("/invitations")
def send_game_invitation(
    payload: InvitationRequest,
    db: Session = Depends(get_db),
):
    sender_id = str(payload.sender_id)
    receiver_id = str(payload.receiver_id)
    game_type = payload.game_type.upper()

    if sender_id == receiver_id:
        raise HTTPException(status_code=400, detail="You cannot invite yourself")

    if game_type not in GAME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Game type must be TIC_TAC_TOE or CONNECT_FOUR",
        )

    sender = get_active_presence(db, sender_id)
    receiver = get_active_presence(db, receiver_id)

    if sender is None:
        raise HTTPException(
            status_code=409,
            detail="You are not currently visible as an active player",
        )

    if sender.table_id != payload.table_id:
        raise HTTPException(
            status_code=409,
            detail="Your active table does not match this request",
        )

    if receiver is None:
        raise HTTPException(
            status_code=409,
            detail="This customer is no longer online",
        )

    now = datetime.now(UTC)

    db.query(GameInvitation).filter(
        GameInvitation.status == "PENDING",
        GameInvitation.expires_at <= now,
    ).update({"status": "EXPIRED"}, synchronize_session=False)

    existing = (
        db.query(GameInvitation)
        .filter(
            GameInvitation.status == "PENDING",
            GameInvitation.expires_at > now,
            or_(
                GameInvitation.sender_id == sender_id,
                GameInvitation.receiver_id == sender_id,
            ),
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="You already have a pending game invitation",
        )

    invitation = GameInvitation(
        sender_id=sender_id,
        receiver_id=receiver_id,
        sender_table_id=sender.table_id,
        receiver_table_id=receiver.table_id,
        game_type=game_type,
        status="PENDING",
        expires_at=now + timedelta(seconds=INVITATION_SECONDS),
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return invitation_response(invitation)


@router.get("/invitations")
def list_game_invitations(
    visitor_id: UUID,
    db: Session = Depends(get_db),
):
    now = datetime.now(UTC)

    db.query(GameInvitation).filter(
        GameInvitation.status == "PENDING",
        GameInvitation.expires_at <= now,
    ).update({"status": "EXPIRED"}, synchronize_session=False)
    db.commit()

    invitations = (
        db.query(GameInvitation)
        .filter(
            or_(
                GameInvitation.sender_id == str(visitor_id),
                GameInvitation.receiver_id == str(visitor_id),
            )
        )
        .order_by(GameInvitation.created_at.desc())
        .limit(30)
        .all()
    )

    return {"invitations": [invitation_response(item) for item in invitations]}


@router.post("/invitations/{invitation_id}/accept")
def accept_game_invitation(
    invitation_id: int,
    visitor_id: UUID,
    db: Session = Depends(get_db),
):
    invitation = (
        db.query(GameInvitation)
        .filter(GameInvitation.id == invitation_id)
        .with_for_update()
        .first()
    )

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.receiver_id != str(visitor_id):
        raise HTTPException(
            status_code=403,
            detail="Only the invited customer can accept this invitation",
        )

    if invitation.status != "PENDING":
        raise HTTPException(status_code=409, detail="Invitation is no longer pending")

    now = datetime.now(UTC)
    if invitation.expires_at <= now:
        invitation.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=410, detail="Invitation has expired")

    sender = get_active_presence(db, invitation.sender_id)
    receiver = get_active_presence(db, invitation.receiver_id)

    if sender is None or receiver is None:
        invitation.status = "EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=410,
            detail="A player is no longer online",
        )

    room = GameRoom(
        room_code=make_room_code(db),
        game_type=invitation.game_type,
        board=[None] * GAME_TYPES[invitation.game_type],
        status="ACTIVE",
        current_turn="X",
        player_x_id=invitation.sender_id,
        player_o_id=invitation.receiver_id,
        player_x_table_id=invitation.sender_table_id,
        player_o_table_id=invitation.receiver_table_id,
    )

    db.add(room)
    db.flush()

    invitation.status = "ACCEPTED"
    invitation.room_code = room.room_code

    db.commit()
    db.refresh(invitation)
    db.refresh(room)

    return {
        "invitation": invitation_response(invitation),
        "room": {
            "room_code": room.room_code,
            "game_type": room.game_type,
            "board": room.board,
            "status": room.status,
            "current_turn": room.current_turn,
            "player_x_id": room.player_x_id,
            "player_o_id": room.player_o_id,
        },
    }


@router.post("/invitations/{invitation_id}/decline")
def decline_game_invitation(
    invitation_id: int,
    visitor_id: UUID,
    db: Session = Depends(get_db),
):
    invitation = (
        db.query(GameInvitation)
        .filter(GameInvitation.id == invitation_id)
        .with_for_update()
        .first()
    )

    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.receiver_id != str(visitor_id):
        raise HTTPException(
            status_code=403,
            detail="Only the invited customer can decline this invitation",
        )

    if invitation.status != "PENDING":
        raise HTTPException(status_code=409, detail="Invitation is no longer pending")

    if invitation.expires_at <= datetime.now(UTC):
        invitation.status = "EXPIRED"
        db.commit()
        raise HTTPException(status_code=410, detail="Invitation has expired")

    invitation.status = "DECLINED"
    db.commit()
    db.refresh(invitation)

    return invitation_response(invitation)
