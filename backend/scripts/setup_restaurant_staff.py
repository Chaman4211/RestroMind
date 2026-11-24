import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.staff_user import StaffUser

OWNER_ID = 21
OWNER_EMAIL = "chamanafzaal01@gmail.com"

TEST_NAME_PATTERN = "Permission Test %"
TEST_EMAIL_PATTERN = "permission-%@example.com"

TEAM = [
    ("Ahmed Raza", "ahmed.raza.manager@restromind.test", "0300-0000001", "MANAGER"),
    ("Usman Tariq", "usman.tariq.chef@restromind.test", "0300-0000002", "HEAD_CHEF"),
    ("Bilal Ahmed", "bilal.ahmed.chef@restromind.test", "0300-0000003", "CHEF"),
    (
        "Hamza Ali",
        "hamza.ali.kitchen@restromind.test",
        "0300-0000004",
        "KITCHEN_ASSISTANT",
    ),
    ("Ali Hassan", "ali.hassan.waiter@restromind.test", "0300-0000005", "WAITER"),
    ("Fahad Malik", "fahad.malik.waiter@restromind.test", "0300-0000006", "WAITER"),
    ("Saad Iqbal", "saad.iqbal.waiter@restromind.test", "0300-0000007", "WAITER"),
    ("Hira Khan", "hira.khan.cashier@restromind.test", "0300-0000008", "CASHIER"),
    (
        "Imran Shah",
        "imran.shah.cleaning@restromind.test",
        "0300-0000009",
        "CLEANING_STAFF",
    ),
    (
        "Nadeem Akhtar",
        "nadeem.akhtar.cleaning@restromind.test",
        "0300-0000010",
        "CLEANING_STAFF",
    ),
    ("Sana Iqbal", "sana.iqbal.host@restromind.test", "0300-0000011", "HOST"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually remove test profiles and create the restaurant team.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        owner = db.scalar(
            select(StaffUser).where(
                StaffUser.id == OWNER_ID,
                StaffUser.email == OWNER_EMAIL,
                StaffUser.role == "OWNER",
            )
        )

        if owner is None:
            raise SystemExit(
                "STOPPED: Chaman's expected Owner account was not found. "
                "No database changes were made."
            )

        fake_users = db.scalars(
            select(StaffUser).where(
                StaffUser.name.like(TEST_NAME_PATTERN),
                StaffUser.email.like(TEST_EMAIL_PATTERN),
                StaffUser.id != OWNER_ID,
            )
        ).all()

        existing_emails = set(
            db.scalars(
                select(StaffUser.email).where(StaffUser.email.is_not(None))
            ).all()
        )
        missing_team = [member for member in TEAM if member[1] not in existing_emails]

        print(f"Verified Owner: {owner.name} | {owner.email} | ID {owner.id}")
        print(f"Fake Permission Test profiles to remove: {len(fake_users)}")
        for member in fake_users:
            print(f"  REMOVE: ID {member.id} | {member.name} | {member.email}")

        print(f"Restaurant staff profiles to create: {len(missing_team)}")
        for name, email, phone, role in missing_team:
            print(f"  CREATE: {name} | {role} | {email} | {phone}")

        if not args.apply:
            print("\\nDRY RUN ONLY. No database changes were made.")
            print("Review the list, then run with --apply to make the changes.")
            return

        for member in fake_users:
            db.delete(member)

        for name, email, phone, role in missing_team:
            db.add(
                StaffUser(
                    name=name,
                    email=email,
                    phone=phone,
                    role=role,
                    is_active=True,
                )
            )

        db.commit()

        staff = db.scalars(select(StaffUser).order_by(StaffUser.id)).all()

        print("\\nSETUP COMPLETE")
        print(f"Removed fake profiles: {len(fake_users)}")
        print(f"Created staff profiles: {len(missing_team)}")
        print(f"Total staff profiles now: {len(staff)}")
        print("\\nCurrent staff directory:")
        for member in staff:
            print(
                f"  {member.id}: {member.name} | {member.role} | "
                f"{member.email} | {member.phone}"
            )


if __name__ == "__main__":
    main()
