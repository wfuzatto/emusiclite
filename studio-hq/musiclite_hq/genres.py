import re, unicodedata
SUPPORTED_GENRES=("sertanejo","rock","funk","hiphop","chillstep")
def _slug(value):
    value=unicodedata.normalize("NFKD",value or "").encode("ascii","ignore").decode("ascii").lower().strip()
    return re.sub(r"[^a-z0-9]+","_",value).strip("_")
def normalize_genre(value=None,prompt=None):
    aliases={
        "sertanejo":"sertanejo","sertanejo_universitario":"sertanejo","universitario":"sertanejo","country_br":"sertanejo",
        "rock":"rock","rock_n_roll":"rock","rock_and_roll":"rock","rock_brasileiro":"rock","hard_rock":"rock",
        "metal":"rock","metalcore":"rock",
        "funk":"funk","funk_carioca":"funk","baile_funk":"funk","funk_br":"funk","funk_brasileiro":"funk","mandelao":"funk","tamborzao":"funk",
        "hiphop":"hiphop","hip_hop":"hiphop","hip_hop_americano":"hiphop","american_hip_hop":"hiphop",
        "southern_hip_hop":"hiphop","southern_rap":"hiphop","luxury_rap":"hiphop","luxury_trap":"hiphop","trap":"hiphop","trap_americano":"hiphop",
        "chillstep":"chillstep","chill_step":"chillstep","melodic_dubstep":"chillstep","ambient_dubstep":"chillstep",
        "chill_dubstep":"chillstep","liquid_dubstep":"chillstep","melodic_chillstep":"chillstep",
    }
    if value:
        slug=_slug(str(value))
        if slug not in aliases: raise ValueError(f"Genero nao suportado: {value}. Opcoes: {', '.join(SUPPORTED_GENRES)}")
        return aliases[slug]
    text=_slug(prompt or "")
    if any(x in text for x in ("chillstep","chill_step","melodic_dubstep","ambient_dubstep","chill_dubstep","liquid_dubstep")): return "chillstep"
    if any(x in text for x in ("hip_hop","hiphop","southern_rap","southern_hip_hop","luxury_trap","luxury_rap","trap_americano")): return "hiphop"
    if any(x in text for x in ("funk","baile_funk","mandelao","tamborzao")): return "funk"
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
        "funk":{
            "default_bpm":150,
            "engine":"HQ5 Funk Carioca: kit VCSL CC0 + tamborzao/kick/hats sintetizados + sub 808 + swing e mix dedicados",
            "structure":"intro/verse/build/drop/break/final_drop/outro",
        },
        "hiphop":{
            "default_bpm":84,
            "engine":"HQ6 American Hip-Hop: half-time drums + 808 + upright piano + cinematic brass/strings VSCO 2 CE CC0",
            "structure":"intro/verse/hook/verse2/hook2/breakdown/final_hook/outro",
        },
        "chillstep":{
            "default_bpm":140,
            "engine":"HQ8 Chillstep: half-time electronic drums + deep sub + stereo pad + pluck + melodic lead, deterministic local synthesis",
            "structure":"intro/build/drop/breakdown/build2/final_drop/outro",
        },
    }
