import operator
import os
from copy import deepcopy
from datetime import datetime, timedelta

import discord
from __main__ import send_cmd_help
from cogs.utils.dataIO import fileIO, dataIO
from discord.ext import commands


class Nooknet:
    """Outils communautaires dédiés à AC:NH"""
    def __init__(self, bot):
        self.bot = bot
        self.data = dataIO.load_json("data/nooknet/data.json")

    def save(self):
        fileIO("data/nooknet/data.json", "save", self.data)


    def get_server(self, server):
        if server.id not in self.data["SERVERS"]:
            self.data["SERVERS"][server.id] = {"navets": {}}
            self.save()
        return self.data["SERVERS"][server.id]

    async def new_turnip_value(self, user: discord.Member, value):
        """Ajoute une valeur de navets sur un serveur"""
        data = self.get_server(user.server)
        api = self.bot.get_cog("Sonar").api
        ts = datetime.utcnow()

        # Traduction et formattage
        day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi','Dimanche']
        trad = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday','Sunday']
        today_name = datetime.now().strftime("%A")
        today_trad = day_names[trad.index(today_name)]
        dimanche = today_name == "Sunday"
        periode = "AM" if datetime.now().hour < 12 else "PM"
        date = datetime.now().strftime("%d/%m/%Y") + "/" + periode
        peritxt = "{} {} {}".format(today_trad, datetime.now().strftime("%m/%Y"), "Matin" if periode == "AM" else "Après-midi")

        # Création de la période
        if date not in data["navets"]:
            if dimanche and periode == "PM":
                return False
            else:
                data["navets"][date] = {"type": "buy" if dimanche else "sell",
                                        "day": datetime.now().strftime("%d/%m/%Y"),
                                        "values": []}

        # Alertes de logs
        if dimanche:
            if value < self.get_lowest_turnip(user.server, date):
                if api.preload_channel(user.server, "app_nooknet_navet_lowest"):
                    em = discord.Embed(
                        description="Les navets les moins chers (**{}** clochettes) sont désormais chez {}".format(value, user.mention),
                        color=0x00962A, timestamp=ts)  # Vert_feuille
                    em.set_author(name="Nouvelle valeur minimale de navets", icon_url="https://i.imgur.com/NucNCk2.png")
                    em.set_footer(text="Période: {}".format(peritxt))
                    await api.publish_log(user.server, "app_nooknet_navet_lowest", em)

        elif value > self.get_highest_turnip(user.server, date):
            if api.preload_channel(user.server, "app_nooknet_navet_highest"):
                em = discord.Embed(
                    description="La reprise la plus profitable (**{}** clochettes) est désormais chez {}".format(value,
                                                                                                               user.mention),
                    color=0x00962A, timestamp=ts)  # Vert_feuille
                em.set_author(name="Nouvelle valeur maximale de navets", icon_url="https://i.imgur.com/NucNCk2.png")
                em.set_footer(text="Période: {}".format(peritxt))
                await api.publish_log(user.server, "app_nooknet_navet_highest", em)

        # Ajout de la valeur au registre
        data["navets"][date]["values"].append((user.id, value))

        # Nettoyage des données plus vieilles que 10 jours
        before = datetime.now() - timedelta(days = 10)
        date_before = before.strftime("%d/%m/%Y")
        modif_cop = deepcopy(data["navets"])
        for d in modif_cop:
            if d.startswith(date_before):
                del data["navets"][d]

        self.save()
        return True

    def get_highest_turnip(self, server, date):
        data = self.get_server(server)
        if date in data["navets"]:
            highest, user = 0, None
            for v in data["navets"][date]["values"]:
                if v[1] > highest:
                    highest = v[1]
                    user = v[0]
            if user:
                return (user, highest)
        return ()

    def get_lowest_turnip(self, server, date):
        data = self.get_server(server)
        if date in data["navets"]:
            lowest, user = 1000, None
            for v in data["navets"][date]["values"]:
                if v[1] < lowest:
                    lowest = v[1]
                    user = v[0]
            if user:
                return (user, lowest)
        return ()

    def get_day_turnip(self, server, date):
        data = self.get_server(server)
        if date in data["navets"]:
            l = []
            for v in data["navets"][date]["values"]:
                l.append([v[0], v[1]])
            sort = sorted(l, key=operator.itemgetter(1), reverse=True)
            return sort
        return []

    def get_member(self, user: discord.Member):
        server = self.get_server(user.server)
        if user.id not in server:
            server[user.id] = {"code": "",
                               "photo": "",
                               "island_name": "",
                               "user_name": "",
                               "message": ""}
            self.save()
        return server[user.id]

    def verif_code_ami(self, code: str):
        """Vérifie que le code ami Nintendo est valable"""
        if "-" in code:
            if len(code) == 14:
                for e in code.split("-"):
                    if not e or len(e) != 4 or not e.isdigit():
                        return False
                return code
            elif len(code) == 17:
                spt = code.split("-")
                if spt[0].lower() == "sw":
                    spt.remove(spt[0])
                    for e in spt:
                        if not e or len(e) != 4 or not e.isdigit():
                            return False
                    return "-".join(spt)
        return False


    @commands.group(name="nooknet", aliases=["nook"], pass_context=True, invoke_without_command=True, no_pm=True)
    async def _nooknet(self, ctx, membre: discord.Member = None):
        """Profil Nooknet du membre et commandes associées

        -> En absence de mention, renvoie le profil du membre à l'origine de la commande"""
        if ctx.invoked_subcommand is None:
            if not membre:
                membre = ctx.message.author
            await ctx.invoke(self.profil, user=membre)

    @_nooknet.command(pass_context=True)
    async def profil(self, ctx, user: discord.Member = None):
        if not user: user = ctx.message.author
        data = self.get_member(user)
        em = discord.Embed(description="> {}".format(data["message"]) if data["message"] else None, color=user.color,
                           timestamp=ctx.message.timestamp)
        title = user.name if user.display_name == user.name else "{} « {} »".format(user.name, user.display_name)
        em.set_author(name=title, icon_url=user.avatar_url)
        em.set_thumbnail(url=data["photo"] if data["photo"] else None)
        if data["code"]:
            em.add_field(name="Code ami", value="SW-{}".format(data["code"]), inline=False)
        if data["island_name"] and data["user_name"]:
            em.add_field(name="Île et nom", value="**{}** — *{}*".format(data["island_name"], data["user_name"]), inline=False)
        elif data["island_name"] and not data["user_name"]:
            em.add_field(name="Nom de l'Île", value="**{}**".format(data["island_name"]), inline=False)
        elif not data["island_name"] and data["user_name"]:
            em.add_field(name="Nom du villageois", value="*{}*".format(data["user_name"]), inline=False)
        await self.bot.say(embed=em)

    @_nooknet.command(pass_context=True)
    async def code(self, ctx, code_ami: str = ""):
        """Ajouter/modifier/retirer son code ami

        Laisser le champ vide retire l'affichage du code ami dans le profil"""
        data = self.get_member(ctx.message.author)
        if code_ami:
            if self.verif_code_ami(code_ami):
                data["code"] = self.verif_code_ami(code_ami)
                self.save()
                await self.bot.say("**Code ami modifié** • Consultez votre profil avec `;nook` pour le voir !")
            else:
                await self.bot.say("**Code ami invalide** • Il doit être dans le format `SW-0123-4567-8910` ou "
                                   "`0123-4567-8910`")
        else:
            data["code"] = ""
            self.save()
            await self.bot.say("**Code ami retiré** • Il ne s'affichera plus dans votre profil Nooknet.")

    @_nooknet.command(pass_context=True)
    async def photo(self, ctx, url: str = ""):
        """Ajouter/modifier/retirer la photo personnalisée sur votre profil Nooknet

        Doit être une URL (hébergée sur un site tel que Imgur)"""
        data = self.get_member(ctx.message.author)
        if url:
            if url.endswith((".png", ".jpeg", ".jpg", ".gif")):
                data["photo"] = url
                self.save()
                await self.bot.say("**Image modifiée** • Consultez votre profil avec `;nook` pour la voir !")
            else:
                await self.bot.say("**Image non supportée** • L'URL doit se terminer par un de ces formats : `.png` `.jpeg` `.jpg` `.gif`")
        else:
            data["photo"] = ""
            self.save()
            await self.bot.say("**Image retirée** • Elle ne s'affichera plus sur votre profil Nooknet.")

    @_nooknet.command(pass_context=True)
    async def island(self, ctx, nom: str = ""):
        """Ajouter/modifier/retirer le nom de votre Ile

        Laisser le champ vide permet de retirer l'affichage du nom"""
        data = self.get_member(ctx.message.author)
        if nom:
            data["island_name"] = nom
            self.save()
            await self.bot.say("**Nom d'île ajouté** • Il s'affichera sur votre profil Nooknet (`;nook`).")
        else:
            data["island_name"] = ""
            self.save()
            await self.bot.say("**Nom retiré** • Il ne s'affichera plus sur votre profil Nooknet.")

    @_nooknet.command(pass_context=True)
    async def msg(self, ctx, message: str = ""):
        """Ajouter/modifier/retirer un message sur votre profil

        Laisser le champ vide permet de retirer l'affichage de celui-ci"""
        data = self.get_member(ctx.message.author)
        if message:
            data["message"] = message
            self.save()
            await self.bot.say("**Message ajouté** • Il s'affichera sur votre profil Nooknet (`;nook`).")
        else:
            data["message"] = ""
            self.save()
            await self.bot.say("**Message retiré** • Il ne s'affichera plus sur votre profil Nooknet.")


    @commands.group(name="navet", aliases=["turnip"], pass_context=True, no_pm=True)
    async def _navet(self, ctx):
        """Mise en commun des valeurs des navets"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_navet.command(pass_context=True)
    async def add(self, ctx, valeur: int):
        """Ajouter la valeur des navets sur son île sur la période en cours"""
        serv = self.get_server(ctx.message.server)
        dimanche = datetime.now().strftime("%A") == "Sunday"
        periode = "AM" if datetime.now().hour < 12 else "PM"
        if dimanche and periode == "PM":
            await self.bot.say("**Inutile** • Il est impossible d'acheter des navets après 12h (heure française)")
        else:
            await self.new_turnip_value(ctx.message.author, valeur)
            await self.bot.say("**Valeur ajoutée** • Consultez le registre avec `;navet info`")

    @_navet.command(pass_context=True, name="info")
    async def values_list(self, ctx, date = None):
        """Liste les valeurs des navets au jour (max. 10 jours) et période rentré (par défaut la période en cours)

        La date doit être au format JJ/MM/AAAA/PP avec pour PP soit AM (matin) ou PM (après-midi)
        Ex: 01/04/2020/PM"""
        if not date: date = datetime.now().strftime("%d/%m/%Y") + "/" + "AM" if datetime.now().hour < 12 else "PM"
        dimanche = datetime.now().strftime("%A") == "Sunday"
        if len(date) == 11:
            liste = self.get_day_turnip(ctx.message.server, date)
            if liste:
                if dimanche:
                    liste.reverse()
                txt = ""
                for v in liste:
                    try:
                        user = ctx.message.server.get_member(v[0])
                        user = user.mention
                    except:
                        user = "@" + self.bot.get_user_info(v[0]).name
                    txt += "`{}` — {}\n".format(v[1], user)

                em = discord.Embed(
                    description=txt, color=0x00962A, timestamp=ctx.message.timestamp)  # Vert_feuille
                em.set_author(name="Registre des valeurs du navet", icon_url="https://i.imgur.com/NucNCk2.png")
                em.set_footer(text="Période = {} {}".format(date, "(Achat)" if dimanche else "(Vente)"))
            else:
                await self.bot.say("**Aucune donnée pour ce jour** — Elles ont peut-être expirées ou la date est trop lointaine.")
        else:
            await self.bot.say("**Date invalide** — Rentrez une date sous le format `JJ/MM/AAAA/PP` avec PP `AM` (Matin) ou `PM` (Après-midi)\n"
                               "Vous pouvez aussi laisser vite pour consulter la période en cours")


def check_folders():
    folders = ("data", "data/nooknet/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Création du fichier " + folder)
            os.makedirs(folder)


def check_files():
    if not os.path.isfile("data/nooknet/data.json"):
        fileIO("data/nooknet/data.json", "save", {"SERVERS": {},
                                                  "GLOBAL": {}})


def setup(bot):
    check_folders()
    check_files()
    n = Nooknet(bot)
    bot.add_cog(n)