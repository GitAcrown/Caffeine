import operator
import os
import re
from datetime import datetime

import discord
import instaloader
import wikipedia
import wikipediaapi
from discord.ext import commands

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class Misc:
    """Outils divers destinés à faciliter certaines actions"""
    def __init__(self, bot):
        self.bot = bot
        self.data = dataIO.load_json("data/misc/data.json")
        self.cache = {"instaload": False}
        self.instaload = instaloader.Instaloader()

    def save(self):
        fileIO("data/misc/data.json", "save", self.data)

    def get_server(self, server):
        if server.id not in self.data:
            self.data[server.id] = {}
            self.save()
        return self.data[server.id]

    def get_setting(self, server, config, default = None):
        data = self.get_server(server)
        if config.lower() not in data:
            data[config.lower()] = default
        return data[config.lower()]

    def add_iam_role(self, role):
        server = role.server
        rolelist = self.get_setting(server, "iam_roles", [])
        if role.id not in rolelist:
            rolelist.append(role.id)
            self.save()
            return True
        return False

    def rem_iam_role(self, role):
        server = role.server
        rolelist = self.get_setting(server, "iam_roles", [])
        if role.id in rolelist:
            rolelist.remove(role.id)
            self.save()
            return True
        return False

    def purge_iam_roles(self, server):
        rolelist = self.get_setting(server, "iam_roles", [])
        for r in rolelist:
            if r not in [r.id for r in server.roles]:
                del rolelist[r]
        self.save()

    def guess_role(self, server, guess, max_tol: int = 0):
        roles = [r for r in server.roles if r.name != "@everyone"]
        if roles:
            guess = self.normalize(guess.lower())
            gl = []
            for r in roles:
                name = self.normalize(r.name.lower())
                if max_tol:
                    if self.leven(guess, name) <= max_tol:
                        gl.append([self.leven(guess, name), r])
                else:
                    gl.append([self.leven(guess, name), r])
            if gl:
                sgl = sorted(gl, key=operator.itemgetter(0))
                if sgl[0]:
                    return sgl[0][1]
        return None

    def detect_roles_in_msg(self, server, msg, max_tol: int = 0):
        roles = [r for r in server.roles if r.name != "@everyone"]
        if roles:
            rlist = []
            for w in msg.split(" "):
                guess = self.guess_role(server, w, max_tol)
                if guess:
                    rlist.append(guess)
            return rlist
        return None


    def leven(self, s1, s2):
        if len(s1) < len(s2):
            return self.leven(s2, s1)
        # len(s1) >= len(s2)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[
                                 j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def normalize(self, txt):
        ch1 = "àâçéèêëîïôöùûüÿ"
        ch2 = "aaceeeeiioouuuy"
        final = []
        for l in txt.lower():
            if l in ch1:
                final.append(ch2[ch1.index(l)])
            else:
                final.append(l)
        return "".join(final)


    @commands.group(name="iam", aliases=["iamnot"], pass_context=True, invoke_without_command=True, no_pm=True)
    async def _iam(self, ctx, role: discord.Role):
        """Auto-attribution de rôles

        Pour configurer la liste des rôles -> ;iam set"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.iam_get, role=role)

    @_iam.command(name="list", pass_context=True)
    async def iam_list(self, ctx):
        """Affiche les rôles auto-attribuables disponibles"""
        server = ctx.message.server
        user = ctx.message.author
        sys = self.get_setting(server, "iam_roles", [])
        if sys:
            txt = ""
            for r in sys:
                role = discord.utils.get(server.roles, id=r)
                rolename = role.mention if role.mentionable else "**@{}**".format(role.name)
                txt += "• {}\n".format(rolename)
        else:
            txt = "Aucun rôle n'est disponible"
        em = discord.Embed(title="Liste des rôles auto-attribuables", description=txt)
        em.set_footer(text="Obtenir un rôle = ;iam <nom du rôle>")
        await self.bot.say(embed=em)

    @_iam.command(name="get", pass_context=True, no_pm=True)
    async def iam_get(self, ctx, role: discord.Role = None):
        """Permet de s'attribuer ou se retirer un rôle"""
        server = ctx.message.server
        user = ctx.message.author
        sys = self.get_setting(server, "iam_roles", [])
        self.purge_iam_roles(server)
        if sys:
            if role:
                if role.id in sys and role in server.roles:
                    try:
                        if role in user.roles:
                            await self.bot.remove_roles(user, role)
                            await self.bot.say("**Rôle `{}` retiré** ─ Vous ne disposez désormais plus de ce rôle.".format(role.name))
                        else:
                            await self.bot.add_roles(user, role)
                            await self.bot.say("**Rôle `{}` ajouté** ─ Vous disposez désormais de ce rôle.".format(role.name))
                    except:
                        await self.bot.say(
                            "**Permissions manquantes** ─ Je n'ai pas le droit de vous attribuer/retirer ce rôle")
                else:
                    await self.bot.say("**Rôle inconnu** ─ Il n'existe pas ou il n'est pas auto-attribuable")
            else:
                txt = ""
                n = 1
                rolelist = []
                for r in sys:
                    role = discord.utils.get(server.roles, id=r)
                    rolelist.append([n, role])
                    rolename = role.mention if role.mentionable else "**@{}**".format(role.name)
                    if role in user.roles:
                        txt += "**{}**. {} (possédé)\n".format(n, rolename)
                    else:
                        txt += "**{}**. {}\n".format(n, rolename)
                    n += 1
                em = discord.Embed(title="Menu ─ Rôles auto-attribuables", description=txt)
                em.set_footer(text="Tapez le nombre correspondant au rôle que vous voulez vous ajouter/retirer")
                msg = await self.bot.say(embed=em)

                rep = await self.bot.wait_for_message(author=user, channel=msg.channel,
                                                      timeout=30)
                if rep is None:
                    await self.bot.delete_message(msg)
                elif rep.content in [str(i[0]) for i in rolelist]:
                    i = [i for i in rolelist if str(i[0]) == rep.content][0]
                    role = i[1]
                    try:
                        if role in user.roles:
                            await self.bot.remove_roles(user, role)
                            await self.bot.say("**Rôle `{}` retiré** ─ Vous ne disposez désormais plus de ce rôle.".format(role.name))
                        else:
                            await self.bot.add_roles(user, role)
                            await self.bot.say("**Rôle `{}` ajouté** ─ Vous disposez désormais de ce rôle.".format(role.name))
                    except:
                        await self.bot.say("**Permissions manquantes** ─ Je n'ai pas le droit de vous attribuer/retirer ce rôle")
                elif rep.content.lower() in ["stop", "quit", "quitter", "0"]:
                    await self.bot.delete_message(msg)
                else:
                    await self.bot.say("**Réponse invalide** ─ Réessayez en tapant un nombre après avoir fait `;iam get`")
                    await self.bot.delete_message(msg)
        else:
            await self.bot.say("Aucun rôle n'a encore été configuré pour être attribuable par ce biais.")

    @_iam.command(name="set", pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def iam_set(self, ctx, role: discord.Role):
        """Configure un rôle pour qu'il puisse être ajouté et retiré seul par un membre

        Utilisez ;iam list pour voir les rôles disponibles"""
        server = ctx.message.server
        if role in server.roles:
            if self.add_iam_role(role):
                await self.bot.say("**Rôle ajouté** ─ Les membres pourront se l'attribuer avec `;iam {}`".format(
                    role.name))
            elif self.rem_iam_role(role):
                await self.bot.say("**Rôle retiré** ─ Les membres ne pourront plus s'attribuer le rôle {}".format(
                    role.name))
            else:
                await self.bot.say("Impossible d'ajouter ou retirer ce rôle, il est peut-être supprimé ou inaccessible.")
        else:
            await self.bot.say("Ce rôle n'existe pas sur ce serveur.")

    @_iam.command(name="auto", pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def iam_autoget(self, ctx):
        """Active/Désactive l'attribution automatique des rôles (figurant dans la liste des rôles auto-attribuables) à un membre qui le demanderait à un modérateur

        - Un nom incomplet sera complété automatiquement si assez proche du réel nom du rôle demandé
        - Envoie un log (si configuré) lorsqu'un rôle est attribué
        Par défaut désactivé"""
        server = ctx.message.server
        sys = self.get_setting(server, "iam_auto", False)
        if sys == True:
            self.data[server.id]["iam_auto"] = False
            self.save()
            await self.bot.say("**Attribution automatique désactivée** ─ Les membres n'auront pas automatiquement un rôle en vous mentionnant")
        else:
            self.data[server.id]["iam_auto"] = True
            self.save()
            await self.bot.say(
                "**Attribution automatique activée** ─ Les membres obtiendront automatiquement le rôle demandé (s'il est configuré) lorsqu'on vous mentionnera (les modérateurs)")


    @commands.command(aliases=["mgr"], pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def magicrole(self, ctx, user: discord.Member, role):
        """Attribue/retire à un membre désigné le rôle souhaité et devine de quel rôle il s'agit si le nom est incomplet

        Attention, cette commande ignore les rôles configurés pour 'iam', elle pioche dans tous les rôles du serveur sans exception"""
        server = ctx.message.server
        guess = self.guess_role(server, role)
        if guess:
            if self.leven(self.normalize(guess.name.lower()), self.normalize(role.lower())) <= len(guess.name) - 1:
                try:
                    if guess in user.roles:
                        await self.bot.remove_roles(user, guess)
                        await self.bot.say("**Rôle `{}` retiré** ─ Ce rôle a été détecté et retiré à {}".format(guess.name, user.name))
                    else:
                        await self.bot.add_roles(user, guess)
                        await self.bot.say(
                            "**Rôle `{}` attribué** ─ Ce rôle a été détecté et attribué à {}".format(guess.name, user.name))
                except:
                    await self.bot.say("**Opération refusée** ─ J'ai détecté le rôle `{}` mais impossible de le donner/retirer pour ce membre".format(guess.name))
            else:
                await self.bot.say(
                    "**Rôle inconnu/trop éloigné** ─ J'ai peut-être trouvé le rôle demandé, mais par mesure de sécurité (car trop éloigné de son nom réel) l'opération n'est pas réalisée.")
        else:
            await self.bot.say("**Rôle inconnu/trop éloigné** ─ J'ai peut-être trouvé le rôle demandé, mais par mesure de sécurité (car trop éloigné de son nom réel) l'opération n'est pas réalisée.")

    @commands.command(pass_context=True)
    async def allavatars(self, ctx, role: discord.Role):
        """Ecrit dans un fichier txt les avatars de toutes les personnes possédant le(s) rôle(s) défini(s)"""
        server = ctx.message.server
        if role in server.roles:
            txt = ""
            for u in server.members:
                if role in u.roles:
                    if u.avatar_url:
                        txt += "{}\t{}\n".format(str(u), u.avatar_url)
            if txt:
                filename = "AVATARS_{}.txt".format(role.name.upper())
                file = open("data/misc/temp/{}".format(filename), "w", encoding="UTF-8")
                file.write(txt)
                file.close()
                try:
                    await self.bot.send_file(ctx.message.channel, "data/misc/temp/{}".format(filename))
                    os.remove("data/misc/temp/{}".format(filename))
                except Exception as e:
                    await self.bot.say("**Impossible d'upload le fichier TXT des avatars** — `{}`".format(e))
        else:
            await self.bot.say("Rôle non reconnu sur ce serveur")


    def redux(self, string: str, separateur: str = ".", limite: int = 2000):
        n = -1
        while len(separateur.join(string.split(separateur)[:n])) >= limite:
            n -= 1
        return separateur.join(string.split(separateur)[:n]) + separateur

    def wiki(self, recherche: str, langue: str = 'fr', souple: bool = True):
        wikipedia.set_lang(langue)
        wikiplus = wikipediaapi.Wikipedia(langue)
        s = wikipedia.search(recherche, 8, True)
        try:
            if s[1]:
                r = s[1]
            else:
                r = s[0][0] if s[0] else None
            if r:
                page = wikipedia.page(r, auto_suggest=souple)
                images = page.images
                image = images[0]
                for i in images:
                    if i.endswith(".png") or i.endswith(".gif") or i.endswith(".jpg") or i.endswith(".jpeg"):
                        image = i
                resum = page.summary
                if not resum:
                    resum = "Contenu indisponible"
                if len(resum) + len(r) > 1995:
                    resum = self.redux(resum, limite=1960)
                p = wikiplus.page(r)
                resum += "\n\n[En savoir plus...]({})".format(p.fullurl)
                em = discord.Embed(title=r.capitalize(), description=resum, color=0xeeeeee)
                em.set_thumbnail(url=image)
                em.set_footer(text="Similaire: {}".format(", ".join(s[0])))
                return em
            else:
                if langue == "en":
                    return "Impossible de trouver {}".format(recherche)
                else:
                    return self.wiki(recherche, "en")
        except:
            if langue == "en":
                if souple:
                    if s[0]:
                        if len(s[0]) >= 2:
                            wikipedia.set_lang("fr")
                            s = wikipedia.search(recherche, 3, True)
                            return "**Introuvable** | Réessayez peut-être avec *{}* ?".format(s[0][1])
                        else:
                            return "**Introuvable** | Aucun résultat pour *{}*".format(recherche)
                    else:
                        return "**Introuvable** | Aucun résultat pour *{}*".format(recherche)
                else:
                    return self.wiki(recherche, "en", False)
            else:
                if souple:
                    return self.wiki(recherche, "en")
                else:
                    return self.wiki(recherche, "fr", False)

    @commands.command(name="wikipedia", aliases=["wiki"], pass_context=True)
    async def wiki_search(self, ctx, *search):
        """Recherche sur Wikipedia (FR si dispo. sinon EN)"""
        search = " ".join(search)
        await self.bot.send_typing(ctx.message.channel)
        result = self.wiki(search)
        if result:
            if type(result) is str:
                await self.bot.say(result)
            else:
                await self.bot.say(embed=result)
        else:
            await self.bot.say("**Erreur** | Aucun résultat ne peut être affiché")

    def load_instagram_post(self, code: str):
        if not self.cache["instaload"]:

            self.instaload.login("atombotapp", "Quelquechose")
            self.instaload.save_session_to_file()
            self.cache["instaload"] = True
        else:
            self.instaload.load_session_from_file("atombotapp")

        post = instaloader.Post.from_shortcode(self.instaload.context, code)
        profile = post.owner_profile
        data = {"owner": {"name": profile.full_name,
                          "username": profile.username,
                          "picture": profile.profile_pic_url},
                "images": [],
                "videos": [],
                "short_url": post.shortcode,
                "timestamp": post.date_utc}

        if post.typename == "GraphSidecar":
            nodes = post.get_sidecar_nodes()
            for node in nodes:
                if node.is_video:
                    data["videos"].append(node.video_url)
                else:
                    data["images"].append(node.display_url)
        elif post.typename == "GraphVideo":
            data["videos"].append(post.video_url)
        else:
            data["images"].append(post.url)
        return data

    """def loot_instagram_post(self, url: str):
        looter = PostLooter(url)
        looter.dump_only = True
        looter.logout()
        infos = looter.info
        data = {"owner": {"name": infos["owner"]["full_name"],
                          "username": infos["owner"]["username"],
                          "picture": infos["owner"]["profile_pic_url"]},
                "images": [],
                "videos": [],
                "short_url": "https://www.instagram.com/p/" + infos["shortcode"],
                "timestamp": datetime.utcfromtimestamp(infos["taken_at_timestamp"])}
        if "edge_sidecar_to_children" in infos:  # plusieurs medias
            medias = infos["edge_sidecar_to_children"]["edges"]
            for media in medias:
                m = media["node"]
                if m["is_video"]:
                    data["videos"].append(m["video_url"])
                else:
                    data["images"].append(m["display_url"])
        elif infos["__typename"] == "GraphImage":
            data["images"].append(infos["display_url"])
        elif infos["__typename"] == "GraphVideo":
            data["videos"].append(infos["video_url"])
        return data"""

    async def on_mess(self, message):
        if message.server:

            if "https://www.instagram.com/p/" in message.content:
                r = re.compile(r'https:\/\/www\.instagram\.com\/p\/([\w\-]+)\/?.*?', re.DOTALL | re.IGNORECASE).findall(
                    message.content)
                if r:
                    code = r[0]
                    data = self.load_instagram_post(code)
                    medias = data["images"] + data["videos"]
                    n = 1
                    for media in medias: # en cas où plusieurs médias
                        print(media)
                        em = discord.Embed(color=message.author.color, timestamp=data["timestamp"])
                        if n == 1:
                            em.set_author(name="{} (@{})".format(data["owner"]["name"], data["owner"]["username"]),
                                          icon_url=data["owner"]["picture"], url=data["short_url"])
                        if media in data["images"]:
                            em.set_image(url=media)
                            em.set_footer(text="Media {}/{}".format(n, len(medias)))
                            await self.bot.send_message(message.channel, embed=em)
                        else:
                            txt = "Media {}/{}\n".format(n, len(medias)) + media
                            await self.bot.send_message(message.channel, txt)
                        n += 1


            if not message.author.bot:
                user = message.author
                api = self.bot.get_cog("Sonar").api
                if self.get_setting(message.server, "iam_auto", False):
                    if self.get_setting(message.server, "iam_roles", []):
                        rolelist = self.get_setting(message.server, "iam_roles", [])
                        if message.mentions:
                            mention = message.mentions[0]
                            if mention.server_permissions.manage_roles and not user.server_permissions.manage_roles:
                                detected = self.detect_roles_in_msg(message.server, message.content, 2)
                                notif = []
                                if detected:
                                    print(detected)
                                    for g in detected:
                                        if g.id in rolelist:
                                            try:
                                                if g not in user.roles:
                                                    await self.bot.add_roles(user, g)
                                                    await self.bot.add_reaction(message, "✅")
                                                    if g.id not in notif:
                                                        if api.preload_channel(user.server, "app_autoattrib"):
                                                            print("log auto_attrib")
                                                            em = discord.Embed(
                                                                description="A obtenu le rôle {} automatiquement après demande à un modérateur.".format(g.name),
                                                                color=0x7B68EE, timestamp=datetime.utcnow())  # Violet
                                                            em.set_author(name=str(user) + " ─ Attribution automatique de rôle", icon_url=user.avatar_url)
                                                            em.set_footer(text="Demandeur ID: {}".format(user.id))
                                                            await api.publish_log(user.server, "app_autoattrib",
                                                                                  em)
                                                            notif.append(g.id)
                                            except:
                                                pass

def check_folders():
    if not os.path.exists("data/misc"):
        print("Création du dossier MISC...")
        os.makedirs("data/misc")

    if not os.path.exists("data/misc/temp"):
        print("Création du dossier MISC/temp...")
        os.makedirs("data/misc/temp")


def check_files():
    if not os.path.isfile("data/misc/data.json"):
        print("Création de misc/data.json")
        fileIO("data/misc/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Misc(bot)
    bot.add_listener(n.on_mess, "on_message")
    bot.add_cog(n)