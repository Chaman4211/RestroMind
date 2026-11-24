import sys
from pathlib import Path

# Add the backend directory so Python can find the existing app package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.menu_item import MenuItem

MENU = [
    # Pakistani / Desi — 15
    (
        "Chicken Karahi",
        "Traditional chicken karahi with tomatoes, ginger and green chillies.",
        "Pakistani / Desi",
        1450,
        ["dairy"],
        "HOT",
    ),
    (
        "Chicken White Karahi",
        "Creamy white chicken karahi with ginger and black pepper.",
        "Pakistani / Desi",
        1550,
        ["dairy"],
        "MEDIUM",
    ),
    (
        "Mutton Karahi",
        "Traditional mutton karahi cooked with tomatoes and spices.",
        "Pakistani / Desi",
        2350,
        [],
        "HOT",
    ),
    (
        "Chicken Handi",
        "Slow-cooked creamy chicken handi with aromatic spices.",
        "Pakistani / Desi",
        1650,
        ["dairy"],
        "MEDIUM",
    ),
    (
        "Chicken Biryani",
        "Fragrant basmati rice layered with spiced chicken.",
        "Pakistani / Desi",
        450,
        [],
        "MEDIUM",
    ),
    (
        "Beef Biryani",
        "Aromatic rice cooked with tender beef and traditional spices.",
        "Pakistani / Desi",
        550,
        [],
        "MEDIUM",
    ),
    (
        "Chicken Pulao",
        "Mildly spiced rice cooked with chicken and whole spices.",
        "Pakistani / Desi",
        420,
        [],
        "MILD",
    ),
    (
        "Beef Nihari",
        "Slow-cooked beef stew served with traditional spices.",
        "Pakistani / Desi",
        650,
        ["gluten"],
        "MEDIUM",
    ),
    (
        "Chicken Haleem",
        "Rich chicken, lentil and wheat stew.",
        "Pakistani / Desi",
        480,
        ["gluten"],
        "MEDIUM",
    ),
    (
        "Seekh Kebab",
        "Grilled minced beef kebabs with herbs and spices.",
        "Pakistani / Desi",
        380,
        [],
        "MEDIUM",
    ),
    (
        "Chicken Tikka",
        "Grilled marinated chicken with traditional tikka spices.",
        "Pakistani / Desi",
        550,
        ["dairy"],
        "HOT",
    ),
    (
        "Beef Chapli Kebab",
        "Peshawari-style flat beef kebab with herbs and spices.",
        "Pakistani / Desi",
        420,
        ["eggs"],
        "HOT",
    ),
    (
        "Chicken Malai Boti",
        "Tender creamy chicken pieces grilled over heat.",
        "Pakistani / Desi",
        650,
        ["dairy"],
        "MILD",
    ),
    (
        "Daal Makhani",
        "Slow-cooked black lentils with a creamy finish.",
        "Pakistani / Desi",
        380,
        ["dairy"],
        "MILD",
    ),
    (
        "Aloo Paratha",
        "Crispy flatbread stuffed with seasoned potatoes.",
        "Pakistani / Desi",
        220,
        ["gluten"],
        "MILD",
    ),
    # Burgers and sandwiches — 10
    (
        "Classic Zinger Burger",
        "Crispy spicy chicken fillet with lettuce and sauce.",
        "Burgers & Sandwiches",
        550,
        ["gluten", "eggs"],
        "MEDIUM",
    ),
    (
        "Mighty Zinger Burger",
        "Double crispy chicken fillets with cheese and sauce.",
        "Burgers & Sandwiches",
        850,
        ["gluten", "dairy", "eggs"],
        "HOT",
    ),
    (
        "Grilled Chicken Burger",
        "Grilled chicken breast with fresh lettuce and sauce.",
        "Burgers & Sandwiches",
        600,
        ["gluten", "eggs"],
        "MILD",
    ),
    (
        "Beef Cheese Burger",
        "Beef patty with cheddar cheese and burger sauce.",
        "Burgers & Sandwiches",
        650,
        ["gluten", "dairy", "eggs"],
        "MILD",
    ),
    (
        "Double Beef Burger",
        "Two beef patties with cheese and house sauce.",
        "Burgers & Sandwiches",
        950,
        ["gluten", "dairy", "eggs"],
        "MEDIUM",
    ),
    (
        "Chicken Club Sandwich",
        "Triple-layer sandwich with chicken, egg and vegetables.",
        "Burgers & Sandwiches",
        550,
        ["gluten", "eggs"],
        "MILD",
    ),
    (
        "Chicken Cheese Sandwich",
        "Chicken filling with melted cheese in toasted bread.",
        "Burgers & Sandwiches",
        480,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "BBQ Chicken Burger",
        "Grilled chicken with smoky BBQ sauce.",
        "Burgers & Sandwiches",
        620,
        ["gluten"],
        "MILD",
    ),
    (
        "Crispy Chicken Wrap",
        "Crispy chicken, fresh vegetables and creamy sauce in a wrap.",
        "Burgers & Sandwiches",
        520,
        ["gluten", "dairy"],
        "MEDIUM",
    ),
    (
        "Spicy Jalapeno Burger",
        "Chicken burger with jalapenos and spicy sauce.",
        "Burgers & Sandwiches",
        680,
        ["gluten", "dairy"],
        "EXTRA_HOT",
    ),
    # Pizza — 8
    (
        "Chicken Tikka Pizza",
        "Pizza topped with chicken tikka, cheese and vegetables.",
        "Pizza",
        1100,
        ["gluten", "dairy"],
        "MEDIUM",
    ),
    (
        "Chicken Fajita Pizza",
        "Chicken fajita, capsicum, onion and mozzarella cheese.",
        "Pizza",
        1150,
        ["gluten", "dairy"],
        "MEDIUM",
    ),
    (
        "Malai Boti Pizza",
        "Creamy chicken malai boti with mozzarella cheese.",
        "Pizza",
        1250,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "BBQ Chicken Pizza",
        "Smoky BBQ chicken, onion and melted cheese.",
        "Pizza",
        1200,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Pepperoni-Style Chicken Pizza",
        "Chicken-based halal-style topping with cheese and herbs.",
        "Pizza",
        1250,
        ["gluten", "dairy"],
        "MEDIUM",
    ),
    (
        "Vegetable Supreme Pizza",
        "Mushrooms, olives, capsicum, onion and cheese.",
        "Pizza",
        1000,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Creamy Garlic Chicken Pizza",
        "Chicken, garlic sauce and mozzarella cheese.",
        "Pizza",
        1250,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Four Cheese Pizza",
        "A rich combination of four cheeses on a pizza base.",
        "Pizza",
        1300,
        ["gluten", "dairy"],
        "MILD",
    ),
    # Rolls and shawarma — 7
    (
        "Chicken Shawarma",
        "Chicken shawarma with vegetables and garlic sauce.",
        "Rolls & Shawarma",
        300,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Zinger Paratha Roll",
        "Crispy chicken wrapped in a flaky paratha.",
        "Rolls & Shawarma",
        420,
        ["gluten", "dairy"],
        "MEDIUM",
    ),
    (
        "Chicken Malai Roll",
        "Creamy grilled chicken wrapped in a fresh paratha.",
        "Rolls & Shawarma",
        450,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Beef Seekh Roll",
        "Grilled beef seekh kebab with chutney and salad.",
        "Rolls & Shawarma",
        400,
        ["gluten"],
        "MEDIUM",
    ),
    (
        "Chicken Cheese Roll",
        "Chicken filling with melted cheese in a paratha.",
        "Rolls & Shawarma",
        430,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Spicy Chicken Shawarma",
        "Spicy chicken shawarma with garlic sauce.",
        "Rolls & Shawarma",
        350,
        ["gluten", "dairy"],
        "HOT",
    ),
    (
        "Afghani Chicken Roll",
        "Creamy Afghani-style chicken wrapped in paratha.",
        "Rolls & Shawarma",
        470,
        ["gluten", "dairy"],
        "MILD",
    ),
    # Rice and biryani — 6
    (
        "Chicken Fried Rice",
        "Wok-fried rice with chicken, vegetables and egg.",
        "Rice & Biryani",
        480,
        ["eggs", "soy"],
        "MILD",
    ),
    (
        "Chicken Manchurian Rice",
        "Chicken in tangy Manchurian sauce served with rice.",
        "Rice & Biryani",
        650,
        ["soy", "gluten"],
        "MEDIUM",
    ),
    (
        "Beef Pulao",
        "Traditional beef pulao with aromatic whole spices.",
        "Rice & Biryani",
        520,
        [],
        "MILD",
    ),
    (
        "Chicken Mandi",
        "Arabian-style rice with roasted chicken and spices.",
        "Rice & Biryani",
        850,
        [],
        "MILD",
    ),
    (
        "Chicken Kabsa",
        "Spiced Arabian rice served with roasted chicken.",
        "Rice & Biryani",
        900,
        [],
        "MILD",
    ),
    (
        "Vegetable Fried Rice",
        "Wok-fried rice with mixed vegetables and soy seasoning.",
        "Rice & Biryani",
        380,
        ["soy"],
        "MILD",
    ),
    # Snacks and sides — 4
    (
        "Masala French Fries",
        "Crispy fries tossed in house masala seasoning.",
        "Snacks & Sides",
        250,
        [],
        "MEDIUM",
    ),
    (
        "Chicken Nuggets",
        "Golden fried chicken nuggets with dipping sauce.",
        "Snacks & Sides",
        380,
        ["gluten", "eggs"],
        "MILD",
    ),
    (
        "Chicken Cheese Balls",
        "Crispy bites filled with chicken and cheese.",
        "Snacks & Sides",
        420,
        ["gluten", "dairy"],
        "MILD",
    ),
    (
        "Garlic Mayo Fries",
        "Crispy fries topped with garlic mayonnaise.",
        "Snacks & Sides",
        320,
        ["eggs"],
        "MILD",
    ),
]


def main():
    if len(MENU) != 50:
        raise ValueError(f"Expected 50 dishes, found {len(MENU)}")

    db = SessionLocal()
    added = 0
    skipped = 0

    try:
        existing_names = {name.casefold() for (name,) in db.query(MenuItem.name).all()}

        for name, description, category, price, allergens, spice in MENU:
            if name.casefold() in existing_names:
                skipped += 1
                continue

            db.add(
                MenuItem(
                    name=name,
                    description=description,
                    category=category,
                    price=price,
                    allergens=allergens,
                    spice_level=spice,
                    is_available=True,
                )
            )
            existing_names.add(name.casefold())
            added += 1

        db.commit()

        print("\n========== HALAL MENU SEED RESULT ==========")
        print(f"Sample dishes in script: {len(MENU)}")
        print(f"New dishes added:        {added}")
        print(f"Existing dishes skipped: {skipped}")
        print(f"Total menu items now:    {db.query(MenuItem).count()}")

        print("\n========== MENU BY CATEGORY ==========")
        from sqlalchemy import func

        rows = (
            db.query(MenuItem.category, func.count(MenuItem.id))
            .group_by(MenuItem.category)
            .order_by(MenuItem.category)
            .all()
        )
        for category, count in rows:
            print(f"{category}: {count}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
