from datetime import datetime
from typing import Any

import pycountry
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from members.models import Member
from ultihub.settings import ORIGINAL_EVIDENCE_LOGIN, ORIGINAL_EVIDENCE_PASSWORD

SEASON_ID = 23
ORIGINAL_EVIDENCE_URL = "https://api.evidence.czechultimate.cz/"
CLUB_MAP = {  # old ID -> new ID
    "1": 9,  # 3SB
    "2": 12,  # Atrofované Ruce
    "3": None,  # BOATEAM
    "4": 7,  # F.U.J.
    "5": 29,  # Frkot
    "6": None,  # Hot Beaches
    "7": None,  # Létající Cirkus
    "8": 11,  # PeaceEgg
    "9": 1,  # Prague Devils
    "10": 30,  # Pražská 7
    "11": None,  # Rektální vyšetření
    "12": 8,  # Terrible Monkeys
    "13": None,  # ThREeBONes
    "14": None,  # Únikový východ
    "15": None,  # Žlutá Zimnice
    "16": None,  # SPLT
    "17": None,  # Prague Lions
    "18": None,  # Outsiterz
    "19": None,  # Golden ants
    "20": 18,  # Chlupatá Žába
    "21": None,  # Discgolf
    "22": 24,  # TIOS
    "23": 4,  # Východní Blok
    "24": 19,  # Left Overs
    "25": None,  # Neza?azení
    "26": None,  # Spirit on Lemon
    "27": None,  # Flying Dogs
    "28": None,  # ČVUT
    "29": None,  # Hairy Jet
    "30": None,  # Figurky Slonů
    "31": None,  # Freestyle
    "32": None,  # LOL
    "33": None,  # Polmos
    "34": None,  # Mortherns
    "35": 31,  # Kulatá šachovnice
    "36": None,  # Falcon
    "37": None,  # Prakem zničíš
    "38": None,  # Hairy Block
    "39": None,  # 3SB-Atruc
    "40": 25,  # Trubky
    "41": None,  # W_ANT
    "42": None,  # Komba ušatá
    "43": None,  # LayD's,
    "44": None,  # PeaceEgg-Atruc
    "45": None,  # Route 88
    "46": None,  # TREE
    "47": None,  # Mosquito Attack
    "48": None,  # Ježkovy voči
    "49": 21,  # Chupacabras
    "50": None,  # Figurky Slonů + 3SB
    "51": None,  # Yellow Block
    "52": None,  # 7 Opic
    "53": None,  # Tree Monkeys
    "54": None,  # Mimolety
    "55": None,  # Přelouč
    "56": None,  # poplatek odpusten
    "57": 14,  # Dream Team Béčko
    "58": None,  # jElita
    "59": 3,  # Rainbow Banana
    "60": None,  # Frozen Angels
    "61": None,  # Velká Morava
    "62": None,  # duplicity
    "63": 32,  # U.F.O. (Ubiquitous Frisbee Ordinands)
    "64": 6,  # Kapři Ultimate
    "65": None,  # Žalymáda
    "66": 10,  # Kachny Příbram
    "67": 20,  # BUFU
    "68": None,  # Idzem Nejdzem
    "69": 15,  # Poletíme
    "70": 13,  # Duranga
    "71": 16,  # Sunset
    "72": None,  # L. D. C.
    "73": 2,  # Atletico Maják Vsetín
    "74": 28,  # Skydivers
    "75": None,  # Walkers Šumperk
    "76": None,  # Ameba
    "77": 5,  # Rakety Žižkoff
    "78": 23,  # Czech Masters
    "79": None,  # Brblava
    "80": 22,  # YOLO
    "81": 17,  # Sokol Křemže
    "82": None,  # Králíci z Klobouku
    "83": 27,  # Micropachycephalosauři
    "84": 26,  # Björn
}
TOURNAMENT_MAP = {  # old ID -> new ID
    "273": 2,  # Kvalifikace JHMČR mix - západ
    "274": 1,  # Kvalifikace JHMČR mix - východ
    "275": 4,  # Finále JHMČR mix - 1. liga
    "276": 3,  # Finále JHMČR mix - 2. liga
    "277": 6,  # Kvalifikace HMČR mix - Praha
    "278": 5,  # Kvalifikace HMČR mix - Morava a Východní Čechy
    "279": 7,  # Kvalifikace HMČR mix - Jihozápad
    "280": 11,  # HMČR mixed - 1.liga
    "281": 10,  # HMČR mixed - 2.liga
    "282": 9,  # HMČR mixed - 3. liga
    "283": 8,  # HMČR mixed - 4.liga
    "284": 13,  # Kvalifikace HMČR open - Praha
    "285": 16,  # Kvalifikace HMČR women - Praha
    "286": 15,  # Kvalifikace HMČR open - MVČ
    "287": 18,  # Kvalifikace HMČR women - MVČ
    "288": 14,  # Kvalifikace HMČR open - jihozápad
    "289": 17,  # Kvalifikace HMČR women - jihozápad
}


def _iso3_to_iso2(iso3: str) -> str | None:
    try:
        return pycountry.countries.get(alpha_3=iso3).alpha_2
    except AttributeError:
        return None


def _validate_birth_number(dob: str, rc: str) -> bool:
    if len(rc) not in [9, 10] or not rc.isdigit():
        return False

    year = int(rc[:2])
    month = int(rc[2:4])
    day = int(rc[4:6])

    # It works for years 1954-1999 and 2000-2053
    full_year = 1900 + year if year >= 54 else 2000 + year

    # Women have month + 50
    if month > 50:
        month -= 50

    try:
        dob_parsed = datetime.strptime(dob, "%Y-%m-%d")
        rc_parsed = datetime(full_year, month, day)
        if dob_parsed != rc_parsed:
            return False
    except ValueError:
        return False

    return not (len(rc) == 10 and int(rc) % 11 != 0)


class Client:
    def __init__(self) -> None:
        json = {"login": ORIGINAL_EVIDENCE_LOGIN, "password": ORIGINAL_EVIDENCE_PASSWORD}
        resp = requests.post(ORIGINAL_EVIDENCE_URL + "user/login", json=json)
        self.token = resp.json()["token"]["token"]

    def get(
        self, path: str, _filter: dict | None = None, _extend: bool = False, **params: Any
    ) -> dict:
        if _filter:
            path = path + "?" + "&".join(f"filter[{k}]={v}" for k, v in _filter.items())
        if _extend:
            path += "&extend=1"
        return requests.get(
            ORIGINAL_EVIDENCE_URL + path, json={"token": self.token, **params}
        ).json()["data"]


class Command(BaseCommand):
    def _get_birth_number(self, player: dict, birth_date: str) -> str | None:
        if player.get("personal_identification_number"):
            birth_number = player["personal_identification_number"].replace("/", "")
            if _validate_birth_number(birth_date, birth_number):
                return birth_number
        return None

    def _get_nationality(self, player: dict, valid_birth_number: str | None) -> str | None:
        if player.get("nationality"):
            return _iso3_to_iso2(player["nationality"]["iso_code"])
        elif valid_birth_number:
            return "CZ"
        else:
            return None

    def import_member(self, client: Client, player: dict) -> None:
        player_id = player["id"]
        player_at_team = client.get("list/player_at_team", {"player_id": player_id}, _extend=True)[
            0
        ]

        club_id = CLUB_MAP[player_at_team["team"]["id"]]
        birth_date = player["birth_date"][:10]
        birth_number = self._get_birth_number(player, birth_date)
        nationality = self._get_nationality(player, birth_number)

        warnings = []
        if not club_id:  # KO
            warnings.append(f"Missing club {club_id}")
        if not birth_number:  # OK
            warnings.append("Invalid or missing birth number")
        if not nationality:  # OK
            warnings.append("Missing nationality")
        if nationality != "CZ":  # OK
            address = client.get(f"player/{player_id}/address")
            warnings.append(f"Address check: {address}")
        if warnings:
            self.stdout.write(
                f"{player_id} {player['first_name']} {player['last_name']}:"
                f" {', '.join(warnings)} {player}"
            )

        created_at = timezone.make_aware(
            datetime.strptime(player["created_at"], "%Y-%m-%d %H:%M:%S"),
            timezone.get_current_timezone(),
        )

        try:
            with transaction.atomic():
                Member.objects.get_or_create(
                    original_id=player_id,
                    club_id=club_id,
                    first_name=player["first_name"],
                    last_name=player["last_name"],
                    birth_date=birth_date,
                    sex=1 if player["sex"] == "female" else 2,
                    citizenship=nationality,
                    birth_number=birth_number if nationality == "CZ" else "",
                )
                Member.objects.filter(id=player_id).update(created_at=created_at)
        except Exception as ex:
            self.stdout.write(f"Error: {ex} {player}")
            return None

    def handle(self, *args: Any, **kwargs: Any) -> None:
        client = Client()
        self.stdout.write(f"Logged with {client.token}")

        teams = {}
        for team in client.get("/list/team"):
            teams[team["id"]] = team["name"]

        for tournament in client.get("/list/tournament", {"season_id": SEASON_ID}):
            tournament_id = tournament["id"]
            if tournament_id != "284":
                continue

            self.stdout.write(
                f"================ Tournament {tournament_id} {tournament['name']} ================"
            )

            tournament_extra = client.get(
                "/list/tournament_belongs_to_league_and_division",
                {"tournament_id": tournament_id},
            )
            assert len(tournament_extra) == 1

            for roster in client.get(
                "list/roster",
                {"tournament_belongs_to_league_and_division_id": tournament_extra[0]["id"]},
            ):
                self.stdout.write(
                    f'-------------- {teams[roster["team_id"]]} {roster["name"]} --------------'
                )

                for player in client.get(
                    "list/player_at_roster",
                    {"roster_id": roster["id"]},
                    _extend=True,
                ):
                    self.import_member(client, player["player"])
