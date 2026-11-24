from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.game_invitation import GameInvitation, GamePlayerPresence
from app.models.game_room import GameRoom
from app.models.restaurant_table import RestaurantTable

client = TestClient(app)


def create_test_table():
    with SessionLocal() as db:
        table = RestaurantTable(
            table_number=f"GAME-{uuid4().hex[:8]}",
            name="Game Invitation Test Table",
            status="FREE",
        )
        db.add(table)
        db.commit()
        db.refresh(table)
        return table.id


def cleanup_game_data(visitor_ids, table_ids):
    with SessionLocal() as db:
        db.query(GameInvitation).filter(
            (GameInvitation.sender_id.in_(visitor_ids))
            | (GameInvitation.receiver_id.in_(visitor_ids))
        ).delete(synchronize_session=False)

        db.query(GameRoom).filter(
            (GameRoom.player_x_id.in_(visitor_ids))
            | (GameRoom.player_o_id.in_(visitor_ids))
        ).delete(synchronize_session=False)

        db.query(GamePlayerPresence).filter(
            GamePlayerPresence.visitor_id.in_(visitor_ids)
        ).delete(synchronize_session=False)

        db.query(RestaurantTable).filter(
            RestaurantTable.id.in_(table_ids)
        ).delete(synchronize_session=False)

        db.commit()


def register_player(visitor_id, table_id):
    return client.post(
        "/api/v1/games/presence",
        json={"visitor_id": visitor_id, "table_id": table_id},
    )


def test_customer_can_invite_another_customer_and_start_game():
    first_table = create_test_table()
    second_table = create_test_table()
    player_one = str(uuid4())
    player_two = str(uuid4())
    visitor_ids = [player_one, player_two]
    table_ids = [first_table, second_table]

    try:
        assert register_player(player_one, first_table).status_code == 200
        assert register_player(player_two, second_table).status_code == 200

        players_response = client.get(
            "/api/v1/games/players",
            params={"visitor_id": player_one},
        )
        assert players_response.status_code == 200
        players = players_response.json()["players"]
        assert any(player["visitor_id"] == player_two for player in players)

        invitation_response = client.post(
            "/api/v1/games/invitations",
            json={
                "sender_id": player_one,
                "receiver_id": player_two,
                "table_id": first_table,
                "game_type": "TIC_TAC_TOE",
            },
        )
        assert invitation_response.status_code == 200
        invitation = invitation_response.json()
        assert invitation["status"] == "PENDING"
        invitation_id = invitation["id"]

        receiver_invitations = client.get(
            "/api/v1/games/invitations",
            params={"visitor_id": player_two},
        )
        assert receiver_invitations.status_code == 200
        assert any(
            item["id"] == invitation_id
            for item in receiver_invitations.json()["invitations"]
        )

        accept_response = client.post(
            f"/api/v1/games/invitations/{invitation_id}/accept",
            params={"visitor_id": player_two},
        )
        assert accept_response.status_code == 200

        result = accept_response.json()
        assert result["invitation"]["status"] == "ACCEPTED"
        assert result["room"]["status"] == "ACTIVE"
        assert result["room"]["game_type"] == "TIC_TAC_TOE"
        assert result["room"]["player_x_id"] == player_one
        assert result["room"]["player_o_id"] == player_two
        assert len(result["room"]["board"]) == 9

        room_code = result["room"]["room_code"]

        player_one_room = client.get(
            f"/api/v1/games/rooms/{room_code}",
            params={"player_id": player_one},
        )
        player_two_room = client.get(
            f"/api/v1/games/rooms/{room_code}",
            params={"player_id": player_two},
        )

        assert player_one_room.status_code == 200
        assert player_two_room.status_code == 200
        assert player_one_room.json()["player_role"] == "X"
        assert player_two_room.json()["player_role"] == "O"
    finally:
        cleanup_game_data(visitor_ids, table_ids)


def test_customer_can_decline_game_invitation():
    first_table = create_test_table()
    second_table = create_test_table()
    player_one = str(uuid4())
    player_two = str(uuid4())
    visitor_ids = [player_one, player_two]
    table_ids = [first_table, second_table]

    try:
        register_player(player_one, first_table)
        register_player(player_two, second_table)

        invitation_response = client.post(
            "/api/v1/games/invitations",
            json={
                "sender_id": player_one,
                "receiver_id": player_two,
                "table_id": first_table,
                "game_type": "CONNECT_FOUR",
            },
        )
        assert invitation_response.status_code == 200
        invitation_id = invitation_response.json()["id"]

        decline_response = client.post(
            f"/api/v1/games/invitations/{invitation_id}/decline",
            params={"visitor_id": player_two},
        )

        assert decline_response.status_code == 200
        assert decline_response.json()["status"] == "DECLINED"
        assert decline_response.json()["room_code"] is None
    finally:
        cleanup_game_data(visitor_ids, table_ids)


def test_only_invited_customer_can_accept_invitation():
    first_table = create_test_table()
    second_table = create_test_table()
    player_one = str(uuid4())
    player_two = str(uuid4())
    stranger = str(uuid4())
    visitor_ids = [player_one, player_two, stranger]
    table_ids = [first_table, second_table]

    try:
        register_player(player_one, first_table)
        register_player(player_two, second_table)

        invitation_response = client.post(
            "/api/v1/games/invitations",
            json={
                "sender_id": player_one,
                "receiver_id": player_two,
                "table_id": first_table,
                "game_type": "TIC_TAC_TOE",
            },
        )
        assert invitation_response.status_code == 200
        invitation_id = invitation_response.json()["id"]

        response = client.post(
            f"/api/v1/games/invitations/{invitation_id}/accept",
            params={"visitor_id": stranger},
        )

        assert response.status_code == 403
    finally:
        cleanup_game_data(visitor_ids, table_ids)


def test_expired_invitation_cannot_be_accepted():
    first_table = create_test_table()
    second_table = create_test_table()
    player_one = str(uuid4())
    player_two = str(uuid4())
    visitor_ids = [player_one, player_two]
    table_ids = [first_table, second_table]

    try:
        register_player(player_one, first_table)
        register_player(player_two, second_table)

        invitation_response = client.post(
            "/api/v1/games/invitations",
            json={
                "sender_id": player_one,
                "receiver_id": player_two,
                "table_id": first_table,
                "game_type": "TIC_TAC_TOE",
            },
        )
        assert invitation_response.status_code == 200
        invitation_id = invitation_response.json()["id"]

        with SessionLocal() as db:
            invitation = db.get(GameInvitation, invitation_id)
            invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()

        response = client.post(
            f"/api/v1/games/invitations/{invitation_id}/accept",
            params={"visitor_id": player_two},
        )

        assert response.status_code == 410

        with SessionLocal() as db:
            invitation = db.get(GameInvitation, invitation_id)
            assert invitation.status == "EXPIRED"
    finally:
        cleanup_game_data(visitor_ids, table_ids)


def test_customers_at_same_table_can_invite_each_other():
    table_id = create_test_table()
    player_one = str(uuid4())
    player_two = str(uuid4())
    visitor_ids = [player_one, player_two]

    try:
        assert register_player(player_one, table_id).status_code == 200
        assert register_player(player_two, table_id).status_code == 200

        invitation_response = client.post(
            "/api/v1/games/invitations",
            json={
                "sender_id": player_one,
                "receiver_id": player_two,
                "table_id": table_id,
                "game_type": "CONNECT_FOUR",
            },
        )

        assert invitation_response.status_code == 200
        invitation_id = invitation_response.json()["id"]

        accept_response = client.post(
            f"/api/v1/games/invitations/{invitation_id}/accept",
            params={"visitor_id": player_two},
        )

        assert accept_response.status_code == 200
        result = accept_response.json()

        assert result["invitation"]["status"] == "ACCEPTED"
        assert result["room"]["status"] == "ACTIVE"
        assert result["room"]["game_type"] == "CONNECT_FOUR"
        assert result["room"]["player_x_id"] == player_one
        assert result["room"]["player_o_id"] == player_two
    finally:
        cleanup_game_data(visitor_ids, [table_id])
