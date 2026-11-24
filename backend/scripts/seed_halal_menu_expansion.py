import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.menu_item import MenuItem

EXTRA_MENU = [
    # Burgers & Sandwiches — 2
    (
        "Crispy Chicken Supreme Burger",
        "Crispy halal chicken fillet with cheese, lettuce and house sauce.",
        "Burgers & Sandwiches",
        720,
        ["gluten", "dairy", "eggs"],
        "MEDIUM",
    ),
    (
        "Grilled Beef Sandwich",
        "Grilled halal beef with caramelized onion and fresh vegetables.",
        "Burgers & Sandwiches",
        680,
        ["gluten", "dairy"],
        "MILD",
    ),
    # Pakistani / Desi — 3
    (
        "Chicken Qeema",
        "Traditional minced chicken cooked with tomatoes and Pakistani spices.",
        "Pakistani / Desi",
        520,
        [],
        "MEDIUM",
    ),
    (
        "Chana Masala",
        "Chickpeas cooked in a traditional tomato and spice gravy.",
        "Pakistani / Desi",
        350,
        [],
        "MEDIUM",
    ),
    (
        "Sarson Ka Saag with Makki Roti",
        "Traditional mustard greens served with corn flatbread.",
        "Pakistani / Desi",
        580,
        ["gluten", "dairy"],
        "MILD",
    ),
    # Pizza — 4
    (
        "Peri Peri Chicken Pizza",
        "Halal chicken, peri peri sauce, capsicum and mozzarella.",
        "Pizza",
        1300,
        ["gluten", "dairy"],
        "HOT",
    ),
    (
        "Achari Chicken Pizza",
        "Chicken with achari spices, onion and mozzarella.",
        "Pizza",
        1250,
        ["gluten", "dairy"],
        "HOT",
    ),
    (
        "Cheese Lover Pizza",
        "A generous combination of mozzarella and other cheeses.",
        "Pizza",
        1400,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Spicy Vegetable Pizza",
        "Capsicum, onion, olives, jalapenos and cheese.",
        "Pizza",
        1100,
        ["gluten", "dairy"],
        "HOT",
    ),
    # Rice & Biryani — 2
    (
        "Chicken Tikka Rice",
        "Spiced rice served with grilled chicken tikka pieces.",
        "Rice & Biryani",
        620,
        [],
        "MEDIUM",
    ),
    (
        "Egg Fried Rice",
        "Wok-fried rice with egg, vegetables and light seasoning.",
        "Rice & Biryani",
        420,
        ["eggs", "soy"],
        "MILD",
    ),
    # Rolls & Shawarma — 2
    (
        "Paneer Paratha Roll",
        "Grilled paneer with vegetables and mint chutney in paratha.",
        "Rolls & Shawarma",
        420,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Chicken Fajita Wrap",
        "Chicken fajita strips with capsicum and creamy sauce.",
        "Rolls & Shawarma",
        490,
        ["gluten", "dairy"],
        "MEDIUM",
    ),
    # Snacks & Sides — 3
    (
        "Loaded Chicken Fries",
        "Fries topped with halal chicken, cheese and house sauce.",
        "Snacks & Sides",
        520,
        ["dairy", "eggs"],
        "MEDIUM",
    ),
    (
        "Crispy Onion Rings",
        "Golden battered onion rings with dipping sauce.",
        "Snacks & Sides",
        280,
        ["gluten", "eggs"],
        "MILD",
    ),
    (
        "Mozzarella Sticks",
        "Crispy fried mozzarella sticks with tomato dip.",
        "Snacks & Sides",
        450,
        ["gluten", "dairy"],
        "MILD",
    ),
    # BBQ & Grilled — 8
    (
        "Chicken Bihari Boti",
        "Tender halal chicken marinated in Bihari spices and grilled.",
        "BBQ & Grilled",
        720,
        ["dairy"],
        "HOT",
    ),
    (
        "Beef Bihari Boti",
        "Halal beef strips marinated with traditional Bihari spices.",
        "BBQ & Grilled",
        850,
        [],
        "HOT",
    ),
    (
        "Chicken Reshmi Kebab",
        "Soft minced chicken kebabs with herbs and mild spices.",
        "BBQ & Grilled",
        650,
        ["dairy"],
        "MILD",
    ),
    (
        "Beef Seekh Kebab Platter",
        "Grilled halal beef seekh kebabs with chutney and salad.",
        "BBQ & Grilled",
        780,
        [],
        "MEDIUM",
    ),
    (
        "Chicken Leg Piece BBQ",
        "Chargrilled chicken leg with house BBQ marinade.",
        "BBQ & Grilled",
        620,
        [],
        "MEDIUM",
    ),
    (
        "Grilled Chicken Tikka Platter",
        "Chicken tikka served with naan, salad and chutney.",
        "BBQ & Grilled",
        950,
        ["gluten", "dairy"],
        "HOT",
    ),
    (
        "Malai Boti Platter",
        "Creamy grilled chicken malai boti with fresh salad.",
        "BBQ & Grilled",
        1100,
        ["dairy"],
        "MILD",
    ),
    (
        "Mixed BBQ Platter",
        "A selection of halal chicken and beef kebabs and grilled boti.",
        "BBQ & Grilled",
        1850,
        ["dairy"],
        "MEDIUM",
    ),
    # Pasta — 6
    (
        "Chicken Alfredo Pasta",
        "Creamy pasta with halal chicken and parmesan-style cheese.",
        "Pasta",
        780,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Chicken Tikka Pasta",
        "Pasta tossed with chicken tikka and a spiced creamy sauce.",
        "Pasta",
        750,
        ["gluten", "dairy"],
        "MEDIUM",
    ),
    (
        "Creamy Mushroom Pasta",
        "Pasta with mushrooms in a creamy garlic sauce.",
        "Pasta",
        680,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Spicy Arrabbiata Pasta",
        "Pasta with tomato, garlic and chilli sauce.",
        "Pasta",
        620,
        ["gluten"],
        "HOT",
    ),
    (
        "Chicken Mac and Cheese",
        "Macaroni with halal chicken and rich cheese sauce.",
        "Pasta",
        720,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Beef Lasagna",
        "Layered pasta with halal beef, tomato sauce and cheese.",
        "Pasta",
        850,
        ["gluten", "dairy"],
        "MILD",
    ),
    # Chinese Food — 4
    (
        "Chicken Chow Mein",
        "Stir-fried noodles with halal chicken and vegetables.",
        "Chinese Food",
        620,
        ["gluten", "soy"],
        "MEDIUM",
    ),
    (
        "Chicken Shashlik with Rice",
        "Halal chicken and vegetables in tangy shashlik sauce.",
        "Chinese Food",
        680,
        ["soy", "gluten"],
        "MEDIUM",
    ),
    (
        "Sweet and Sour Chicken",
        "Crispy halal chicken in sweet and sour sauce.",
        "Chinese Food",
        650,
        ["gluten", "soy"],
        "MILD",
    ),
    (
        "Chicken Chilli Dry",
        "Halal chicken tossed with green chillies, garlic and peppers.",
        "Chinese Food",
        720,
        ["soy"],
        "HOT",
    ),
    # Cold Drinks & Juices — 6
    (
        "Fresh Orange Juice",
        "Freshly squeezed orange juice.",
        "Cold Drinks & Juices",
        300,
        [],
        "MILD",
    ),
    (
        "Fresh Apple Juice",
        "Fresh apple juice served chilled.",
        "Cold Drinks & Juices",
        320,
        [],
        "MILD",
    ),
    (
        "Fresh Mango Juice",
        "Fresh mango juice made with ripe mangoes.",
        "Cold Drinks & Juices",
        350,
        [],
        "MILD",
    ),
    (
        "Mint Lemonade",
        "Refreshing lemon drink with mint.",
        "Cold Drinks & Juices",
        220,
        [],
        "MILD",
    ),
    (
        "Regular Soft Drink",
        "Chilled carbonated soft drink.",
        "Cold Drinks & Juices",
        150,
        [],
        "MILD",
    ),
    (
        "Mineral Water",
        "Bottled drinking water.",
        "Cold Drinks & Juices",
        100,
        [],
        "MILD",
    ),
    # Tea, Coffee & Shakes — 4
    (
        "Doodh Patti Chai",
        "Traditional Pakistani milk tea.",
        "Tea, Coffee & Shakes",
        150,
        ["dairy"],
        "MILD",
    ),
    (
        "Cappuccino",
        "Espresso coffee topped with steamed milk foam.",
        "Tea, Coffee & Shakes",
        320,
        ["dairy"],
        "MILD",
    ),
    (
        "Chocolate Milkshake",
        "Thick chocolate milkshake made with milk and ice cream.",
        "Tea, Coffee & Shakes",
        380,
        ["dairy"],
        "MILD",
    ),
    (
        "Mango Milkshake",
        "Creamy mango shake made with milk.",
        "Tea, Coffee & Shakes",
        400,
        ["dairy"],
        "MILD",
    ),
    # Desserts — 6
    (
        "Gulab Jamun",
        "Traditional milk-solid sweets in sugar syrup.",
        "Desserts",
        220,
        ["dairy", "gluten"],
        "MILD",
    ),
    (
        "Kheer",
        "Traditional rice pudding with milk and cardamom.",
        "Desserts",
        250,
        ["dairy"],
        "MILD",
    ),
    (
        "Chocolate Brownie",
        "Chocolate brownie served as a dessert portion.",
        "Desserts",
        300,
        ["gluten", "dairy", "eggs"],
        "MILD",
    ),
    (
        "Chocolate Lava Cake",
        "Warm chocolate cake with a soft chocolate centre.",
        "Desserts",
        380,
        ["gluten", "dairy", "eggs"],
        "MILD",
    ),
    (
        "Kunafa",
        "Traditional pastry dessert with cheese and syrup.",
        "Desserts",
        450,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Vanilla Ice Cream",
        "Vanilla ice cream served in a dessert cup.",
        "Desserts",
        220,
        ["dairy"],
        "MILD",
    ),
]


def size_options(category, price):
    price = int(price)

    if category == "Pizza":
        return {
            "Small": round(price * 0.75),
            "Medium": price,
            "Large": round(price * 1.35),
        }

    if category in ("Pakistani / Desi", "Rice & Biryani", "BBQ & Grilled"):
        return {
            "Half": round(price * 0.62),
            "Full": price,
        }

    if category in ("Burgers & Sandwiches", "Pasta", "Chinese Food"):
        return {
            "Regular": price,
            "Large": round(price * 1.35),
        }

    if category == "Snacks & Sides":
        return {
            "Small": price,
            "Large": round(price * 1.7),
        }

    if category in ("Cold Drinks & Juices", "Tea, Coffee & Shakes"):
        return {
            "Small": price,
            "Medium": round(price * 1.35),
            "Large": round(price * 1.7),
        }

    return {}


def validate_initial_count(initial_count):
    if initial_count > 100:
        raise RuntimeError(
            f"Found {initial_count} menu items. Refusing to change a menu "
            "that already exceeds the requested 100."
        )


def validate_final_count(final_count):
    if final_count != 100:
        raise RuntimeError(
            f"Expected exactly 100 menu items after expansion, found {final_count}. "
            "Transaction will be rolled back."
        )


def main():
    if len(EXTRA_MENU) != 50:
        raise ValueError(f"Expected 50 new dishes, found {len(EXTRA_MENU)}")

    db = SessionLocal()
    added = 0
    updated = 0
    skipped = 0

    try:
        initial_count = db.query(MenuItem).count()
        validate_initial_count(initial_count)

        # Add size options to existing suitable items, without overwriting
        # size prices that a restaurant manager may already have configured.
        existing_items = db.query(MenuItem).all()
        for item in existing_items:
            options = size_options(item.category, item.price)
            if options and not item.size_prices:
                item.size_prices = options
                updated += 1

        existing_names = {item.name.casefold(): item for item in existing_items}

        for name, description, category, price, allergens, spice in EXTRA_MENU:
            if name.casefold() in existing_names:
                skipped += 1
                continue

            item = MenuItem(
                name=name,
                description=description,
                category=category,
                price=price,
                size_prices=size_options(category, price),
                allergens=allergens,
                spice_level=spice,
                is_available=True,
            )
            db.add(item)
            existing_names[name.casefold()] = item
            added += 1

        db.flush()
        final_count = db.query(MenuItem).count()

        validate_final_count(final_count)

        db.commit()

        print("\n========== HALAL MENU EXPANSION ==========")
        print(f"New dishes in script:       {len(EXTRA_MENU)}")
        print(f"New dishes added:           {added}")
        print(f"Already existing skipped:  {skipped}")
        print(f"Existing items size-updated:{updated}")
        print(f"TOTAL MENU ITEMS:           {final_count}")

        print("\n========== MENU BY CATEGORY ==========")
        rows = (
            db.query(MenuItem.category, func.count(MenuItem.id))
            .group_by(MenuItem.category)
            .order_by(MenuItem.category)
            .all()
        )
        for category, count in rows:
            print(f"{category}: {count}")

        print(
            "\nSample prices are in PKR and should be adjusted "
            "to actual restaurant rates."
        )

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
