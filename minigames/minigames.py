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

        L'offre doit être comprise entre 5 et 500"""
        user = ctx.message.author
        server = ctx.message.server
        cash = self.bot.get_cog("Cash").api
        base = offre
        cooldown = 10

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
                    disp = "> **Offre:** {}\n\n".format(cur.sformat(offre))
                    disp += "{}∥{}∥{}\n".format(cols[0][0], cols[1][0], cols[2][0])
                    disp += "{}∥{}∥{}**⯇**\n".format(cols[0][1], cols[1][1], cols[2][1])
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
                    if base == 7: intro = "Que ce chiffre vous porte chance."
                    if base == 69: intro = "Nice."
                    if base == 42: intro = "La réponse à la vie, l'univers et tout le reste"
                    if base == 28: intro = "Un nombre parfait pour jouer"
                    if base == 161: intro = "Le nombre d'or pour porter chance"
                    if base == 420: intro = "420BLAZEIT"
                    if base == 314: intro = "π"
                    msg = None
                    for i in range(3):
                        points = "⬥" * (i + 1)
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
                                           color=0x49d295)
                    else:
                        cash.remove_credits(user, base, "Perte à la machine à sous", ["slot"])
                        em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=disp,
                                           color=0xd24957)
                    em.set_footer(text=gaintxt.format(cur.sformat(offre)))
                    await self.bot.delete_message(msg)
                    await self.bot.say(embed=em)
                else:
                    await self.bot.say("**Cooldown** ─ Slot possible dans {}".format(cool.auto))
            else:
                await self.bot.say("**Solde insuffisant** ─ Réduisez votre offre si possible")
        else:
            await self.bot.say("Un compte ***Cash*** est nécessaire pour jouer à la machine à sous.")

    @commands.command(pass_context=True)
    async def fontaine(self, ctx):
        """Que vous réserve la fontaine aujourd'hui ?"""
        user, server = ctx.message.author, ctx.message.server
        cash = self.bot.get_cog("Cash").api
        cur = cash.get_currency(server)
        if await cash.login(user):
            if cash.enough_credits(user, 1):
                cool = cash.get_cooldown(user, "fontaine")
                if not cool:
                    intro = random.choice(["Vous lancez une pièce", "Vous déposez une pièce",
                                           "Voilà une pièce de plus dans la fontaine", "Vous jetez une pièce",
                                           "Une pièce tombe dans la fontaine"])
                    msg = None
                    for i in range(3):
                        points = "⬦" * (i + 1)
                        txt = "**Fontaine** ─ {} {}".format(intro, points)
                        if not msg:
                            msg = await self.bot.say(txt)
                        else:
                            await self.bot.edit_message(msg, txt)
                        await asyncio.sleep(0.4)

                    async def send_result(txt):
                        em = discord.Embed(description=txt, color=0xFFEADB)
                        em.set_author(name="Fontaine", icon_url=user.avatar_url)
                        await self.bot.say(embed=em)

                    event = random.randint(1, 10)
                    if 1 <= event <= 5:
                        txt = random.choice(["Et... rien ne se passe.", "Vous avez gaché votre argent.",
                                             "Vous n'avez clairement pas de chance, il ne s'est rien produit.",
                                             "Mince, c'est loupé.", "Dommage, il n'y a rien.", "Et... R. A. S.",
                                             "Comme prévu, il ne se passe rien.", "♪ Non, rien de rien... ♫",
                                             "Vous avez beau bien regarder et croiser les doigts, il ne se passe rien.",
                                             "`Erreur 402, payez davantage.`", "Vous regardez aux alentours... rien.",
                                             "Continuez de perdre votre argent inutilement.", "Dommage, loupé !",
                                             "La chance sourit aux audacieux, dit-on.", "Inutile, inutile, inutile..."])
                        cash.remove_credits(user, 1, "Fontaine", ["fontaine"])
                        cash.add_cooldown(user, "fontaine", 120)
                        await send_result(txt)
                    elif event == 6:
                        txt = random.choice(
                            ["Vous n'aviez pas vu que la fontaine était vide... Vous récuperez votre pièce.",
                             "Quelqu'un vous arrête : vous ne **devez pas** lancer des pièces dans cette fontaine ! (Vous récuperez votre pièce)",
                             "Vous changez d'avis, finalement vous gardez votre pièce.",
                             "Vous loupez bêtement la fontaine et vous récuperez la pièce...",
                             "Oups ! Dans votre confusion vous avez confondu la fontaine et vos WC. Vous récuperez la pièce.",
                             "La chose que vous avez lancé n'était peut-être pas une pièce, finalement... (Vous ne dépensez rien)"])
                        cash.add_cooldown(user, "fontaine", 60)
                        await send_result(txt)
                    elif event == 7:
                        txt = random.choice([
                            "Miracle ! Votre banquière vous informe qu'un inconnu a transféré {} crédits sur votre compte !",
                            "Vous trouvez sur le chemin du retour un ticket de loto gagnant de {} bits !",
                            "Vous trouvez sur le chemin du retour une pièce rare, valant {} bits !",
                            "Avec cette chance, vous gagnez un pari important et vous obtenez {} bits !",
                            "Vous croisez Bill Gates qui vous donne {} crédits !",
                            "Vous croisez Elon Musk qui vous donne {} crédits (et promet un tour de fusée).",
                        "Vous croisez Jeff Bezos qui vous verse {} crédits sur votre compte pour acheter votre silence sur vous-savez-quoi."])
                        cash.add_cooldown(user, "fontaine", 180)
                        val = random.randint(10, 200)
                        cash.add_credits(user, val - 1, "Fontaine", ["fontaine"])
                        await send_result(txt.format(val))
                    elif event == 8 or event == 9:
                        cash.add_cooldown(user, "fontaine", 180)
                        situation = random.randint(1, 3)

                        if situation == 1:
                            txt = "Sur le retour, vous apercevez un musicien de rue qui semble avoir remporté pas mal d'argent aujourd'hui et il a le dos tourné, occupé à arranger son instrument.\n" \
                                  "**Prenez-vous le risque de lui voler ses gains ?**"
                            em = discord.Embed(description=txt, color=0xFFEADB)
                            em.set_author(name="Fontaine", icon_url=user.avatar_url)
                            dil = await self.bot.say(embed=em)
                            await asyncio.sleep(0.1)
                            await self.bot.add_reaction(dil, "✅")
                            await self.bot.add_reaction(dil, "❎")
                            rep = await self.bot.wait_for_reaction(["✅", "❎"], message=dil, timeout=30, user=user)
                            if rep is None or rep.reaction.emoji == "❎":
                                await self.bot.delete_message(dil)
                                result = random.choice(["success", "fail"])
                                if result == "success":
                                    txt = random.choice(["En faisant demi-tour vous êtes rattrapé par un caméraman : "
                                                         "c'était une scène en caméra cachée ! Vous gagnez {} crédits pour vous dédommager.",
                                                         "Alors que vous aviez abandonné, vous recevez un appel : un remboursement inattendu de {} crédits a fait surface sur votre compte !",
                                                         "L'homme vous rattrape : il a bien vu votre intention et décide de vous donner une partie de ses gains ! (+{} crédits)"])
                                    val = random.randint(5, 30)
                                    cash.add_credits(user, val - 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format(val))
                                else:
                                    txt = random.choice(["L'homme se remet à jouer et vous restez là, à le regarder.",
                                                         "L'homme se retourne et se met à chanter du Bigflo et Oli, c'est dommage.",
                                                         "L'homme se retourne et se met à chanter du Justin Bieber, c'était pourtant mérité...",
                                                         "L'homme vous regarde d'un air louche et s'enfuit en emportant ses gains."])
                                    cash.remove_credits(user, 1, "Fontaine", ["fontaine"])
                                    await send_result(txt)
                            else:
                                await self.bot.delete_message(dil)
                                result = random.choice(["success", "fail"])
                                if result == "success":
                                    txt = random.choice(["Il ne vous a pas vu ! Vous partez avec {} crédits !",
                                                         "C'est un succès, vous récuperez {} crédits.",
                                                         "Bien joué, il ne vous a pas repéré ! Vous récuperez {} crédits !",
                                                         "Vous subtilisez avec succès {} crédits de sa gamelle !"])
                                    val = random.randint(10, 75)
                                    cash.add_credits(user, val - 1, "Fontaine",["fontaine"])
                                    await send_result(txt.format(val))
                                else:
                                    txt = random.choice([
                                        "Oups, c'est un échec cuisant. Il appelle la police et vous lui devez {} crédits...",
                                        "L'homme vous rattrape et vous perdez {} crédits, en plus de ceux que vous avez tenté de lui voler...",
                                        "~~C'est un succès~~ vous trébuchez et l'homme vous rattrape et vous tabasse. Vous perdez {} crédits.",
                                        "Une vieille dame vous assomme avec son sac alors que vous étiez en train de ramasser les pièces. A votre réveil vous aviez perdu {} crédits."])
                                    val = random.randint(20, 80)
                                    cash.remove_credits(user, val + 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format(val))
                        elif situation == 2:
                            txt = "En rentrant chez vous, une femme laisse tomber un porte-monnaie devant vous.\n" \
                                  "**Est-ce que vous le gardez ?**"
                            em = discord.Embed(description=txt, color=0xFFEADB)
                            em.set_author(name="Fontaine", icon_url=user.avatar_url)
                            dil = await self.bot.say(embed=em)
                            await asyncio.sleep(0.1)
                            await self.bot.add_reaction(dil, "✅")
                            await self.bot.add_reaction(dil, "❎")
                            rep = await self.bot.wait_for_reaction(["✅", "❎"], message=dil, timeout=30, user=user)
                            if rep is None or rep.reaction.emoji == "❎":
                                await self.bot.delete_message(dil)
                                result = random.choice(["success", "fail"])
                                if result == "success":
                                    txt = random.choice([
                                        "Vous la rattrapez et vous lui rendez le porte-monnaie. Pour vous remercier elle vous donne quelques pièces. (+{} crédits)",
                                        "Vous essayez de la rattraper mais votre embonpoint vous en empêche et elle disparaît. Finalement, vous le gardez. (+{} crédits)",
                                        "Vous lui rendez le porte-monnaie. Pour vous remercier elle vous donne un ticket de loto qui s'avère être gagnant ! (+{} crédits)"])
                                    val = random.randint(8, 40)
                                    cash.add_credits(user, val - 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format(val))
                                else:
                                    txt = random.choice([
                                        "Vous lui rendez avec succès le porte-monnaie et elle s'en va prendre un taxi de luxe.",
                                        "Vous arrivez à la rattraper, vous lui rendez le porte-monnaie mais il était de toute manière vide, il n'y avait que des photos !",
                                        "Vous tentez de la rattraper mais vous échouez. Vous regardez le porte-monnaie mais il est vide..."])
                                    cash.remove_credits(user, 1, "Fontaine", True, ["fontaine"])
                                    await send_result(txt)
                            else:
                                await self.bot.delete_message(dil)
                                result = random.choice(["success", "fail"])
                                if result == "success":
                                    txt = random.choice(
                                        ["Super ! Le porte-monnaie est plein de liquide ! Vous gagnez {} crédits.",
                                         "Le porte-monnaie est plutôt vide, mais vous vous contentez des restes. (+{} crédits)",
                                         "Vous récuperez rapidement le porte-monnaie. Miracle ! Vous y trouvez {} crédits.",
                                         "Vous vous sentez mal mais au moins, vous récuperez {} crédits !"])
                                    val = random.randint(30, 90)
                                    cash.add_credits(user, val - 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format(val))
                                else:
                                    txt = random.choice([
                                        "Vous essayez de le récuperer mais la femme s'est retournée et le ramasse avant vous. Elle vous donne une claque qui vous met K.O. (-{} crédits de frais médicaux)",
                                        "Ayant eu l'impression d'être suivie, la femme appelle la police et ceux-ci vous arrêtent en possession de son porte-monnaie ! Vous perdez {} crédits.",
                                        "Vous ramassez le porte-monnaie sur le bord du trottoir avant de vous faire renverser ! Le porte-monnaie, vide, ne vous servira pas pour payer le frais d'hospitalisation... (-{} crédits)"])
                                    val = random.randint(40, 120)
                                    cash.remove_credits(user, val + 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format(val))
                        elif situation == 3:
                            txt = "Il semblerait que la fontaine soit tombée en panne à cause de votre lancer de pièce.\n" \
                                  "**Tentez-vous de la remettre en marche ?**"
                            em = discord.Embed(description=txt, color=0xFFEADB)
                            em.set_author(name="Fontaine", icon_url=user.avatar_url)
                            dil = await self.bot.say(embed=em)
                            await asyncio.sleep(0.1)
                            await self.bot.add_reaction(dil, "✅")
                            await self.bot.add_reaction(dil, "❎")
                            rep = await self.bot.wait_for_reaction(["✅", "❎"], message=dil, timeout=30, user=user)
                            if rep is None or rep.reaction.emoji == "❎":
                                await self.bot.delete_message(dil)
                                result = random.choice(["success", "fail"])
                                if result == "success":
                                    txt = random.choice(["Vous vous en allez, sans que personne n'ai rien vu.",
                                                         "Vous faîtes semblant de n'avoir rien vu, en vous décalant discrètement sur le côté.",
                                                         "Vous vous éclipsez discrètement afin de ne pas être remarqué.",
                                                         "Vous dissumulez votre visage en courant au loin."])
                                    cash.remove_credits(user, 1, "Fontaine", True)
                                    await send_result(txt)
                                else:
                                    txt = random.choice([
                                        "Vous essayez de fuir mais un passant vous rattrape : va falloir payer la réparation ! (-{} crédits)",
                                        "Alors que vous tentez de vous éclipser discrètement, un passant vous pointe du doigt... Vous êtes repéré ! (-{} crédits)",
                                        "En tentant de fuir de manière discrète vous trébuchez sur la fontaine et vous perdez {} crédits..."])
                                    val = random.randint(40, 80)
                                    cash.remove_credits(user, val + 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format((val)))
                            else:
                                await self.bot.delete_message(dil)
                                result = random.choice(["success", "fail"])
                                if result == "success":
                                    txt = random.choice(
                                        ["Vous arrivez à déboucher le trou créé avec toutes les pièces jetées. Vous en profitez pour en prendre une poignée. (+{} crédits)",
                                            "Vous réussissez à réparer la fontaine : la mairie vous remercie avec un chèque de {} crédits.",
                                            "Grâce à votre talent (ou votre chance, qui sait ?) vous réussissez à réparer la fontaine. Pour vous récompenser, la ville vous verse {} crédits."])
                                    val = random.randint(40, 100)
                                    cash.add_credits(user, val - 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format(val))
                                else:
                                    txt = random.choice(
                                        ["Vous tentez de déboucher la fontaine mais c'est un échec cuisant."
                                         " Vous allez devoir payer les techniciens qui vont le faire à votre place. (-{} crédits)",
                                         "Après avoir essayé plusieurs fois, vous abandonnez. La ville vous demande alors de payer {} crédits de frais de réparation.",
                                         "Malheureusement pour vous, un touriste qui passait faire la "
                                         "même chose que vous s'est énervé de voir la fontaine dans un tel état et vous casse le nez. (-{} crédits de frais médicaux)"])
                                    val = random.randint(20, 60)
                                    cash.remove_credits(user, val + 1, "Fontaine", ["fontaine"])
                                    await send_result(txt.format(val))
                    else:
                        txt = random.choice(
                            ["Tout d'un coup vous avez le vertige... vous tombez dans les pommes... (-{} crédits)",
                             "Un policier vous arrête : c'est interdit de lancer des pièces dans une fontaine historique ! Vous recevez une amende de {} crédits.",
                             "Exaspéré de voir qu'il ne se produit rien, vous donnez un coup de pied sur un rocher : vous vous brisez la jambe, ça va coûter cher en frais médicaux ! (-{} crédits)",
                             "Exaspéré de voir qu'il ne s'est rien produit, vous roulez à 110 sur une route à 80 : vous recevez une amende de {} crédits le lendemain.",
                             "Votre banquier vous appelle : il y a eu une erreur concernant votre dernier virement, vous allez devoir payer de nouveau... (-{} crédits)",
                             "Alors que vous passiez dans une rue étroite, un rocher en forme de croix vous tombe dessus. Vous vous réveillez à l'hopital alors que votre meilleur ami criait votre nom. (-{} crédits)"])
                        val = random.randint(10, 80)
                        cash.remove_credits(user, val + 1, "Fontaine", ["fontaine"])
                        await send_result(txt.format(val))
                else:
                    txt = random.choice(["Vous êtes trop fatigué pour lancer des pièces dans une fontaine...",
                                         "La fontaine est fermée pour travaux ",
                                         "Une impressionnante queue vous empêche de faire un voeux.",
                                         "Vous n'allez quand même pas passer la journée à lancer des pièces, si ?",
                                         "Il semblerait que la chance, ça se mérite.",
                                         "**P A S  E N C O R E.**",
                                         "Ceci est un easter-egg.",
                                         "La fontaine n'est pas encore prête à vous accueillir.",
                                         "`Une fontaine est d'abord le lieu d'une source, d'une « eau vive qui sort "
                                         "de terre », selon le premier dictionnaire de l'Académie française. C'est "
                                         "également une construction architecturale, généralement accompagnée d'un bassin, d'où jaillit de l'eau.`",
                                         "Vous ne semblez pas assez patient pour mériter cette action.",
                                         "Où trouvez-vous tout ce temps pour gâcher votre argent comme ça ?!",
                                         "Et puis d'ailleurs, elle vient d'où cette pratique qui consiste à jeter de l'argent dans une fontaine ?",
                                         "**Le saviez-vous** : la coutume de lancer une pièce dans la fontaine vient de la *fontana di Trevi* à Rome.\nIl est de coutume de jeter une pièce de monnaie par le bras droit en tournant le dos à la fontaine avant de quitter « la ville éternelle », une superstition associée à la fontaine étant que celui qui fait ce geste est assuré de revenir dans la capitale italienne afin de retrouver cette pièce."])
                    txt += " (Cooldown {})".format(cool.auto)
                    await self.bot.say(txt)


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