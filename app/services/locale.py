"""Shop-language pack. Catalog prices stay in flow.py; only chrome is translated."""

from typing import Dict, Optional, Tuple

LANGS = ("mk", "sr", "hr", "sq", "de", "en")

_PICK = {
    "mk": "mk",
    "makedonski": "mk",
    "macedonian": "mk",
    "sr": "sr",
    "srpski": "sr",
    "serbian": "sr",
    "hr": "hr",
    "hrvatski": "hr",
    "croatian": "hr",
    "sq": "sq",
    "shqip": "sq",
    "albanian": "sq",
    "de": "de",
    "deutsch": "de",
    "german": "de",
    "nemacki": "de",
    "njemacki": "de",
    "en": "en",
    "english": "en",
    "engleski": "en",
}

_HINTS = (
    ("sq", ("pershendetje", "faleminderit", "shqip", "une ", "eshte", "telefoni", "shto ne")),
    ("de", ("hallo", "guten tag", "guten morgen", "bitte", "danke", "handy", "in den korb", "deutsch")),
    ("en", ("hello", "hi there", "please", "thank you", "english", "add to cart", "under ")),
    ("hr", ("hrvatski", "mobitel", "bok ", "sto zelim", "kosaricu")),
    ("sr", ("srpski", "cao", "zelim", "u korpu", "molim te")),
    ("mk", ("makedonski", "zdravo", "sakam", "molam", "denari", "u kosnicka")),
)

COPY: Dict[str, Dict[str, str]] = {
    "mk": {
        "greeting": "Zdravo. Izberi jezik, pa kazi sto baras.",
        "lang_set": "Vo red, nastavuvame na makedonski. Sto baras?",
        "choose": "Izberi kategorija ili proizvodi na akcija.",
        "sale": "Na akcija",
        "no_sale": "Sega nema proizvodi na akcija.",
        "pick_model": "Prvo izberi model, pa U kosnicka.",
        "in_cart": "{title} e vo kosnickata.",
        "in_cart_addon": "{title} e vo kosnickata. Nastavi kupovina — vtoriot proizvod preku Ana ima 20% popust. Preporaka: {addon}, sega {price} MKD.",
        "add_addon": "Nastavi · -20%",
        "shipping": "Besplatna dostava nad 3.000 MKD. Pod toa 150 MKD, 1–3 dena.",
        "fallback": "Izberi od ponudenite opcii.",
        "change_lang": "Jezik",
        "cart": "U kosnicka",
        "other": "Druga",
        "photo": "Vidi slika",
        "installment": "Na rate",
        "back": "Nazad",
        "categories": "Kategorii",
        "pick_lang": "Jazik",
        "look_next": "Dodadeno vo kosnicka. Nastavete so kupovinate na kombinacijata — 3 artikli i imate 20% na site.",
        "look_done": "Kombinacijata e cela. 20% na site 3 artikli.",
    },
    "sr": {
        "greeting": "Ćao. Izaberi jezik, pa reci šta tražiš.",
        "lang_set": "U redu, nastavljamo na srpskom. Šta tražiš?",
        "choose": "Izaberi kategoriju ili proizvode na akciji.",
        "sale": "Na akciji",
        "no_sale": "Trenutno nema proizvoda na akciji.",
        "pick_model": "Prvo izaberi model, pa U korpu.",
        "in_cart": "{title} je u korpi.",
        "in_cart_addon": "{title} je u korpi. Nastavi kupovinu — drugi proizvod preko Ane ima 20% popusta. Preporuka: {addon}, sada {price} MKD.",
        "add_addon": "Nastavi · -20%",
        "shipping": "Besplatna dostava preko 3.000 MKD. Ispod toga 150 MKD, 1–3 dana.",
        "fallback": "Izaberi jednu od ponuđenih opcija.",
        "change_lang": "Jezik",
        "cart": "U korpu",
        "other": "Drugi",
        "photo": "Vidi sliku",
        "installment": "Na rate",
        "back": "Nazad",
        "categories": "Kategorije",
        "pick_lang": "Jezik",
    },
    "hr": {
        "greeting": "Bok. Odaberi jezik, pa reci što tražiš.",
        "lang_set": "U redu, nastavljamo na hrvatskom. Što tražiš?",
        "choose": "Odaberi kategoriju ili proizvode na akciji.",
        "sale": "Na akciji",
        "no_sale": "Trenutačno nema proizvoda na akciji.",
        "pick_model": "Prvo odaberi model, pa U košaricu.",
        "in_cart": "{title} je u košarici.",
        "in_cart_addon": "{title} je u košarici. Nastavi kupnju — drugi proizvod preko Ane ima 20% popusta. Preporuka: {addon}, sada {price} MKD.",
        "add_addon": "Nastavi · -20%",
        "shipping": "Besplatna dostava iznad 3.000 MKD. Ispod toga 150 MKD, 1–3 dana.",
        "fallback": "Odaberi jednu od ponuđenih opcija.",
        "change_lang": "Jezik",
        "cart": "U košaricu",
        "other": "Drugi",
        "photo": "Vidi sliku",
        "installment": "Na rate",
        "back": "Natrag",
        "categories": "Kategorije",
        "pick_lang": "Jezik",
    },
    "sq": {
        "greeting": "Pershëndetje. Zgjidh gjuhën, pastaj thuaj çfarë kërkon.",
        "lang_set": "Në rregull, vazhdojmë në shqip. Çfarë kërkon?",
        "choose": "Zgjidh kategorinë ose produktet në zbritje.",
        "sale": "Në zbritje",
        "no_sale": "Tani nuk ka produkte në zbritje.",
        "pick_model": "Së pari zgjidh modelin, pastaj Shto në shportë.",
        "in_cart": "{title} është në shportë.",
        "in_cart_addon": "{title} është në shportë. Vazhdo blerjen — produkti i dytë nëpërmjet Anës ka 20% zbritje. Rekomandim: {addon}, tani {price} MKD.",
        "add_addon": "Vazhdo · -20%",
        "shipping": "Dërgesë falas mbi 3.000 MKD. Nën këtë 150 MKD, 1–3 ditë.",
        "fallback": "Zgjidh një nga opsionet.",
        "change_lang": "Gjuha",
        "cart": "Shto në shportë",
        "other": "Tjetër",
        "photo": "Shiko foton",
        "installment": "Me këste",
        "back": "Prapa",
        "categories": "Kategoritë",
        "pick_lang": "Gjuha",
    },
    "de": {
        "greeting": "Hallo. Sprache wählen, dann sagen, was Sie suchen.",
        "lang_set": "Alles klar, weiter auf Deutsch. Was suchen Sie?",
        "choose": "Kategorie oder Angebote wählen.",
        "sale": "Im Angebot",
        "no_sale": "Gerade keine Angebote.",
        "pick_model": "Zuerst ein Modell wählen, dann In den Korb.",
        "in_cart": "{title} liegt im Korb.",
        "in_cart_addon": "{title} liegt im Korb. Weiter einkaufen — das zweite Produkt über Ana hat 20% Rabatt. Empfehlung: {addon}, jetzt {price} MKD.",
        "add_addon": "Weiter · -20%",
        "shipping": "Kostenloser Versand ab 3.000 MKD. Darunter 150 MKD, 1–3 Tage.",
        "fallback": "Bitte eine der Optionen wählen.",
        "change_lang": "Sprache",
        "cart": "In den Korb",
        "other": "Anderes",
        "photo": "Bild zeigen",
        "installment": "Raten",
        "back": "Zurück",
        "categories": "Kategorien",
        "pick_lang": "Sprache",
    },
    "en": {
        "greeting": "Hello. Pick a language, then tell me what you need.",
        "lang_set": "Got it — we continue in English. What are you looking for?",
        "choose": "Pick a category or items on sale.",
        "sale": "On sale",
        "no_sale": "Nothing is on sale right now.",
        "pick_model": "Pick a model first, then Add to cart.",
        "in_cart": "{title} is in the cart.",
        "in_cart_addon": "{title} is in the cart. Keep shopping — the next product through Ana is 20% off. Pick: {addon}, now {price} MKD.",
        "add_addon": "Continue · -20%",
        "shipping": "Free shipping over 3,000 MKD. Below that 150 MKD, 1–3 days.",
        "fallback": "Choose one of the options.",
        "change_lang": "Language",
        "cart": "Add to cart",
        "other": "Another",
        "photo": "See photo",
        "installment": "Installments",
        "back": "Back",
        "categories": "Categories",
        "pick_lang": "Language",
    },
}

LANG_CHIPS = (
    ("MK · Македонски", "mk"),
    ("SR · Srpski", "sr"),
    ("HR · Hrvatski", "hr"),
    ("SQ · Shqip", "sq"),
    ("DE · Deutsch", "de"),
    ("EN · English", "en"),
)

GREETING_ALL = (
    "Zdravo · Ćao · Bok · Pershëndetje · Hallo · Hello. "
    "Izberi jezik / Choose a language."
)

CART_PHRASES = (
    "u korpu",
    "u kosnicka",
    "u kosaricu",
    "korpa",
    "kosnicka",
    "kosarica",
    "kupi",
    "dodaj u korpu",
    "dodaj u kosnicka",
    "shto ne shporte",
    "shto ne shport",
    "bli",
    "in den korb",
    "kaufen",
    "add to cart",
    "buy",
    "dodaj so -20%",
    "dodaj sa -20%",
    "dodaj s -20%",
    "shto me -20%",
    "mit -20% legen",
    "add at -20%",
)


TONE = {
    "clinic": {
        "mk": {
            "sale": "Uslugi",
            "no_sale": "Nema slobodni termini na ponuda.",
            "cart": "Zakazi",
            "pick_model": "Prvo izberi usluga, pa Zakazi.",
            "in_cart": "{title} e zakazan.",
            "in_cart_addon": "{title} e zakazan. Nastavi — vtorata usluga preku Ana ima 20% popust. Preporaka: {addon}, sega {price} MKD.",
        },
        "sr": {
            "sale": "Usluge",
            "no_sale": "Nema slobodnih termina na ponudi.",
            "cart": "Zakaži",
            "pick_model": "Prvo izaberi uslugu, pa Zakaži.",
            "in_cart": "{title} je zakazan.",
            "in_cart_addon": "{title} je zakazan. Nastavi — druga usluga preko Ane ima 20% popusta. Preporuka: {addon}, sada {price} MKD.",
        },
        "en": {
            "sale": "Services",
            "no_sale": "No offers right now.",
            "cart": "Book",
            "pick_model": "Pick a service, then Book.",
            "in_cart": "{title} is booked.",
            "in_cart_addon": "{title} is booked. Continue — the next service through Ana is 20% off. Pick: {addon}, now {price} MKD.",
        },
    },
    "hotel": {
        "mk": {
            "sale": "Ponuda",
            "no_sale": "Nema sobi na ponuda.",
            "cart": "Rezerviraj",
            "pick_model": "Prvo izberi soba, pa Rezerviraj.",
            "in_cart": "{title} e rezervirana.",
            "in_cart_addon": "{title} e rezervirana. Nastavi — vtoriot dodatok preku Ana ima 20% popust. Preporaka: {addon}, sega {price} MKD.",
        },
        "sr": {
            "sale": "Ponuda",
            "no_sale": "Nema soba na ponudi.",
            "cart": "Rezerviši",
            "pick_model": "Prvo izaberi sobu, pa Rezerviši.",
            "in_cart": "{title} je rezervisana.",
            "in_cart_addon": "{title} je rezervisana. Nastavi — drugi dodatak preko Ane ima 20% popusta. Preporuka: {addon}, sada {price} MKD.",
        },
        "en": {
            "sale": "Offers",
            "no_sale": "No rooms on offer.",
            "cart": "Reserve",
            "pick_model": "Pick a room, then Reserve.",
            "in_cart": "{title} is reserved.",
            "in_cart_addon": "{title} is reserved. Continue — the next extra through Ana is 20% off. Pick: {addon}, now {price} MKD.",
        },
    },
}


def say(lang: str, key: str, mode: str = "shop", **values: object) -> str:
    if mode != "shop":
        tone = (TONE.get(mode) or {}).get(lang) or (TONE.get(mode) or {}).get("mk") or {}
        override = tone.get(key)
        if override:
            return override.format(**values) if values else override
    pack = COPY.get(lang) or COPY["mk"]
    text = pack.get(key) or COPY["mk"][key]
    if values:
        return text.format(**values)
    return text


def explicit_lang(folded: str) -> Optional[str]:
    return _PICK.get(folded)


def detect_lang(folded: str) -> Optional[str]:
    picked = explicit_lang(folded)
    if picked:
        return picked
    for lang, hints in _HINTS:
        if any(hint in folded for hint in hints):
            return lang
    return None


def language_chips() -> Tuple[Tuple[str, str], ...]:
    return LANG_CHIPS
