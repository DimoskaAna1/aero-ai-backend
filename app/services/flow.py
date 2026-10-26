import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from app.services.locale import (
    CART_PHRASES,
    GREETING_ALL,
    detect_lang,
    explicit_lang,
    language_chips,
    say,
)
from app.services.luna_catalog import build_luna
from app.services.memory import (
    cart_ids,
    flow_lang,
    flow_page,
    flow_position,
    remember_cart,
    set_flow,
    set_flow_lang,
    set_flow_page,
)

_FOLDS = str.maketrans(
    {"š": "s", "č": "c", "ć": "c", "ž": "z", "đ": "d", "ë": "e", "ç": "c", "ä": "a", "ö": "o", "ü": "u"}
)
_CYRILLIC_DIGRAPHS = (("љ", "lj"), ("њ", "nj"), ("ѓ", "gj"), ("ќ", "kj"), ("џ", "dz"), ("ѕ", "dz"), ("ђ", "dj"))
_CYRILLIC = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ж": "z",
        "з": "z",
        "и": "i",
        "ј": "j",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "c",
        "ш": "s",
        "ћ": "c",
    }
)


def _fold(text: str) -> str:
    """One alphabet for Macedonian, Serbian, Cyrillic, and Latin."""
    lowered = text.casefold().replace("ß", "ss")
    for source, target in _CYRILLIC_DIGRAPHS:
        lowered = lowered.replace(source, target)
    return " ".join(lowered.translate(_CYRILLIC).translate(_FOLDS).split())


@dataclass(frozen=True)
class Choice:
    label: str
    message: str


@dataclass(frozen=True)
class Product:
    id: str
    title: str
    detail: str
    image_url: str
    aliases: Tuple[str, ...] = ()
    price_mkd: int = 0
    on_sale: bool = False
    old_price_mkd: int = 0
    facts: str = ""
    gallery: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Subcategory:
    id: str
    label: str
    products: Tuple[Product, ...]
    aliases: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    children: Tuple[Subcategory, ...]
    aliases: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CartOffer:
    id: str
    title: str
    price_mkd: int
    image_url: str = ""
    old_price_mkd: int = 0
    combo_percent: int = 0
    combo_ids: Tuple[str, ...] = ()
    detail: str = ""
    images: Tuple[str, ...] = ()


@dataclass(frozen=True)
class FlowReply:
    text: str
    suggestions: List[Choice] = field(default_factory=list)
    image_url: str = ""
    cart: Optional[CartOffer] = None
    card: Optional[CartOffer] = None
    cards: List[CartOffer] = field(default_factory=list)


_WASHER = "https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?auto=format&fit=crop&w=640&q=80"
_WASHER_TWO = "https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?auto=format&fit=crop&w=640&q=80"
_FRIDGE = "https://images.unsplash.com/photo-1571175443880-49e1d25b2bc5?auto=format&fit=crop&w=640&q=80"
_FRIDGE_TWO = "https://images.unsplash.com/photo-1536353284924-9220c464e262?auto=format&fit=crop&w=640&q=80"
_PHONE = "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=640&q=80"
_PHONE_TWO = "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?auto=format&fit=crop&w=640&q=80"

ANANAS = (
    Category(
        "bela-tehnika",
        "Bela tehnika",
        (
            Subcategory(
                "masini",
                "Masini za perenje",
                (
                    Product(
                        "beko-8",
                        "Beko 8 kg",
                        "Beko ves masina 8 kg, 1200 obrtaja. Cena 27.990 MKD. Na 12 rata po 2.333 MKD. Besplatna dostava.",
                        _WASHER,
                        ("beko", "ves masina"),
                        27990,
                    ),
                    Product(
                        "gorenje-7",
                        "Gorenje 7 kg",
                        "Gorenje ves masina 7 kg, 1400 obrtaja. Cena 21.990 MKD, beshe 24.990 MKD. Na akcija. Na 12 rata po 1.833 MKD.",
                        _WASHER_TWO,
                        ("gorenje masina",),
                        21990,
                        True,
                        24990,
                    ),
                ),
                ("ves masina", "masina za perenje", "masini"),
            ),
            Subcategory(
                "frizideri",
                "Frizideri",
                (
                    Product(
                        "gorenje-nrk",
                        "Gorenje NRK 619",
                        "Gorenje kombinovan frizider NRK 619. Cena 32.490 MKD. Na 12 rata po 2.708 MKD.",
                        _FRIDGE,
                        ("gorenje frizider",),
                        32490,
                    ),
                    Product(
                        "beko-fridge",
                        "Beko RCSA 270",
                        "Beko kombinovan frizider RCSA 270. Cena 19.990 MKD, beshe 22.490 MKD. Na akcija.",
                        _FRIDGE_TWO,
                        ("beko frizider",),
                        19990,
                        True,
                        22490,
                    ),
                ),
                ("frizider",),
            ),
            Subcategory(
                "sudo",
                "Sudo masini",
                (
                    Product(
                        "beko-sudo",
                        "Beko DFN 264",
                        "Beko sudo masina DFN 264. Cena 16.990 MKD. Na 12 rata po 1.416 MKD.",
                        _WASHER,
                        ("sudo", "sudo masina"),
                        16990,
                    ),
                ),
                ("sudo masini", "sudo masina"),
            ),
            Subcategory(
                "ploci",
                "Spojni ploci",
                (
                    Product(
                        "gorenje-ploca",
                        "Gorenje staklokeramicka ploca",
                        "Gorenje spojna ploca. Cena 11.490 MKD.",
                        _WASHER_TWO,
                        ("ploca", "spojna ploca"),
                        11490,
                    ),
                ),
                ("spojni ploci", "ploci"),
            ),
        ),
        ("bela tehnika", "tehnika"),
    ),
    Category(
        "telefoni",
        "Telefoni i fotografija",
        (
            Subcategory(
                "mobilni",
                "Mobilni telefoni",
                (
                    Product(
                        "redmi-13",
                        "Xiaomi Redmi 13",
                        "Xiaomi Redmi 13 128GB. Cena 12.990 MKD, beshe 14.990 MKD. Na akcija. Na 6 rata po 2.165 MKD.",
                        _PHONE,
                        ("redmi", "xiaomi"),
                        12990,
                        True,
                        14990,
                    ),
                    Product(
                        "galaxy-a55",
                        "Samsung Galaxy A55",
                        "Samsung Galaxy A55 8/128. Cena 24.990 MKD. Na 12 rata po 2.083 MKD. Besplatna dostava.",
                        _PHONE,
                        ("galaxy", "samsung"),
                        24990,
                    ),
                    Product(
                        "iphone-13",
                        "iPhone 13",
                        "iPhone 13 128GB. Cena 42.990 MKD. Na 12 rata po 3.583 MKD. Besplatna dostava.",
                        _PHONE_TWO,
                        ("iphone", "ajfon"),
                        42990,
                    ),
                ),
                ("mobilni", "telefon"),
            ),
            Subcategory(
                "futrole",
                "Futrole i stakla",
                (
                    Product(
                        "futrola-13",
                        "Futrola iPhone 13",
                        "Silikonska futrola za iPhone 13. Cena 1.290 MKD.",
                        _PHONE_TWO,
                        ("futrola", "maska iphone"),
                        1290,
                    ),
                    Product(
                        "maska-redmi",
                        "Maska Redmi 13",
                        "Silikonska maska za Xiaomi Redmi 13. Cena 990 MKD.",
                        _PHONE,
                        ("maska redmi", "maska"),
                        990,
                    ),
                    Product(
                        "maska-a55",
                        "Maska Galaxy A55",
                        "Silikonska maska za Samsung Galaxy A55. Cena 1.190 MKD.",
                        _PHONE,
                        ("maska samsung", "maska a55"),
                        1190,
                    ),
                ),
                ("futrole", "stakla", "maski"),
            ),
            Subcategory(
                "kameri",
                "Kameri",
                (
                    Product(
                        "canon-200",
                        "Canon EOS 2000D",
                        "Canon EOS 2000D fotoaparat. Cena 28.990 MKD.",
                        _PHONE,
                        ("canon", "fotoaparat"),
                        28990,
                    ),
                ),
                ("kameri", "fotoaparat"),
            ),
        ),
        ("telefoni", "foto"),
    ),
    Category(
        "it",
        "Laptopovi i IT",
        (
            Subcategory(
                "laptopovi",
                "Laptopovi",
                (
                    Product(
                        "ideapad-3",
                        "Lenovo IdeaPad 3",
                        "Lenovo IdeaPad 3, 16 GB RAM. Cena 36.990 MKD. Na 12 rata po 3.083 MKD.",
                        "",
                        ("lenovo", "laptop"),
                        36990,
                    ),
                ),
                ("laptopovi", "laptop"),
            ),
            Subcategory(
                "monitori",
                "Monitori",
                (
                    Product(
                        "monitor-27",
                        "Monitor 27",
                        "Monitor 27 inca. Cena 9.990 MKD, beshe 12.490 MKD. Na akcija.",
                        "",
                        ("monitor",),
                        9990,
                        True,
                        12490,
                    ),
                ),
                ("monitori", "monitor"),
            ),
            Subcategory(
                "periferii",
                "Periferii",
                (
                    Product(
                        "mis-logi",
                        "Logitech mis",
                        "Logitech bezičen mis. Cena 1.990 MKD.",
                        "",
                        ("mis", "logitech"),
                        1990,
                    ),
                ),
                ("periferii", "mis", "tastatura"),
            ),
        ),
        ("laptopovi", "it"),
    ),
    Category(
        "tv",
        "TV i audio",
        (
            Subcategory(
                "televizori",
                "Televizori",
                (
                    Product(
                        "tv-55",
                        "TV 55 4K",
                        "Televizor 55 inca 4K. Cena 24.990 MKD, beshe 29.990 MKD. Na akcija.",
                        "",
                        ("televizor", "tv"),
                        24990,
                        True,
                        29990,
                    ),
                ),
                ("televizori", "televizor"),
            ),
            Subcategory(
                "soundbar",
                "Soundbar",
                (
                    Product(
                        "soundbar-1",
                        "Soundbar 2.1",
                        "Soundbar 2.1. Cena 8.990 MKD.",
                        "",
                        ("soundbar",),
                        8990,
                    ),
                ),
                ("soundbar",),
            ),
            Subcategory(
                "slusalki",
                "Slusalki",
                (
                    Product(
                        "sony-wh",
                        "Sony WH-CH520",
                        "Sony slusalki. Cena 3.490 MKD, beshe 4.490 MKD. Na akcija.",
                        "",
                        ("sony", "slusalki"),
                        3490,
                        True,
                        4490,
                    ),
                ),
                ("slusalki",),
            ),
        ),
        ("tv", "audio"),
    ),
    Category(
        "mali",
        "Mali kucni aparati",
        (
            Subcategory(
                "usisuvaci",
                "Usisuvaci",
                (
                    Product(
                        "xiaomi-robot",
                        "Xiaomi robot usisuvac",
                        "Xiaomi robot usisuvac. Cena 18.490 MKD. Na 6 rata po 3.082 MKD.",
                        "",
                        ("usisuvac", "robot"),
                        18490,
                    ),
                ),
                ("usisuvaci", "usisuvac"),
            ),
            Subcategory(
                "kafe",
                "Kafe aparati",
                (
                    Product(
                        "delonghi",
                        "DeLonghi kafe aparat",
                        "DeLonghi kafe aparat. Cena 9.990 MKD.",
                        "",
                        ("kafe", "delonghi"),
                        9990,
                    ),
                ),
                ("kafe aparati", "kafe aparat"),
            ),
        ),
        ("mali kucni aparati", "mali aparati"),
    ),
    Category(
        "sport",
        "Sport i nega",
        (
            Subcategory(
                "patiki",
                "Patiki",
                (
                    Product(
                        "nike-7",
                        "Nike Revolution 7",
                        "Nike Revolution 7. Cena 4.490 MKD, beshe 5.990 MKD. Na akcija.",
                        "",
                        ("nike", "patiki"),
                        4490,
                        True,
                        5990,
                    ),
                ),
                ("patiki",),
            ),
            Subcategory(
                "nega",
                "Licna nega",
                (
                    Product(
                        "philips-fen",
                        "Philips susilo za kosa",
                        "Philips susilo za kosa. Cena 4.290 MKD.",
                        "",
                        ("philips", "fen", "susilo"),
                        4290,
                    ),
                ),
                ("licna nega", "nega"),
            ),
        ),
        ("sport", "nega"),
    ),
)

_CLINIC_IMG = "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=640&q=80"
_HOTEL_IMG = "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=640&q=80"
_MEAL_IMG = "https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?auto=format&fit=crop&w=640&q=80"

CLINIC = (
    Category(
        "pregledi",
        "Pregledi",
        (
            Subcategory(
                "opsti",
                "Opst pregled",
                (
                    Product("pregled", "Opst pregled", "Opst pregled, 20 min. Cena 1.500 MKD.", _CLINIC_IMG, ("pregled",), 1500),
                    Product(
                        "kontrola",
                        "Kontrolen pregled",
                        "Kontrola, 15 min. Cena 800 MKD, beshe 1.200 MKD. Na akcija.",
                        _CLINIC_IMG,
                        ("kontrola",),
                        800,
                        True,
                        1200,
                    ),
                ),
                ("pregled",),
            ),
        ),
        ("pregledi", "doktor"),
    ),
    Category(
        "stomatolog",
        "Stomatolog",
        (
            Subcategory(
                "zabi",
                "Zabi",
                (
                    Product("vadene", "Vadene zab", "Vadene zab. Cena 2.500 MKD.", _CLINIC_IMG, ("zab", "vadene"), 2500),
                    Product("kamenac", "Cistenje kamenac", "Cistenje kamenac. Cena 1.800 MKD.", _CLINIC_IMG, ("kamenac",), 1800),
                ),
                ("stomatolog", "zab"),
            ),
        ),
        ("stomatolog",),
    ),
    Category(
        "lab",
        "Laboratorija",
        (
            Subcategory(
                "krv",
                "Analizi",
                (
                    Product("krvna", "Krvna slika", "Krvna slika, rezultat isti den. Cena 900 MKD.", _CLINIC_IMG, ("krv", "laboratorija"), 900),
                ),
                ("analizi", "krv"),
            ),
        ),
        ("laboratorija",),
    ),
)

HOTEL = (
    Category(
        "sobi",
        "Sobi",
        (
            Subcategory(
                "nokj",
                "Nokjevki",
                (
                    Product("standard", "Standardna soba", "Standardna soba, 1 nokj. Cena 4.200 MKD.", _HOTEL_IMG, ("standard", "soba"), 4200),
                    Product(
                        "more",
                        "Soba so pogled na more",
                        "Pogled na more, 1 nokj. Cena 6.800 MKD, beshe 7.600 MKD. Na akcija.",
                        _HOTEL_IMG,
                        ("more", "pogled"),
                        6800,
                        True,
                        7600,
                    ),
                    Product("suite", "Suite", "Suite, 1 nokj. Cena 11.900 MKD.", _HOTEL_IMG, ("suite",), 11900),
                ),
                ("soba", "nokj"),
            ),
        ),
        ("sobi", "hotel"),
    ),
    Category(
        "dodatoci",
        "Dodatoci",
        (
            Subcategory(
                "extra",
                "Za prestojot",
                (
                    Product("dorucok", "Dorucok", "Dorucok za eden gost. Cena 900 MKD.", _MEAL_IMG, ("dorucok", "breakfast"), 900),
                    Product("late", "Late checkout", "Late checkout do 14h. Cena 1.200 MKD.", _HOTEL_IMG, ("late", "checkout"), 1200),
                    Product("transfer", "Transfer aerodrom", "Transfer do aerodrom. Cena 1.800 MKD.", _HOTEL_IMG, ("transfer", "aerodrom"), 1800),
                ),
                ("dorucok", "transfer"),
            ),
        ),
        ("dodatoci",),
    ),
)

LUNA = build_luna()
_CATALOGS = {"ananas": ANANAS, "health-clinic": CLINIC, "baltic": HOTEL, "luna": LUNA}
_MODE = {"health-clinic": "clinic", "baltic": "hotel", "luna": "look"}
_LOOKS = {
    "luna": (
        ("dress-black", "bag-black", "heels-black"),
        ("dress-red", "bag-mini", "heels-nude"),
    ),
}
_PAIR = {
    "redmi-13": "maska-redmi",
    "galaxy-a55": "maska-a55",
    "iphone-13": "futrola-13",
    "tv-55": "soundbar-1",
    "ideapad-3": "mis-logi",
    "pregled": "krvna",
    "vadene": "kamenac",
    "standard": "dorucok",
    "more": "dorucok",
    "suite": "late",
}
_FAMILY_ADDON = {
    "telefoni": ("maska-redmi", "maska-a55", "futrola-13", "sony-wh"),
    "it": ("mis-logi", "monitor-27"),
    "tv": ("soundbar-1",),
}
_BUNDLE_OFF = 0.8
_PAGE = 12
_SALE = "__sale__"


def _line(tenant_id: str, lang: str, key: str, **values: object) -> str:
    return say(lang, key, _MODE.get(tenant_id, "shop"), **values)


def opening_choices(tenant_id: str, lang: str = "") -> List[Choice]:
    tree = _CATALOGS.get(tenant_id)
    if not tree:
        return []
    if lang:
        choices = [Choice(_line(tenant_id, lang, "sale"), "Na akcija")]
        choices.extend(Choice(category.label, category.label) for category in tree)
        choices.append(Choice(say(lang, "change_lang"), "jezik"))
        return choices
    return [Choice(label, message) for label, message in language_chips()]


def knowledge_rows(tenant_id: str) -> List[dict]:
    """Catalog lines stored as tenant knowledge, one row per product."""
    tree = _CATALOGS.get(tenant_id)
    if not tree:
        return []
    rows = []
    for category in tree:
        for child in category.children:
            for product in child.products:
                rows.append(
                    {
                        "kind": "product",
                        "title": product.title,
                        "body": product.detail,
                        "attributes": {
                            "category": category.label,
                            "subcategory": child.label,
                            "id": product.id,
                            "image_url": product.image_url,
                            "price_mkd": product.price_mkd,
                            "on_sale": product.on_sale,
                            "old_price_mkd": product.old_price_mkd,
                        },
                    }
                )
    return rows


def advance(tenant_id: str, session_id: str, message: str) -> Optional[FlowReply]:
    """Move one step in the store menu. None when this tenant has no menu."""
    tree = _CATALOGS.get(tenant_id)
    if not tree:
        return None
    folded = _fold(message)
    lang = flow_lang(tenant_id, session_id)
    picked = explicit_lang(folded)
    if folded in ("jezik", "jazik", "gjuha", "sprache", "language") or (not lang and folded == "menu"):
        return _ask_lang(tenant_id, session_id)
    if picked:
        set_flow_lang(tenant_id, session_id, picked)
        lang = picked
        return FlowReply(say(lang, "lang_set"), opening_choices(tenant_id, lang), "")
    if not lang:
        guessed = detect_lang(folded)
        catalog_ready = _search_catalog(tree, folded) is not None or _best_match(tree, folded) is not None
        if guessed and not catalog_ready:
            set_flow_lang(tenant_id, session_id, guessed)
            return FlowReply(say(guessed, "lang_set"), opening_choices(tenant_id, guessed), "")
        if guessed:
            set_flow_lang(tenant_id, session_id, guessed)
            lang = guessed
        elif catalog_ready:
            set_flow_lang(tenant_id, session_id, "mk")
            lang = "mk"
        else:
            return _ask_lang(tenant_id, session_id)
    listed = _search_catalog(tree, folded)
    if listed is not None:
        reply, category_id = listed
        set_flow(tenant_id, session_id, category_id, "", "")
        return reply
    category_id, subcategory_id, product_id = flow_position(tenant_id, session_id)
    category = _by_id(tree, category_id)
    subcategory = _child(category, subcategory_id) if category else None
    product = _product(subcategory, product_id) if subcategory else None

    if folded in ("jos", "uste", "more", "dalje", "next"):
        page = flow_page(tenant_id, session_id) + 1
        if category_id == _SALE:
            return _show_sale(tenant_id, session_id, page)
        if category and subcategory:
            return _show_subcategory(tenant_id, session_id, category, subcategory, page)
        if category:
            return _show_category(tenant_id, session_id, category, page)

    if _has(folded, ("kategorii", "kategorija", "kategorije", "pocetok", "meni", "menu", "kategorien")):
        return _root(tenant_id, session_id)
    if _has(folded, ("akcija", "popust", "ponuda", "snizen", "zbritje", "angebot", "sale")):
        return _show_sale(tenant_id, session_id)
    if folded in ("nazad", "natrag", "prapa", "zuruck", "back"):
        return _back(tenant_id, session_id, category, subcategory, product)

    wanted_cart = folded in CART_PHRASES
    if wanted_cart:
        if product:
            return _put_in_cart(tenant_id, session_id, tree, product)
        return FlowReply(_line(tenant_id, lang, "pick_model"), _here(tree, category, subcategory, product, lang, tenant_id), "")

    match = _best_match(tree, folded)
    if match is not None:
        kind, payload = match
        if kind == "product":
            parent_category, parent_sub, item = payload
            return _show_product(tenant_id, session_id, parent_category, parent_sub, item, item.detail, True)
        if kind == "subcategory":
            parent_category, item = payload
            return _show_subcategory(tenant_id, session_id, parent_category, item)
        return _show_category(tenant_id, session_id, payload)

    wanted_image = folded in ("slika", "sliku", "slike", "vidi slika", "vidi sliku", "bild", "photo", "foto")
    wanted_other = folded in ("druga", "drugi", "drugu", "uste", "druga masina", "tjetër", "anderes", "another")
    if subcategory and wanted_other:
        nxt = _next_product(subcategory, product)
        return _show_product(
            tenant_id,
            session_id,
            category,
            subcategory,
            nxt,
            nxt.detail,
            True,
        )
    if product and wanted_image:
        return _show_product(tenant_id, session_id, category, subcategory, product, product.detail, True)
    if product and folded in ("na rate", "rata", "rati", "keste", "raten", "installments"):
        return FlowReply(product.detail, _product_choices(lang, tenant_id), "")
    if folded in ("dostava", "isporaka", "shipping", "versand", "dergese"):
        return FlowReply(say(lang, "shipping"), _here(tree, category, subcategory, product, lang), "")
    return FlowReply(say(lang, "fallback"), _here(tree, category, subcategory, product, lang), "")


def _ask_lang(tenant_id: str, session_id: str) -> FlowReply:
    set_flow(tenant_id, session_id, "", "", "")
    return FlowReply(GREETING_ALL, [Choice(label, message) for label, message in language_chips()], "")


def _root(tenant_id: str, session_id: str) -> FlowReply:
    set_flow(tenant_id, session_id, "", "", "")
    lang = flow_lang(tenant_id, session_id) or "mk"
    return FlowReply(say(lang, "choose"), opening_choices(tenant_id, lang), "")


def _offer(product: Product) -> CartOffer:
    picture = product.image_url or _PHONE
    old = product.old_price_mkd if product.on_sale else 0
    return CartOffer(product.id, product.title, _product_price(product), picture, old)


def _nav_choices(lang: str, extras: Optional[Sequence[Choice]] = None) -> List[Choice]:
    choices = list(extras or ())
    choices.append(Choice(say(lang, "categories"), "kategorii"))
    choices.append(Choice(say(lang, "change_lang"), "jezik"))
    return choices


def _window(items: Sequence, page: int):
    page = max(0, page)
    start = page * _PAGE
    chunk = list(items[start : start + _PAGE])
    total = len(items)
    more = start + _PAGE < total
    if not total:
        label = "0"
    elif total <= _PAGE and page == 0:
        label = str(total)
    else:
        label = "{start}–{end} od {total}".format(
            start=start + 1,
            end=min(total, start + len(chunk)),
            total=total,
        )
    return chunk, more, label


def _show_sale(tenant_id: str, session_id: str, page: int = 0) -> FlowReply:
    set_flow(tenant_id, session_id, _SALE, "", "")
    set_flow_page(tenant_id, session_id, page)
    tree = _CATALOGS.get(tenant_id) or ()
    lang = flow_lang(tenant_id, session_id) or "mk"
    rows = _sale_rows(tree)
    if not rows:
        return FlowReply(_line(tenant_id, lang, "no_sale"), opening_choices(tenant_id, lang), "")
    chunk, more, span = _window(rows, page)
    extras = [Choice("Jos", "jos")] if more else []
    cards = [_offer(product) for _category, _child, product in chunk]
    return FlowReply(
        _line(tenant_id, lang, "sale") + ". " + span + ".",
        _nav_choices(lang, extras),
        "",
        None,
        None,
        cards,
    )


def _sale_rows(tree: Sequence[Category]) -> List[Tuple[Category, Subcategory, Product]]:
    rows = []
    for category in tree:
        for child in category.children:
            for product in child.products:
                if product.on_sale:
                    rows.append((category, child, product))
    return rows


def _show_category(tenant_id: str, session_id: str, category: Category, page: int = 0) -> FlowReply:
    set_flow(tenant_id, session_id, category.id, "", "")
    set_flow_page(tenant_id, session_id, page)
    lang = flow_lang(tenant_id, session_id) or "mk"
    products = [product for child in category.children for product in child.products]
    chunk, more, span = _window(products, page)
    extras = [Choice(child.label, child.label) for child in category.children]
    if more:
        extras.insert(0, Choice("Jos", "jos"))
    extras.append(Choice(say(lang, "back"), "nazad"))
    cards = [_offer(product) for product in chunk]
    return FlowReply(category.label + ". " + span + ".", _nav_choices(lang, extras), "", None, None, cards)


def _show_subcategory(
    tenant_id: str,
    session_id: str,
    category: Category,
    subcategory: Subcategory,
    page: int = 0,
) -> FlowReply:
    set_flow(tenant_id, session_id, category.id, subcategory.id, "")
    set_flow_page(tenant_id, session_id, page)
    lang = flow_lang(tenant_id, session_id) or "mk"
    chunk, more, span = _window(subcategory.products, page)
    extras = [Choice("Jos", "jos")] if more else []
    extras.append(Choice(say(lang, "back"), "nazad"))
    cards = [_offer(product) for product in chunk]
    return FlowReply(subcategory.label + ". " + span + ".", _nav_choices(lang, extras), "", None, None, cards)


def _show_product(
    tenant_id: str,
    session_id: str,
    category: Category,
    subcategory: Subcategory,
    product: Product,
    text: str,
    with_image: bool,
) -> FlowReply:
    set_flow(tenant_id, session_id, category.id, subcategory.id, product.id)
    lang = flow_lang(tenant_id, session_id) or "mk"
    shots = product.gallery or ((product.image_url,) if with_image and product.image_url else ())
    return FlowReply(
        text,
        _product_choices(lang, tenant_id),
        "",
        None,
        CartOffer(
            product.id,
            product.title,
            _product_price(product),
            product.image_url,
            detail=product.facts or product.detail,
            images=shots,
        ),
    )


def _back(
    tenant_id: str,
    session_id: str,
    category: Optional[Category],
    subcategory: Optional[Subcategory],
    product: Optional[Product],
) -> FlowReply:
    if product and category and subcategory:
        return _show_subcategory(tenant_id, session_id, category, subcategory)
    if subcategory and category:
        return _show_category(tenant_id, session_id, category)
    if category:
        return _root(tenant_id, session_id)
    return _root(tenant_id, session_id)


def _put_in_cart(
    tenant_id: str,
    session_id: str,
    tree: Sequence[Category],
    product: Product,
) -> FlowReply:
    lang = flow_lang(tenant_id, session_id) or "mk"
    look = _look_for(tenant_id, product.id)
    if look:
        return _put_look(tenant_id, session_id, tree, product, look, lang)
    taken = cart_ids(tenant_id, session_id)
    price = _product_price(product)
    if taken:
        price = int(round(price * _BUNDLE_OFF))
    remember_cart(tenant_id, session_id, product.id)
    owned = taken + [product.id]
    addon = _recommend(tree, product, owned) if not taken else None
    suggestions = [
        Choice(say(lang, "categories"), "kategorii"),
        Choice(_line(tenant_id, lang, "sale"), "Na akcija"),
        Choice(say(lang, "back"), "nazad"),
    ]
    card = None
    cards: List[CartOffer] = []
    if addon:
        parent, child, extra = addon
        full = _product_price(extra)
        extra_price = int(round(full * _BUNDLE_OFF))
        set_flow(tenant_id, session_id, parent.id, child.id, extra.id)
        suggestions = [
            Choice(say(lang, "add_addon"), "u kosnicka"),
            Choice(say(lang, "categories"), "kategorii"),
            Choice(_line(tenant_id, lang, "sale"), "Na akcija"),
        ]
        card = CartOffer(extra.id, extra.title, extra_price, extra.image_url or _PHONE, full)
        cards = [card]
        text = _line(tenant_id, lang, "in_cart_addon", title=product.title, addon=extra.title, price=_money(extra_price))
    else:
        text = _line(tenant_id, lang, "in_cart", title=product.title)
    return FlowReply(
        text,
        suggestions,
        "",
        CartOffer(product.id, product.title, price, product.image_url),
        card,
        cards,
    )


def _look_for(tenant_id: str, product_id: str) -> Optional[Tuple[str, ...]]:
    for trio in _LOOKS.get(tenant_id, ()):
        if product_id in trio:
            return trio
    return None


def _put_look(
    tenant_id: str,
    session_id: str,
    tree: Sequence[Category],
    product: Product,
    look: Tuple[str, ...],
    lang: str,
) -> FlowReply:
    taken = cart_ids(tenant_id, session_id)
    full = _product_price(product)
    remember_cart(tenant_id, session_id, product.id)
    owned = taken + [product.id]
    missing = [item_id for item_id in look if item_id not in owned]
    price = full
    percent = 0
    if not missing:
        percent = 20
        price = int(round(full * _BUNDLE_OFF))
        text = say(lang, "look_done")
        cards: List[CartOffer] = []
    else:
        text = say(lang, "look_next")
        cards = []
        for item_id in missing:
            found = _locate(tree, item_id)
            if found:
                cards.append(_offer(found[2]))
        if cards:
            parent, child, nxt = _locate(tree, cards[0].id)
            set_flow(tenant_id, session_id, parent.id, child.id, nxt.id)
    return FlowReply(
        text,
        [],
        "",
        CartOffer(product.id, product.title, price, product.image_url, full if percent else 0, percent, look if percent else ()),
        None,
        cards,
    )


def _recommend(
    tree: Sequence[Category],
    product: Product,
    taken: Sequence[str],
) -> Optional[Tuple[Category, Subcategory, Product]]:
    wanted = []
    paired = _PAIR.get(product.id)
    if paired:
        wanted.append(paired)
    home = ""
    for category in tree:
        extras = _FAMILY_ADDON.get(category.id, ())
        if any(item.id == product.id for child in category.children for item in child.products):
            home = category.id
            wanted.extend(extras)
    ranked = []
    for category in tree:
        for child in category.children:
            for item in child.products:
                if item.id in taken:
                    continue
                score = 0
                if item.id == paired:
                    score += 100
                elif item.id in wanted:
                    score += 60
                if home and category.id == home:
                    score += 30
                if item.on_sale:
                    score += 20
                if _product_price(item) < _product_price(product):
                    score += 10
                ranked.append((score, _product_price(item), category, child, item))
    if not ranked:
        return None
    ranked.sort(key=lambda row: (-row[0], row[1]))
    _score, _price, category, child, item = ranked[0]
    return category, child, item


def _locate(tree: Sequence[Category], product_id: str) -> Optional[Tuple[Category, Subcategory, Product]]:
    for category in tree:
        for child in category.children:
            for item in child.products:
                if item.id == product_id:
                    return category, child, item
    return None


def _product_choices(lang: str = "mk", tenant_id: str = "") -> List[Choice]:
    return [
        Choice(_line(tenant_id, lang, "cart"), "u kosnicka"),
        Choice(_line(tenant_id, lang, "sale"), "Na akcija"),
        Choice(say(lang, "other"), "druga"),
        Choice(say(lang, "photo"), "slika"),
        Choice(say(lang, "installment"), "na rate"),
        Choice(say(lang, "back"), "nazad"),
    ]


def _here(
    tree: Sequence[Category],
    category: Optional[Category],
    subcategory: Optional[Subcategory],
    product: Optional[Product],
    lang: str = "mk",
    tenant_id: str = "",
) -> List[Choice]:
    if product:
        return _product_choices(lang, tenant_id)
    if subcategory and category:
        choices = [Choice(item.title, item.title) for item in subcategory.products]
        choices.append(Choice("Nazad", "nazad"))
        return choices
    if category:
        choices = [Choice(child.label, child.label) for child in category.children]
        choices.append(Choice("Kategorii", "kategorii"))
        return choices
    return [Choice(item.label, item.label) for item in tree]


def _best_match(tree: Sequence[Category], folded: str):
    found = []
    for category in tree:
        _consider(found, folded, category.label, category.aliases, "category", category, 2)
        for child in category.children:
            _consider(found, folded, child.label, child.aliases, "subcategory", (category, child), 2)
            for product in child.products:
                _consider(found, folded, product.title, product.aliases, "product", (category, child, product), 3)
    if not found:
        return None
    found.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return found[0][2], found[0][3]


def _consider(found: list, folded: str, label: str, aliases: Sequence[str], kind: str, payload, rank: int) -> None:
    for name in (_fold(label),) + tuple(_fold(alias) for alias in aliases):
        if name and (name == folded or name in folded):
            found.append((len(name), rank, kind, payload))
            return


def _next_product(subcategory: Subcategory, current: Optional[Product]) -> Product:
    products = subcategory.products
    if current is None:
        return products[0]
    for index, product in enumerate(products):
        if product.id == current.id:
            return products[(index + 1) % len(products)]
    return products[0]


_AMOUNT = re.compile(r"\d{1,3}(?:[ .]\d{3})+|\d{2,7}")
_EUR_TO_MKD = 61.5
_GROUPS = (
    ("telefon", ("telefon", "mobil", "iphone", "ajfon", "galaxy", "redmi", "handy", "phone")),
    ("masina", ("masina", "masini", "ves masina", "perenje", "peraln")),
    ("frizider", ("frizider",)),
    ("laptop", ("laptop", "lenovo")),
    ("tv", ("televizor", "tv 55", "tv")),
    ("usisuvac", ("usisuvac", "robot")),
)
_BROAD = (
    "telefon",
    "mobil",
    "masina",
    "masini",
    "frizider",
    "perenje",
    "peraln",
    "laptop",
    "televizor",
    "usisuvac",
)
_SPECIFIC = (
    "samsung",
    "iphone",
    "ajfon",
    "galaxy",
    "redmi",
    "xiaomi",
    "beko",
    "gorenje",
    "lenovo",
    "nike",
    "sony",
    "philips",
)
# Stems, so "излистајме", "излиште", and "izlistaj" all become the same list request.
_LIST_STEMS = (
    "izlis",
    "lista",
    "prikaz",
    "pokaz",
    "najd",
    "nadj",
    "baram",
    "sakam",
    "site",
    "sve",
    "search",
    "looking",
    "find",
    "suchen",
    "zeig",
    "gjej",
    "kerkoj",
)


def _money(amount: int) -> str:
    return "{:,}".format(amount).replace(",", ".")


def _product_price(product: Product) -> int:
    if product.price_mkd:
        return product.price_mkd
    return _listed_price(product.detail)


def _listed_price(detail: str) -> int:
    match = re.search(r"cena (\d{1,3}(?:\.\d{3})+)", _fold(detail))
    if not match:
        return 0
    return int(match.group(1).replace(".", ""))


def _budget(folded: str) -> Tuple[Optional[int], str]:
    """Turn the first amount into an MKD ceiling. Euros use a fixed local rate."""
    amounts = [int(match.group(0).replace(" ", "").replace(".", "")) for match in _AMOUNT.finditer(folded)]
    if not amounts:
        return None, ""
    if _has(folded, ("nad ", "preku")) and not _has(folded, ("do ",)):
        return None, ""
    raw = amounts[0]
    if _has(folded, ("evr", "euro", "eur")):
        return int(round(raw * _EUR_TO_MKD)), "{amount} EUR".format(amount=_money(raw))
    if not _has(folded, ("den", "mkd", "cena", "do ", "nad ", "preku")):
        return None, ""
    return raw, ""


def _search_catalog(tree: Sequence[Category], folded: str) -> Optional[Tuple[FlowReply, str]]:
    """Build a catalog query from the sentence, in whichever language it arrived."""
    asks = _has(folded, _LIST_STEMS)
    ceiling, money_note = _budget(folded)
    sale_only = _has(folded, ("akcija", "popust", "snizen"))
    if not asks and ceiling is None:
        return None
    group = ""
    group_words: Tuple[str, ...] = ()
    for name, words in _GROUPS:
        if _has(folded, words):
            group = name
            group_words = words
            break
    if not group and ceiling is None and not sale_only:
        return None
    needles = tuple(word for word in _SPECIFIC if word in folded and word not in _BROAD)
    matches = []
    for category in tree:
        for child in category.children:
            for product in child.products:
                blob = _fold(product.title + " " + product.detail + " " + " ".join(product.aliases) + " " + child.label)
                if group and not _has(blob, group_words):
                    continue
                if needles and not _has(_fold(product.title + " " + " ".join(product.aliases)), needles):
                    continue
                price = _product_price(product)
                if sale_only and not product.on_sale:
                    continue
                if ceiling is not None and price > ceiling:
                    continue
                matches.append((price, category, child, product))
    matches.sort(key=lambda item: item[0])
    label = {
        "telefon": "Telefoni",
        "masina": "Masini za perenje",
        "frizider": "Frizideri",
        "laptop": "Laptopovi",
        "tv": "Televizori",
        "usisuvac": "Usisuvaci",
    }.get(group, "Proizvodi")
    if ceiling is None:
        limit = ""
    elif money_note:
        limit = " do {note} ({amount} MKD)".format(note=money_note, amount=_money(ceiling))
    else:
        limit = " do {amount} MKD".format(amount=_money(ceiling))
    if sale_only:
        label = "Na akcija, " + label.lower() if group else "Na akcija"
    if not matches:
        nearest = _nearest(tree, group, needles)
        if nearest is None:
            return (
                FlowReply(
                    "Nema takvi proizvodi vo katalogot.",
                    [Choice(item.label, item.label) for item in tree],
                    "",
                ),
                "",
            )
        return (
            FlowReply(
                "Nema {what}{limit}. Najblisku e {title} za {price} MKD.".format(
                    what=label.lower(),
                    limit=limit,
                    title=nearest[1].title,
                    price=_money(nearest[0]),
                ),
                [Choice(nearest[1].title, nearest[1].title), Choice("Kategorii", "kategorii")],
                "",
            ),
            "",
        )
    total = len(matches)
    matches = matches[:_PAGE]
    cards = [_offer(product) for _price, _category, _child, product in matches]
    choices = [Choice(child.label, child.label) for _price, _category, child, _product in matches]
    seen = []
    unique = []
    for choice in choices:
        if choice.message in seen:
            continue
        seen.append(choice.message)
        unique.append(choice)
    unique.append(Choice("Kategorii", "kategorii"))
    category_id = matches[0][1].id if len({row[1].id for row in matches}) == 1 else ""
    headline = "{what}{limit}. {shown} od {total}.".format(
        what=label, limit=limit, shown=len(matches), total=total
    )
    return FlowReply(headline, unique, "", None, None, cards), category_id


def _nearest(tree: Sequence[Category], group: str, needles: Sequence[str] = ()) -> Optional[Tuple[int, Product]]:
    words = ()
    for name, group_words in _GROUPS:
        if name == group:
            words = group_words
    ranked = []
    for category in tree:
        for child in category.children:
            for product in child.products:
                blob = _fold(product.title + " " + child.label + " " + " ".join(product.aliases))
                if words and not _has(blob, words):
                    continue
                if needles and not _has(_fold(product.title + " " + " ".join(product.aliases)), needles):
                    continue
                ranked.append((_product_price(product), product))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0])
    return ranked[0]


def _has(folded: str, phrases: Sequence[str]) -> bool:
    return any(phrase in folded for phrase in phrases)


def _by_id(tree: Sequence[Category], category_id: str) -> Optional[Category]:
    for category in tree:
        if category.id == category_id:
            return category
    return None


def _child(category: Optional[Category], subcategory_id: str) -> Optional[Subcategory]:
    if category is None:
        return None
    for child in category.children:
        if child.id == subcategory_id:
            return child
    return None


def _product(subcategory: Optional[Subcategory], product_id: str) -> Optional[Product]:
    if subcategory is None:
        return None
    for product in subcategory.products:
        if product.id == product_id:
            return product
    return None
