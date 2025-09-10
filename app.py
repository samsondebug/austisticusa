#!/usr/bin/env python3
# Streamlit web app for Replit: Hypothetical Ancient Battles Post Generator — PRO+ (Valedictorian)
# Additions over Pro:
# - Expanded KB: 20+ factions with tuned stats and presets
# - Weather + Scenario engines that modify visuals, context, and outcomes
# - Commander traits system affecting cohesion, initiative, and morale
# - Balance sliders for weighting arms (discipline, ranged, cavalry, logistics, armor, siege)
# - Naval mode with separate scoring and prompt motifs
# - Tournament tab: bracket or round-robin, Elo updates, leaderboard export
# - Style Packs for prompts (Cinematic, Documentary, Painterly)
# - Seed audit trail in every export
# - Strict prompt lint + cultural sensitivity
# - Caching everywhere safe
#
# Requirements (requirements.txt):
# streamlit==1.37.1
# pandas==2.2.2
# python-dateutil==2.9.0.post0

from __future__ import annotations
import io, json, math, os, random, re, textwrap, zipfile
from dataclasses import dataclass
from typing import Dict, List, Tuple
from datetime import datetime

import pandas as pd
import streamlit as st
import altair as alt
from typing import Optional

try:
    # Optional deps for video assembly
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips, AudioFileClip
    MOVIEPY_OK = True
except Exception:
    MOVIEPY_OK = False

st.set_page_config(page_title="Hypothetical Battles — Pro+", layout="wide", initial_sidebar_state="expanded")

# -------------------- Domain Model --------------------
@dataclass
class Faction:
    name: str
    era: str
    ranged: int        # 0-5
    cavalry: int       # 0-5
    infantry: int      # 0-5
    armor: int         # 0-5
    discipline: int    # 0-5
    siege: int         # 0-5
    logistics: int     # 0-5
    naval: int         # 0-5
    terrain_pref: List[str]
    palettes: List[str]
    motifs: List[str]

# MAXIMUM OVERDRIVE: 60+ factions with Asian dynasties prioritized
KB: Dict[str, Faction] = {
    # East Asian Dynasties (PRIORITIZED)
    "Han Dynasty": Faction("Han Dynasty","Classical China",4,3,4,3,4,3,4,3,["plains","hills"],["imperial red","jade green"],["crossbows","chariots","drums"]),
    "Tang Dynasty": Faction("Tang Dynasty","Golden Age China",4,3,4,3,4,3,4,3,["plains","urban"],["silk banners","dragon gold"],["heavy cavalry","crossbows","artistry"]),
    "Song Dynasty": Faction("Song Dynasty","Medieval China",4,2,3,3,4,4,4,3,["river valleys","urban"],["porcelain blue","ink black"],["gunpowder arrows","siege engines","scholar warriors"]),
    "Yuan Dynasty": Faction("Yuan Dynasty","Mongol China",5,5,3,3,4,4,5,3,["steppe","plains"],["jade and sable","storm skies"],["horse archers","mass cavalry","keshik guards"]),
    "Ming Dynasty": Faction("Ming Dynasty","Early Modern China",4,3,4,4,4,5,5,4,["plains","walls"],["vermilion","forbidden purple"],["arquebuses","fortress cannons","dragon fleets"]),
    "Qing Dynasty": Faction("Qing Dynasty","Late Imperial China",4,4,4,4,4,4,4,4,["plains","urban"],["yellow banners","imperial silver"],["banner armies","matchlocks","cavalry"]),
    "Samurai": Faction("Samurai","Feudal Japan",3,2,4,3,4,2,3,3,["hills","forests"],["lacquered black","blood red"],["katana duel","yumi volleys","bushido"]),
    "Ashigaru": Faction("Ashigaru","Feudal Japan",3,2,3,2,3,2,3,2,["plains","hills"],["peasant brown","spear lines"],["yari spear wall","arquebus","ashigaru levy"]),
    "Ninja": Faction("Ninja","Feudal Japan",4,1,2,1,4,1,2,1,["forests","urban"],["shadow black","midnight blue"],["assassins","smoke bombs","stealth raids"]),
    "Koreans": Faction("Koreans","Three Kingdoms/Joseon",3,3,3,3,3,3,3,3,["hills","coast"],["turtle ships","crimson armor"],["archers","swords","navy"]),
    "Khmer": Faction("Khmer","Angkor",3,2,3,3,3,3,3,3,["river valleys","urban"],["stone grey","jungle green"],["war elephants","temple guards","fortresses"]),
    "Thai": Faction("Thai","Ayutthaya",3,3,3,2,3,2,3,2,["plains","river valleys"],["golden spires","saffron"],["elephants","archers","palace guards"]),
    "Vietnamese": Faction("Vietnamese","Medieval",3,3,3,2,3,2,3,2,["forests","river valleys"],["jungle mist","bronze drums"],["guerrilla warfare","spears","boats"]),
    "Mongols": Faction("Mongols","Steppe Empire",5,5,2,2,4,3,5,1,["steppe","plains"],["cold steppe blues","dust storms"],["horse archers","encirclement","keshik charge"]),
    "Huns": Faction("Huns","Late Antiquity",4,5,1,1,3,1,3,1,["steppe","plains"],["storm grey","leather"],["composite bows","raids","scorched earth"]),
    "Tatars": Faction("Tatars","Steppe",4,4,2,2,3,2,3,1,["plains","steppe"],["sable brown","steppe haze"],["raids","sabres","horse bows"]),
    "Tibetans": Faction("Tibetans","Himalayan",3,2,3,2,3,2,3,2,["hills","snow"],["mountain mist","prayer flags"],["yak cavalry","slings","monastery warriors"]),
    "Burmese": Faction("Burmese","Pagan",3,2,3,2,3,2,3,2,["river valleys","forests"],["golden pagodas","teak wood"],["war elephants","spears","temple guards"]),
    "Japanese Clans": Faction("Japanese Clans","Sengoku",3,2,4,3,4,2,3,3,["hills","forests"],["clan banners","steel grey"],["katana","yari","teppo"]),
    "Chinese Warlords": Faction("Chinese Warlords","Warring States",4,3,4,3,3,3,3,3,["plains","hills"],["bronze","warring colors"],["crossbows","chariots","infantry"]),
    # Classical / Europe
    "Romans": Faction("Romans","Classical",2,2,5,4,5,5,5,3,["plains","hills"],["iron red","sandstone"],["testudo","pilum volley","eagle standards"]),
    "Greeks": Faction("Greeks","Classical",2,2,4,3,4,3,4,4,["hills","coast"],["bronze","Aegean blue"],["phalanx","triremes","hoplons"]),
    "Spartans": Faction("Spartans","Classical Greek",2,1,5,4,5,2,3,1,["hills","plains"],["bronze red cloaks","laconic steel"],["phalanx wall","shield clash","spear thrust"]),
    "Vikings": Faction("Vikings","Norse",2,1,4,3,3,2,2,5,["coast","snow"],["cold blue","storm seas"],["longships","axes","shield wall"]),
    "Carthaginians": Faction("Carthaginians","Classical",2,2,3,3,3,3,4,5,["coast","plains"],["Tyrian purple","sunlit harbors"],["elephants","quinqueremes","mercenary lines"]),
    "Celts": Faction("Celts","Iron Age",2,2,3,2,2,1,2,2,["forests","hills"],["verdant greens","storm-grey"],["war cries","chariots","wild charge"]),
    "Byzantines": Faction("Byzantines","Medieval",3,3,4,3,4,4,4,4,["urban","hills"],["imperial gold","purple cloaks"],["cataphracts","Greek fire","defensive lines"]),
    "Knights": Faction("Knights","High Medieval",2,4,4,4,3,2,3,2,["plains","hills"],["steel and heraldry","castle stone"],["lance charge","plate armor","standards"]),
    "Gauls": Faction("Gauls","Iron Age",2,2,3,2,2,1,2,2,["forests","plains"],["wode-blue","forest haze"],["horns","chariots","wild charge"]),
    "Macedonians": Faction("Macedonians","Classical",2,2,5,3,4,3,4,3,["plains","hills"],["royal purple","sarissa shine"],["phalanx","cavalry wedge","siege towers"]),
    # Middle East
    "Persians": Faction("Persians","Achaemenid",3,3,3,2,3,3,4,3,["plains","desert"],["lapis","amber"],["Immortals","war elephants","chariots"]),
    "Ottomans": Faction("Ottomans","Gunpowder Empire",4,3,4,3,4,5,4,4,["plains","urban"],["emerald","smoke"],["janissaries","bombards","crescent"]),
    "Mughals": Faction("Mughals","Early Modern India",4,3,4,3,4,4,4,3,["plains","river valleys"],["silk brocade","marble domes"],["war elephants","matchlocks","archers"]),
    "Arabs": Faction("Arabs","Early Islamic",3,4,3,2,3,2,3,3,["desert","plains"],["desert gold","crescent silver"],["cavalry charge","archery","faith"]),
    "Turks": Faction("Turks","Seljuk",3,3,3,3,3,3,3,2,["plains","hills"],["silk banners","desert steel"],["cavalry charge","archery volleys","siege engines"]),
    # Africa
    "Egyptians": Faction("Egyptians","Bronze to Late",2,2,3,2,3,3,3,3,["desert","river valleys"],["sunstone","Nile reeds"],["chariots","archers","sacred standards"]),
    "Mali": Faction("Mali","Sahelian Medieval",2,2,3,2,3,2,4,2,["desert","river valleys"],["gold dust","Sahara dusk"],["cavalry","griots","caravans"]),
    "Ethiopians": Faction("Ethiopians","Axumite/Solomonic",3,2,3,2,3,2,3,2,["hills","river valleys"],["highland blues","basalt"],["spears","rock-hewn lines","shields"]),
    "Zulu": Faction("Zulu","19th c.",2,2,4,2,4,1,2,1,["plains","hills"],["savanna gold","storm build"],["impi horns","assegai","shield rush"]),
    "Numidians": Faction("Numidians","North Africa",2,3,2,2,3,2,3,3,["plains","desert"],["desert tan","oasis green"],["light cavalry","javelins","skirmishers"]),
    "Berbers": Faction("Berbers","North Africa",2,3,2,2,3,2,3,3,["desert","hills"],["desert ochre","Atlas blue"],["cavalry raids","mountain ambush","desert warfare"]),
    # Americas
    "Aztecs": Faction("Aztecs","Mesoamerican",3,1,3,2,3,1,2,1,["plains","forests"],["earthy ochres","jade"],["jaguar warriors","macuahuitl","eagle knights"]),
    "Mayans": Faction("Mayans","Mesoamerican",3,1,3,2,3,1,2,1,["forests","hills"],["verdigris","jungle mist"],["atlatl","obsidian blades","pyramids"]),
    "Incas": Faction("Incas","Andean",3,1,3,2,4,2,4,2,["hills","river valleys"],["andes slate","sun gold"],["slings","terraces","runners"]),
    "Native North Americans": Faction("Native North Americans","Varied",3,2,2,1,3,1,2,1,["plains","forests"],["buffalo plains","cedar smoke"],["bows","lances","ambushes"]),
    "Cherokee": Faction("Cherokee","Woodlands",3,2,2,1,3,1,2,1,["forests","hills"],["forest green","river stone"],["bows","tomahawks","ambush"]),
    "Sioux": Faction("Sioux","Plains",3,4,3,2,3,1,2,1,["plains","hills"],["buffalo hide","prairie fire"],["horse archers","raids","spears"]),
    "Iroquois": Faction("Iroquois","Woodlands",3,2,3,2,3,1,2,1,["forests","hills"],["longhouse wood","forest mist"],["bows","axes","ambush"]),
    "Toltecs": Faction("Toltecs","Mesoamerican",3,1,3,2,3,1,2,1,["plains","forests"],["stone grey","jade green"],["warriors","pyramids","obsidian blades"]),
    "Olmecs": Faction("Olmecs","Mesoamerican",2,1,2,2,2,1,2,1,["forests","river valleys"],["stone heads","jungle green"],["clubs","ambush","rituals"]),
    # Indian Subcontinent
    "Indians": Faction("Indians","Mauryan-Gupta",3,2,3,2,3,3,3,3,["plains","river valleys"],["saffron and teak","monsoon haze"],["elephants","chariots","archers"]),
    "Rajputs": Faction("Rajputs","Medieval India",3,4,4,3,4,2,3,2,["plains","hills"],["rajput saffron","desert pride"],["cavalry charge","honor duels","fortress warfare"]),
    "Delhi Sultanate": Faction("Delhi Sultanate","Medieval India",4,3,4,3,4,4,4,3,["plains","urban"],["sultanate green","minaret gold"],["cavalry","archers","siege engines"]),
    "Marathas": Faction("Marathas","Early Modern India",3,4,3,2,4,2,3,2,["hills","plains"],["saffron banners","guerrilla brown"],["guerrilla cavalry","hill forts","mobility"]),
    "Sikhs": Faction("Sikhs","18th-19th c.",3,3,4,3,4,2,3,2,["plains","hills"],["khalsa blue","steel kirpan"],["cavalry","muskets","warrior faith"]),
}

TERRAIN_RULES = {
    "plains": ["sun-bleached flats", "rolling fields"],
    "hills": ["misty foothills", "undulating ridgelines"],
    "forests": ["dense woodland", "dark conifer stands"],
    "steppe": ["endless grass seas", "cold steppe horizon"],
    "desert": ["saffron dunes", "heat shimmer and sand haze"],
    "coast": ["rocky shoreline", "spray and slate waves"],
    "urban": ["broken walls and gatehouses", "narrow streets"],
    "walls": ["battlements and siege towers"],
    "river valleys": ["broad river meanders", "fog over terraces"],
    "open sea": ["whitecaps and spray", "overcast swells"],
}

WEATHER = {
    "clear": {"vis": ", crisp air", "score": 0.0},
    "fog": {"vis": ", ground fog and haze", "score": -0.1},
    "rain": {"vis": ", rain sheeting and churned mud", "score": -0.05},
    "snow": {"vis": ", blowing snow and breath vapor", "score": -0.05},
    "windy": {"vis": ", whipping banners and dust plumes", "score": -0.02},
}

SCENARIOS = {
    "open field": {"desc": "battle lines form and advance", "mod": {"cavalry": 0.1, "infantry": 0.05}},
    "ambush": {"desc": "surprise strike on a flank", "mod": {"discipline": -0.05, "cavalry": 0.05, "ranged": 0.05}},
    "river crossing": {"desc": "forcing a ford under fire", "mod": {"discipline": 0.1, "ranged": 0.05, "cavalry": -0.05}},
    "hill defense": {"desc": "defender holds ridgeline", "mod": {"discipline": 0.05, "infantry": 0.05, "ranged": 0.05}},
    "siege": {"desc": "walls, engines, attrition", "mod": {"siege": 0.15, "logistics": 0.1}},
    "naval": {"desc": "oared rams, boarding, missiles", "mod": {"naval": 0.3, "ranged": 0.05}},
}

MIDJOURNEY_BASE = "--v 6 --style raw --s {stylize} --chaos {chaos}"
# MAXIMUM OVERDRIVE TikTok-Shock Prompts
CAMERA_OPTS_169 = [
    "ultra-wide anime energy shot, meteors raining from neon storm skies, armies colliding in fire rain, hyper detail chaos, thunder explosions",
    "drone zoom over colossal banners whipping in hurricane winds, neon lightning splitting dimensions, sparks and debris tornados, cinematic mayhem",
    "ground smash perspective, dust explosions with fire rain, motion blur soldiers mid-leap through meteor showers, impossible scale energy",
]
CAMERA_OPTS_916 = [
    "vertical anime close-up, glowing katana eyes, neon sparks erupting, furious clash mid-frame with dragon lightning",
    "low-angle towering samurai vs cavalry, colossal banners exploding overhead, neon storm skies tearing reality",
    "tight TikTok crop, chaotic firelight with anime energy, steel sparks mid-swing, viral shot composition with meteor rain",
]

STYLE_PACKS = {
    "Cinematic": {"add": ["cinematic lighting", "storm clouds", "intense contrast"], "s": [250,300,350]},
    "Documentary": {"add": ["natural light", "dust haze", "realistic grit"], "s": [200,220,240]},
    "Painterly": {"add": ["oil-paint look", "bold color strokes", "dramatic highlights"], "s": [300,350,400]},
    "TikTok-Hype": {"add": ["explosive energy", "slow-motion sparks", "hyper-saturated colors", "viral thumbnail quality", "lightning strikes", "fire explosions"], "s": [350,400,450]},
    "FULL-CRACKED-ASIAN": {"add": ["anime battle energy", "glowing katanas", "dragon lightning", "neon storm skies", "impossible scale", "maximum chaos", "meteors raining", "fire rain cascades", "colossal banners"], "s": [400,450,500]},
}

PRESETS = {
    "Romans": {"palette":"iron and crimson","camera":"low-angle wide"},
    "Mongols": {"palette":"cold steppe blues","camera":"telephoto compression"},
    "Samurai": {"palette":"lacquered black and vermilion","camera":"portrait close-up"},
    "Ottomans": {"palette":"emerald and gold","camera":"elevated three-quarters view"},
}

BANNED = {"savage","barbaric","primitive"}

# Commander traits
COMMANDERS = {
    "aggressive": {"cavalry": 0.05, "initiative": 0.05},
    "defensive": {"discipline": 0.05, "armor": 0.03},
    "cunning": {"ranged": 0.05, "initiative": 0.03},
    "logistician": {"logistics": 0.08},
}

# -------------------- User Config (Optional) --------------------
# Allow users to add custom factions, style packs, and presets that persist across sessions.
DATA_DIR = "data"
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    pass

USER_FACTIONS_PATH = os.path.join(DATA_DIR, "user_factions.json")
USER_STYLE_PACKS_PATH = os.path.join(DATA_DIR, "user_style_packs.json")
USER_PRESETS_PATH = os.path.join(DATA_DIR, "user_presets.json")

def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def _factions_from_json(obj) -> Dict[str, Faction]:
    out: Dict[str, Faction] = {}
    # Support either list-of-dicts or mapping name->dict
    items = obj.items() if isinstance(obj, dict) else [
        (d.get("name"), d) for d in (obj or []) if isinstance(d, dict)
    ]
    for name, d in items:
        if not name or not isinstance(d, dict):
            continue
        try:
            out[name] = Faction(
                name=name,
                era=d.get("era", "Custom"),
                ranged=int(d.get("ranged", 0)),
                cavalry=int(d.get("cavalry", 0)),
                infantry=int(d.get("infantry", 0)),
                armor=int(d.get("armor", 0)),
                discipline=int(d.get("discipline", 0)),
                siege=int(d.get("siege", 0)),
                logistics=int(d.get("logistics", 0)),
                naval=int(d.get("naval", 0)),
                terrain_pref=list(d.get("terrain_pref", ["plains"])),
                palettes=list(d.get("palettes", ["neutral tones"])),
                motifs=list(d.get("motifs", ["banners"]))
            )
        except Exception:
            # Skip malformed entries
            continue
    return out

# Load user overrides and merge into base dicts
_user_factions_raw = _load_json(USER_FACTIONS_PATH, default=[])
USER_KB = _factions_from_json(_user_factions_raw)
USER_STYLE_PACKS = _load_json(USER_STYLE_PACKS_PATH, default={})
USER_PRESETS = _load_json(USER_PRESETS_PATH, default={})

# Merge: user entries override base if names collide
if USER_KB:
    KB.update(USER_KB)
if isinstance(USER_STYLE_PACKS, dict) and USER_STYLE_PACKS:
    STYLE_PACKS.update({k: v for k, v in USER_STYLE_PACKS.items() if isinstance(v, dict) and "add" in v and "s" in v})
if isinstance(USER_PRESETS, dict) and USER_PRESETS:
    PRESETS.update({k: v for k, v in USER_PRESETS.items() if isinstance(v, dict)})

# -------------------- Utilities --------------------
@st.cache_data
def demo_plan_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"Day":1, "Matchup / Theme":"Romans vs. Samurai"},
        {"Day":2, "Matchup / Theme":"Romans vs. Mongols"},
        {"Day":3, "Matchup / Theme":"Romans vs. Persians"},
    ])

def sanitize(text: str) -> str:
    t = text
    for w in BANNED: t = t.replace(w, "")
    return t

# -------------------- Engines --------------------

def pick_terrain_key(a: Faction, b: Faction, naval_mode: bool) -> str:
    if naval_mode: return "open sea"
    pool = a.terrain_pref + b.terrain_pref + ["plains"]
    return random.choice(pool)

def pick_terrain_desc(key: str, weather_key: str) -> str:
    base = random.choice(TERRAIN_RULES.get(key, [key]))
    vis = WEATHER[weather_key]["vis"]
    return base + vis


def _resolve_style(style_pack: str, rotation_idx: int | None = None) -> Dict:
    if style_pack in STYLE_PACKS:
        return STYLE_PACKS[style_pack]
    if style_pack.lower() in {"random","randomized"}:
        return STYLE_PACKS[random.choice(list(STYLE_PACKS.keys()))]
    if style_pack.lower() in {"rotate","rotation"} and rotation_idx is not None:
        names = list(STYLE_PACKS.keys())
        return STYLE_PACKS[names[rotation_idx % len(names)]]
    return STYLE_PACKS["Cinematic"]

def _resolve_style_name(style_pack: str, rotation_idx: int | None = None) -> str:
    if style_pack in STYLE_PACKS:
        return style_pack
    if style_pack.lower() in {"random","randomized"}:
        return random.choice(list(STYLE_PACKS.keys()))
    if style_pack.lower() in {"rotate","rotation"} and rotation_idx is not None:
        names = list(STYLE_PACKS.keys())
        return names[rotation_idx % len(names)]
    return "Cinematic"

def build_prompts(a: Faction, b: Faction, terrain_desc: str, style_pack: str, rotation_idx: int | None = None) -> Tuple[str,str]:
    style = _resolve_style(style_pack, rotation_idx)
    adds = ", ".join(style["add"])
    stylize = random.choice(style["s"])
    palette = random.choice(a.palettes + b.palettes)
    motifs = ", ".join(random.sample(a.motifs, 1) + random.sample(b.motifs, 1))
    c169 = random.choice(CAMERA_OPTS_169)
    c916 = random.choice(CAMERA_OPTS_916)
    chaos = random.choice([0, 7, 12])
    p169 = f"{a.name} vs {b.name}, {terrain_desc}, {motifs}, {palette}, {adds}, {c169} --ar 16:9 {MIDJOURNEY_BASE.format(stylize=stylize, chaos=chaos)}"
    p916 = f"{a.name} vs {b.name}, {terrain_desc}, {motifs}, {palette}, {adds}, {c916} --ar 9:16 {MIDJOURNEY_BASE.format(stylize=stylize, chaos=chaos)}"
    return p169, p916


def apply_preset(prompt: str, name: str) -> str:
    pr = PRESETS.get(name)
    return prompt if not pr else prompt.replace("--style raw", f"--style raw, {pr['palette']}, {pr['camera']}")


def lint_prompt(prompt: str, a: Faction, b: Faction) -> str:
    gunpowder_ok = any(x in (a.era + b.era) for x in ["Gunpowder","Song","Yuan","Ottoman"]) or (a.name=="Chinese" or b.name=="Chinese")
    p = prompt
    if not gunpowder_ok:
        p = p.replace("bombards","catapults").replace("rifles","bows")
    return sanitize(p)


def context_text(a: Faction, b: Faction, terrain_desc: str, scenario_key: str) -> str:
    scen = SCENARIOS[scenario_key]["desc"]
    txt = (
        f"On {terrain_desc}, {scen}. {a.name} deploy with {random.choice(a.motifs)} and drilled formations; "
        f"{b.name} answer with {random.choice(b.motifs)} from the {b.era}. Scouts test flanks, missiles trade, then main bodies commit."
    )
    return textwrap.fill(sanitize(txt), width=110)


def outcome(a: Faction, b: Faction, terrain_key: str, scenario_key: str, weather_key: str, weights: Dict[str,float], cmd_a: str, cmd_b: str, naval_mode: bool) -> Tuple[str,str,float,float]:
    def terr_mod(f: Faction) -> float:
        return 1.0 if terrain_key in f.terrain_pref else 0.0
    def cmd_mod(cmd: str, stat: str) -> float:
        return COMMANDERS.get(cmd, {}).get(stat, 0.0)

    def score(f: Faction, cmd: str) -> float:
        w = weights
        base = (
            w['discipline']*(f.discipline + 5*cmd_mod(cmd,'discipline')) +
            w['infantry']*f.infantry + w['armor']*(f.armor + 5*cmd_mod(cmd,'armor')) +
            w['logistics']*(f.logistics + 5*cmd_mod(cmd,'logistics')) +
            w['ranged']*(f.ranged + 5*cmd_mod(cmd,'ranged')) +
            w['cavalry']*(f.cavalry + 5*cmd_mod(cmd,'cavalry')) +
            w['siege']*f.siege + w['naval']*f.naval*(1.0 if naval_mode else 0.2)
        )
        base *= 1.0 + 0.05*terr_mod(f)
        base *= 1.0 + WEATHER[weather_key]['score']
        scen_mods = SCENARIOS[scenario_key]['mod']
        for k,v in scen_mods.items():
            base *= 1.0 + v
        return base

    a_score = score(a, cmd_a) + random.uniform(-0.8,0.8)
    b_score = score(b, cmd_b) + random.uniform(-0.8,0.8)

    if a_score >= b_score:
        winner, loser, ws, ls = a, b, a_score, b_score
    else:
        winner, loser, ws, ls = b, a, b_score, a_score

    reasons = []
    if winner.ranged > loser.ranged: reasons.append("missile superiority set tempo")
    if winner.cavalry > loser.cavalry: reasons.append("mobility took the flanks")
    if winner.discipline > loser.discipline: reasons.append("cohesion held under pressure")
    if winner.armor > loser.armor: reasons.append("protection blunted shock")
    if winner.logistics > loser.logistics: reasons.append("supply depth sustained lines")
    if winner.siege > loser.siege and SCENARIOS[scenario_key]==SCENARIOS['siege']: reasons.append("engineers dictated pace")
    if terr_mod(winner) and not terr_mod(loser): reasons.append("terrain familiarity mattered")
    if naval_mode and winner.naval > loser.naval: reasons.append("seamanship and ramming skill dominated")
    reasons.append(f"commander edge: {cmd_a if winner==a else cmd_b}")

    margin = ws / max(ls, 0.001)
    why = f"{winner.name} win: " + ", ".join(reasons) + f". Margin ~{margin:.2f}x. Visual: emphasize {random.choice(winner.motifs)} against {random.choice(loser.motifs)}."
    return winner.name, textwrap.fill(sanitize(why), width=110), ws, ls


def heuristic_score(prompt: str) -> float:
    score = 0.0
    for token in ["cinematic","motion blur","dust","smoke","banners","low-angle","close-up","dynamic","telephoto","sparks"]:
        if token in prompt: score += 1.0
    if "--chaos 0" in prompt: score += 0.3
    if "--chaos 12" in prompt: score += 0.2
    return score

# -------------------- Advanced Analysis --------------------

def choose_attacker(a: Faction, b: Faction, cmd_a: str, cmd_b: str) -> str:
    """Heuristic: higher cavalry+ranged+logistics+commander initiative tends to attack."""
    init_bonus = {"aggressive": 0.5, "cunning": 0.25, "defensive": -0.25, "logistician": 0.1}
    sa = a.cavalry + a.ranged + a.logistics + init_bonus.get(cmd_a, 0)
    sb = b.cavalry + b.ranged + b.logistics + init_bonus.get(cmd_b, 0)
    if abs(sa - sb) < 0.5:
        return random.choice([a.name, b.name])
    return a.name if sa > sb else b.name

def estimate_force_sizes(a: Faction, b: Faction, scenario_key: str, naval_mode: bool) -> Tuple[int,int]:
    """Rough force size estimate per side; scaled by logistics, era, and scenario."""
    if naval_mode or scenario_key == "naval":
        base_min, base_max = 1500, 8000
    elif scenario_key == "siege":
        base_min, base_max = 8000, 50000
    else:
        base_min, base_max = 6000, 45000
    def side_size(f: Faction) -> int:
        logi = max(0, min(5, f.logistics))
        scale = 0.6 + 0.1*logi + random.uniform(-0.05, 0.05)
        return int(max(base_min, min(base_max, scale * random.randint(base_min, base_max))))
    return side_size(a), side_size(b)

def scenario_intensity(scenario_key: str) -> float:
    return {
        "open field": 0.22,
        "ambush": 0.30,
        "river crossing": 0.28,
        "hill defense": 0.24,
        "siege": 0.35,
        "naval": 0.26,
    }.get(scenario_key, 0.22)

def casualty_breakdown(size: int, rate: float) -> Tuple[int,int,int]:
    """Split casualties into killed/wounded/captured with rough proportions."""
    killed = int(rate * size * random.uniform(0.30, 0.45))
    wounded = int(rate * size * random.uniform(0.45, 0.60))
    captured = max(0, int(rate * size) - killed - wounded)
    return killed, wounded, captured

def estimate_casualties(
    a: Faction, b: Faction, winner: str, margin: float, scenario_key: str, weather_key: str,
    terrain_key: str, naval_mode: bool, size_a: int, size_b: int, attacker: str
) -> Dict[str, object]:
    """Return casualty numbers and rates for A and B, plus duration."""
    intensity = scenario_intensity(scenario_key)
    # Margin effect: decisive margins punish the loser
    loser_rate = min(0.65, max(0.12, intensity * (0.8 + 0.6*(margin-1.0))))
    winner_rate = min(0.28, max(0.03, intensity * (0.35 - 0.2*(margin-1.0))))
    # Scenario asymmetry tweaks
    if scenario_key == "ambush":
        loser_rate *= 1.15
        winner_rate *= 0.9
    elif scenario_key == "river crossing":
        if attacker == winner:
            winner_rate *= 1.05
        else:
            winner_rate *= 1.2
            loser_rate *= 0.95
    elif scenario_key == "siege":
        winner_rate *= 1.1
        loser_rate *= 1.2
    # Weather dampens killing slightly when poor
    w = WEATHER.get(weather_key, {"score": 0.0}).get("score", 0.0)
    if w < 0:
        factor = max(0.85, 1.0 + w)
        winner_rate *= factor
        loser_rate *= factor
    # Clamp sanity
    winner_rate = float(max(0.01, min(0.30, winner_rate)))
    loser_rate = float(max(0.08, min(0.65, loser_rate)))

    # Map rates to sides
    if winner == a.name:
        rate_a, rate_b = winner_rate, loser_rate
    else:
        rate_a, rate_b = loser_rate, winner_rate

    killed_a, wounded_a, captured_a = casualty_breakdown(size_a, rate_a)
    killed_b, wounded_b, captured_b = casualty_breakdown(size_b, rate_b)

    # Duration estimate
    if scenario_key == "ambush":
        duration = f"{random.randint(2,5)} hours"
    elif scenario_key == "naval":
        duration = f"{random.randint(3,8)} hours"
    elif scenario_key == "siege":
        d = random.randint(3, 21)
        duration = f"{d} days"
    else:
        duration = f"{random.randint(6,12)} hours"

    return {
        "rate_a": round(100*rate_a, 1),
        "rate_b": round(100*rate_b, 1),
        "cas_a": {"killed": killed_a, "wounded": wounded_a, "captured": captured_a, "total": killed_a+wounded_a+captured_a},
        "cas_b": {"killed": killed_b, "wounded": wounded_b, "captured": captured_b, "total": killed_b+wounded_b+captured_b},
        "duration": duration,
    }

def build_deep_context(
    a: Faction, b: Faction, winner: str, attacker: str, terrain_desc: str, scenario_key: str,
    weather_key: str, casualties: Dict[str,object]
) -> str:
    """Narrative with phases and key moments."""
    phases = []
    phases.append(f"Opening: light troops screen and probe under {WEATHER[weather_key]['vis'].strip(', ')} on {terrain_desc}.")
    if scenario_key in ("ambush","river crossing"):
        phases.append("Disruption: the defender reels as the attacker forces the tempo and shapes the field.")
    else:
        phases.append("Main engagement: lines close; missiles and engines set a brutal pace before infantry clinch.")
    if winner == a.name:
        swing = f"{a.name} gain momentum—cohesion holds while pressure builds on {b.name}'s flank."
    else:
        swing = f"{b.name} turn the tide—discipline and timing crack {a.name}'s line."
    phases.append(f"Turning point: {swing}")
    phases.append("Collapse: reserves commit, one wing buckles and a controlled pursuit seals the result.")

    cas_a = casualties["cas_a"]; cas_b = casualties["cas_b"]
    summ = (
        f"Casualties — {a.name}: {cas_a['total']:,} (K:{cas_a['killed']:,} W:{cas_a['wounded']:,} C:{cas_a['captured']:,}) · "
        f"{b.name}: {cas_b['total']:,} (K:{cas_b['killed']:,} W:{cas_b['wounded']:,} C:{cas_b['captured']:,})."
    )
    dur = casualties["duration"]
    txt = (
        f"Attacker: {attacker}. Conditions: {scenario_key}, {WEATHER[weather_key]['vis'].strip(', ')}. \n"
        f"Phases: {' | '.join(phases)} \n"
        f"Outcome: {winner} carry the field after {dur}. {summ}"
    )
    return textwrap.fill(sanitize(txt), width=110)

# -------------------- Lore/Commentary Generator --------------------

HOOK_TEMPLATES = [
    "What if {A} met {B} at full strength on {terrain}?",
    "{eraA} vs {eraB}: whose banners hold when steel meets storm?",
    "As fierce as {compare}, but {twist}.",
    "Prophecy whispers and drums thunder—{A} against {B} under blazing skies.",
]
TACTICAL_TEMPLATES = [
    "{attacker} seizes initiative; a sudden push at the {flank} widens into a breach.",
    "Missiles rake the line; {winner} press while {loser} staggers over {terrain}.",
    "A {moment} turns the field; discipline and timing decide it in {duration}.",
]
FAN_TEMPLATES = [
    "Does discipline beat zeal? Your call.",
    "Tap left for cavalry, right for archers.",
    "Who carries the banners at dusk? Vote below.",
    "Is logistics the real hero? Decide the victor.",
]
COMPARE_POOL = ["Yarmouk","Cannae","Hattin","Ain Jalut","Thermopylae","Hastings"]
TWISTS = [
    "brother versus brother","under twin comets","in a dust‑storm crossing","with drums echoing over dunes",
    "as night falls early","with reserves late to the field"
]
MOMENTS = ["flank charge","shield‑wall collapse","arrow storm lull","cavalry counter‑thrust","river ford panic"]
FLANKS = ["left","right","center","river bank","ridge"]

QUOTES_PD = [
    {"text": "In the midst of chaos, there is also opportunity.", "author": "Sun Tzu"},
    {"text": "Strategy without tactics is the slowest route to victory. Tactics without strategy is the noise before defeat.", "author": "Sun Tzu"},
    {"text": "The past resembles the future more than one drop of water resembles another.", "author": "Ibn Khaldun"},
    {"text": "Great deeds are usually wrought at great risks.", "author": "Herodotus"},
]

def generate_lore_snippets(
    a: Faction, b: Faction, winner: str, attacker: str, scenario_key: str, weather_key: str,
    terrain_desc: str, analysis_txt: str, casualties: Dict[str,object], day_idx: int,
    pov: str = "mixed"
) -> Dict[str,str]:
    random.seed(day_idx * 100003)
    eraA, eraB = a.era, b.era
    terrain_short = terrain_desc.split(",")[0]
    hook = random.choice(HOOK_TEMPLATES).format(
        A=a.name, B=b.name, eraA=eraA, eraB=eraB, terrain=terrain_short,
        compare=random.choice(COMPARE_POOL), twist=random.choice(TWISTS)
    )
    loser = b.name if winner == a.name else a.name
    tac = random.choice(TACTICAL_TEMPLATES).format(
        attacker=attacker, winner=winner, loser=loser, terrain=terrain_short,
        duration=casualties.get("duration","hours"), moment=random.choice(MOMENTS), flank=random.choice(FLANKS)
    )
    fan = random.choice(FAN_TEMPLATES)

    # Tone rotation: mythic, tactical, cinematic
    tones = ["mythic","tactical","cinematic"]
    tone = tones[day_idx % len(tones)]
    if tone == "mythic":
        hook = hook + " Omens blaze overhead; each side claims mandate."
    elif tone == "cinematic":
        tac = tac + " Dust turns to sparks in the gale; banners whip like lightning."

    # Occasional POV or alt‑history tease
    if day_idx % 5 == 0:
        hook = "I was there—" + hook[0].lower() + hook[1:]
    if day_idx % 7 == 0:
        fan = fan + " Had that charge landed, would the map be different?"

    # POV transforms
    pov_mode = (pov or "").lower()
    if pov_mode == "mixed":
        pov_mode = random.choice(["soldier","commander","bard","none"]) if day_idx % 2 == 0 else "none"
    if pov_mode in {"soldier","commander","bard"}:
        if pov_mode == "soldier":
            hook = "I " + hook[0].lower() + hook[1:]
            tac = "From the ranks, " + tac[0].lower() + tac[1:]
        elif pov_mode == "commander":
            hook = "From my saddle I considered this: " + hook[0].lower() + hook[1:]
            tac = "I commit reserves as " + tac[0].lower() + tac[1:]
        elif pov_mode == "bard":
            hook = "Hear now: " + hook
            tac = "Let the record sing—" + tac[0].lower() + tac[1:]

    vo = f"{hook} {tac} {fan}"
    quote = None
    if day_idx % 3 == 1:
        q = random.choice(QUOTES_PD)
        quote = f"\"{q['text']}\" — {q['author']}"
    return {
        "Lore Hook": sanitize(hook),
        "Tactical Beat": sanitize(tac),
        "Fan Prompt": sanitize(fan),
        "VO Script": sanitize(vo),
        "Quote": sanitize(quote) if quote else "",
        "Tone": tone,
    }

def generate_lore_variants(
    a: Faction, b: Faction, winner: str, attacker: str, scenario_key: str, weather_key: str,
    terrain_desc: str, analysis_txt: str, casualties: Dict[str,object], day_idx: int, count: int = 3,
    pov: str = "mixed"
) -> List[Dict[str,str]]:
    variants = []
    for i in range(max(1, int(count))):
        variants.append(
            generate_lore_snippets(
                a,b,winner,attacker,scenario_key,weather_key,terrain_desc,analysis_txt,casualties,
                day_idx=day_idx*10 + i, pov=pov
            )
        )
    return variants

def generate_alt_timeline(
    a: Faction, b: Faction, actual_winner: str, attacker: str, scenario_key: str, weather_key: str,
    terrain_desc: str, analysis_txt: str, casualties: Dict[str,object], day_idx: int
) -> Dict[str,str]:
    # Flip winner and loser for narrative only
    alt_winner = b.name if actual_winner == a.name else a.name
    lore = generate_lore_snippets(a, b, alt_winner, attacker, scenario_key, weather_key, terrain_desc, analysis_txt, casualties, day_idx=day_idx+77, pov="mixed")
    lore["Alt Winner"] = alt_winner
    lore["Alt VO"] = lore.get("VO Script","") + " (alt timeline)"
    return lore
# -------------------- Builders --------------------

def build_single(a: Faction, b: Faction, seed_base: int, idx: int, style_pack: str, scenario_key: str, weather_key: str, weights: Dict[str,float], cmd_a: str, cmd_b: str, naval_mode: bool) -> Dict:
    random.seed(seed_base + idx)
    tkey = pick_terrain_key(a,b, naval_mode)
    tdesc = pick_terrain_desc(tkey, weather_key)
    p169_1, p916_1 = build_prompts(a,b, tdesc, style_pack, rotation_idx=idx)
    p169_2, p916_2 = build_prompts(a,b, tdesc, style_pack, rotation_idx=idx+1)
    p169_1, p916_1 = apply_preset(p169_1, a.name), apply_preset(p916_1, b.name)
    p169_2, p916_2 = apply_preset(p169_2, a.name), apply_preset(p916_2, b.name)
    p169_1, p916_1 = lint_prompt(p169_1,a,b), lint_prompt(p916_1,a,b)
    p169_2, p916_2 = lint_prompt(p169_2,a,b), lint_prompt(p916_2,a,b)
    p169 = p169_1 if heuristic_score(p169_1)>=heuristic_score(p169_2) else p169_2
    p916 = p916_1 if heuristic_score(p916_1)>=heuristic_score(p916_2) else p916_2
    ctx = context_text(a,b, tdesc, scenario_key)
    winner, why, ws, ls = outcome(a,b, tkey, scenario_key, weather_key, weights, cmd_a, cmd_b, naval_mode)
    attacker = choose_attacker(a,b, cmd_a, cmd_b)
    margin = (ws / max(ls, 0.001)) if ws and ls else 1.0
    size_a, size_b = estimate_force_sizes(a,b, scenario_key, naval_mode)
    cas = estimate_casualties(a,b, winner, margin, scenario_key, weather_key, tkey, naval_mode, size_a, size_b, attacker)
    deep = build_deep_context(a,b, winner, attacker, tdesc, scenario_key, weather_key, cas)
    pov_mode = st.session_state.get('pov_mode', 'mixed') if hasattr(st, 'session_state') else 'mixed'
    alt_enable = st.session_state.get('alt_timeline', True) if hasattr(st, 'session_state') else True
    lore = generate_lore_snippets(a,b, winner, attacker, scenario_key, weather_key, tdesc, deep, cas, idx, pov=pov_mode)
    lore_variants = generate_lore_variants(a,b, winner, attacker, scenario_key, weather_key, tdesc, deep, cas, idx, count=3, pov=pov_mode)
    alt = generate_alt_timeline(a,b, winner, attacker, scenario_key, weather_key, tdesc, deep, cas, idx) if alt_enable else {"Alt Winner":"","Alt VO":""}
    style_used = _resolve_style_name(style_pack, idx)
    poll = build_poll(a,b, scenario_key)
    caption = [
        "Who wins? Vote below. #HypotheticalBattles",
        "Your call. Tactics > luck. Vote.",
        "Decide it in the comments.",
        "Lore or logistics—what wins?",
    ][(seed_base+idx)%4]
    return {
        "Day": f"Day {idx+1}",
        "Matchup": f"{a.name} vs {b.name}",
        "MidJourney 16:9": p169,
        "MidJourney 9:16": p916,
        "Context": ctx,
        "Analysis": deep,
        "Who Won?": winner,
        "Why They Won": why,
        "Attacker": attacker,
        "Duration": cas["duration"],
        "Casualties A": cas["cas_a"]["total"],
        "Casualties B": cas["cas_b"]["total"],
        "Casualty Rate A (%)": cas["rate_a"],
        "Casualty Rate B (%)": cas["rate_b"],
        "Lore Hook": lore["Lore Hook"],
        "Tactical Beat": lore["Tactical Beat"],
        "Fan Prompt": lore["Fan Prompt"],
        "VO Script": lore["VO Script"],
        "Tone": lore.get("Tone",""),
        "Quote": lore.get("Quote",""),
        "Style Used": style_used,
        "Hook A": lore_variants[0].get("Lore Hook",""),
        "Hook B": lore_variants[1].get("Lore Hook","") if len(lore_variants)>1 else "",
        "Hook C": lore_variants[2].get("Lore Hook","") if len(lore_variants)>2 else "",
        "VO A": lore_variants[0].get("VO Script",""),
        "VO B": lore_variants[1].get("VO Script","") if len(lore_variants)>1 else "",
        "VO C": lore_variants[2].get("VO Script","") if len(lore_variants)>2 else "",
        "Alt Winner": alt.get("Alt Winner",""),
        "Alt VO": alt.get("Alt VO",""),
        "Poll Q": poll["Poll Q"],
        "Poll Opt 1": poll["Opt 1"],
        "Poll Opt 2": poll["Opt 2"],
        "Poll Opt 3": poll["Opt 3"],
        "Killed A": cas["cas_a"]["killed"],
        "Wounded A": cas["cas_a"]["wounded"],
        "Captured A": cas["cas_a"]["captured"],
        "Killed B": cas["cas_b"]["killed"],
        "Wounded B": cas["cas_b"]["wounded"],
        "Captured B": cas["cas_b"]["captured"],
        "Caption": caption,
        "Seed": seed_base + idx,
        "Score A": ws if winner==a else ls,
        "Score B": ws if winner==b else ls,
    }

@st.cache_data
def build_schedule(base_df: pd.DataFrame, days: int, seed_base: int, style_pack: str, scenario_key: str, weather_key: str, weights: Dict[str,float], cmd_a: str, cmd_b: str, naval_mode: bool) -> pd.DataFrame:
    rows = []
    for i in range(int(days)):
        src = base_df.iloc[i % len(base_df)]
        matchup = str(src.get("Matchup / Theme", "Romans vs. Samurai"))
        if "vs" in matchup:
            a_name = matchup.split("vs")[0].replace(".", "").strip()
            b_name = matchup.split("vs")[1].replace(".", "").strip()
        else:
            a_name, b_name = "Romans", "Samurai"
        a = KB.get(a_name, KB["Romans"]) ; b = KB.get(b_name, KB["Samurai"]) 
        row = build_single(a,b, seed_base, i, style_pack, scenario_key, weather_key, weights, cmd_a, cmd_b, naval_mode)
        rows.append(row)
    return pd.DataFrame(rows)

# -------------------- Preset Management --------------------

def get_preset_settings(preset_name: str):
    """Get complete settings for different presets"""
    presets = {
        "Balanced": {
            "weights": {"discipline": 1.4, "infantry": 1.3, "armor": 1.1, "logistics": 1.2, "ranged": 1.15, "cavalry": 1.1, "siege": 0.9, "naval": 1.0},
            "style_pack": "Cinematic",
            "scenario": "open field",
            "weather": "clear",
            "naval_mode": False,
            "cmd_a": "aggressive",
            "cmd_b": "defensive"
        },
        "TikTok Viral": {
            "weights": {"discipline": 1.2, "infantry": 1.4, "armor": 1.0, "logistics": 1.0, "ranged": 1.3, "cavalry": 1.5, "siege": 0.8, "naval": 1.2},
            "style_pack": "FULL-CRACKED-ASIAN",
            "scenario": "ambush",
            "weather": "windy",
            "naval_mode": False,
            "cmd_a": "aggressive",
            "cmd_b": "aggressive"
        },
        "Historian": {
            "weights": {"discipline": 1.6, "infantry": 1.2, "armor": 1.2, "logistics": 1.4, "ranged": 1.1, "cavalry": 1.0, "siege": 1.1, "naval": 1.0},
            "style_pack": "Documentary",
            "scenario": "open field",
            "weather": "clear",
            "naval_mode": False,
            "cmd_a": "cunning",
            "cmd_b": "defensive"
        }
    }
    return presets.get(preset_name, presets["Balanced"])

# -------------------- Weight Management --------------------

def get_balanced_weights() -> Dict[str, float]:
    """Return balanced default weights"""
    return {
        'discipline': 1.4, 'infantry': 1.3, 'armor': 1.1, 'logistics': 1.2,
        'ranged': 1.15, 'cavalry': 1.1, 'siege': 0.9, 'naval': 1.0
    }

def get_randomized_weights() -> Dict[str, float]:
    """Return randomized weights"""
    return {
        'discipline': random.uniform(0.5, 2.0), 'infantry': random.uniform(0.5, 2.0),
        'armor': random.uniform(0.5, 2.0), 'logistics': random.uniform(0.5, 2.0),
        'ranged': random.uniform(0.5, 2.0), 'cavalry': random.uniform(0.5, 2.0),
        'siege': random.uniform(0.3, 1.5), 'naval': random.uniform(0.3, 1.8)
    }

def search_factions(query: str) -> List[str]:
    """Search factions by name"""
    if not query:
        return sorted(KB.keys())
    
    query_lower = query.lower()
    matches = []
    
    # Exact matches first
    for name in KB.keys():
        if query_lower == name.lower():
            matches.append(name)
    
    # Starts with matches
    for name in KB.keys():
        if name.lower().startswith(query_lower) and name not in matches:
            matches.append(name)
    
    # Contains matches
    for name in KB.keys():
        if query_lower in name.lower() and name not in matches:
            matches.append(name)
    
    # Era matches
    for name, faction in KB.items():
        if query_lower in faction.era.lower() and name not in matches:
            matches.append(name)
    
    return sorted(matches)

def get_auto_balanced_weights(a: Faction, b: Faction, scenario_key: str, naval_mode: bool) -> Dict[str, float]:
    """Calculate fair weights based on the matchup"""
    # Base on average stats of both factions
    avg_discipline = (a.discipline + b.discipline) / 2
    avg_infantry = (a.infantry + b.infantry) / 2
    avg_armor = (a.armor + b.armor) / 2
    avg_logistics = (a.logistics + b.logistics) / 2
    avg_ranged = (a.ranged + b.ranged) / 2
    avg_cavalry = (a.cavalry + b.cavalry) / 2
    avg_siege = (a.siege + b.siege) / 2
    avg_naval = (a.naval + b.naval) / 2
    
    # Normalize weights based on faction strengths
    base = 1.0
    weights = {
        'discipline': base + (avg_discipline / 5.0) * 0.5,
        'infantry': base + (avg_infantry / 5.0) * 0.4,
        'armor': base + (avg_armor / 5.0) * 0.3,
        'logistics': base + (avg_logistics / 5.0) * 0.3,
        'ranged': base + (avg_ranged / 5.0) * 0.4,
        'cavalry': base + (avg_cavalry / 5.0) * 0.4,
        'siege': base + (avg_siege / 5.0) * 0.2,
        'naval': base + (avg_naval / 5.0) * (0.6 if naval_mode else 0.1)
    }
    
    # Adjust for scenario
    scen_mods = SCENARIOS[scenario_key]['mod']
    for stat, mod in scen_mods.items():
        if stat in weights:
            weights[stat] *= (1.0 + mod)
    
    return weights

# -------------------- Tournament / Elo --------------------

def expected_score(ra, rb):
    return 1.0 / (1.0 + 10 ** ((rb - ra) / 400))

def update_elo(ra, rb, sa, k=24):
    ea = expected_score(ra, rb)
    ra2 = ra + k * (sa - ea)
    rb2 = rb + k * ((1 - sa) - (1 - ea))
    return ra2, rb2

@st.cache_data
def play_round_robin(names: List[str], seed: int, weights: Dict[str,float], style_pack: str, scenario_key: str, weather_key: str, naval_mode: bool):
    random.seed(seed)
    elo = {n: 1500.0 for n in names}
    matches = []
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            a, b = KB[names[i]], KB[names[j]]
            # quick sim
            win, _, sa, sb = outcome(a,b, pick_terrain_key(a,b,naval_mode), scenario_key, weather_key, weights, 'aggressive','defensive', naval_mode)
            sa_n = 1.0 if win==a.name else 0.0
            elo[a.name], elo[b.name] = update_elo(elo[a.name], elo[b.name], sa_n)
            matches.append({"A": a.name, "B": b.name, "Winner": win})
    table = pd.DataFrame({"Faction": list(elo.keys()), "Elo": list(elo.values())}).sort_values("Elo", ascending=False)
    return table, pd.DataFrame(matches)

# ====== AUTO-PUBLISH MODULE ======
SAFE_DIR = "bundle"  # written to working dir
os.makedirs(SAFE_DIR, exist_ok=True)

# Tokens that should NEVER appear unless in the matchup text
MISMATCH_BLOCKLIST = [
    "samurai","ninja","ronin","vikings","viking","knights","janissary","janissaries",
    "muskets","rifles","bombards","aztecs","maya","incas","mongols","huns","celts",
    "greeks","romans","byzantines","ottomans","zulu","mali","ethiopians","carthage",
    "persians","chinese","han","tang","song","yuan","ming","qing","koreans","khmer","thai","vietnamese",
]

def prompt_autoclean(prompt: str, matchup: str) -> str:
    """Remove culture tokens not present in the matchup text; light de-dupe and spacing."""
    keep = set(re.findall(r"[A-Za-z]+", matchup.lower()))
    p = prompt
    for tok in MISMATCH_BLOCKLIST:
        if tok not in keep:
            # remove exact token or plural with simple boundaries
            p = re.sub(rf"(?i)\b{tok}s?\b", "", p)
    # collapse spaces and stray commas
    p = re.sub(r"\s{2,}", " ", p)
    p = re.sub(r",\s*,", ", ", p)
    p = re.sub(r"\s+,", ",", p)
    return p.strip()

def build_prompt_sheet(schedule_df: pd.DataFrame) -> pd.DataFrame:
    """Two rows per day: 16:9 and 9:16, prompts auto-cleaned vs matchup."""
    rows = []
    for _, r in schedule_df.iterrows():
        matchup = str(r["Matchup"])
        p169 = prompt_autoclean(str(r["MidJourney 16:9"]), matchup)
        p916 = prompt_autoclean(str(r["MidJourney 9:16"]), matchup)
        rows.append({"Day": r["Day"], "Aspect": "16:9", "Prompt": p169, "Seed": r.get("Seed","")})
        rows.append({"Day": r["Day"], "Aspect": "9:16", "Prompt": p916, "Seed": r.get("Seed","")})
    return pd.DataFrame(rows)

def write_markdown_cards(schedule_df: pd.DataFrame, root: str) -> None:
    cards_dir = os.path.join(root, "cards")
    os.makedirs(cards_dir, exist_ok=True)
    for _, r in schedule_df.iterrows():
        slug = str(r["Day"]).lower().replace(" ", "-")
        md = f"""# {r['Day']} - {r['Matchup']}
Seed: {r.get('Seed','')}

**MidJourney 16:9**: {prompt_autoclean(str(r['MidJourney 16:9']), str(r['Matchup']))}

**MidJourney 9:16**: {prompt_autoclean(str(r['MidJourney 9:16']), str(r['Matchup']))}

**Context**: {r['Context']}

**Analysis**: {r.get('Analysis','')}

**Who Won?**: {r['Who Won?']}

**Why They Won**: {r['Why They Won']}

**Attacker**: {r.get('Attacker','')}

**Duration**: {r.get('Duration','')}

**Casualties**:

- {str(r['Matchup']).split(' vs ')[0]}: {r.get('Casualties A','')} total ({r.get('Casualty Rate A (%)','')}%)
- {str(r['Matchup']).split(' vs ')[1]}: {r.get('Casualties B','')} total ({r.get('Casualty Rate B (%)','')}%)

**Caption**: {r['Caption']}
\n+**Hook**: {r.get('Lore Hook','')}
\n+**Tactical Beat**: {r.get('Tactical Beat','')}
\n+**Fan Prompt**: {r.get('Fan Prompt','')}
\n+**VO Script**: {r.get('VO Script','')}
"""
        with open(os.path.join(cards_dir, f"{slug}.md"), "w", encoding="utf-8") as f:
            f.write(md)

def build_asset_manifest(schedule_df: pd.DataFrame, root: str) -> pd.DataFrame:
    """
    Create a manifest of expected image filenames so you can batch-upload later.
    Example names: day01_169_seed12345.jpg, day01_916_seed12345.jpg
    """
    man_rows = []
    for idx, r in enumerate(schedule_df.itertuples(index=False), start=1):
        seed = getattr(r, "Seed", "")
        daynum = f"{idx:02d}"
        man_rows += [
            {"Day": getattr(r, "Day"), "File": f"assets/day{daynum}/day{daynum}_169_seed{seed}.jpg", "Aspect":"16:9"},
            {"Day": getattr(r, "Day"), "File": f"assets/day{daynum}/day{daynum}_916_seed{seed}.jpg", "Aspect":"9:16"},
        ]
    man = pd.DataFrame(man_rows)
    man_path = os.path.join(root, "asset_manifest.csv")
    man.to_csv(man_path, index=False)
    return man

def build_midjourney_queue(schedule_df: pd.DataFrame, aspects: str = "both") -> str:
    """Return a text block with Discord-ready /imagine lines for MJ.
    aspects: '169', '916', or 'both'
    """
    lines = []
    for r in schedule_df.itertuples(index=False):
        matchup = getattr(r, "Matchup")
        if aspects in ("169", "both"):
            p = getattr(r, "MidJourney 16:9")
            lines.append(f"/imagine prompt: {p}  # {matchup}")
        if aspects in ("916", "both"):
            p = getattr(r, "MidJourney 9:16")
            lines.append(f"/imagine prompt: {p}  # {matchup}")
    return "\n".join(lines)

def save_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def build_poll(a: Faction, b: Faction, scenario_key: str) -> Dict[str, str]:
    base_q = {
        "open field": "What wins today?",
        "ambush": "Surprise or discipline—who prevails?",
        "river crossing": "Hold the ford or force it?",
        "hill defense": "Height or momentum?",
        "siege": "Engines or endurance?",
        "naval": "Rams or missiles at sea?",
    }.get(scenario_key, "What wins this battle?")
    opts = ["Discipline", "Cavalry", "Archers", "Siege"]
    # light scenario tweak
    if scenario_key in ("river crossing","naval"): opts[2] = "Missiles"
    return {"Poll Q": base_q, "Opt 1": opts[0], "Opt 2": opts[1], "Opt 3": opts[2]}

def build_ahk_autopaste(queue_text: str, window_hint: str = "Discord") -> str:
    """Build a Windows AutoHotkey v1 script that pastes prompts line-by-line into Discord.
    Disclaimer: UI automation of Discord may violate Discord/Midjourney ToS. Use responsibly.
    Launch the script, focus the target Discord channel, then press F8 to run.
    """
    lines = []
    for raw in queue_text.splitlines():
        s = raw.strip()
        if not s:
            continue
        # Escape quotes for AHK string literal
        s = s.replace('"', '""')
        lines.append(s)
    arr = ",\n    ".join([f'"{s}"' for s in lines])
    ahk = f"""; AutoHotkey v1 script – paste MJ prompts (Generated by app)
#SingleInstance Force
SetTitleMatchMode, 2
SetKeyDelay, 50, 20

; Focus target window (adjust if needed)
WinActivate, {window_hint}
Sleep, 800

lines := [
    {arr}
]

F8::
for i, s in lines
{
    Clipboard := s
    Sleep, 100
    Send, ^v
    Sleep, 250
    Send, {Enter}
    Sleep, 1500
}
return
"""
    return ahk

def package_all(schedule_df: pd.DataFrame) -> bytes:
    """Write CSV/JSON, prompt sheet, markdown cards, manifest; return ZIP bytes."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = os.path.join(SAFE_DIR, f"export_{ts}")
    os.makedirs(root, exist_ok=True)

    # Cleaned copies
    cleaned = schedule_df.copy()
    cleaned["MidJourney 16:9"] = [
        prompt_autoclean(p, m) for p, m in zip(cleaned["MidJourney 16:9"], cleaned["Matchup"])
    ]
    cleaned["MidJourney 9:16"] = [
        prompt_autoclean(p, m) for p, m in zip(cleaned["MidJourney 9:16"], cleaned["Matchup"])
    ]

    # Base exports
    cleaned.to_csv(os.path.join(root, "battles.csv"), index=False)
    cleaned.to_json(os.path.join(root, "battles.json"), orient="records", indent=2)

    # Prompt sheet
    prompt_df = build_prompt_sheet(cleaned)
    prompt_df.to_csv(os.path.join(root, "midjourney_prompts.csv"), index=False)

    # Captions & Voiceover
    cap_rows = []
    for _, r in cleaned.iterrows():
        cap_rows.append({
            "Day": r["Day"],
            "Matchup": r["Matchup"],
            "Hook": r.get("Lore Hook",""),
            "Tactical": r.get("Tactical Beat",""),
            "Fan": r.get("Fan Prompt",""),
            "VO": r.get("VO Script",""),
            "Quote": r.get("Quote",""),
        })
    captions_df = pd.DataFrame(cap_rows)
    captions_df.to_csv(os.path.join(root, "captions_voiceover.csv"), index=False)

    # Lore variants CSV
    var_rows = []
    for _, r in cleaned.iterrows():
        var_rows.append({
            "Day": r["Day"], "Matchup": r["Matchup"],
            "Hook A": r.get("Hook A",""), "VO A": r.get("VO A",""),
            "Hook B": r.get("Hook B",""), "VO B": r.get("VO B",""),
            "Hook C": r.get("Hook C",""), "VO C": r.get("VO C",""),
            "Alt Winner": r.get("Alt Winner",""), "Alt VO": r.get("Alt VO",""),
        })
    pd.DataFrame(var_rows).to_csv(os.path.join(root, "captions_voiceover_variants.csv"), index=False)

    # Polls CSV
    poll_rows = []
    for _, r in cleaned.iterrows():
        poll_rows.append({
            "Day": r["Day"], "Matchup": r["Matchup"],
            "Question": r.get("Poll Q",""),
            "Option 1": r.get("Poll Opt 1",""),
            "Option 2": r.get("Poll Opt 2",""),
            "Option 3": r.get("Poll Opt 3",""),
        })
    polls_df = pd.DataFrame(poll_rows)
    polls_df.to_csv(os.path.join(root, "polls.csv"), index=False)

    # Overlays (PNG) for hooks
    overlays_dir = os.path.join(root, "overlays")
    os.makedirs(overlays_dir, exist_ok=True)
    overlay_theme = (st.session_state.get('overlay_theme','Dark') if hasattr(st,'session_state') else 'Dark')
    overlay_pos = (st.session_state.get('overlay_pos','Top') if hasattr(st,'session_state') else 'Top')
    overlay_aspects = (st.session_state.get('overlay_aspects',["9:16"]) if hasattr(st,'session_state') else ["9:16"])
    overlay_font = (st.session_state.get('overlay_font_size', 64) if hasattr(st,'session_state') else 64)
    overlay_shadow = (st.session_state.get('overlay_shadow', 160) if hasattr(st,'session_state') else 160)
    overlay_wrap = (st.session_state.get('overlay_wrap', 18) if hasattr(st,'session_state') else 18)
    for i, r in enumerate(cleaned.itertuples(index=False), start=1):
        hook = getattr(r, "Lore Hook", "") or getattr(r, "Hook A", "") or getattr(r, "Hook", "")
        if not hook:
            continue
        for asp in overlay_aspects:
            try:
                size = TARGET_V if asp == "9:16" else TARGET_H
                png = render_text_overlay_png(hook, size=size, theme=overlay_theme.lower(), position=overlay_pos.lower(), font_size=int(overlay_font), shadow_alpha=int(overlay_shadow), wrap=int(overlay_wrap))
                suffix = "916" if asp == "9:16" else "169"
                with open(os.path.join(overlays_dir, f"day{i:02d}_overlay_{suffix}.png"), "wb") as f:
                    f.write(png)
            except Exception:
                pass

    # Markdown cards
    write_markdown_cards(cleaned, root)

    # Asset manifest
    manifest = build_asset_manifest(cleaned, root)

    # Midjourney queue text (both aspects)
    queue_txt = build_midjourney_queue(cleaned, aspects="both")
    save_text(os.path.join(root, "midjourney_queue.txt"), queue_txt)
    # AutoHotkey helper (Windows)
    save_text(os.path.join(root, "midjourney_autopaste.ahk"), build_ahk_autopaste(queue_txt))

    # Bundle
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # write files from disk
        for path in ["battles.csv","battles.json","midjourney_prompts.csv","captions_voiceover.csv","captions_voiceover_variants.csv","polls.csv","asset_manifest.csv","midjourney_queue.txt","midjourney_autopaste.ahk"]:
            zf.write(os.path.join(root, path), arcname=path)
        # write cards
        cards_dir = os.path.join(root, "cards")
        for fn in os.listdir(cards_dir):
            zf.write(os.path.join(cards_dir, fn), arcname=f"cards/{fn}")
        # write overlays
        for fn in os.listdir(overlays_dir):
            zf.write(os.path.join(overlays_dir, fn), arcname=f"overlays/{fn}")
        # include user config (if any)
        try:
            for p in [USER_FACTIONS_PATH, USER_STYLE_PACKS_PATH, USER_PRESETS_PATH]:
                if os.path.exists(p):
                    zf.write(p, arcname=f"config/{os.path.basename(p)}")
        except Exception:
            pass
    return buf.getvalue()

# -------------------- Reel Builder --------------------
TARGET_V = (1080, 1920)
TARGET_H = (1920, 1080)

def _best_font(size: int) -> Optional[ImageFont.ImageFont]:
    # Try a few common fonts; fallback to default
    candidates = [
        "arial.ttf", "Roboto-Regular.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def render_caption_frame(img_bytes: bytes, size=(1080,1920), title: str = "", subtitle: str = "", footer: str = "") -> Image.Image:
    base = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    # letterbox to target size
    tw, th = size
    iw, ih = base.size
    target_aspect = tw / th
    src_aspect = iw / ih
    if src_aspect > target_aspect:
        # wider than target: height fits, crop width
        new_h = th
        new_w = int(src_aspect * new_h)
    else:
        new_w = tw
        new_h = int(new_w / src_aspect)
    base_resized = base.resize((new_w, new_h), Image.LANCZOS)
    # crop center
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    frame = base_resized.crop((left, top, left + tw, top + th))
    draw = ImageDraw.Draw(frame)

    # Overlay blocks
    pad = 36
    title_font = _best_font(56)
    body_font = _best_font(36)
    footer_font = _best_font(28)

    # Semi-transparent rect behind text for readability
    def rect(xy, alpha=140):
        x1, y1, x2, y2 = xy
        overlay = Image.new('RGBA', (x2-x1, y2-y1), (0,0,0,alpha))
        frame_rgba = frame.convert('RGBA')
        frame_rgba.paste(overlay, (x1, y1), overlay)
        return frame_rgba.convert('RGB')

    y = pad
    if title:
        txt = title[:200]
        w, h = draw.textlength(txt, font=title_font), title_font.size + 8
        frame = rect((pad//2, y-pad//2, tw - pad//2, y + h + pad//2))
        draw = ImageDraw.Draw(frame)
        draw.text((pad, y), txt, fill=(255,255,255), font=title_font)
        y += h + pad
    if subtitle:
        # wrap subtitle to 38 chars/line approx
        lines = textwrap.wrap(subtitle, width=38)
        block = "\n".join(lines)
        # measure height
        h_total = (body_font.size + 8) * len(lines)
        frame = rect((pad//2, y-pad//2, tw - pad//2, y + h_total + pad//2))
        draw = ImageDraw.Draw(frame)
        draw.multiline_text((pad, y), block, fill=(240,240,240), font=body_font, spacing=6)
        y += h_total + pad
    if footer:
        lines = textwrap.wrap(footer, width=40)
        block = "\n".join(lines)
        h_total = (footer_font.size + 6) * len(lines)
        frame = rect((pad//2, th - h_total - 2*pad, tw - pad//2, th - pad//2))
        draw = ImageDraw.Draw(frame)
        draw.multiline_text((pad, th - h_total - pad), block, fill=(230,230,230), font=footer_font, spacing=4)
    return frame

def render_text_overlay_png(text: str, size=(1080,1920), theme: str = "dark", position: str = "top", font_size: int = 64, shadow_alpha: int = 160, wrap: int = 18) -> bytes:
    if not MOVIEPY_OK:
        # We still rely on PIL; if not available, raise
        try:
            from PIL import Image, ImageDraw, ImageFont  # type: ignore
        except Exception as e:
            raise RuntimeError("Pillow not available to render overlays") from e
    tw, th = size
    img = Image.new("RGBA", (tw, th), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    font = _best_font(int(font_size))
    # word wrap
    lines = textwrap.wrap(text, width=int(wrap))
    # measure block height
    font_h = font.size + 16
    block_h = font_h * len(lines)
    # choose vertical position
    pos = (position or "top").lower()
    if pos == "middle":
        y = max(12, (th - block_h)//2)
    elif pos == "bottom":
        y = max(12, th - block_h - int(th*0.08))
    else:
        y = int(th*0.08)
    pad = 24
    # optional theme background
    if theme.lower() == "gradient":
        # simple dark gradient band behind text
        band = Image.new('RGBA', (tw, block_h + 2*pad), (0,0,0,0))
        for i in range(band.size[1]):
            alpha = int(160 * (1 - i/ band.size[1]))
            ImageDraw.Draw(band).line([(0,i),(tw,i)], fill=(0,0,0,alpha))
        img.paste(band, (0, max(0, y - pad)), band)
    for line in lines:
        # shadow/outline
        alpha = max(0, min(255, int(shadow_alpha)))
        shadow_col = (0,0,0,alpha) if theme.lower() != "light" else (255,255,255,alpha)
        fg = (255,255,255,235) if theme.lower() != "light" else (10,10,10,235)
        # draw with a thin outline to improve readability
        try:
            draw.text((pad, y), line, font=font, fill=fg, stroke_width=2, stroke_fill=shadow_col)
        except TypeError:
            # fallback for PIL without stroke support
            draw.text((pad+2, y+2), line, font=font, fill=shadow_col)
            draw.text((pad, y), line, font=font, fill=fg)
        y += font.size + 16
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()

# -------------------- Viral Pipeline Helpers --------------------
def _sec_from_srt(ts: str) -> float:
    # format: HH:MM:SS,mmm
    try:
        hms, ms = ts.split(',')
        h, m, s = [int(x) for x in hms.split(':')]
        return h*3600 + m*60 + s + int(ms)/1000.0
    except Exception:
        return 0.0

def parse_srt(text: str):
    events = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for b in blocks:
        lines = [l.strip('\ufeff') for l in b.splitlines() if l.strip()]
        if len(lines) < 2: continue
        if '-->' in lines[0]:
            times = lines[0]
            idx_line = None
            content_lines = lines[1:]
        else:
            idx_line = lines[0]
            times = lines[1] if len(lines) > 1 else ''
            content_lines = lines[2:]
        if '-->' not in times: continue
        start_s, end_s = [t.strip() for t in times.split('-->')]
        start = _sec_from_srt(start_s)
        end = _sec_from_srt(end_s)
        txt = sanitize(' '.join(content_lines))
        if end > start:
            events.append({"start": start, "end": end, "text": txt})
    return events

def auto_segment_times(duration: float, target: float = 30.0, min_len: float = 15.0, max_len: float = 45.0):
    times = []
    t = 0.0
    while t < duration - min_len:
        end = min(t + target, duration)
        # clamp
        if end - t < min_len and times:
            # extend previous
            prev_t, prev_e = times.pop()
            times.append((prev_t, duration))
            return times
        if end - t > max_len:
            end = t + max_len
        times.append((t, end))
        t = end
    if not times or times[-1][1] < duration:
        if times and (duration - times[-1][0]) >= min_len:
            times[-1] = (times[-1][0], duration)
        else:
            times.append((t, duration))
    return times

def add_hook_overlay_clip(clip, text: str, theme: str = 'dark', position: str = 'top', seconds: float = 2.0):
    if not text:
        return clip
    try:
        png = render_text_overlay_png(text, size=(int(clip.w), int(clip.h)), theme=theme, position=position, font_size=64, shadow_alpha=160, wrap=18)
        ov = ImageClip(np.array(Image.open(io.BytesIO(png))).astype('uint8')).set_duration(min(seconds, clip.duration)).set_pos((0,0))
        return CompositeVideoClip([clip, ov])
    except Exception:
        return clip

def burn_srt_on_clip(clip, events, position: str = 'bottom', font_size: int = 48):
    overlays = []
    for ev in events:
        start, end, text = ev['start'], ev['end'], ev['text']
        if end <= 0 or start >= clip.duration:
            continue
        s_local = max(0, start)
        e_local = min(clip.duration, end)
        png = render_text_overlay_png(text, size=(int(clip.w), int(clip.h)), theme='dark', position=position, font_size=font_size, shadow_alpha=200, wrap=24)
        ov = ImageClip(np.array(Image.open(io.BytesIO(png))).astype('uint8')).set_start(s_local).set_duration(e_local - s_local).set_pos((0,0))
        overlays.append(ov)
    return CompositeVideoClip([clip, *overlays]) if overlays else clip

def adapt_aspect_clip(clip, target_size):
    tw, th = target_size
    # scale and center-crop
    src_aspect = clip.w / clip.h
    dst_aspect = tw / th
    if src_aspect > dst_aspect:
        new_h = th
        new_w = int(src_aspect * new_h)
    else:
        new_w = tw
        new_h = int(new_w / src_aspect)
    scaled = clip.resize((new_w, new_h))
    x1 = (new_w - tw) // 2
    y1 = (new_h - th) // 2
    return scaled.crop(x1=x1, y1=y1, x2=x1+tw, y2=y1+th)

def sample_thumbnails(clip, every_sec: float = 1.0, top_k: int = 3):
    frames = []
    t = 0.1
    while t < clip.duration:
        img = clip.get_frame(t)
        # focus measure via simple Laplacian-like kernel
        gray = np.dot(img[...,:3],[0.299,0.587,0.114]).astype('float32')
        # approximate laplacian variance
        gy, gx = np.gradient(gray)
        g2 = (gx*gx + gy*gy).mean()
        frames.append((g2, t, img))
        t += every_sec
    frames.sort(key=lambda x: x[0], reverse=True)
    return frames[:top_k]

def retention_scan(clip, window: float = 2.0, step: float = 0.5):
    # heuristic: low motion + low audio rms windows
    rows = []
    try:
        audio = clip.audio.to_soundarray(fps=22050)
        rms = np.sqrt((audio**2).mean(axis=1)) if audio.ndim>1 else np.sqrt((audio**2).mean())
        # crude overall audio
        a_level = rms.mean() if hasattr(rms,'mean') else float(rms)
    except Exception:
        a_level = 0.0
    t = 0.0
    last = None
    while t + window <= clip.duration:
        frame_a = clip.get_frame(t)
        frame_b = clip.get_frame(min(clip.duration-0.001, t+window))
        diff = np.abs(frame_a.astype('float32') - frame_b.astype('float32')).mean()
        low_motion = diff < 8.0
        low_audio = a_level < 0.01
        if low_motion and low_audio:
            rows.append({"start": round(t,2), "end": round(t+window,2), "flag": "low energy"})
        t += step
    return pd.DataFrame(rows)

def build_viral_package(video_file, srt_text: str | None, music_file, hook_text: str, aspects: List[str]) -> Tuple[bytes, Dict[str, object]]:
    if not MOVIEPY_OK:
        raise RuntimeError("MoviePy/Pillow/numpy not installed")
    # Save inputs
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = os.path.join(SAFE_DIR, f"viral_{ts}")
    os.makedirs(root, exist_ok=True)
    in_path = os.path.join(root, "input.mp4")
    with open(in_path, 'wb') as f:
        f.write(video_file.read())
    clip = None
    try:
        clip = __import__('moviepy.editor', fromlist=['VideoFileClip']).VideoFileClip(in_path)
        segs = auto_segment_times(clip.duration, target=30.0, min_len=15.0, max_len=45.0)
        srt_events = parse_srt(srt_text) if srt_text else []
        # outputs
        out_info = []
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            # thumbnails directory
            # per segment
            for idx, (s,e) in enumerate(segs, start=1):
                sub = clip.subclip(s, e)
                sub = add_hook_overlay_clip(sub, hook_text, theme='gradient', position='top', seconds=2.0)
                if srt_events:
                    # shift events into local times
                    evs = [{"start": ev['start']-s, "end": ev['end']-s, "text": ev['text']} for ev in srt_events if ev['end']>s and ev['start']<e]
                    sub = burn_srt_on_clip(sub, evs, position='bottom', font_size=48)
                # mix music if provided
                if music_file is not None:
                    mpath = os.path.join(root, f"music_{idx}.mp3")
                    with open(mpath, 'wb') as fm:
                        fm.write(music_file.read())
                    music = AudioFileClip(mpath).volumex(0.4)
                    base_a = sub.audio.volumex(0.7) if sub.audio else None
                    if base_a:
                        sub = sub.set_audio(__import__('moviepy.editor', fromlist=['CompositeAudioClip']).CompositeAudioClip([base_a, music.set_duration(sub.duration)]))
                    else:
                        sub = sub.set_audio(music.set_duration(sub.duration))
                # thumbnails
                thumbs = sample_thumbnails(sub, every_sec=1.0, top_k=2)
                for k,(score,tsec,img) in enumerate(thumbs, start=1):
                    name = f"thumb_seg{idx}_{k}.jpg"
                    bio = io.BytesIO()
                    Image.fromarray(img).save(bio, format='JPEG', quality=92)
                    zf.writestr(f"thumbnails/{name}", bio.getvalue())
                # export aspects
                for asp in aspects:
                    size = TARGET_V if asp == '9:16' else TARGET_H if asp == '16:9' else (1080,1350)
                    tag = '916' if asp=='9:16' else '169' if asp=='16:9' else '45'
                    out_clip = adapt_aspect_clip(sub, size)
                    outp = os.path.join(root, f"seg{idx}_{tag}.mp4")
                    out_clip.write_videofile(outp, fps=30, codec='libx264', audio_codec='aac', threads=2, verbose=False, logger=None)
                    with open(outp,'rb') as fv:
                        zf.writestr(f"segments/seg{idx}_{tag}.mp4", fv.read())
                out_info.append({"segment": idx, "start": round(s,2), "end": round(e,2)})
            # retention report
            rep = retention_scan(clip)
            if not rep.empty:
                zf.writestr("retention_report.csv", rep.to_csv(index=False))
            # posting plan stub
            plan_rows = []
            for row in out_info:
                cap = hook_text + " " + "#history #battle #viral #shorts"
                plan_rows.append({"Segment": row['segment'], "Caption": cap, "Hashtags": "#history #battle #viral #shorts", "Formats": ",".join(aspects)})
            zf.writestr("posting_plan.csv", pd.DataFrame(plan_rows).to_csv(index=False))
        return buf.getvalue(), {"segments": out_info}
    finally:
        try:
            if clip: clip.close()
        except Exception:
            pass

def build_reel_from_uploads(images: List[io.BytesIO], schedule_df: pd.DataFrame, aspect: str = "9:16", seconds_per: float = 3.5, fps: int = 30, bgm_path: Optional[str] = None) -> Tuple[bytes, str]:
    if not MOVIEPY_OK:
        raise RuntimeError("MoviePy/Pillow/numpy not installed; cannot build reel.")
    size = TARGET_V if aspect == "9:16" else TARGET_H
    clips = []
    used = 0
    for i, r in enumerate(schedule_df.itertuples(index=False)):
        if i >= len(images):
            break
        img_bytes = images[i].read()
        img_frame = render_caption_frame(
            img_bytes, size=size,
            title=f"{getattr(r,'Day')} • {getattr(r,'Matchup')}",
            subtitle=f"Winner: {getattr(r,'Who Won?')}",
            footer=f"Why: {getattr(r,'Why They Won')}"
        )
        # convert to clip
        arr = np.array(img_frame)
        clip = ImageClip(arr).set_duration(seconds_per)
        clips.append(clip)
        used += 1
    if not clips:
        raise RuntimeError("No images provided to build the reel.")
    video = concatenate_videoclips(clips, method="compose")
    if bgm_path:
        try:
            audio = AudioFileClip(bgm_path).volumex(0.5)
            video = video.set_audio(audio)
        except Exception:
            pass
    # write to memory
    tmp = io.BytesIO()
    # MoviePy writes to file path; write to SAFE_DIR and read back
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(SAFE_DIR, "reels")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"reel_{aspect.replace(':','x')}_{ts}.mp4")
    video.write_videofile(out_path, fps=fps, codec="libx264", audio_codec="aac", threads=2, verbose=False, logger=None)
    with open(out_path, "rb") as f:
        data = f.read()
    name = os.path.basename(out_path)
    return data, name

# -------------------- UI --------------------
st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); 
           border-radius: 15px; margin-bottom: 20px;">
    <h1 style="color: white; margin: 0; font-size: 2.5em;">⚡ MAXIMUM OVERDRIVE ⚡</h1>
    <h2 style="color: #f0f0f0; margin: 10px 0; font-size: 1.2em;">Hypothetical Battles Generator</h2>
    <p style="color: #e0e0e0; margin: 0; font-size: 1em;">🚀 ONE-CLICK GENERATION | 60+ FACTIONS | FULL-CRACKED-ASIAN STYLE</p>
</div>
""", unsafe_allow_html=True)

st.info("🎯 **Quick Start**: Use preset buttons in sidebar → Search factions → Hit 'ONE-CLICK ALL' for instant results!")

single_tab, schedule_tab, tourney_tab, publish_tab, custom_tab, reels_tab = st.tabs(["Single Battle","Schedule","Tournament","Auto-Publish","Customize","Reels"]) 
single_tab, schedule_tab, tourney_tab, publish_tab, custom_tab, reels_tab, viral_tab, fan_tab, analytics_tab = st.tabs(["Single Battle","Schedule","Tournament","Auto-Publish","Customize","Reels","Viral","Fan Mode","Analytics"]) 

with custom_tab:
    st.subheader("Customize Data (Persisted)")
    st.caption("Create or edit your own factions, style packs, and presets. Saved to `data/` and auto-merged.")

    st.markdown("**Add / Update Single Faction**")
    with st.form("add_faction_form"):
        c1, c2, c3 = st.columns([2,2,2], gap="small")
        with c1:
            fx_name = st.text_input("Name", placeholder="e.g., Dragon Empire")
            fx_era = st.text_input("Era", value="Custom")
            fx_palettes = st.text_input("Palettes (comma-separated)", value="crimson gold, obsidian black")
            fx_motifs = st.text_input("Motifs (comma-separated)", value="dragon banners, thunder spears")
        with c2:
            fx_ranged = st.slider("Ranged", 0, 5, 3)
            fx_cavalry = st.slider("Cavalry", 0, 5, 3)
            fx_infantry = st.slider("Infantry", 0, 5, 3)
            fx_armor = st.slider("Armor", 0, 5, 3)
        with c3:
            fx_discipline = st.slider("Discipline", 0, 5, 3)
            fx_siege = st.slider("Siege", 0, 5, 2)
            fx_logistics = st.slider("Logistics", 0, 5, 3)
            fx_naval = st.slider("Naval", 0, 5, 1)
        terrains = list(TERRAIN_RULES.keys())
        fx_terrain = st.multiselect("Terrain Pref", terrains, default=["plains"])
        submitted = st.form_submit_button("Save Faction", type="primary")
        if submitted:
            if fx_name.strip():
                try:
                    # Load current file, update, and save
                    cur = _load_json(USER_FACTIONS_PATH, default=[])
                    # Normalize to mapping for easy update
                    if isinstance(cur, list):
                        cur_map = {d.get("name"): d for d in cur if isinstance(d, dict) and d.get("name")}
                    elif isinstance(cur, dict):
                        cur_map = {str(k): v for k, v in cur.items() if isinstance(v, dict)}
                    else:
                        cur_map = {}
                    cur_map[fx_name] = {
                        "name": fx_name,
                        "era": fx_era,
                        "ranged": fx_ranged,
                        "cavalry": fx_cavalry,
                        "infantry": fx_infantry,
                        "armor": fx_armor,
                        "discipline": fx_discipline,
                        "siege": fx_siege,
                        "logistics": fx_logistics,
                        "naval": fx_naval,
                        "terrain_pref": fx_terrain,
                        "palettes": [s.strip() for s in fx_palettes.split(",") if s.strip()],
                        "motifs": [s.strip() for s in fx_motifs.split(",") if s.strip()],
                    }
                    # Save back as list for readability
                    _save_json(USER_FACTIONS_PATH, list(cur_map.values()))
                    st.success(f"Saved faction '{fx_name}'.")
                    # Update in-memory and rerun
                    KB.update(_factions_from_json([cur_map[fx_name]]))
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to save: {e}")
            else:
                st.warning("Please provide a Name for the faction.")

    st.markdown("**Edit Raw JSON**")
    raw_f = _load_json(USER_FACTIONS_PATH, default=[])
    raw_text = st.text_area("user_factions.json", value=json.dumps(raw_f, indent=2, ensure_ascii=False), height=200)
    if st.button("Save user_factions.json"):
        try:
            data = json.loads(raw_text)
            _save_json(USER_FACTIONS_PATH, data)
            KB.update(_factions_from_json(data))
            st.success("Saved user_factions.json")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

    st.divider()
    st.markdown("**Style Packs (JSON)**")
    sp_cur = _load_json(USER_STYLE_PACKS_PATH, default=USER_STYLE_PACKS or {})
    sp_text = st.text_area("user_style_packs.json", value=json.dumps(sp_cur, indent=2, ensure_ascii=False), height=200)
    c_sp1, c_sp2 = st.columns([1,1])
    if c_sp1.button("Save user_style_packs.json"):
        try:
            data = json.loads(sp_text)
            _save_json(USER_STYLE_PACKS_PATH, data)
            if isinstance(data, dict):
                STYLE_PACKS.update({k: v for k, v in data.items() if isinstance(v, dict) and "add" in v and "s" in v})
            st.success("Saved user_style_packs.json")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
    if c_sp2.button("Reset user_style_packs.json"):
        try:
            _save_json(USER_STYLE_PACKS_PATH, {})
            st.info("Cleared user_style_packs.json")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to reset: {e}")

with reels_tab:
    st.subheader("Reel Maker (MJ → Video)")
    st.caption("Drop in your Midjourney images, and we’ll create a vertical reel with captions (winner + why).")

    if not MOVIEPY_OK:
        st.warning("MoviePy/Pillow/numpy not installed. Install extras to enable rendering.")

    # Source schedule
    src_df_r = None
    for key in ["result","schedule_df","last_schedule"]:
        if key in st.session_state and isinstance(st.session_state[key], pd.DataFrame):
            src_df_r = st.session_state[key]
            break

    up_df = st.file_uploader("Or upload schedule CSV/JSON", ["csv","json"], key="reels_up_df")
    if up_df is not None:
        try:
            if up_df.name.lower().endswith(".csv"):
                src_df_r = pd.read_csv(up_df)
            else:
                src_df_r = pd.read_json(up_df)
        except Exception as e:
            st.error(f"Failed to read schedule: {e}")

    if src_df_r is None:
        st.info("No schedule detected. Generate it in Schedule tab or upload CSV/JSON.")
    else:
        st.success(f"Schedule loaded with {len(src_df_r)} rows")
        st.dataframe(src_df_r.head(6), use_container_width=True)

    st.markdown("---")
    col_a, col_b = st.columns([3,2])
    with col_a:
        imgs = st.file_uploader("Upload Midjourney images (ordered by day)", ["png","jpg","jpeg"], accept_multiple_files=True, key="reel_imgs")
        bgm = st.file_uploader("Optional background music (mp3/m4a/aac)", ["mp3","m4a","aac"], key="reel_bgm")
    with col_b:
        aspect = st.selectbox("Aspect", ["9:16","16:9"], index=0)
        seconds = st.slider("Seconds per image", 2.0, 8.0, 3.5, 0.5)
        fps = st.slider("FPS", 24, 60, 30, 1)

    btn = st.button("Build Reel", type="primary")
    if btn:
        if not MOVIEPY_OK:
            st.error("MoviePy not available.")
        elif src_df_r is None:
            st.error("No schedule loaded.")
        elif not imgs:
            st.error("Please upload at least one image.")
        else:
            try:
                # persist bgm to a temp path if provided
                bgm_path = None
                if bgm is not None:
                    bgm_dir = os.path.join(SAFE_DIR, "reels")
                    os.makedirs(bgm_dir, exist_ok=True)
                    bgm_path = os.path.join(bgm_dir, f"bgm_{bgm.name}")
                    with open(bgm_path, "wb") as f:
                        f.write(bgm.read())
                data, name = build_reel_from_uploads(imgs, src_df_r, aspect=aspect, seconds_per=seconds, fps=fps, bgm_path=bgm_path)
                st.video(data)
                st.download_button("Download Reel (.mp4)", data, file_name=name, mime="video/mp4", type="primary")
                st.success("Reel created.")
        except Exception as e:
            st.error(f"Failed to build reel: {e}")

with viral_tab:
    st.subheader("One-Button Viral Pipeline")
    st.caption("Upload a raw video. I’ll auto-cut, add a hook overlay, burn captions (SRT optional), adapt formats (9:16 / 16:9 / 4:5), pick thumbnails, run a quick retention scan, and bundle everything.")

    if not MOVIEPY_OK:
        st.warning("MoviePy/Pillow/numpy not installed. Install deps to enable pipeline.")

    vfile = st.file_uploader("Raw video (mp4/mov)", ["mp4","mov","mkv"], key="viral_video")
    srt_up = st.file_uploader("Optional: subtitles (.srt)", ["srt"], key="viral_srt")
    music_up = st.file_uploader("Optional: music track (mp3/m4a)", ["mp3","m4a"], key="viral_music")
    hook_text = st.text_input("Hook overlay (first 2s)", value=(st.session_state.get('current_card',{}).get('Lore Hook','') if 'current_card' in st.session_state else ""))
    aspects = st.multiselect("Output formats", ["9:16","16:9","4:5"], default=["9:16","16:9"]) 
    run = st.button("Run Viral Pipeline", type="primary")
    if run:
        if not vfile:
            st.error("Please upload a video file.")
        else:
            try:
                srt_text = srt_up.read().decode("utf-8", errors="ignore") if srt_up else None
                zip_bytes, info = build_viral_package(vfile, srt_text, music_up, hook_text, aspects)
                st.success("Pipeline complete.")
                st.download_button("Download Viral Bundle (ZIP)", zip_bytes, file_name="viral_bundle.zip", mime="application/zip", type="primary")
                st.json(info)
            except Exception as e:
                st.error(f"Viral pipeline failed: {e}")

with fan_tab:
    st.subheader("Fan Battle Mode (In‑App Voting)")
    # Locate a schedule
    sched = None
    for key in ["result","schedule_df","last_schedule"]:
        if key in st.session_state and isinstance(st.session_state[key], pd.DataFrame):
            sched = st.session_state[key]
            break
    if sched is None or len(sched) == 0:
        st.info("Generate a schedule in the Schedule tab or Auto‑Publish to enable Fan Mode.")
    else:
        day_sel = st.selectbox("Select Day to Vote", list(sched["Day"]), index=max(0, len(sched)-1))
        row = sched[sched["Day"] == day_sel].iloc[0]
        a_name, b_name = [s.strip() for s in str(row["Matchup"]).split("vs")] if "vs" in str(row["Matchup"]) else ("Romans","Greeks")
        choice = st.radio("Vote the winner", [a_name, b_name], horizontal=True)
        if st.button("Submit Vote"):
            votes = st.session_state.get('fan_votes', {})
            votes[str(day_sel)] = choice
            st.session_state.fan_votes = votes
            st.success(f"Recorded vote: {choice}")

        st.markdown("---")
        st.caption("Promote the voted winner into a new Day (ladder mode)")
        if st.button("Append Next Day From Winner", type="primary"):
            try:
                winner = st.session_state.get('fan_votes', {}).get(str(day_sel), a_name)
                # pick a challenger different from winner
                pool = [k for k in KB.keys() if k != winner]
                challenger = random.choice(pool) if pool else b_name
                a, b = KB[winner], KB[challenger]
                cfg = st.session_state.current_settings if 'current_settings' in st.session_state else get_preset_settings("Balanced")
                style_mode = st.session_state.get('style_mode','Default')
                style_pack_effective = cfg["style_pack"] if style_mode == 'Default' else ('Randomized' if style_mode == 'Randomized' else 'Rotate')
                idx_new = int(len(sched))
                seed_base = st.session_state.get('seed_base', 12345)
                new_row = build_single(a,b, seed_base, idx_new, style_pack_effective, cfg["scenario"], cfg["weather"], cfg["weights"], cfg["cmd_a"], cfg["cmd_b"], cfg["naval_mode"]) 
                st.session_state['last_schedule'] = pd.concat([sched, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"Appended Day {idx_new+1}: {winner} vs {challenger}")
            except Exception as e:
                st.error(f"Failed to append: {e}")

with analytics_tab:
    st.subheader("Analytics: Hooks, Styles, Engagement")
    st.caption("Import an engagement CSV and join with your schedule to see what works.")
    eng = st.file_uploader("Engagement CSV (columns: Day, Likes, Comments, Views optional)", ["csv"], key="eng_csv")
    sched_src = st.file_uploader("Optional: Battles CSV (to join)", ["csv"], key="sched_csv")
    df_sched = None
    if sched_src is not None:
        try:
            df_sched = pd.read_csv(sched_src)
        except Exception as e:
            st.error(f"Failed to read battles CSV: {e}")
    elif 'last_schedule' in st.session_state and isinstance(st.session_state['last_schedule'], pd.DataFrame):
        df_sched = st.session_state['last_schedule']
    elif 'result' in st.session_state and isinstance(st.session_state['result'], pd.DataFrame):
        df_sched = st.session_state['result']

    if eng is not None and df_sched is not None:
        try:
            df_eng = pd.read_csv(eng)
            # Column mapping
            cols = list(df_eng.columns)
            c_day = st.selectbox("Map: Day column", cols, index=0)
            c_likes = st.selectbox("Map: Likes column", cols, index=min(1,len(cols)-1))
            c_comments = st.selectbox("Map: Comments column", cols, index=min(2,len(cols)-1))
            c_views = st.selectbox("Map: Views column (optional)", ["<none>"]+cols, index=0)
            df = df_eng.rename(columns={c_day:"Day", c_likes:"Likes", c_comments:"Comments"})
            if c_views != "<none>":
                df = df.rename(columns={c_views:"Views"})
            df = df.merge(df_sched, on="Day", how="left")
            metric = st.selectbox("Engagement metric", ["Likes+Comments","(Likes+Comments)/Views"], index=0)
            if metric == "Likes+Comments":
                df['Engagement'] = df['Likes'].fillna(0) + df['Comments'].fillna(0)
            else:
                denom = df['Views'].replace({0:None}).fillna(1)
                df['Engagement'] = (df['Likes'].fillna(0) + df['Comments'].fillna(0)) / denom
            # Heatmap Tone x Style
            tone_col = 'Tone' if 'Tone' in df.columns else 'Analysis'
            style_col = 'Style Used' if 'Style Used' in df.columns else 'Style'
            pivot = df.groupby([tone_col, style_col])['Engagement'].mean().reset_index().rename(columns={tone_col:'Tone', style_col:'Style'})
            st.dataframe(pivot.sort_values('Engagement', ascending=False).head(20), use_container_width=True)
            chart = alt.Chart(pivot).mark_rect().encode(x='Style:N', y='Tone:N', color=alt.Color('Engagement:Q', scale=alt.Scale(scheme='plasma'))).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        except Exception as e:
            st.error(f"Analytics failed: {e}")
    else:
        st.info("Upload an engagement CSV and ensure a schedule is available to join.")

    st.divider()
    st.markdown("**Presets (JSON)**")
    pr_cur = _load_json(USER_PRESETS_PATH, default=USER_PRESETS or {})
    pr_text = st.text_area("user_presets.json", value=json.dumps(pr_cur, indent=2, ensure_ascii=False), height=200)
    c_pr1, c_pr2 = st.columns([1,1])
    if c_pr1.button("Save user_presets.json"):
        try:
            data = json.loads(pr_text)
            _save_json(USER_PRESETS_PATH, data)
            if isinstance(data, dict):
                PRESETS.update({k: v for k, v in data.items() if isinstance(v, dict)})
            st.success("Saved user_presets.json")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
    if c_pr2.button("Reset user_presets.json"):
        try:
            _save_json(USER_PRESETS_PATH, {})
            st.info("Cleared user_presets.json")
            st.experimental_rerun()
        except Exception as e:
            st.error(f"Failed to reset: {e}")

with st.sidebar:
    st.subheader("⚙️ Quick Setup")
    
    # Preset Selection
    st.markdown("**🎯 Battle Presets**")
    col1, col2, col3 = st.columns(3)
    
    # Initialize session state for settings
    if 'current_settings' not in st.session_state:
        st.session_state.current_settings = get_preset_settings("Balanced")
    
    with col1:
        if st.button("🎯\nBalanced", help="Realistic historical battles", use_container_width=True):
            st.session_state.current_settings = get_preset_settings("Balanced")
            st.rerun()
    with col2:
        if st.button("📱\nTikTok Viral", help="Maximum chaos and spectacle", use_container_width=True):
            st.session_state.current_settings = get_preset_settings("TikTok Viral")
            st.rerun()
    with col3:
        if st.button("📜\nHistorian", help="Accurate documentary style", use_container_width=True):
            st.session_state.current_settings = get_preset_settings("Historian")
            st.rerun()
    
    st.divider()
    
    # Global Settings (always visible)
    seed_base = st.number_input("🎲 Seed base", min_value=0, max_value=1_000_000, value=12345)
    
    # Current preset info
    current_preset = "Custom"
    for preset_name, preset_data in [("Balanced", get_preset_settings("Balanced")), ("TikTok Viral", get_preset_settings("TikTok Viral")), ("Historian", get_preset_settings("Historian"))]:
        if st.session_state.current_settings == preset_data:
            current_preset = preset_name
            break
    
    st.info(f"🎨 Current preset: **{current_preset}**")
    
    # Advanced Settings in Accordion
    with st.expander("🔧 Advanced Settings", expanded=False):
        style_pack = st.selectbox("Style pack", list(STYLE_PACKS.keys()), 
                                 index=list(STYLE_PACKS.keys()).index(st.session_state.current_settings["style_pack"]))
        scenario_key = st.selectbox("Scenario", list(SCENARIOS.keys()), 
                                   index=list(SCENARIOS.keys()).index(st.session_state.current_settings["scenario"]))
        weather_key = st.selectbox("Weather", list(WEATHER.keys()), 
                                  index=list(WEATHER.keys()).index(st.session_state.current_settings["weather"]))
        naval_mode = st.toggle("Naval mode", value=st.session_state.current_settings["naval_mode"])
        
        st.markdown("**Balance Weights**")
        
        # Quick weight controls
        wcol1, wcol2, wcol3 = st.columns(3)
        with wcol1:
            if st.button("🎯 Reset", help="Reset to balanced weights"):
                st.session_state.current_settings["weights"] = get_balanced_weights()
                st.rerun()
        with wcol2:
            if st.button("🎲 Random", help="Randomize all weights"):
                st.session_state.current_settings["weights"] = get_randomized_weights()
                st.rerun()
        with wcol3:
            if st.button("⚖️ Auto", help="Auto-balance for current matchup"):
                a_name = st.session_state.get('faction_a_name', 'Romans')
                b_name = st.session_state.get('faction_b_name', 'Greeks')
                a, b = KB.get(a_name, KB['Romans']), KB.get(b_name, KB['Greeks'])
                st.session_state.current_settings["weights"] = get_auto_balanced_weights(a, b, scenario_key, naval_mode)
                st.rerun()
        
        # Weight sliders
        weights = {}
        for stat in ['discipline', 'infantry', 'armor', 'logistics', 'ranged', 'cavalry', 'siege', 'naval']:
            weights[stat] = st.slider(stat.title(), 0.1, 2.0, 
                                    st.session_state.current_settings["weights"][stat], 
                                    key=f'{stat}_slider')
        
        st.session_state.current_settings["weights"] = weights
        
        st.markdown("**Commander Traits**")
        cmd_a = st.selectbox("Commander A", list(COMMANDERS.keys()), 
                            index=list(COMMANDERS.keys()).index(st.session_state.current_settings["cmd_a"]))
        cmd_b = st.selectbox("Commander B", list(COMMANDERS.keys()), 
                            index=list(COMMANDERS.keys()).index(st.session_state.current_settings["cmd_b"]))
        
        st.session_state.current_settings["cmd_a"] = cmd_a
        st.session_state.current_settings["cmd_b"] = cmd_b
    
    # UI polish controls
    st.markdown("**Content Controls**")
    pov_mode_sel = st.selectbox("POV Mode", ["Mixed","Soldier","Commander","Bard","None"], index=0)
    st.session_state.pov_mode = pov_mode_sel.lower()
    st.session_state.alt_timeline = st.toggle("Alt-Timeline Snippet", value=True)
    style_mode_sel = st.selectbox("Style Mode", ["Default","Randomized","Rotate"], index=0)
    st.session_state.style_mode = style_mode_sel

    st.markdown("**Overlay Controls**")
    st.session_state.overlay_theme = st.selectbox("Overlay Theme", ["Dark","Light","Gradient"], index=0)
    st.session_state.overlay_pos = st.selectbox("Overlay Position", ["Top","Middle","Bottom"], index=0)
    st.session_state.overlay_aspects = st.multiselect("Overlay Aspects", ["9:16","16:9"], default=["9:16"])    
    st.session_state.overlay_font_size = st.slider("Overlay Font Size", 36, 96, 64, 2)
    st.session_state.overlay_shadow = st.slider("Overlay Shadow Strength", 0, 255, 160, 5)
    st.session_state.overlay_wrap = st.slider("Overlay Line Width", 12, 28, 18, 1)

    # Update current settings
    st.session_state.current_settings["style_pack"] = style_pack
    st.session_state.current_settings["scenario"] = scenario_key
    st.session_state.current_settings["weather"] = weather_key
    st.session_state.current_settings["naval_mode"] = naval_mode
    
    # Extract values for use in main app
    weights = st.session_state.current_settings["weights"]
    cmd_a = st.session_state.current_settings["cmd_a"]
    cmd_b = st.session_state.current_settings["cmd_b"]

with single_tab:
    st.subheader("⚔️ Generate Single Battle")
    
    # Faction Selection with Search
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🏰 Faction A**")
        search_a = st.text_input("🔍 Search Faction A", placeholder="Type to search (e.g. Han, Roman, Samurai)...")
        faction_options_a = search_factions(search_a)
        if faction_options_a:
            a_name = st.selectbox("Select Faction A", faction_options_a, label_visibility="collapsed", key='faction_a_select')
        else:
            st.error("No factions found")
            a_name = "Romans"
    
    with col2:
        st.markdown("**🛡️ Faction B**")
        search_b = st.text_input("🔍 Search Faction B", placeholder="Type to search (e.g. Tang, Greek, Viking)...")
        faction_options_b = search_factions(search_b)
        if faction_options_b:
            b_name = st.selectbox("Select Faction B", faction_options_b, label_visibility="collapsed", key='faction_b_select')
        else:
            st.error("No factions found")
            b_name = "Greeks"
    
    # Store faction names in session state for auto-balance feature
    st.session_state.faction_a_name = a_name
    st.session_state.faction_b_name = b_name
    
    # Generate Buttons
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("⚔️ **GENERATE BATTLE**", type="secondary", use_container_width=True):
            with st.spinner("Generating epic battle..."):
                a, b = KB[a_name], KB[b_name]
                style_mode = st.session_state.get('style_mode','Default')
                style_pack_effective = style_pack if style_mode == 'Default' else ('Randomized' if style_mode == 'Randomized' else 'Rotate')
                card = build_single(a,b, seed_base, 0, style_pack_effective, scenario_key, weather_key, weights, cmd_a, cmd_b, naval_mode)
                st.session_state['current_card'] = card
    
    with col2:
        if st.button("🚀 **ONE-CLICK ALL**", type="primary", use_container_width=True, help="Generate + Auto-approve + Package for download"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("⚔️ Generating battle...")
                progress_bar.progress(25)
                
                # Generate battle
                a, b = KB[a_name], KB[b_name]
                card = build_single(a,b, seed_base, 0, style_pack, scenario_key, weather_key, weights, cmd_a, cmd_b, naval_mode)
                st.session_state['current_card'] = card
                
                status_text.text("✅ Auto-approving...")
                progress_bar.progress(50)
                
                # Auto-approve and add to buffer
                if "buffer" not in st.session_state: 
                    st.session_state["buffer"] = []
                
                battle_data = {k: card[k] for k in [
                    "Matchup","MidJourney 16:9","MidJourney 9:16","Context","Who Won?","Why They Won","Caption","Seed"]}
                st.session_state["buffer"].append(battle_data)
                
                status_text.text("📦 Packaging files...")
                progress_bar.progress(75)
                
                # Create instant download package
                buf_df = pd.DataFrame(st.session_state["buffer"])
                
                # Create comprehensive package
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Add CSV and JSON exports
                    zf.writestr("battles.csv", buf_df.to_csv(index=False))
                    zf.writestr("battles.json", json.dumps(st.session_state["buffer"], indent=2))
                    
                    # Add prompt sheet for MidJourney
                    prompt_rows = []
                    for i, battle in enumerate(st.session_state["buffer"]):
                        prompt_rows.append({"Battle": i+1, "Matchup": battle["Matchup"], "Aspect": "16:9", "Prompt": battle["MidJourney 16:9"]})
                        prompt_rows.append({"Battle": i+1, "Matchup": battle["Matchup"], "Aspect": "9:16", "Prompt": battle["MidJourney 9:16"]})
                    prompt_df = pd.DataFrame(prompt_rows)
                    zf.writestr("midjourney_prompts.csv", prompt_df.to_csv(index=False))
                    
                    # Add individual markdown files
                    for i, battle in enumerate(st.session_state["buffer"]):
                        slug = battle["Matchup"].lower().replace(" ", "-").replace("vs", "vs")
                        md = f"""# {battle['Matchup']}
Seed: {battle['Seed']}

## MidJourney Prompts

### Desktop/YouTube (16:9)
```
{battle['MidJourney 16:9']}
```

### Mobile/TikTok (9:16)
```
{battle['MidJourney 9:16']}
```

## Battle Content

**Context**: {battle['Context']}

**Winner**: {battle['Who Won?']}

**Why They Won**: {battle['Why They Won']}

**Social Media Caption**: {battle['Caption']}
"""
                        zf.writestr(f"battles/{slug}.md", md)
                
                progress_bar.progress(100)
                status_text.text("🎉 ONE-CLICK COMPLETE!")
                
                # Success metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⚔️ Generated", "1 Battle")
                with col2:
                    st.metric("📝 Buffer", len(st.session_state["buffer"]))
                with col3:
                    st.metric("📦 Files", "Ready")
                
                # Instant download
                st.download_button(
                    "🚀 **INSTANT DOWNLOAD PACKAGE**", 
                    buf.getvalue(), 
                    file_name=f"one-click-battle-{card['Matchup'].lower().replace(' ', '-')}.zip", 
                    mime="application/zip", 
                    type="primary", 
                    use_container_width=True
                )
                
                st.balloons()
                
            except Exception as e:
                st.error(f"🚨 One-click failed: {str(e)}")
                status_text.text("❌ One-click failed")
                progress_bar.progress(0)
    
    # Display results if available
    if 'current_card' in st.session_state:
        card = st.session_state['current_card']
        
        # Preview Cards Layout
        st.markdown("---")
        st.markdown(f"### 🏆 {card['Matchup']} Battle Results")
        
        # Side-by-side preview cards
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📱 TikTok/Mobile (9:16)**")
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <div style="color: white; font-weight: bold; margin-bottom: 8px;">PROMPT:</div>
                    <div style="color: #f0f0f0; font-size: 0.9em; font-family: monospace; 
                               background: rgba(0,0,0,0.3); padding: 8px; border-radius: 5px;">
                        {}
                    </div>
                </div>
                """.format(card["MidJourney 9:16"][:200] + "..." if len(card["MidJourney 9:16"]) > 200 else card["MidJourney 9:16"]), unsafe_allow_html=True)
            
            with st.expander("Full 9:16 Prompt"):
                st.code(card["MidJourney 9:16"], language="text")
        
        with col2:
            st.markdown("**📺 Desktop/YouTube (16:9)**")
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                           padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <div style="color: white; font-weight: bold; margin-bottom: 8px;">PROMPT:</div>
                    <div style="color: #f0f0f0; font-size: 0.9em; font-family: monospace; 
                               background: rgba(0,0,0,0.3); padding: 8px; border-radius: 5px;">
                        {}
                    </div>
                </div>
                """.format(card["MidJourney 16:9"][:200] + "..." if len(card["MidJourney 16:9"]) > 200 else card["MidJourney 16:9"]), unsafe_allow_html=True)
            
            with st.expander("Full 16:9 Prompt"):
                st.code(card["MidJourney 16:9"], language="text")
        
        # Content card
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                   padding: 20px; border-radius: 15px; margin: 20px 0;">
            <div style="color: white;">
                <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 15px;">📖 BATTLE STORY</div>
                <div style="margin-bottom: 10px;"><strong>Context:</strong> {}</div>
                <div style="margin-bottom: 10px;"><strong>🏆 Winner:</strong> {}</div>
                <div style="margin-bottom: 10px;"><strong>🎯 Why:</strong> {}</div>
                <div style="margin-bottom: 10px;"><strong>📝 Caption:</strong> {}</div>
                <div style="font-size: 0.8em; opacity: 0.8;">🎲 Seed: {}</div>
            </div>
        </div>
        """.format(card['Context'], card['Who Won?'], card['Why They Won'], card['Caption'], card['Seed']), unsafe_allow_html=True)
        
        # Quality Control & Export
        with st.expander("✅ Quality Check & Export", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                ok1 = st.checkbox("No anachronism in prompt text")
                ok2 = st.checkbox("Rationale matches visual emphasis")
            with col2:
                ok3 = st.checkbox("Clear silhouettes / readable action")
                ok4 = st.checkbox("Viral potential maximized")
            
            if "buffer" not in st.session_state: st.session_state["buffer"] = []
            
            if st.button("✅ Approve and add to CSV buffer", use_container_width=True) and all([ok1,ok2,ok3,ok4]):
                st.session_state["buffer"].append({k: card[k] for k in [
                    "Matchup","MidJourney 16:9","MidJourney 9:16","Context","Who Won?","Why They Won","Caption","Seed"]})
                st.success("✨ Added to buffer!")
        
        # Exports section
        with st.expander("📦 Exports", expanded=bool(st.session_state.get("buffer"))):
            if st.session_state.get("buffer"):
                buf_df = pd.DataFrame(st.session_state["buffer"])
                st.info(f"📋 {len(st.session_state['buffer'])} battles in buffer")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📊 Download CSV buffer", buf_df.to_csv(index=False).encode(), "battles_buffer.csv", "text/csv", use_container_width=True)
                with col2:
                    if st.button("🗑️ Clear buffer", use_container_width=True):
                        st.session_state["buffer"] = []
                        st.rerun()
            else:
                st.info("📎 No approved battles in buffer yet")

with schedule_tab:
    st.subheader("Build Full Schedule")
    up = st.file_uploader("Roadmap CSV/XLSX (Day, Matchup / Theme, optional prompts)", ["csv","xlsx"])
    days = st.number_input("Days", min_value=1, max_value=180, value=90)
    seed_sched = st.number_input("Schedule seed", min_value=0, max_value=1_000_000, value=4242)
    
    # One-Click Automation Feature
    st.divider()
    st.markdown("### 🚀 OVERDRIVE MODE")
    st.markdown("💥 Generate everything instantly and package for social media!")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        auto_days = st.number_input("📅 Days to generate", min_value=1, max_value=180, value=30, key="auto_days")
        st.caption("Generates complete battles with prompts, context, winners, and exports")
    with col2:
        if st.button("🚀 **OVERDRIVE GENERATE**", type="primary", use_container_width=True):
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("📄 Loading base template...")
                progress_bar.progress(10)
                
                # Use demo plan if no upload
                base = (pd.read_csv(up) if (up and up.name.lower().endswith(".csv")) else pd.read_excel(up) if up else demo_plan_df())
                
                status_text.text(f"⚔️ Generating {auto_days} epic battles...")
                progress_bar.progress(20)
                
                style_mode = st.session_state.get('style_mode','Default') if hasattr(st,'session_state') else 'Default'
                style_pack_effective = style_pack if style_mode == 'Default' else ('Randomized' if style_mode == 'Randomized' else 'Rotate')
                result = build_schedule(base, int(auto_days), int(seed_sched), style_pack_effective, scenario_key, weather_key, weights, cmd_a, cmd_b, naval_mode)
                progress_bar.progress(60)
                
                status_text.text("🎨 Creating prompt sheets...")
                # Create prompt sheet for MidJourney
                prompt_rows = []
                for _, r in result.iterrows():
                    prompt_rows.append({"Day": r['Day'], "Aspect": "16:9", "Prompt": r['MidJourney 16:9']})
                    prompt_rows.append({"Day": r['Day'], "Aspect": "9:16", "Prompt": r['MidJourney 9:16']})
                prompt_df = pd.DataFrame(prompt_rows)
                progress_bar.progress(75)
                
                status_text.text("📦 Packaging everything...")
                # Bundle everything in ZIP
                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("schedule.csv", result.to_csv(index=False))
                    zf.writestr("schedule.json", json.dumps(result.to_dict(orient="records"), indent=2))
                    zf.writestr("prompt_sheet.csv", prompt_df.to_csv(index=False))
                    # Captions & Voiceover
                    cap_rows = []
                    for _, rr in result.iterrows():
                        cap_rows.append({
                            "Day": rr["Day"],
                            "Matchup": rr["Matchup"],
                            "Hook": rr.get("Lore Hook",""),
                            "Tactical": rr.get("Tactical Beat",""),
                            "Fan": rr.get("Fan Prompt",""),
                            "VO": rr.get("VO Script",""),
                            "Quote": rr.get("Quote",""),
                        })
                    zf.writestr("captions_voiceover.csv", pd.DataFrame(cap_rows).to_csv(index=False))
                    # Variants
                    var_rows = []
                    for _, rr in result.iterrows():
                        var_rows.append({
                            "Day": rr["Day"], "Matchup": rr["Matchup"],
                            "Hook A": rr.get("Hook A",""), "VO A": rr.get("VO A",""),
                            "Hook B": rr.get("Hook B",""), "VO B": rr.get("VO B",""),
                            "Hook C": rr.get("Hook C",""), "VO C": rr.get("VO C",""),
                            "Alt Winner": rr.get("Alt Winner",""), "Alt VO": rr.get("Alt VO",""),
                        })
                    zf.writestr("captions_voiceover_variants.csv", pd.DataFrame(var_rows).to_csv(index=False))
                    # Polls
                    poll_rows = []
                    for _, rr in result.iterrows():
                        poll_rows.append({
                            "Day": rr["Day"], "Matchup": rr["Matchup"],
                            "Question": rr.get("Poll Q",""),
                            "Option 1": rr.get("Poll Opt 1",""),
                            "Option 2": rr.get("Poll Opt 2",""),
                            "Option 3": rr.get("Poll Opt 3",""),
                        })
                    zf.writestr("polls.csv", pd.DataFrame(poll_rows).to_csv(index=False))
                    
                    # Individual markdown cards
                    for _, r in result.iterrows():
                        slug = str(r["Day"]).lower().replace(" ", "-")
                        md = f"""# {r['Day']} - {r['Matchup']}
Seed: {r['Seed']}

**MidJourney 16:9**: {r['MidJourney 16:9']}

**MidJourney 9:16**: {r['MidJourney 9:16']}

**Context**: {r['Context']}

**Analysis**: {r.get('Analysis','')}

**Who Won?**: {r['Who Won?']}

**Why They Won**: {r['Why They Won']}

**Attacker**: {r.get('Attacker','')}

**Duration**: {r.get('Duration','')}

**Casualties**:

- {str(r['Matchup']).split(' vs ')[0]}: {r.get('Casualties A','')} total ({r.get('Casualty Rate A (%)','')}%)
- {str(r['Matchup']).split(' vs ')[1]}: {r.get('Casualties B','')} total ({r.get('Casualty Rate B (%)','')}%)

**Caption**: {r['Caption']}

**Hook**: {r.get('Lore Hook','')}

**Tactical Beat**: {r.get('Tactical Beat','')}

**Fan Prompt**: {r.get('Fan Prompt','')}

**VO Script**: {r.get('VO Script','')}

**Quote**: {r.get('Quote','')}

**Poll**: {r.get('Poll Q','')}
 - {r.get('Poll Opt 1','')}
 - {r.get('Poll Opt 2','')}
 - {r.get('Poll Opt 3','')}
"""
                        zf.writestr(f"cards/{slug}.md", md)
                
                progress_bar.progress(100)
                status_text.text("✨ OVERDRIVE COMPLETE!")
                
                # Success display
                st.balloons()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("⚔️ Battles Generated", len(result))
                with col2:
                    st.metric("🎨 Prompts Created", len(prompt_df))
                with col3:
                    st.metric("📦 Files Packaged", len(result) + 3)
                
                st.download_button("🚀 **DOWNLOAD OVERDRIVE PACKAGE**", buf.getvalue(), 
                                 file_name="overdrive_battles_package.zip", mime="application/zip", 
                                 type="primary", use_container_width=True)
                
                # Show preview with better styling
                with st.expander("👀 Preview Generated Battles", expanded=True):
                    st.dataframe(result.head(10), width='stretch')
                    if len(result) > 10:
                        st.caption(f"Showing first 10 of {len(result)} generated battles...")
                
            except Exception as e:
                st.error(f"🚨 Generation failed: {str(e)}")
                status_text.text("❌ Generation failed")
                progress_bar.progress(0)
    
    st.divider()
    st.markdown("### 🔧 Manual Generation (Advanced)")

    if st.button("Generate Schedule"):
        base = (pd.read_csv(up) if (up and up.name.lower().endswith(".csv")) else pd.read_excel(up) if up else demo_plan_df())
        style_mode = st.session_state.get('style_mode','Default') if hasattr(st,'session_state') else 'Default'
        style_pack_effective = style_pack if style_mode == 'Default' else ('Randomized' if style_mode == 'Randomized' else 'Rotate')
        result = build_schedule(base, int(days), int(seed_sched), style_pack_effective, scenario_key, weather_key, weights, cmd_a, cmd_b, naval_mode)
        st.dataframe(result, width='stretch', height=620)

        csv_bytes = result.to_csv(index=False).encode()
        st.download_button("Download CSV", csv_bytes, file_name="hypo_battles_schedule.csv", mime="text/csv")
        json_bytes = json.dumps(result.to_dict(orient="records"), indent=2).encode()
        st.download_button("Download JSON", json_bytes, file_name="hypo_battles_schedule.json", mime="application/json")

        # Create prompt sheet
        prompt_rows = []
        for _, r in result.iterrows():
            prompt_rows.append({"Day": r['Day'], "Aspect": "16:9", "Prompt": r['MidJourney 16:9']})
            prompt_rows.append({"Day": r['Day'], "Aspect": "9:16", "Prompt": r['MidJourney 9:16']})
        prompt_df = pd.DataFrame(prompt_rows)
        st.download_button("Download Prompt Sheet CSV", prompt_df.to_csv(index=False).encode(), "prompt_sheet.csv", "text/csv")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for _, r in result.iterrows():
                slug = str(r["Day"]).lower().replace(" ", "-")
                md = f"""# {r['Day']} - {r['Matchup']}
Seed: {r['Seed']}

**MidJourney 16:9**: {r['MidJourney 16:9']}

**MidJourney 9:16**: {r['MidJourney 9:16']}

**Context**: {r['Context']}

**Analysis**: {r.get('Analysis','')}

**Who Won?**: {r['Who Won?']}

**Why They Won**: {r['Why They Won']}

**Attacker**: {r.get('Attacker','')}

**Duration**: {r.get('Duration','')}

**Casualties**:

- {str(r['Matchup']).split(' vs ')[0]}: {r.get('Casualties A','')} total ({r.get('Casualty Rate A (%)','')}%)
- {str(r['Matchup']).split(' vs ')[1]}: {r.get('Casualties B','')} total ({r.get('Casualty Rate B (%)','')}%)

**Caption**: {r['Caption']}
"""
                zf.writestr(f"{slug}.md", md)
        st.download_button("Markdown cards (.zip)", buf.getvalue(), file_name="hypo_battles_cards.zip", mime="application/zip")

with tourney_tab:
    st.subheader("Tournament Simulator (Round-robin with Elo)")
    choices = st.multiselect("Select factions", sorted(KB.keys()), default=["Romans","Mongols","Samurai","Vikings","Greeks","Ottomans"])
    seed_t = st.number_input("Tournament seed", min_value=0, max_value=1_000_000, value=777)
    if st.button("Run Tournament") and len(choices) >= 3:
        table, matches = play_round_robin(choices, int(seed_t), weights, style_pack, scenario_key, weather_key, naval_mode)
        st.dataframe(table, width='stretch')
        st.dataframe(matches, width='stretch', height=300)
        st.download_button("Download Leaderboard CSV", table.to_csv(index=False).encode(), "leaderboard.csv", "text/csv")

st.toast("Pro+ features loaded.")

with publish_tab:
    st.subheader("📦 One-Click: Build Upload Bundle")
    st.caption("Creates battles.csv, battles.json, midjourney_prompts.csv, per-day Markdown cards, and an asset manifest.")
    
    # Source: if user has already generated a schedule, use it from st.session_state
    src_df = None
    for key in ["result","schedule_df","last_schedule"]:
        if key in st.session_state and isinstance(st.session_state[key], pd.DataFrame):
            src_df = st.session_state[key]
            break
    
    upload = st.file_uploader("Or upload a schedule CSV/JSON", ["csv","json"], key="auto_pub_up")
    if upload is not None:
        if upload.name.lower().endswith(".csv"):
            src_df = pd.read_csv(upload)
        else:
            src_df = pd.read_json(upload)
    
    if src_df is None:
        st.warning("⚠️ No schedule in memory. Generate in the Schedule tab or upload CSV/JSON.")
    else:
        st.info(f"📊 Found schedule with {len(src_df)} battles")
        st.dataframe(src_df.head(10), use_container_width=True, height=260)
        if len(src_df) > 10:
            st.caption(f"Showing first 10 of {len(src_df)} battles...")

        # Quick downloads (Prompts / Captions / Polls / Overlays)
        try:
            prompt_sheet = build_prompt_sheet(src_df)
            st.download_button(
                "Prompts CSV", 
                prompt_sheet.to_csv(index=False).encode(),
                file_name="midjourney_prompts.csv", 
                mime="text/csv"
            )

            cap_rows = []
            for _, rr in src_df.iterrows():
                cap_rows.append({
                    "Day": rr.get("Day",""),
                    "Matchup": rr.get("Matchup",""),
                    "Hook": rr.get("Lore Hook",""),
                    "Tactical": rr.get("Tactical Beat",""),
                    "Fan": rr.get("Fan Prompt",""),
                    "VO": rr.get("VO Script",""),
                    "Quote": rr.get("Quote",""),
                })
            st.download_button("Captions & VO CSV", pd.DataFrame(cap_rows).to_csv(index=False).encode(), "captions_voiceover.csv", "text/csv")

            poll_rows = []
            for _, rr in src_df.iterrows():
                poll_rows.append({
                    "Day": rr.get("Day",""),
                    "Matchup": rr.get("Matchup",""),
                    "Question": rr.get("Poll Q",""),
                    "Option 1": rr.get("Poll Opt 1",""),
                    "Option 2": rr.get("Poll Opt 2",""),
                    "Option 3": rr.get("Poll Opt 3",""),
                })
            st.download_button("Polls CSV", pd.DataFrame(poll_rows).to_csv(index=False).encode(), "polls.csv", "text/csv")

            aspects = st.session_state.get('overlay_aspects',["9:16"]) if hasattr(st,'session_state') else ["9:16"]
            theme = st.session_state.get('overlay_theme','Dark') if hasattr(st,'session_state') else 'Dark'
            pos = st.session_state.get('overlay_pos','Top') if hasattr(st,'session_state') else 'Top'
            fsize = st.session_state.get('overlay_font_size', 64) if hasattr(st,'session_state') else 64
            shad = st.session_state.get('overlay_shadow', 160) if hasattr(st,'session_state') else 160
            wrapw = st.session_state.get('overlay_wrap', 18) if hasattr(st,'session_state') else 18
            mem = io.BytesIO()
            with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as zf2:
                for i, r in enumerate(src_df.itertuples(index=False), start=1):
                    hook = getattr(r, "Lore Hook", "") or getattr(r, "Hook A", "") or getattr(r, "Hook", "")
                    if not hook:
                        continue
                    for asp in aspects:
                        size = TARGET_V if asp == "9:16" else TARGET_H
                        png = render_text_overlay_png(str(hook), size=size, theme=theme.lower(), position=pos.lower(), font_size=int(fsize), shadow_alpha=int(shad), wrap=int(wrapw))
                        suffix = "916" if asp == "9:16" else "169"
                        zf2.writestr(f"day{i:02d}_overlay_{suffix}.png", png)
            st.download_button("Overlays (.zip)", mem.getvalue(), file_name="overlays.zip", mime="application/zip")
        except Exception:
            pass
        
        if st.button("🔥 **MAKE THE BUNDLE**", type="primary", use_container_width=True):
            with st.spinner("Creating publishing bundle..."):
                zip_bytes = package_all(src_df)
                
            st.success("✨ Bundle ready for download!")
            
            # Main bundle download
            st.download_button(
                "📦 **Download Complete Bundle (ZIP)**", 
                zip_bytes, 
                file_name="hypothetical_battles_bundle.zip", 
                mime="application/zip",
                type="primary",
                use_container_width=True
            )
            
            # Quick access downloads  
            prompt_sheet = build_prompt_sheet(src_df)
            st.download_button(
                "📋 MidJourney Prompts CSV", 
                prompt_sheet.to_csv(index=False).encode(),
                file_name="midjourney_prompts.csv", 
                mime="text/csv"
            )

st.toast("🚀 AUTO-PUBLISH MODULE loaded.")
