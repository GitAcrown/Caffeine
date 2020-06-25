import os
import random
import time
import math

import discord

from .utils.dataIO import fileIO, dataIO
import math
import os
import random
import time

import discord

from .utils.dataIO import fileIO, dataIO

ETALON_DEFAULT = 200
STAMINA_DEFAULT = 50

ITEMS = {}


class SilkError(Exception):
    pass

class ForbiddenAction(SilkError):
    pass

class UniqueDuplicata(SilkError):
    pass

class ItemUnknown(SilkError):
    pass


class SilkItem: # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def __init__(self, cog, item_id: str):
        self.cog = cog
        self.id = item_id
        self.raw = ITEMS[self.id]

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.raw["name"]

    @property
    def type(self):
        return type(self).__name__

    @property
    def properties(self):
        return self.raw["prts"]

    @property
    def value(self):
        return self.raw["value"] if "value" in self.raw else None

    @property
    def image(self):
        return self.raw["img"] if "img" in self.raw else ""


class SilkEquip(SilkItem):
    def __init__(self, cog, item_id):
        super().__init__(cog, item_id)
        self.specs = self.raw["specs"]

    @property
    def desc(self):
        return self.raw["desc"]


class SilkConso(SilkItem):
    def __init__(self, cog, item_id):
        super().__init__(cog, item_id)
        self.effects = self.raw["effects"]

    @property
    def desc(self):
        return self.raw["desc"]


class SilkUser: # @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    def __init__(self, cog, user: discord.Member):
        self.cog = cog
        self.user = user
        self.raw = self.cog.get_server(user.server)["USERS"][user.id]

    def __str__(self):
        return self.user.mention

    def __int__(self):
        return self.user.id

    @property
    def xp(self):
        return self.raw["xp"]

    @xp.setter
    def xp(self, value: int):
        self.raw["xp"] = value

    @property
    def level(self):
        return self.cog.xp_to_level(self.xp)

    @property
    def stamina(self):
        return self.raw["stamina"]

    @stamina.setter
    def stamina(self, value: int):
        if value >= 0:
            self.raw["stamina"] = value
        else:
            raise ForbiddenAction("Impossible d'avoir une valeur négative pour 'SilkUser.stamina'")

    @property
    def max_stamina(self):
        return self._get_max_stamina()

    def _get_max_stamina(self):
        return STAMINA_DEFAULT + (self.level - 1) * 2

    @property
    def inventory(self):
        return self.raw["inventory"]

    @property
    def equipment(self):
        return self.raw["equipment"]

    @property
    def status(self):
        return self.raw["status"]

    @property
    def cache(self):
        return self.raw["cache"]

class SilkAPI: # ================================================================
    """API de Silkroad"""
    def __init__(self, bot, path):
        self.bot = bot
        self.data = dataIO.load_json(path)
        self.session = {}
        self.autosave = 0

    def save(self, force: bool = False):
        if (time.time() - self.autosave) > 10 or force:
            fileIO("data/silkroad/data.json", "save", self.data)
            self.autosave = time.time()


    def get_server(self, server):
        if server.id not in self.data:
            self.data[server.id] = {"USERS": {},
                                    "SYS": {"channels": [],
                                            "event_etalon": ETALON_DEFAULT,
                                            "event_marge": 20,
                                            "event_cooldown": 300}}
            self.save(True)
        return self.data[server.id]


    def get_session(self, server):
        if server.id not in self.session:
            self.session[server.id] = {"msg_nb": 0,
                                       "event_last": 0,
                                       "event_trigger": 0,
                                       "event_pending": False,

                                       "_events": {},
                                       "_users": {}}
        return self.session[server.id]


    def random_trigger_count(self, server):
        sys = self.get_server(server)["SYS"]
        if sys:
            prc = sys["event_marge"] / 100
            scount = sys["event_etalon"]
            delta = round(scount * prc)
            return random.randint(scount - delta, scount + delta)
        return ETALON_DEFAULT


    def get_user(self, user: discord.Member):
        serv = self.get_server(user.server)["USERS"]
        if user.id not in serv:
            serv[user.id] = {"xp": 0,
                             "stamina": STAMINA_DEFAULT,
                             "inventory": {},
                             "equipment": {},
                             "status": {},
                             "cache": {}}
            self.save()
        return SilkUser(self, user)

    def level_to_xp(self, lvl: int):
        return 25 * lvl * (lvl + 1)

    def xp_to_level(self, xp: int):
        return int((math.sqrt(625+100 * xp) - 25)/ 50)

    def level_progress(self, xp: int, k: int = 1):
        """Donne l'XP restant a acquérir pour arriver au level n+k"""
        return self.level_to_xp(self.xp_to_level(xp) + k) - xp


    def enough_stamina(self, user: discord.Member, cost: int) -> bool:
        """Vérifie si le joueur possède assez d'énergie pour l'action"""
        player = self.get_user(user)
        return player.stamina >= cost

    def charge_stamina(self, user: discord.Member, qte: int):
        """Ajoute de l'énergie au joueur"""
        player = self.get_user(user)
        if player.stamina + qte > player.max_stamina:
            qte = player.max_stamina - player.stamina
        player.stamina += qte
        self.save()

    def boost_stamina(self, user: discord.Member, qte: int):
        """Ajoute l'énergie en ignorant la limite maximale"""
        player = self.get_user(user)
        player.stamina += qte
        self.save()

    def consume_stamina(self, user: discord.Member, qte: int):
        """Retire de l'énergie au joueur"""
        player = self.get_user(user)
        if player.stamina - qte >= 0:
            qte = player.stamina
        player.stamina -= qte
        self.save()


    def get_item(self, item_id: str):
        if item_id in ITEMS:
            if "specs" in ITEMS[item_id]:
                return SilkEquip(self, item_id)
            elif "effect" in ITEMS[item_id]:
                return SilkConso(self, item_id)
            else:
                return SilkItem(self, item_id)
        raise ItemUnknown("Item {} inconnu".format(item_id))

    def get_all_items(self, *filter):
        """Renvoie tous les items. Peuvent être filtrés si filtre(s) spécifié(s) (cumulatifs)"""
        if filter:
            return [self.get_item(i) for i in ITEMS if [p for p in ITEMS[i]["prts"] if p in filter]]
        else:
            return [self.get_item(i) for i in ITEMS]

    def add_item(self, user: discord.Member, item: SilkItem, qte = 1):
        """Ajoute un item à l'inventaire d'un membre"""
        player = self.get_user(user)
        if item.type == "SilkEquip":
            qte = 1
            if item.id in player.inventory:
                raise UniqueDuplicata("Impossible d'ajouter un item unique s'il y en a déjà un dans l'inventaire")

        if item.id not in player.inventory:
            player.inventory[item.id] = qte
        else:
            player.inventory[item.id] += qte
        self.save()

    def remove_item(self, user: discord.Member, item: SilkItem, qte = 1):
        """Retire un item à l'inventaire d'un membre"""
        player = self.get_user(user)
        if item.id in player.inventory:
            if item.type == "SilkEquip":
                qte = 1
                if item.id in player.equipment:
                    self.detach_equipment(user, item)

            if qte >= player.inventory[item.id]:
                del player.inventory[item.id]
            else:
                player.inventory[item.id] -= qte
            self.save()
        else:
            raise ForbiddenAction("Impossible de retirer un item non possédé")


    def attach_equipment(self, user: discord.Member, item: SilkEquip):
        """Equipe un item au membre"""
        player = self.get_user(user)
        if item.id in player.inventory:
            if item.id not in player.equipment:
                saved = self.load_item_specs(user, item)
                if saved:
                    player.equipment[item.id] = saved
                else:
                    player.equipment[item.id] = item.specs
                self.save()
        else:
            raise ForbiddenAction("L'item qui veut être équipé n'est pas dans l'inventaire cible")

    def detach_equipment(self, user: discord.Member, item: SilkEquip):
        """Désequipe un item au membre"""
        player = self.get_user(user)
        if item.id in player.inventory:
            if item.id in player.equipment:
                self.save_item_specs(user, item)
                del player.equipment[item.id]
                self.save()
        else:
            raise ForbiddenAction("L'item qui veut être déséquippé n'est pas dans l'inventaire cible")

    def save_item_specs(self, user: discord.Member, item: SilkEquip):
        player = self.get_user(user)
        if "backup_specs" not in player.cache:
            player.cache["backup_specs"] = {}

        if item.id in player.inventory:
            if item.id in player.equipment:
                if player.equipment[item.id] != item.specs:
                    player.cache["backup_specs"][item.id] = player.equipment[item.id]
                    self.save()

    def load_item_specs(self, user: discord.Member, item: SilkEquip):
        player = self.get_user(user)
        if "backup_specs" in player.cache:
            if item.id in player.cache["backup_specs"]:
                return player.cache["backup_specs"][item.id]
        return None


    def apply_effects(self, user: discord.Member, item: SilkConso):
        player = self.get_user(user)
        log = []
        for name, delay in item.effects:
            if name in player.status:
                player.status[name] += delay
            else:
                player.status[name] = time.time() + delay
            if delay == 0:
                player.status[name] = 0
            if player.status[name] <= time.time():
                del player.status[name]
            if name in player.status:
                log.append(name)
        self.save()
        return log

    def remove_effects(self, user: discord.Member, item: SilkConso):
        player = self.get_user(user)
        player = self.get_user(user)
        log = []
        for name, delay in item.effects:
            if name in player.status:
                del player.status[name]
                log.append(name)
        self.save()
        return log

class Silkroad: # ---------------------------------------------------------------
    """Minez, combattez, devenez riche !"""

    def __init__(self, bot):
        self.bot = bot
        self.api = SilkAPI(bot, "data/silkroad/data.json")
        # Pour importer l'API : self.bot.get_cog("Silkroad").api


    def __unload(self):
        self.api.save(True)
        print("Silkroad - Sauvegarde effectuée")


def check_folders():
    if not os.path.exists("data/silkroad"):
        print("Creation du dossier Silkroad ...")
        os.makedirs("data/silkroad")


def check_files():
    if not os.path.isfile("data/silkroad/data.json"):
        print("Ouverture de silkroad/data.json ...")
        fileIO("data/silkroad/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Silkroad(bot)
    bot.add_listener(n.get_message_post, 'on_message')
    bot.add_listener(n.get_reaction_add, "on_reaction_add")
    bot.add_cog(n)
