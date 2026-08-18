import re
import unicodedata

SUPPORTED_GENRES = ("sertanejo", "rock")

def _slug(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value

def normalize_genre(value=None, prompt=None):
    if value:
        slug = _slug(str(value))
        aliases = {
            "sertanejo": "sertanejo",
            "sertanejo_universitario": "sertanejo",
            "universitario": "sertanejo",
            "country_br": "sertanejo",
            "rock": "rock",
            "rock_n_roll": "rock",
            "rock_and_roll": "rock",
            "rock_brasileiro": "rock",
            "hard_rock": "rock",
        }
        if slug not in aliases:
            raise ValueError(
                f"Genero nao suportado: {value}. Opcoes: {', '.join(SUPPORTED_GENRES)}"
            )
        return aliases[slug]

    text = _slug(prompt or "")
    if "rock" in text:
        return "rock"
    if "sertanejo" in text or "universitario" in text:
        return "sertanejo"
    return "sertanejo"

def genre_info():
    return {
        "sertanejo": {
            "default_bpm": 126,
            "instruments": ["drums", "bass", "guitar", "piano", "accordion"],
            "description": "Sertanejo/pop com violao de aco e acordeon.",
        },
        "rock": {
            "default_bpm": 132,
            "instruments": ["drums", "bass", "guitar_l", "guitar_r"],
            "description": "Rock com bateria forte, baixo pulsante e guitarra eletrica double-track.",
        },
    }
