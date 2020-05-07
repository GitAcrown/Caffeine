import asyncio
import os
import random

import discord
from discord.ext import commands

from .utils.dataIO import fileIO, dataIO


class Minigames:
    """Regroupement de mini-jeux compatibles avec l'économie"""
    def __init__(self, bot):
        self.bot = bot
        self.data = dataIO.load_json("data/minigames/data.json")

    def save(self):
        fileIO("data/minigames/data.json", "save", self.data)

    """def get_server(self, server):
        if server.id not in self.data:
            self.data[server.id] = {}
            self.save()
        return self.data[server.id]"""

    @commands.command(pass_context=True, aliases=["mas"])
    async def slot(self, ctx, offre: int = None):
        """Jouer à la machine à sous

        L'offre doit être comprise entre 10 et 500"""
        user = ctx.message.author
        server = ctx.message.server
        cash = self.bot.get_cog("Cash").api

        if not offre:
            txt = ":100: x3 = Offre x 50\n" \
                  ":gem: x3 = Offre x 20\n" \
                  ":gem: x2 = Offre X 10\n" \
                  ":four_leaf_clover: x3 = Offre x 12\n" \
                  ":four_leaf_clover: x2 = Offre x 4\n" \
                  "**fruit** x3 = Offre x 6\n" \
                  "**fruit** x2 = Offre x 3\n" \
                  ":zap: x1 ou x2 = Gains nuls\n" \
                  ":zap: x3 = Offre x 100"
            em = discord.Embed(title="Gains possibles", description=txt)
            await self.bot.say(embed=em)
            return
        if not 5 <= offre <= 500:
            await self.bot.say("**Offre invalide** ─ Elle doit être comprise entre 5 et 500.")
            return
        base = offre
        cooldown = 10
        cur = cash.get_currency(server)
        if await cash.login(user):
            if cash.enough_credits(user, offre):
                cool = cash.get_cooldown(user, "slot")
                if not cool:
                    cash.add_cooldown(user, "slot", cooldown)
                    roue = [":zap:", ":gem:", ":cherries:", ":strawberry:", ":watermelon:", ":tangerine:", ":lemon:",
                            ":four_leaf_clover:", ":100:"]
                    plus_after = [":zap:", ":gem:", ":cherries:"]
                    plus_before = [":lemon:", ":four_leaf_clover:", ":100:"]
                    roue = plus_before + roue + plus_after
                    cols = []
                    for i in range(3):
                        n = random.randint(3, 11)
                        cols.append([roue[n - 1], roue[n], roue[n + 1]])
                    centre = [cols[0][1], cols[1][1], cols[2][1]]
                    disp = "**Offre:** {}\n\n".format(cur.sformat(offre))
                    disp += "{}∥{}∥{}\n".format(cols[0][0], cols[1][0], cols[2][0])
                    disp += "{}∥{}∥{}**⇦**\n".format(cols[0][1], cols[1][1], cols[2][1])
                    disp += "{}∥{}∥{}\n".format(cols[0][2], cols[1][2], cols[2][2])
                    c = lambda x: centre.count(":{}:".format(x))
                    if ":zap:" in centre:
                        if c("zap") == 3:
                            offre *= 100
                            gaintxt = "3x ⚡ ─ Tu gagnes {}"
                        else:
                            offre = 0
                            gaintxt = "Tu t'es fait zap ⚡ ─ Tu perds ta mise !"
                    elif c("100") == 3:
                        offre *= 50
                        gaintxt = "3x 💯 ─ Tu gagnes {}"
                    elif c("gem") == 3:
                        offre *= 20
                        gaintxt = "3x 💎 ─ Tu gagnes {}"
                    elif c("gem") == 2:
                        offre *= 10
                        gaintxt = "2x 💎 ─ Tu gagnes {}"
                    elif c("four_leaf_clover") == 3:
                        offre *= 12
                        gaintxt = "3x 🍀 ─ Tu gagnes {}"
                    elif c("four_leaf_clover") == 2:
                        offre *= 4
                        gaintxt = "2x 🍀 ─ Tu gagnes {}"
                    elif c("cherries") == 3 or c("strawberry") == 3 or c("watermelon") == 3 or c("tangerine") == 3 or c(
                            "lemon") == 3:
                        offre *= 6
                        gaintxt = "3x un fruit ─ Tu gagnes {}"
                    elif c("cherries") == 2 or c("strawberry") == 2 or c("watermelon") == 2 or c("tangerine") == 2 or c(
                            "lemon") == 2:
                        offre *= 3
                        gaintxt = "2x un fruit ─ Tu gagnes {}"
                    else:
                        offre = 0
                        gaintxt = "Perdu ─ Tu perds ta mise !"

                    intros = ["Ça tourne", "Croisez les doigts", "Peut-être cette fois-ci", "Alleeeezzz",
                              "Ah les jeux d'argent", "Les dés sont lancés", "Il vous faut un peu de CHANCE",
                              "C'est parti", "Bling bling", "Le début de la richesse"]
                    intro = random.choice(intros)
                    if base == 69: intro = "Oh, petit cochon"
                    if base == 42: intro = "La réponse à la vie, l'univers et tout le reste"
                    if base == 28: intro = "Un nombre parfait pour jouer"
                    if base == 161: intro = "Le nombre d'or pour porter chance"
                    if base == 420: intro = "420BLAZEIT"
                    if base == 314: intro = "π"
                    msg = None
                    for i in range(3):
                        points = "⯌" * (i + 1)
                        txt = "**Machine à sous** ─ {} {}".format(intro, points)
                        if not msg:
                            msg = await self.bot.say(txt)
                        else:
                            await self.bot.edit_message(msg, txt)
                        await asyncio.sleep(0.4)
                    if offre > 0:
                        gain = offre - base
                        cash.add_credits(user, gain, "Gain à la machine à sous", ["slot"])
                        em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=disp,
                                           color=0xd4af37)
                    else:
                        cash.remove_credits(user, base, "Perte à la machine à sous", ["slot"])
                        em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=disp,
                                           color=0xd4af37)
                    em.set_footer(text=gaintxt.format(cur.sformat(offre)))
                    await self.bot.delete_message(msg)
                    await self.bot.say(embed=em)
                else:
                    await self.bot.say("**Cooldown** ─ Slot possible dans {}".format(cool.string))
            else:
                await self.bot.say("**Solde insuffisant** ─ Réduisez votre offre si possible")
        else:
            await self.bot.say("Un compte Wallet est nécessaire pour jouer à la machine à sous.")


def check_folders():
    if not os.path.exists("data/minigames"):
        print("Création du dossier MINIGAMES...")
        os.makedirs("data/minigames")


def check_files():
    if not os.path.isfile("data/minigames/data.json"):
        print("Création de minigames/data.json")
        fileIO("data/minigames/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Minigames(bot)
    bot.add_cog(n)