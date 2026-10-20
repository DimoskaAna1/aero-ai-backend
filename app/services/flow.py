import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from app.services.memory import flow_position, set_flow

_FOLDS = str.maketrans({"š": "s", "č": "c", "ć": "c", "ž": "z", "đ": "d"})
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
    lowered = text.casefold()
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
class FlowReply:
    text: str
    suggestions: List[Choice] = field(default_factory=list)
    image_url: str = ""


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
                    ),
                    Product(
                        "gorenje-7",
                        "Gorenje 7 kg",
                        "Gorenje ves masina 7 kg, 1400 obrtaja. Cena 24.990 MKD. Na 12 rata po 2.083 MKD. Besplatna dostava.",
                        _WASHER_TWO,
                        ("gorenje masina",),
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
                    ),
                    Product(
                        "beko-fridge",
                        "Beko RCSA 270",
                        "Beko kombinovan frizider RCSA 270. Cena 22.490 MKD. Na 12 rata po 1.874 MKD.",
                        _FRIDGE_TWO,
                        ("beko frizider",),
                    ),
                ),
                ("frizider",),
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
                        "Xiaomi Redmi 13 128GB. Cena 14.990 MKD. Na 6 rata po 2.498 MKD. Besplatna dostava.",
                        _PHONE,
                        ("redmi", "xiaomi"),
                    ),
                    Product(
                        "galaxy-a55",
                        "Samsung Galaxy A55",
                        "Samsung Galaxy A55 8/128. Cena 24.990 MKD. Na 12 rata po 2.083 MKD. Besplatna dostava.",
                        _PHONE,
                        ("galaxy", "samsung"),
                    ),
                    Product(
                        "iphone-13",
                        "iPhone 13",
                        "iPhone 13 128GB. Cena 42.990 MKD. Na 12 rata po 3.583 MKD. Besplatna dostava.",
                        _PHONE_TWO,
                        ("iphone", "ajfon"),
                    ),
                ),
                ("mobilni", "telefon"),
            ),
        ),
        ("telefoni", "foto"),
    ),
)

_CATALOGS = {"ananas": ANANAS}
_SHIPPING = (
    "Besplatna dostava za porudzbini preku 3.000 MKD. "
    "Pod toa, dostavata e 150 MKD i stignuva za 1 do 3 rabotni dena."
)


def opening_choices(tenant_id: str) -> List[Choice]:
    tree = _CATALOGS.get(tenant_id)
    if not tree:
        return []
    return [Choice(category.label, category.label) for category in tree]


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
    listed = _search_catalog(tree, folded)
    if listed is not None:
        reply, category_id = listed
        set_flow(tenant_id, session_id, category_id, "", "")
        return reply
    category_id, subcategory_id, product_id = flow_position(tenant_id, session_id)
    category = _by_id(tree, category_id)
    subcategory = _child(category, subcategory_id) if category else None
    product = _product(subcategory, product_id) if subcategory else None

    if _has(folded, ("kategorii", "kategorija", "pocetok", "meni")):
        return _root(tenant_id, session_id)
    if folded == "nazad":
        return _back(tenant_id, session_id, category, subcategory, product)

    wanted_image = _has(folded, ("slika", "sliku", "slike", "fotografija"))
    wanted_other = _has(folded, ("druga", "drugi", "drugu", "uste"))
    if subcategory and wanted_other:
        nxt = _next_product(subcategory, product)
        return _show_product(
            tenant_id,
            session_id,
            category,
            subcategory,
            nxt,
            "Ova e drugiot model. " + nxt.detail,
            True,
        )
    if product and wanted_image:
        return _show_product(tenant_id, session_id, category, subcategory, product, product.detail, True)
    if product and _has(folded, ("na rate", "rata", "rati")):
        return FlowReply(product.detail, _product_choices(), "")
    if _has(folded, ("dostava", "isporaka", "shipping")):
        return FlowReply(_SHIPPING, _here(tree, category, subcategory, product), "")

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
    return FlowReply("Izberi od ponudenite opcii.", _here(tree, category, subcategory, product), "")


def _root(tenant_id: str, session_id: str) -> FlowReply:
    set_flow(tenant_id, session_id, "", "", "")
    return FlowReply("Izberi kategorija.", opening_choices(tenant_id), "")


def _show_category(tenant_id: str, session_id: str, category: Category) -> FlowReply:
    set_flow(tenant_id, session_id, category.id, "", "")
    choices = [Choice(child.label, child.label) for child in category.children]
    choices.append(Choice("Kategorii", "kategorii"))
    return FlowReply("{label}. Izberi podkategorija.".format(label=category.label), choices, "")


def _show_subcategory(
    tenant_id: str,
    session_id: str,
    category: Category,
    subcategory: Subcategory,
) -> FlowReply:
    set_flow(tenant_id, session_id, category.id, subcategory.id, "")
    choices = [Choice(product.title, product.title) for product in subcategory.products]
    choices.append(Choice("Nazad", "nazad"))
    return FlowReply("{label}. Izberi model.".format(label=subcategory.label), choices, "")


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
    return FlowReply(text, _product_choices(), product.image_url if with_image else "")


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


def _product_choices() -> List[Choice]:
    return [
        Choice("Druga masina", "druga"),
        Choice("Vidi slika", "slika"),
        Choice("Na rate", "na rate"),
        Choice("Nazad", "nazad"),
    ]


def _here(
    tree: Sequence[Category],
    category: Optional[Category],
    subcategory: Optional[Subcategory],
    product: Optional[Product],
) -> List[Choice]:
    if product:
        return _product_choices()
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
    ("telefon", ("telefon", "mobil", "samsung", "iphone", "ajfon", "galaxy", "redmi", "xiaomi")),
    ("masina", ("masina", "masini", "ves masina", "perenje", "peraln")),
    ("frizider", ("frizider",)),
)
_BROAD = ("telefon", "mobil", "masina", "masini", "frizider", "perenje", "peraln")
_SPECIFIC = ("samsung", "iphone", "ajfon", "galaxy", "redmi", "xiaomi", "beko", "gorenje")
# Stems, so "излистајме", "излиште", and "izlistaj" all become the same list request.
_LIST_STEMS = ("izlis", "lista", "prikaz", "pokaz", "najd", "nadj", "baram", "sakam", "site", "sve")


def _money(amount: int) -> str:
    return "{:,}".format(amount).replace(",", ".")


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
    if not asks and ceiling is None:
        return None
    group = ""
    group_words: Tuple[str, ...] = ()
    for name, words in _GROUPS:
        if _has(folded, words):
            group = name
            group_words = words
            break
    if not group and ceiling is None:
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
                price = _listed_price(product.detail)
                if ceiling is not None and price > ceiling:
                    continue
                matches.append((price, category, child, product))
    matches.sort(key=lambda item: item[0])
    label = {"telefon": "Telefoni", "masina": "Masini za perenje", "frizider": "Frizideri"}.get(group, "Proizvodi")
    if ceiling is None:
        limit = ""
    elif money_note:
        limit = " do {note} ({amount} MKD)".format(note=money_note, amount=_money(ceiling))
    else:
        limit = " do {amount} MKD".format(amount=_money(ceiling))
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
    lines = ["{what}{limit}:".format(what=label, limit=limit)]
    choices = []
    subcategories = []
    category_ids = []
    for price, category, child, product in matches:
        lines.append("{title} — {price} MKD".format(title=product.title, price=_money(price)))
        choices.append(Choice("{title} · {price}".format(title=product.title, price=_money(price)), product.title))
        if child.id not in [item.id for item in subcategories]:
            subcategories.append(child)
        if category.id not in category_ids:
            category_ids.append(category.id)
    lines.append("Izberi podkategorija.")
    for child in subcategories:
        choices.append(Choice(child.label, child.label))
    choices.append(Choice("Kategorii", "kategorii"))
    category_id = category_ids[0] if len(category_ids) == 1 else ""
    return FlowReply("\n".join(lines), choices, ""), category_id


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
                ranked.append((_listed_price(product.detail), product))
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
