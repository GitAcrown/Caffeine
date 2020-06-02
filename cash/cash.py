import asyncio
import operator
import os
import random
import string
import time
from collections import namedtuple
from copy import deepcopy
from datetime import datetime, timedelta

import discord
from __main__ import send_cmd_help
from discord.ext import commands

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class CashAccount:
    def __init__(self, cog, user: discord.Member):
        self.cog = cog
        self.user = user
        self.raw = self.cog.get_server(user.server, "users")[user.id]

    def __str__(self):
        return self.user.mention

    def __int__(self):
        return self.solde

    @property
    def solde(self):
        return self.raw["solde"]

    @solde.setter
    def solde(self, value: int):
        if value >= 0:
            self.raw["solde"] = value

    @property
    def logs(self):
        liste = []
        for op in self.raw["logs"]:
            liste.append(CashOperation(self, op))
        return liste

    def check_operation(self, opid: str):
        for op in self.logs:
            if op.opid == opid:
                return op
        return None

    @property
    def cache(self):
        return self.raw["cache"]


class CashOperation:
    def __init__(self, account: CashAccount, opid):
        self.account = account
        self.opid = opid
        self.raw = account.raw["logs"][opid]

    def __str__(self):
        return str(self.opid)

    @property
    def timestamp(self):
        return datetime.fromtimestamp(self.raw["timestamp"])

    @property
    def delta(self):
        return self.raw["delta"]

    @property
    def desc(self):
        return self.raw["desc"]

    @property
    def tags(self):
        return self.raw["tags"]

    @property
    def links(self):
        return self.raw["links"]


class CashCurrency:
    def __init__(self, cog, server):
        self.cog = cog
        self.server = server
        self.raw_currency = self.cog.get_server(self.server, "sys")["currency"]

    def __str__(self):
        return self.code

    def __int__(self):
        return self.stocks

    @property
    def symbole(self):
        return self.raw_currency["symbole"]

    @property
    def singulier(self):
        return self.raw_currency["singulier"]

    @property
    def pluriel(self):
        return self.raw_currency["pluriel"]

    @property
    def code(self):
        return self.raw_currency["code"].upper()

    def tformat(self, val: int):
        """Formatte automatiquement la somme donnée en texte"""
        if val <= 1:
            return str(val) + " " + self.singulier
        else:
            return str(val) + " " + self.pluriel

    def sformat(self, val: int):
        """Formatte automatiquement la somme donnée avec son symbole"""
        return str(val) + self.symbole

    @property
    def stocks(self):
        users = self.cog.get_server(self.server, "users")
        total = sum(users[u]["solde"] for u in users)
        return total


class CashAPI:
    """API de Cash - Economie virtuelle sur Atom"""

    def __init__(self, bot, path):
        self.bot = bot
        self.data = dataIO.load_json(path)
        self.cooldown = {}
        self.autosave = 0
        self.import_from_wallet()

    def save(self, force: bool = False):
        if (time.time() - self.autosave) > 10 or force:
            fileIO("data/cash/data.json", "save", self.data)
            self.autosave = time.time()

    def ping(self):
        return datetime.now()

    def import_from_wallet(self, force: bool = False):
        """Réimporte les informations à partir de Wallet"""
        try:
            pay = dataIO.load_json("data/wallet/data.json")
            for serv in pay:
                if serv not in self.data or force:
                    server = self.bot.get_server(serv)
                    self.data[server.id] = {"USERS": {},
                                            "SYS": {"bank": {"name": "Banque {}".format(server.name),
                                                             "base_rj": 200},
                                                    "currency": {"code": server.name[:3].upper(),
                                                                 "symbole": "α",
                                                                 "singulier": "atom",
                                                                 "pluriel": "atoms"},
                                                    "online": False},
                                            "CACHE": {}}
                    for user in pay[serv]["USERS"]:
                        data = pay[serv]["USERS"][user]
                        self.data[server.id]["USERS"][user] = {"solde": data["solde"],
                                                               "logs": {},
                                                               "cache": {}}
            self.save(True)
            return True
        except:
            return False


    def get_server(self, server, sub: str = None, reset= False):
        if server.id not in self.data or reset:
            self.data[server.id] = {"USERS": {},
                                    "SYS": {"bank": {"name": "Banque {}".format(server.name),
                                                     "base_rj": 200},
                                            "currency": {"code": server.name[:3].upper(),
                                                         "symbole": "α",
                                                         "singulier": "atom",
                                                         "pluriel": "atoms"},
                                            "online": False},
                                    "CACHE": {}}
            self.save(True)
        return self.data[server.id][sub.upper()] if sub else self.data[server.id]

    def total_credits_on(self, server):
        """Renvoie tous les crédits en circulation sur un serveur"""
        if server.id in self.data:
            total = sum(
                [self.data[server.id]["USERS"][user]["solde"] for user in self.data[server.id]["USERS"]])
            return total
        return 0

    def total_accounts_on(self, server):
        """Renvoie le nb de comptes ouverts sur un serveur"""
        if server.id in self.data:
            return len(self.data[server.id]["USERS"])
        return 0

    def get_top(self, server, limit: int = 20):
        """Renvoie un top des plus riches du serveur"""
        if server.id in self.data:
            results = {}
            for user in self.data[server.id]["USERS"]:
                results[user] = self.data[server.id]["USERS"][user]["solde"]
            s = sorted(results.items(), key=lambda kv: kv[1], reverse=True)[:limit]
            top = []
            for u in s:
                try:
                    top.append(CashAccount(self, server.get_member(u[0])))
                except:
                    pass
            return top
        return False

    def top_find(self, user: discord.Member):
        """Retrouve la place du membre dans le top de son serveur"""
        server = user.server
        if server.id in self.data:
            results = {}
            for u in self.data[server.id]["USERS"]:
                results[u] = self.data[server.id]["USERS"][u]["solde"]
            sort = sorted(results.items(), key=lambda kv: kv[1], reverse=True)
            for i in sort:
                if user.id == i[0]:
                    return sort.index(i) + 1
        return False


    def get_account(self, user: discord.Member):
        users = self.get_server(user.server, "users")
        if user.id in users:
            return CashAccount(self, user)
        return None

    def create_account(self, user: discord.Member):
        users = self.get_server(user.server, "users")
        if user.id not in users:
            users[user.id] = {"solde": self.get_server(user.server, "sys")["bank"]["base_rj"] * 3,
                              "logs": {},
                              "cache": {}}
            self.save(True)
        return CashAccount(self, user)

    def get_all_accounts(self, server) -> [CashAccount]:
        """Renvoie tous les comptes du serveur"""
        accounts = []
        data = self.get_server(server, "users")
        if data:
            for user in server.members:
                if user.id in data:
                    accounts.append(CashAccount(self, user))
        return accounts

    async def login(self, user: discord.Member):
        """Propose l'inscription à Cash, sinon renvoie le compte du membre"""
        server = user.server
        banque = self.get_server(server, "sys")["bank"]["name"]
        if not self.get_account(user):
            txt = "Vous n'avez pas de compte chez **{}**.\n" \
                  "Voulez-vous en ouvrir un pour profiter de l'économie virtuelle sur ce serveur ?".format(banque)
            em = discord.Embed(description=txt, color=user.color)

            msg = await self.bot.say(embed=em)
            await asyncio.sleep(0.1)
            await self.bot.add_reaction(msg, "✔")
            await self.bot.add_reaction(msg, "✖")
            await asyncio.sleep(0.1)

            def check(reaction, user):
                return not user.bot

            rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=20, check=check, user=user)
            if rep is None or rep.reaction.emoji == "✖":
                await self.bot.clear_reactions(msg)
                txt = "Création de compte annulée.\n" \
                      "Vous pouvez en ouvrir un à tout moment avec la commande `;cash new`"
                em = discord.Embed(description=txt, color=user.color)
                await self.bot.edit_message(msg, embed=em)
                return False
            elif rep.reaction.emoji == "✔":
                await self.bot.clear_reactions(msg)
                if self.create_account(user):
                    txt = "Votre compte a été créé avec succès !\n" \
                          "Vous pouvez désormais profiter des fonctionnalités liées à l'économie virtuelle sur ce serveur."
                    em = discord.Embed(description=txt, color=user.color)
                    await self.bot.edit_message(msg, embed=em)
                    return True
                else:
                    txt = "Votre compte n'a pas pu être créé.\n" \
                          "Réessayez plus tard avec la commande `;cash new`"
                    em = discord.Embed(description=txt, color=user.color)
                    await self.bot.edit_message(msg, embed=em)
                    return True
        return True


    def get_operation(self, server, opid: str):
        for user in self.data[server.id]["USERS"]:
            if opid in self.data[server.id]["USERS"][user]["logs"]:
                try:
                    user = server.get_member(user)
                except:
                    user = self.bot.get_user_info(user)
                return CashOperation(self.get_account(user), opid)
        return None

    def get_all_operations(self, user: discord.Member, limit: int = 3, tags: list = None):
        data = self.get_account(user)
        if data:
            l = []
            for op in data.logs:
                if tags:
                    if [t for t in tags if t in op.tags]:
                        l.append((op.timestamp.timestamp(), op))
                else:
                    l.append((op.timestamp.timestamp(), op))
            ops_sorted = sorted(l, key=operator.itemgetter(0), reverse=True)
            return [i[1] for i in ops_sorted][:limit]
        return []

    def add_operation(self, user: discord.Member, delta: int, desc: str, tags: list= None):
        data = self.get_account(user)
        if data:
            timestamp = datetime.now().timestamp()
            new_key = lambda: "$" + str(''.join(random.SystemRandom().choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(4)))
            opid = new_key()
            while self.get_operation(user.server, opid):
                opid = new_key()
            if delta > 0: tags.append("gain")
            elif delta < 0: tags.append("perte")
            else: tags.append("vide")

            op = {"timestamp": timestamp,
                  "delta": delta,
                  "desc": desc,
                  "tags": tags,
                  "links": []}
            data.raw["logs"][opid] = op
            self.save()
            return CashOperation(data, opid)
        return None

    def link_operations(self, server, opids: list):
        for opid in opids:
            op = self.get_operation(server, opid)
            if op:
                link = opids.copy()
                link.remove(opid)
                op.raw["links"].extend(link)
            else:
                return False
        self.save()
        return True

    def purge_operations(self, user: discord.Member, preserve_days: int = 3):
        verif = time.time() - (86400 * preserve_days)
        acc = self.get_account(user)
        conf = []
        for op in acc.logs:
            if op.timestamp.timestamp() < verif:
                conf.append(op)
                del acc.raw["logs"][op]
        self.save()
        return conf

    def day_operations(self, user: discord.Member, day: str = None):
        if not day:
            day = time.strftime("%d.%m.%Y", time.localtime())
        data = self.get_account(user)
        if data:
            ops = []
            for op in data.logs:
                if datetime.strftime(op.timestamp, "%d.%m.%Y") == day:
                    ops.append((op.timestamp.timestamp(), op))
            ops_sorted = sorted(ops, key=operator.itemgetter(0), reverse=True)
            return [i[1] for i in ops_sorted]
        return []

    def total_delta_for(self, user: discord.Member, day: str = None):
        ops = self.day_operations(user, day)
        if ops:
            return sum([op.delta for op in ops])
        return 0

    def enough_credits(self, user: discord.Member, sum: int):
        data = self.get_account(user)
        if data:
            if data.solde >= abs(int(sum)): return True
        return False

    def add_credits(self, user: discord.Member, sum: int, desc, tags = None):
        data = self.get_account(user)
        if data and sum > 0:
            data.solde += int(sum)
            return self.add_operation(user, sum, desc, tags)
        return None

    def remove_credits(self, user: discord.Member, sum: int, desc, tags = None):
        sum = abs(int(sum))
        data = self.get_account(user)
        if data:
            data.raw["solde"] -= sum
            if data.solde <= 0:
                data.solde = 0
            return self.add_operation(user, -sum, desc, tags)
        return None

    def set_credits(self, user: discord.Member, sum: int, desc, tags = None):
        sum = abs(int(sum))
        data = self.get_account(user)
        if data and sum >= 0:
            data.solde = sum
            return self.add_operation(user, sum, desc, tags)
        return False

    def transfert_credits(self, creancier: discord.Member, debiteur: discord.Member, sum: int, desc, tags = None):
        if creancier != debiteur:
            if sum > 0:
                if self.enough_credits(debiteur, sum):
                    tags.append("transfert")
                    don = self.remove_credits(debiteur, sum, desc, tags)
                    recu = self.add_credits(creancier, sum, desc, tags)
                    self.link_operations(creancier.server, [don.opid, recu.opid])
                    return (don, recu)
        return None

    def get_currency(self, server):
        return CashCurrency(self, server)

    def get_all_currencies(self):
        liste = []
        for s in self.data:
            server = self.bot.get_server(s)
            liste.append(CashCurrency(self, server))
        return liste


    def get_cooldown(self, user: discord.Member, cooldown_id: str):
        server = user.server
        cd = cooldown_id.lower()
        now = lambda: time.time()
        if server.id in self.cooldown:
            if cd in self.cooldown[server.id]:
                if user.id in self.cooldown[server.id][cd]:
                    if now() < self.cooldown[server.id][cd][user.id]:
                        return self.remaining(now(), self.cooldown[server.id][cd][user.id])
                    else:
                        del self.cooldown[server.id][cd][user.id]
        return None

    def add_cooldown(self, user: discord.Member, cooldown_id: str, cooldown: int):
        server = user.server
        cd = cooldown_id.lower()
        end = lambda c: time.time() + c
        if server.id not in self.cooldown: self.cooldown[server.id] = {}
        if cd not in self.cooldown[server.id]: self.cooldown[server.id][cd] = {}
        if user.id in self.cooldown[server.id][cd]:
            self.cooldown[server.id][cd][user.id] += cooldown
        else:
            self.cooldown[server.id][cd][user.id] = end(cooldown)
        return self.get_cooldown(user, cd)

    def reset_cooldown(self, user: discord.member, cooldown_id: str):
        server = user.server
        cd = cooldown_id.lower()
        if server.id in self.cooldown:
            if cd in self.cooldown[server.id]:
                if user.id in self.cooldown[server.id][cd]:
                    del self.cooldown[server.id][cd][user.id]
                    return True
        return None


    def remaining(self, t_from, t_to):
        if t_to <= t_from:
            return self.seconds_format(0)
        return self.seconds_format(round(t_to - t_from))

    def seconds_format(self, seconds: int):
        j = 0
        while seconds >= 86400:
            j += 1
            seconds -= 86400
        h, m, s = [int(n) for n in str(timedelta(seconds=seconds)).split(":")]
        all = []
        if j: all.append(str(j) + "J")
        if h: all.append(str(h) + "h")
        if m: all.append(str(m) + "m")
        if s: all.append(str(s) + "s")
        auto = "`" + " · ".join(all) + "`"
        SecFormat = namedtuple('SecFormat', ['days', 'hours', 'minutes', 'seconds', 'auto'])
        return SecFormat(j, h, m, s, auto)


    def reset_account(self, user: discord.Member):
        server = user.server
        data = self.get_server(server, "users")
        if user.id in data:
            del data[user.id]
            self.save(True)
            return True
        return False

    def purge_accounts(self, server):
        data = self.get_server(server, "users")
        data_copy = deepcopy(data)
        all_users = [u.id for u in server.members]
        confirm = []
        for uid in data_copy:
            if uid not in all_users:
                del data[uid]
                confirm.append(uid)
        self.save(True)
        return confirm

    def reset_server(self, server):
        self.get_server(server, reset=True)
        return True

    def reset_all(self):
        self.data = {}
        self.save(True)
        return True


class Cash:
    """Economie virtuelle"""

    def __init__(self, bot):
        self.bot = bot
        self.api = CashAPI(bot, "data/cash/data.json")
        # Pour importer l'API : self.bot.get_cog("Cash").api

    def check(self, reaction, user):
        return not user.bot

    @commands.group(name="cash", aliases=["b"], pass_context=True, invoke_without_command=True, no_pm=True)
    async def cash_account(self, ctx, membre: discord.Member = None):
        """Ensemble de commandes relatives à Wallet (économie virtuelle)

        En absence de mention, renvoie les détails du compte de l'invocateur"""
        if ctx.invoked_subcommand is None:
            if not membre:
                membre = ctx.message.author
            await ctx.invoke(self.account, user=membre)

    @cash_account.command(pass_context=True)
    async def new(self, ctx):
        """Ouvre un compte Cash sur ce serveur"""
        user = ctx.message.author
        data = self.api.get_account(user)
        if not data:
            self.api.create_account(user)
            await self.bot.say("**Compte créé** ─ Vous pouvez le consulter avec `;cash`")
        else:
            await self.bot.say("**Vous avez déjà un compte** ─ Consultez-le avec `;cash`")

    @cash_account.command(pass_context=True)
    async def account(self, ctx, user: discord.Member = None):
        """Affiche le compte Cash d'un membre (ou soi-même)"""
        user = user if user else ctx.message.author
        same = True if user == ctx.message.author else False
        if same or self.api.get_account(user):
            if await self.api.login(user):
                cur = self.api.get_currency(user.server)
                data = self.api.get_account(user)
                total = self.api.total_delta_for(user)
                delta_emoji = "📉" if total < 0 else "📈"
                total = "+{}".format(total) if total >= 0 else "{}".format(total)
                top = self.api.top_find(user) if self.api.top_find(user) else "Ø"

                txt = "💰 **Solde** ─ {}\n".format(cur.tformat(data.solde))
                txt += "{} **Aujourd'hui** ─ {}\n".format(delta_emoji, total)
                txt += "🏆 **Classé #{}**\n".format(top)

                name = user.name if not same else "Votre compte"
                em = discord.Embed(title=name, description=txt, color=user.color, timestamp=ctx.message.timestamp)
                em.set_thumbnail(url=user.avatar_url)

                ops = self.api.get_all_operations(user, 5)
                if ops:
                    logs = ""
                    for op in ops:
                        if op.delta < 0:
                            sum = str(op.delta)
                        else:
                            sum = "+" + str(op.delta)
                        desc = op.desc if len(op.desc) <= 40 else op.desc[:37] + "..."
                        logs += "**{}** ─ *{}*\n".format(sum, desc)
                    em.add_field(name="Historique", value=logs)
                em.set_footer(text="» {}".format(self.api.get_server(user.server, "sys")["bank"]["name"]))
                await self.bot.say(embed=em)
            return
        else:
            await self.bot.say("**Compte inexistant** ─ Le membre visé n'a pas de compte Cash sur ce serveur")

    @cash_account.command(name="logs", pass_context=True)
    async def cash_logs(self, ctx, user: discord.Member = None, *tags):
        """Recherche les dernières opérations bancaires d'un membre"""
        user = user if user else ctx.message.author
        data = self.api.get_account(user)
        if data:
            cur = self.api.get_currency(user.server)
            txt = ""
            page = 1
            now = datetime.now()
            if not tags:
                tags = None
                tagtxt = ""
            else:
                tagtxt = " • Tags: {}".format(", ".join("#{}".format(t) for t in tags))
            for op in self.api.get_all_operations(user, 20, tags):
                ts, tstxt = op.timestamp, ""
                if ts.date() == now.date():
                    if ts.hour == now.hour:
                        tstxt = "À l'instant"
                    else:
                        tstxt = ts.strftime("%H:%M")
                else:
                    tstxt = ts.strftime("%d.%m.%Y")
                txt += "{} » `{}` · **{}** ─ *{}*\n".format(tstxt, op.opid, cur.sformat(op.delta), op.desc)
                if len(txt) > 1950 * page:
                    em = discord.Embed(title="Historique des opérations de {}".format(user), description=txt,
                                       color=user.color, timestamp=ctx.message.timestamp)
                    em.set_footer(text="Page n°{}{}".format(page, tagtxt))
                    await self.bot.say(embed=em)
                    txt = ""
                    page += 1
            if txt:
                em = discord.Embed(title="Historique des opérations de {}".format(user), description=txt,
                                   color=user.color, timestamp=ctx.message.timestamp)
                em.set_footer(text="Page n°{}{}".format(page, tagtxt))
                await self.bot.say(embed=em)
        else:
            await self.bot.say("**Compte inexistant** ─ Le membre visé n'a pas de compte Cash sur ce serveur")

    @cash_account.command(name="get", pass_context=True)
    async def cash_get(self, ctx, operation_id: str):
        """Consulter les détails d'une opération sur ce serveur"""
        server = ctx.message.server
        if len(operation_id) == 4:
            operation_id = "$" + operation_id
        op = self.api.get_operation(server, operation_id)
        if op:
            cur = self.api.get_currency(server)
            if op.tags:
                tags = " ".join(["`{}`".format(i) for i in op.tags])
            else:
                tags = "Aucun"

            txt = "> *{}*\n".format(op.desc)
            txt += "**Delta** ─ {}\n".format(cur.sformat(op.delta))
            txt += "**Compte** ─ {}\n".format(op.account.user.name)
            txt += "**Tags** ─ {}\n".format(tags)
            txt += "**Opérations liées** ─ {}".format(" ".join("`{}`".format(ol.opid) for ol in op.links))
            em = discord.Embed(title="Détails de l'opération » {}".format(op.opid), description=txt,
                               color=op.account.user.color, timestamp=op.timestamp)
            await self.bot.say(embed=em)
        else:
            await self.bot.say(
                "**Identifiant inconnu** ─ Vérifiez que l'identifiant fasse 5 caractères, avec en premier un symbole dollar ($)")

    @commands.command(pass_context=True, no_pm=True)
    async def give(self, ctx, receveur: discord.Member, somme: int, *raison):
        """Transférer des crédits sur le compte d'autrui"""
        server = ctx.message.server
        donateur = ctx.message.author
        cur = self.api.get_currency(server)
        raison = " ".join(raison) if raison else "Don de {} pour {}".format(donateur, receveur)
        if somme > 0:
            if self.api.get_account(receveur):
                if await self.api.login(donateur):
                    if self.api.enough_credits(donateur, somme):
                        txt = "Transfert de {} à {} ···".format(cur.sformat(somme), receveur.mention)
                        em = discord.Embed(description=txt, color=donateur.color)
                        em.set_author(name=str(donateur), icon_url=donateur.avatar_url)
                        msg = await self.bot.say(embed=em)
                        if self.api.transfert_credits(receveur, donateur, somme, raison, ["don"]):
                            await asyncio.sleep(2)
                            txt = "Transfert de {} à {} ··· Succès.".format(cur.sformat(somme), receveur.mention)
                            em = discord.Embed(description=txt, color=receveur.color, timestamp=datetime.utcnow())
                            em.set_author(name=str(donateur), icon_url=donateur.avatar_url)
                            await self.bot.edit_message(msg, embed=em)
                        else:
                            await asyncio.sleep(0.5)
                            await self.bot.say("**Transfert impossible** ─ La banque a refusé ce transfert.")
                    else:
                        await self.bot.say(
                            "**Fonds insuffisants** ─ Vous n'avez pas cette somme sur votre compte, soyez plus raisonnable.")
                else:
                    await self.bot.say(
                        "**Compte inexistant** ─ Vous devez d'abord posséder un compte **Cash** sur ce serveur (`;cash new`)")
            else:
                await self.bot.say(
                    "**Aucun receveur** ─ Le receveur sélectionné ne possède pas de compte **Cash** sur ce serveur.")
        else:
            await self.bot.say("**Somme invalide** ─ La somme donnée doit être positive.")

    @commands.command(pass_context=True, no_pm=True, aliases=["palmares"])
    async def top(self, ctx, top: int = 10):
        """Affiche un top des membres les plus riches du serveur"""
        server = ctx.message.server
        author = ctx.message.author
        palm = self.api.get_top(server, top)
        cur = self.api.get_currency(server)
        n = 1
        txt = ""

        def medal(n):
            if n == 1:
                return " \🥇"
            elif n == 2:
                return " \🥈"
            elif n == 3:
                return " \🥉"
            else:
                return ""

        if palm:
            for user in palm:
                if n < top:
                    if n == 4:
                        txt += "─────────\n"
                    txt += "{}**{}** · {} ─ *{}*\n".format(medal(n), n, cur.sformat(user.solde), user.user)
                    n += 1
            em = discord.Embed(title="Top des plus riches du serveur", description=txt,
                               timestamp=ctx.message.timestamp, color=0xd4af37)
            em.add_field(name="Votre position", value=str(self.api.top_find(ctx.message.author)))
            total = self.api.total_credits_on(server)
            members = self.api.total_accounts_on(server)
            em.set_footer(text="{}/{} comptes".format(cur.sformat(total), members))
            try:
                await self.bot.say(embed=em)
            except:
                await self.bot.say("**Message trop long** ─ Le classement est trop long pour être affiché sur Discord")
        else:
            await self.bot.say("**Serveur vide** ─ Aucun compte ***Cash*** n'est présent sur ce serveur.")

    @commands.command(pass_context=True, no_pm=True, aliases=["rj"])
    async def revenu(self, ctx):
        """Récupérer son revenu journalier"""
        user, server = ctx.message.author, ctx.message.server
        bank = self.api.get_server(server, "sys")["bank"]
        base = bank["base_rj"]
        cur = self.api.get_currency(server)

        if await self.api.login(user):
            data = self.api.get_account(user)
            if "last_pay" not in data.raw["cache"]:
                data.raw["cache"]["last_pay"] = None
            if "msg_pay" not in data.raw["cache"]:
                data.raw["cache"]["msg_pay"] = {"date": None,
                                                "nb": 0}
            txt = ""
            total = 0

            if data.raw["cache"]["last_pay"] != datetime.now().strftime("%d.%m.%Y"):
                txt += "**+ {}** » Base journalière\n".format(cur.sformat(base))
                total += base
                if data.raw["cache"]["last_pay"] == (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y"):
                    cons_bonus = round(base * 0.2)
                    txt += "**+ {}** » Bonus de jours consécutifs (20% BJ)\n".format(cur.sformat(base))
                    total += cons_bonus
                data.raw["cache"]["last_pay"] = datetime.now().strftime("%d.%m.%Y")
            else:
                txt += "**+ 0{}** » Base journalière déjà perçue\n".format(cur.symbole)

            if data.raw["cache"]["msg_pay"]["date"] == datetime.now().strftime("%d.%m.%Y"):
                msg_bonus = round(data.raw["cache"]["msg_pay"]["nb"] * (base * 0.02))
                data.raw["cache"]["msg_pay"]["nb"] = 0
                total += msg_bonus
                txt += "**+ {}** » Revenu d'activité (2% BJ/point)\n".format(cur.sformat(msg_bonus))
            txt += "─────\n"
            txt += "**= {}**".format(cur.tformat(total))

            self.api.add_credits(user, total, "Revenus", ["revenus"])
            self.api.save()
            em = discord.Embed(description=txt, color=user.color, timestamp=ctx.message.timestamp)
            em.set_author(name="Revenus", icon_url=user.avatar_url)
            em.set_footer(text="Nouveau solde = {}".format(cur.sformat(data.solde)))
            await self.bot.say(embed=em)

    @commands.group(name="cashset", aliases=["cs"], pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def _cashset(self, ctx):
        """Commandes de gestion de l'économie"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_cashset.command(pass_context=True)
    async def forcenew(self, ctx, user: discord.Member):
        """Force l'ouverture d'un compte pour un membre"""
        if not self.api.get_account(user):
            self.api.create_account(user)
            await self.bot.say("Compte **Cash** de {} créé avec succès.".format(user.mention))
        else:
            await self.bot.say("Le membre {} possède déjà un compte **Cash**.".format(user.name))

    @_cashset.command(pass_context=True)
    async def purge(self, ctx):
        """Purge les comptes Cash des membres qui ne sont plus sur ce serveur"""
        server = ctx.message.server

        def check(reaction, user):
            return not user.bot

        msg = await self.bot.say(
            "**Attention** ─ Cette commande efface __définitivement__ les comptes Cash des membres absents du serveur.\n"
            "Cette action est irréversible. Voulez-vous continuer ?")
        await self.bot.add_reaction(msg, "✔")
        await self.bot.add_reaction(msg, "✖")
        rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=20, check=check,
                                               user=ctx.message.author)
        if rep is None or rep.reaction.emoji == "✖":
            await self.bot.delete_message(msg)
            await self.bot.say("**Purge annulée**")
        elif rep.reaction.emoji == "✔":
            await self.bot.delete_message(msg)
            l = self.api.purge_accounts(server)
            await self.bot.say("**Purge réalisée** ─ {} comptes ont été supprimés".format(len(l)))

    @_cashset.command(pass_context=True)
    async def set(self, ctx, user: discord.Member, operation: str, *raison):
        """Modifie le solde d'un membre (+/-/=) avec les réserves du serveur

        Exemples :
        ;cs set @Acrone 42 -> Change le solde pour 42
        ;cs set @Acrone +15 -> Ajoute 15 crédits
        ;cs set @Acrone -30 -> Retire 30 crédits"""
        raison = " ".join(raison) if raison else "Modification par un modérateur"
        server = ctx.message.server
        cur = self.api.get_currency(server)

        sonar = self.bot.get_cog("Sonar").api

        async def sonar_log(desc):
            if sonar.preload_channel(user.server, "app_cash_bank"):
                em = discord.Embed(
                    description=desc,
                    color=0xd4af37, timestamp=ctx.message.timestamp)  # doré
                em.set_author(name="Mouvement de fonds de {}".format(
                    self.api.get_server(server, "sys")["bank"]["name"]),
                              icon_url=server.icon_url)
                em.set_footer(text="Auteur ID: {}".format(ctx.message.author.id))
                await sonar.publish_log(user.server, "app_cash_bank", em)

        if self.api.get_account(user):
            if operation.isdigit() or operation.startswith("="):
                if operation.startswith("="):
                    operation = operation[1:]
                operation = int(operation)
                if operation > self.api.get_account(user).solde:
                    delta = operation - self.api.get_account(user).solde
                    self.api.set_credits(user, operation, raison, ["modif"])
                    await self.bot.say("**Solde modifié** ─ Le solde du membre est désormais de {}".format(
                        cur.sformat(self.api.get_account(user).solde)))
                    await sonar_log(
                        "Ajout de **{}** au compte de {}".format(cur.sformat(delta), user.mention))
                else:
                    delta = self.api.get_account(user).solde - operation
                    if delta > 0:
                        self.api.set_credits(user, operation, raison, ["modif"])
                        await sonar_log(
                            "Retrait de **{}** du compte de {}".format(cur.sformat(delta), user.mention))
                        await self.bot.say("**Solde modifié** ─ Le solde du membre est désormais de {}".format(
                            cur.sformat(self.api.get_account(user).solde)))
                    else:
                        await self.bot.say(
                            "**Opération inutile** ─ Il n'y a ni ajout ni retrait d'argent du membre dans cette opération.")

            elif operation.startswith("+"):
                operation = int(operation[1:])
                self.api.add_credits(user, operation, raison, ["modif"])
                await sonar_log(
                    "Don de **{}** au compte de {}".format(cur.sformat(operation), user.mention))
                await self.bot.say(
                    "**Solde modifié** ─ Le solde du membre est désormais de {}".format(
                        cur.sformat(self.api.get_account(user).solde)))

            elif operation.startswith("-"):
                operation = int(operation[1:])
                self.api.remove_credits(user, operation, raison, ["modif"])
                await sonar_log(
                    "Retrait de **{}** du compte de {}".format(cur.sformat(operation), user.mention))
                await self.bot.say(
                    "**Solde modifié** ─ Le solde du membre est désormais de {}".format(
                        cur.sformat(self.api.get_account(user).solde)))
            else:
                await send_cmd_help(ctx)
        else:
            await self.bot.say("Le membre visé n'a pas de compte Cash sur ce serveur.")

    @_cashset.command(pass_context=True)
    async def delete(self, ctx, user: discord.Member):
        """Supprime le compte d'un membre"""
        if self.api.get_account(user):
            self.api.reset_account(user)
            await self.bot.say("Le compte du membre a été effacé.")
        else:
            await self.bot.say("Le membre ne possède pas de compte Wallet")

    @_cashset.command(pass_context=True, hidden=True)
    async def deleteall(self, ctx):
        """Reset les données du serveur"""
        self.api.reset_server(ctx.message.server)
        await self.bot.say("Données du serveur reset.")

    @_cashset.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def totalreset(self, ctx):
        """Efface toutes les données du module"""
        self.api.reset_all()
        await self.bot.say("**Données du module reset.**")


    @_cashset.group(name="bank", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def _bankset(self, ctx):
        """Paramètres spécifiques à la banque"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_bankset.command(pass_context=True)
    async def nom(self, ctx, *nom):
        """Modifier le nom de la banque du serveur"""
        nom = " ".join(nom)
        if len(nom) <= 30:
            self.api.get_server(ctx.message.server, "sys")["bank"]["name"] = nom
            self.api.save(True)
            await self.bot.say("**Nom modifié** ─ La banque s'appelle désormais ***{}***".format(nom))
        else:
            await self.bot.say(
                "**Nom invalide** ─ Pour limiter les soucis d'affichage, il ne peut faire au maximum que 30 caractères.")

    @_bankset.command(pass_context=True)
    async def monnaie(self, ctx, symbole: str, singulier: str, pluriel: str, online_code: str):
        """Modifier le nom, symbole et code de la monnaie
        Format => ;cs bank monnaie "symbole" "singulier" "pluriel" "code à 3 lettres/chiffres"
        Notez que les guillemets ne sont pas nécessaires si les noms n'ont pas d'espace

        Exemple: ;cs bank monnaie "α" "atom" "atoms" "ATO" """
        if len(symbole) == 1:
            if len(singulier) <= 16 and len(pluriel) <= 16:
                if len(online_code) == 3:
                    data = self.api.get_server(ctx.message.server, "sys")["currency"]
                    data["symbole"] = symbole
                    data["singulier"] = singulier
                    data["pluriel"] = pluriel
                    data["code"] = online_code.upper()
                    self.api.save(True)
                    cur = self.api.get_currency(ctx.message.server)
                    await self.bot.say("**Monnaie modifiée** ─ Ci-dessous des exemples d'affichage\n"
                                       "> {0} a gagné {1} !\n"
                                       "> Un transfert de {2} a été réalisé entre X et Y\n"
                                       "> {3} + {2} = {4}\n"
                                       "> Les crédits de {0}, en devise {5} ont été transformés en crédits XXX".format(
                        ctx.message.author.name, cur.sformat(10), cur.tformat(42), cur.tformat(1), cur.sformat(43),
                        cur.code))
                else:
                    await self.bot.say("Le code de votre monnaie doit être composé de 3 caractères seulement.")
            else:
                await self.bot.say(
                    "Les noms au singulier et pluriels ne peuvent contenir que 16 caractères chacun au maximum.")
        else:
            await self.bot.say("Le symbole doit être composé que d'un unique caractère, qu'il soit spécial "
                               "ou non tant qu'il s'affiche correctement sur Discord.")

    @_bankset.command(name="revenus", pass_context=True)
    async def revenus_set(self, ctx, val: int):
        """Modifie la quantité de crédits qu'un membre peut recevoir par jour avec la commande ;revenus et permet de calculer l'argent versée à l'ouverture d'un compte (3x le revenu)

        Par def. 200"""
        cur = self.api.get_currency(ctx.message.server)
        if 500 > val > 0:
            self.api.get_server(ctx.message.server, "sys")["bank"]["base_rj"] = val
            self.api.save(True)
            await self.bot.say(
                "**Revenu de base modifié** ─ Les membres pourront prétendre quotidiennement à {}".format(
                    cur.tformat(val)))
        else:
            await self.bot.say(
                "**Valeur invalide** ─ Le revenu ne peut être qu'un chiffre positif inférieur à 500.")


    async def msg_listener(self, message):
        if message.server:
            author = message.author
            if not author.bot:
                data = self.api.get_account(author)
                if data:
                    if "msg_pay" not in data.raw["cache"]:
                        data.raw["cache"]["msg_pay"] = {"date": None,
                                                          "nb": 0}
                    date = datetime.now().strftime("%d.%m.%Y")
                    if data.raw["cache"]["msg_pay"]["date"] != date:
                        data.raw["cache"]["msg_pay"]["date"] = date
                        data.raw["cache"]["msg_pay"]["nb"] = 0

                    cool = self.api.get_cooldown(author, "msg_pay")
                    if not cool:
                        self.api.add_cooldown(author, "msg_pay", 300)
                        data.raw["cache"]["msg_pay"]["nb"] += 1
                        self.api.save()

    def __unload(self):
        self.api.save(True)
        print("Cash - Sauvegarde effectuée")


def check_folders():
    if not os.path.exists("data/cash"):
        print("Creation du dossier Cash ...")
        os.makedirs("data/cash")


def check_files():
    if not os.path.isfile("data/cash/data.json"):
        print("Ouverture de cash/data.json ...")
        fileIO("data/cash/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Cash(bot)
    bot.add_listener(n.msg_listener, "on_message")
    bot.add_cog(n)
