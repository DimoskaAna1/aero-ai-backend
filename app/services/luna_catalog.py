"""Original LUNA fashion catalog, about 1,000 styles.

Names, prices, and combinations are ours. Photos are a small shared lookbook,
reused by category, so the shop can be searched at market scale.
"""

_DRESS = "https://images.unsplash.com/photo-1704775991534-563c1d548f88?auto=format&fit=crop&w=900&q=80"
_DRESS_BTN = "https://images.unsplash.com/photo-1704775991534-563c1d548f88?auto=format&fit=crop&w=800&h=800&crop=focalpoint&fp-x=0.62&fp-y=0.78&q=80"
_DRESS_NECK = "https://images.unsplash.com/photo-1704775991534-563c1d548f88?auto=format&fit=crop&w=800&h=800&crop=focalpoint&fp-x=0.48&fp-y=0.18&q=80"
_DRESS_RED = "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?auto=format&fit=crop&w=800&q=80"
_BAG = "https://images.unsplash.com/photo-1585488433921-f2ce041b2d64?auto=format&fit=crop&w=800&h=900&crop=focalpoint&fp-x=0.45&fp-y=0.72&q=80"
_BAG_WIDE = "https://images.unsplash.com/photo-1585488433921-f2ce041b2d64?auto=format&fit=crop&w=900&q=80"
_BAG_MINI = "https://images.unsplash.com/photo-1590874103328-eac38a683ce7?auto=format&fit=crop&w=800&q=80"
_HEELS = "https://images.unsplash.com/photo-1564417071269-08e42408c098?auto=format&fit=crop&w=800&q=80"
_HEELS_NUDE = "https://images.unsplash.com/photo-1519415943484-9fa1873496d4?auto=format&fit=crop&w=800&q=80"
_TOP = "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800&q=80"
_RED_BAG = "https://images.unsplash.com/photo-1584917865442-de89df76afd3?auto=format&fit=crop&w=800&q=80"

_LOOK = {
    "dress": (_DRESS, _DRESS_BTN, _DRESS_NECK, _DRESS_RED),
    "top": (_TOP, _DRESS_NECK),
    "bottom": (_DRESS, _TOP),
    "outer": (_DRESS, _DRESS_RED),
    "shoe": (_HEELS, _HEELS_NUDE),
    "bag": (_BAG, _BAG_WIDE, _BAG_MINI, _RED_BAG),
    "extra": (_BAG_MINI, _HEELS_NUDE, _TOP),
}

_COLORS = (
    ("Black", "crna", "crn"),
    ("White", "bela", "bel"),
    ("Red", "crvena", "crven"),
    ("Beige", "bez", "bez"),
    ("Navy", "teget", "teget"),
    ("Pink", "rozeva", "rozev"),
    ("Green", "zelena", "zelen"),
    ("Brown", "kafena", "kafen"),
)


def build_luna():
    from app.services.flow import Category, Product, Subcategory

    dress_black = Product(
        "dress-black",
        "Black Satin Dress",
        "Crna saten haljina. Cena 2.490 MKD.",
        _DRESS,
        ("crna haljina", "black dress", "haljina", "saten"),
        2490,
        False,
        0,
        "Saten. Boja: crna. Duzina: midi.\nKopcanje od strana.\nKombinacija: crna torba i crni stapki — 3 artikli, 20% na site.",
        (_DRESS, _DRESS_BTN, _DRESS_NECK),
    )
    dress_red = Product(
        "dress-red",
        "Red Mini Dress",
        "Crvena mini haljina. Cena 2.790 MKD.",
        _DRESS_RED,
        ("crvena haljina", "red dress"),
        2790,
        False,
        0,
        "Mini. Boja: crvena.\nKombinacija: mini torba i nude stapki — 3 artikli, 20% na site.",
        (_DRESS_RED,),
    )
    bag_black = Product(
        "bag-black",
        "Black Shoulder Bag",
        "Crna torba. Cena 1.290 MKD.",
        _BAG,
        ("crna torba", "black bag", "torba"),
        1290,
        False,
        0,
        "Koza. Boja: crna. Ramena kajs.\nZlatno kopce. Odgovara uz crnu saten haljinu.",
        (_BAG, _BAG_WIDE),
    )
    bag_mini = Product(
        "bag-mini",
        "Mini Bag",
        "Mini torba. Cena 990 MKD.",
        _BAG_MINI,
        ("mini torba", "mini bag"),
        990,
    )
    heels_black = Product(
        "heels-black",
        "Black Heels",
        "Crni stapki. Cena 1.890 MKD.",
        _HEELS,
        ("crni stapki", "black heels", "cipele", "potpetici"),
        1890,
        False,
        0,
        "Koza. Boja: crna. Kajs oko clenka.\nTret del od kombinacijata: haljina + torba + stapki, 20% na site.",
        (_HEELS,),
    )
    heels_nude = Product(
        "heels-nude",
        "Nude Heels",
        "Nude stapki. Cena 1.690 MKD.",
        _HEELS_NUDE,
        ("nude", "nude heels"),
        1690,
    )
    top_white = Product(
        "top-white",
        "White Tee",
        "Bela majica. Cena 790 MKD.",
        _TOP,
        ("bela majica", "white tee", "majica"),
        790,
    )

    departments = (
        (
            "dresses",
            "Haljine",
            ("haljine", "haljina", "dresses", "dress"),
            (
                ("mini", "Mini", ("mini",), 90, 1890, "dress", ("Satin Mini", "Cowl Mini", "Slip Mini", "Ruched Mini"), "haljina", ()),
                ("midi", "Midi", ("midi",), 80, 2490, "dress", ("Satin Midi", "Column Midi", "Wrap Midi", "Bias Midi"), "haljina", (dress_black,)),
                ("maxi", "Maxi", ("maxi",), 50, 2990, "dress", ("Satin Maxi", "Pleat Maxi", "Slip Maxi"), "haljina", ()),
                ("party", "Party", ("party", "vecer"), 40, 3290, "dress", ("Sequin Mini", "Velvet Mini", "Corset Mini"), "haljina", (dress_red,)),
            ),
        ),
        (
            "tops",
            "Majici",
            ("majici", "majica", "top", "tops"),
            (
                ("tee", "Majici", ("majica", "tee"), 70, 790, "top", ("Cotton Tee", "Fitted Tee", "Boxy Tee"), "majica", (top_white,)),
                ("shirt", "Kosuli", ("kosula", "shirt"), 50, 1490, "top", ("Poplin Shirt", "Linen Shirt", "Oxford Shirt"), "kosula", ()),
                ("knit", "Pleteni", ("dzemper", "knit"), 40, 1690, "top", ("Fine Knit", "Rib Knit", "Cardigan"), "dzemper", ()),
                ("body", "Bodi", ("bodi", "bodysuit"), 30, 1290, "top", ("Scoop Body", "Square Body"), "bodi", ()),
            ),
        ),
        (
            "bottoms",
            "Pantaloni",
            ("pantaloni", "pantalon", "jeans", "suknja"),
            (
                ("jeans", "Farmerki", ("farmerki", "jeans"), 60, 1990, "bottom", ("Straight Jean", "Wide Jean", "Slim Jean"), "farmerki", ()),
                ("trousers", "Pantaloni", ("pantalon",), 50, 2190, "bottom", ("Tailored Trouser", "Wide Trouser", "Linen Trouser"), "pantalon", ()),
                ("skirts", "Suknji", ("suknja", "skirt"), 40, 1790, "bottom", ("Satin Skirt", "Denim Skirt", "Pleat Skirt"), "suknja", ()),
            ),
        ),
        (
            "outer",
            "Jakni",
            ("jakni", "jakna", "kaput", "sako"),
            (
                ("blazer", "Sakoi", ("sako", "blazer"), 35, 3490, "outer", ("Tailored Blazer", "Linen Blazer"), "sako", ()),
                ("coat", "Kaputi", ("kaput", "coat"), 35, 4990, "outer", ("Wool Coat", "Trench Coat"), "kaput", ()),
                ("jacket", "Jakni", ("jakna", "jacket"), 30, 3990, "outer", ("Bomber Jacket", "Leather Jacket"), "jakna", ()),
            ),
        ),
        (
            "shoes",
            "Cipele",
            ("cipele", "stapki", "shoes", "heels"),
            (
                ("heels", "Stapki", ("stapki", "heels", "potpetici"), 50, 1890, "shoe", ("Strap Heel", "Slingback Heel", "Court Heel"), "stapki", (heels_black,)),
                ("boots", "Cizmi", ("cizmi", "boots"), 40, 3290, "shoe", ("Ankle Boot", "Knee Boot"), "cizmi", ()),
                ("sandals", "Sandali", ("sandali", "sandal"), 35, 1490, "shoe", ("Strap Sandal", "Kitten Sandal"), "sandali", (heels_nude,)),
                ("sneakers", "Patiki", ("patiki", "sneakers"), 35, 2490, "shoe", ("Court Sneaker", "Runner Sneaker"), "patiki", ()),
            ),
        ),
        (
            "bags",
            "Torbe",
            ("torbe", "torba", "bags", "bag"),
            (
                ("shoulder", "Ramena", ("ramena", "shoulder"), 40, 1290, "bag", ("Shoulder Bag", "Hobo Bag"), "torba", (bag_black,)),
                ("minibag", "Mini", ("mini torba",), 35, 990, "bag", ("Mini Bag", "Box Bag"), "torba", (bag_mini,)),
                ("tote", "Tote", ("tote",), 30, 1590, "bag", ("Shopper Tote", "Leather Tote"), "torba", ()),
            ),
        ),
        (
            "extras",
            "Dodatoci",
            ("dodatoci", "nakit", "naocari"),
            (
                ("jewellery", "Nakit", ("nakit", "obicci"), 20, 690, "extra", ("Hoop Earrings", "Chain Necklace"), "nakit", ()),
                ("sunglasses", "Naocari", ("naocari", "sunglasses"), 15, 890, "extra", ("Cat Eye", "Slim Frame"), "naocari", ()),
            ),
        ),
    )

    categories = []
    for category_id, label, aliases, children in departments:
        built = []
        for sub_id, sub_label, sub_aliases, count, base, pool, styles, noun, heroes in children:
            built.append(
                _subcategory(sub_id, sub_label, sub_aliases, count, base, pool, styles, noun, heroes)
            )
        categories.append(Category(category_id, label, tuple(built), aliases))
    return tuple(categories)


def _subcategory(sub_id, label, aliases, count, base, pool, styles, noun, heroes):
    from app.services.flow import Product, Subcategory

    images = _LOOK[pool]
    products = list(heroes)
    for index in range(count - len(heroes)):
        color_en, color_mk, color_m = _COLORS[index % len(_COLORS)]
        style = styles[index % len(styles)]
        number = index + 1
        title = "{color} {style} {number:03d}".format(color=color_en, style=style, number=number)
        price = base + (index % 11) * 80
        on_sale = index % 9 == 0
        old = int(round(price / 0.8)) if on_sale else 0
        current = int(round(price * 0.8)) if on_sale else price
        image = images[index % len(images)]
        products.append(
            Product(
                "{sub}-{number:03d}".format(sub=sub_id, number=number),
                title,
                "{title}. Cena {price} MKD.".format(title=title, price=_money(current)),
                image,
                (color_mk, color_m, noun, style.lower()),
                current,
                on_sale,
                old,
                "Boja: {color}. {style}.\n{group}.".format(color=color_mk, style=style, group=label),
                (image,),
            )
        )
    return Subcategory(sub_id, label, tuple(products), aliases)


def _money(amount: int) -> str:
    return "{:,}".format(amount).replace(",", ".")
