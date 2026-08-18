import re, unicodedata
SUPPORTED_GENRES=("sertanejo","rock")
def _slug(value):
    value=unicodedata.normalize("NFKD",value or "").encode("ascii","ignore").decode("ascii").lower().strip()
    return re.sub(r"[^a-z0-9]+","_",value).strip("_")
def normalize_genre(value=None,prompt=None):
    aliases={
        "sertanejo":"sertanejo","sertanejo_universitario":"sertanejo","universitario":"sertanejo","country_br":"sertanejo",
        "rock":"rock","rock_n_roll":"rock","rock_and_roll":"rock","rock_brasileiro":"rock","hard_rock":"rock",
        "metal":"rock","metalcore":"rock",
    }
    if value:
        slug=_slug(str(value))
        if slug not in aliases: raise ValueError(f"Genero nao suportado: {value}. Opcoes: {', '.join(SUPPORTED_GENRES)}")
        return aliases[slug]
    text=_slug(prompt or "")
    if any(x in text for x in ("rock","metal","guitarra_distorcida","hard_rock")): return "rock"
    return "sertanejo"
def genre_info():
    return {
        "sertanejo":{
            "default_bpm":126,
            "engine":"HQ3: DRSKit multicanal quando instalado + baixo HQ + violao/acordeon/piano",
            "structure":"intro/verse/pre/chorus/bridge/final_chorus/outro",
        },
        "rock":{
            "default_bpm":132,
            "engine":"HQ3: CrocellKit multicanal + Metal GTX/Standard Guitar + double tracking + cabinet IR",
            "structure":"intro/verse/pre/chorus/bridge/final_chorus/outro",
        },
    }
