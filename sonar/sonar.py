import os
import time
from datetime import datetime

import discord
from __main__ import send_cmd_help
from cogs.utils.dataIO import fileIO, dataIO
from discord.ext import commands

from .utils import checks

CHANNELS = {"message_add": "Diffuse à chaque message posté",
            "message_delete": "Diffuse à chaque message supprimé",
            "message_edit": "Diffuse lors de l'édition d'un message",
            "voice_join": "Diffuse lorsqu'un membre rejoint un salon vocal",
            "voice_quit": "Diffuse lorsqu'un membre quitte un salon vocal",
            "voice_update": "Diffuse lorsqu'un membre change de salon vocal",
            "voice_mute": "Diffuse lorsqu'un membre est mute/demute",
            "voice_deaf": "Diffuse lorsqu'un membre est rendu sourd ou non",
            "member_join": "Diffuse lorsqu'un membre rejoint le serveur",
            "member_quit": "Diffuse lorsqu'un membre quitte le serveur (de lui-même ou via un kick)",
            "member_ban": "Diffuse lorsqu'un membre est banni",
            "member_unban": "Diffuse lorsqu'un membre est débanni",
            "member_update_name": "Diffuse lorsqu'un membre change son pseudo",
            "member_update_nickname": "Diffuse lorsqu'un membre change son surnom (nom visible)",
            "member_update_avatar": "Diffuse lorsqu'un membre change son avatar",
            "member_update_status": "Diffuse lorsqu'un membre change son statut (jeu ou personnalisé)",
            "warning_low": "Diffuse des avertissements de basse priorité",
            "warning_high": "Diffuse des avertissements de haute priorité"}


class SonarAPI:
    def __init__(self, bot, path):
        self.bot = bot
        self.data = dataIO.load_json(path)
        self.last_save = 0
        self.preload = {}

    def save(self, force = False):
        if time.time() >= self.last_save + 30 or force:
            fileIO("data/sonar/data.json", "save", self.data)

    def get_server(self, server, section = None):
        if server.id not in self.data:
            self.data[server.id] = {"SETTINGS": {"logs_groups": {}},
                                    "LOGS": {}}
            self.save(True)
        return self.data[server.id][section.upper()] if section else self.data[server.id]


    def preload_channel(self, server, group):
        superkey = "{}:{}".format(server.id, group)
        if superkey not in self.preload:
            data = self.get_server(server, "settings")["logs_groups"]
            if group in data:
                self.preload[superkey] = self.bot.get_channel(data[group])
            else:
                return None
        return self.preload[superkey]

    def reset_server_preload(self, server):
        data = self.get_server(server, "settings")["logs_groups"]
        for key in self.preload:
            if key.startswith(str(server.id)):
                del self.preload[key]
        return True

    async def publish_log(self, server, group, embed):
        channel = self.preload_channel(server, group)
        if channel:
            await self.bot.send_message(channel, embed=embed)
            return True
        return False

    async def global_publish_log(self, group, embed):
        for sid in self.data:
            server = self.bot.get_server(sid)
            if self.preload_channel(server, group):
                await self.publish_log(server, group, embed)
        return True


class Sonar:
    """Logs et statistiques"""
    def __init__(self, bot):
        self.bot = bot
        self.api = SonarAPI(bot, "data/sonar/data.json")
        self.cache = {"servers_last_warning": 0}

    @commands.group(name="logs", aliases=["sonar"], pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def _logs(self, ctx):
        """Commandes de gestion de logs avancés"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_logs.command(pass_context=True)
    async def info(self, ctx):
        """Affiche la description des différents canaux de logs"""
        desc = ""
        for e in CHANNELS:
            desc += "`{}` • *{}*\n".format(e, CHANNELS[e])
        em = discord.Embed(title="Canaux de logs disponibles", description=desc, color=0xf4f7f7)
        em.set_footer(text="Attribuez des canaux à des salons avec ;logs assign et ;logs unassign")
        await self.bot.say(embed=em)

    @_logs.command(pass_context=True)
    async def assign(self, ctx, *liste):
        """Permet d'attribuer des canaux de logs au channel de la commande (canaux séparés par un espace)

        Ne rien mettre affiche la liste des canaux assignés à ce salon"""
        server, channel = ctx.message.server, ctx.message.channel
        data = self.api.get_server(server, "settings")
        if liste:
            secu = data["logs_groups"]
            verif = []
            for i in liste:
                i = i.lower()
                if i in CHANNELS:
                    if i not in data["logs_groups"]:
                        data["logs_groups"][i] = channel.id
                        verif.append(i)
            if len(verif) == len(liste):
                await self.bot.say("**Attribution réussie** • Les canaux suivants sont désormais attachés au salon "
                                   "{} :\n".format(channel.mention) + ", ".join(verif))
                self.api.reset_server_preload(server)
                self.api.save()
            else:
                await self.bot.say("**Attribution incomplète** • Vérifiez que les noms des canaux sont corrects et "
                                   "séparés d'un espace s'il y en a plusieurs, puis réessayez.")
                data["logs_groups"] = secu
        else:
            desc = ""
            if data["logs_groups"]:
                for can in data["logs_groups"]:
                    if data["logs_groups"][can] == channel.id:
                        desc += "• `{}`\n".format(can)
                if desc:
                    em = discord.Embed(title="Canaux de logs attachés au salon #{}".format(channel.name),
                                       description=desc, color=0xf4f7f7)
                    em.set_footer(text="Attribuez des canaux à ce salon avec ;logs assign suivi de la liste des canaux à ajouter")
                    await self.bot.say(embed=em)
                    return
            await self.bot.say("**Aucun canal de log est attribué à ce salon**")

    @_logs.command(pass_context=True)
    async def unassign(self, ctx, *liste):
        """Permet de retirer des canaux de logs de ce salon (canaux séparés par un espace)

        Ne rien mettre affiche la liste des canaux assignés à ce salon"""
        server, channel = ctx.message.server, ctx.message.channel
        data = self.api.get_server(server, "settings")
        if liste:
            secu = data["logs_groups"]
            verif = []
            for i in liste:
                i = i.lower()
                if i in CHANNELS:
                    if i in data["logs_groups"]:
                        del data["logs_groups"][i]
                        verif.append(i)
            if len(verif) == len(liste):
                await self.bot.say("**Désattribution réussie** • Les canaux suivants sont désormais détachés du salon "
                                   "{} :\n".format(channel.mention) + ", ".join(verif))
                self.api.reset_server_preload(server)
                self.api.save()
            else:
                await self.bot.say("**Désattribution incomplète** • Vérifiez que les noms des canaux sont corrects et "
                                   "séparés d'un espace s'il y en a plusieurs, puis réessayez.")
                data["logs_groups"] = secu
        else:
            desc = ""
            if data["logs_groups"]:
                for can in data["logs_groups"]:
                    if data["logs_groups"][can] == channel.id:
                        desc += "• `{}`\n".format(can)
                if desc:
                    em = discord.Embed(title="Canaux de logs attachés au salon #{}".format(channel.name),
                                       description=desc, color=0xf4f7f7)
                    em.set_footer(
                        text="Attribuez des canaux à ce salon avec ;logs assign suivi de la liste des canaux à ajouter")
                    await self.bot.say(embed=em)
                    return
            await self.bot.say("**Aucun canal de log est attribué à ce salon**")

    @_logs.command(name="reset", pass_context=True)
    async def reset_logs(self, ctx):
        """Reset les canaux de logs afin de tous les détacher de leurs salons respectifs"""
        self.api.get_server(ctx.message.server, "settings")["logs_groups"] = {}
        self.api.reset_server_preload(ctx.message.server)
        self.api.save(True)
        await self.bot.say("**Canaux réinitialisés avec succès**")


    async def on_msg_add(self, message):
        if message.server:
            if self.api.preload_channel(message.server, "message_add"):
                em = discord.Embed(description=message.content, timestamp=message.timestamp, color= 0x63A2D8) # Bleu clair
                em.set_author(name=str(message.author) + " ─ Message posté", icon_url=message.author.avatar_url)
                em.set_footer(text="Auteur ID: {} • Msg ID: {} • Salon: #{}".format(message.author.id, message.id,
                                                                                    message.channel.name))
                await self.api.publish_log(message.server, "message_add", em)

    async def on_msg_delete(self, message):
        if message.server:
            if self.api.preload_channel(message.server, "message_delete"):
                em = discord.Embed(description=message.content, timestamp=message.timestamp,
                                   color=0xE46464)  # Rouge pastel
                em.set_author(name=str(message.author) + " ─ Message supprimé", icon_url=message.author.avatar_url)
                em.set_footer(text="Auteur ID: {} • Salon: #{}".format(message.author.id, message.channel.name))
                await self.api.publish_log(message.server, "message_delete", em)

    async def on_msg_edit(self, before, after):
        if after.server:
            if self.api.preload_channel(after.server, "message_edit"):
                msg_url = "https://discordapp.com/channels/{}/{}/{}".format(after.server.id, after.channel.id, after.id)
                em = discord.Embed(description="[Aller au message]({})".format(msg_url),
                                   timestamp=after.edited_timestamp, color=0x6ED7D3)  # Bleu pastel
                em.add_field(name="Avant", value=before.content, inline=False)
                em.add_field(name="Après", value=before.content, inline=False)
                em.set_author(name=str(after.author) + " ─ Message édité", icon_url=after.author.avatar_url)
                em.set_footer(text="Auteur ID: {} • Msg ID: {}".format(after.author.id, after.id))
                await self.api.publish_log(after.server, "message_edit", em)

    async def on_voice_update(self, before, after):
        if type(after) is discord.Member:
            ts = datetime.utcnow()

            if after.voice_channel:
                if not before.voice_channel:
                    if self.api.preload_channel(after.server, "voice_join"):
                        desc = "S'est connecté sur {}".format(after.voice.voice_channel.mention)
                        em = discord.Embed(description=desc, timestamp=ts, color=0x74D99F)  # Turquoise pastel
                        em.set_author(name=str(after) + " ─ Connexion vocale",
                                      icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {}".format(after.id))
                        await self.api.publish_log(after.server, "voice_join", em)

                elif after.voice_channel != before.voice_channel:
                    if self.api.preload_channel(after.server, "voice_update"):
                        desc = "Est passé de {} à {}".format(before.voice.voice_channel.mention,
                                                             after.voice.voice_channel.mention)
                        em = discord.Embed(description=desc, timestamp=ts, color=0xA8EEC1)  # Turquoise + clair
                        em.set_author(name=str(after) + " ─ Migration vocale",
                                      icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {}".format(after.id))
                        await self.api.publish_log(after.server, "voice_update", em)

            elif before.voice_channel:
                if not after.voice_channel:
                    if self.api.preload_channel(after.server, "voice_quit"):
                        desc = "S'est déconnecté de {}".format(before.voice.voice_channel.mention)
                        em = discord.Embed(description=desc, timestamp=ts, color=0x38C172)  # Turquoise + foncé
                        em.set_author(name=str(after) + " ─ Déconnexion vocale",
                                      icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {}".format(after.id))
                        await self.api.publish_log(after.server, "voice_quit", em)

            if after.voice_channel and before.voice_channel:
                if before.voice.mute and not after.voice.mute:
                    if self.api.preload_channel(after.server, "voice_mute"):
                        desc = "N'est plus mute".format(before.voice.voice_channel.mention)
                        em = discord.Embed(description=desc, timestamp=ts, color=0xF4CA64)  # orange
                        em.set_author(name=str(after) + " ─ Démute",
                                      icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {} • Salon: {}".format(after.id, before.voice.voice_channel.name))
                        await self.api.publish_log(after.server, "voice_mute", em)

                elif not before.voice.mute and after.voice.mute:
                    if self.api.preload_channel(after.server, "voice_mute"):
                        desc = "A été mute".format(before.voice.voice_channel.mention)
                        em = discord.Embed(description=desc, timestamp=ts, color=0xF4CA64)  # orange
                        em.set_author(name=str(after) + " ─ Mute",
                                      icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {} • Salon: {}".format(after.id, before.voice.voice_channel.name))
                        await self.api.publish_log(after.server, "voice_mute", em)

                if before.voice.deaf and not after.voice.deaf:
                    if self.api.preload_channel(after.server, "voice_deaf"):
                        desc = "N'est plus sourd".format(before.voice.voice_channel.mention)
                        em = discord.Embed(description=desc, timestamp=ts, color=0xFAE29F)  # orange clair
                        em.set_author(name=str(after) + " ─ Désassourdi",
                                      icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {} • Salon: {}".format(after.id, before.voice.voice_channel.name))
                        await self.api.publish_log(after.server, "voice_deaf", em)

                elif not before.voice.deaf and after.voice.deaf:
                    if self.api.preload_channel(after.server, "voice_deaf"):
                        desc = "A été mis sourd".format(before.voice.voice_channel.mention)
                        em = discord.Embed(description=desc, timestamp=ts, color=0xFAE29F)  # orange clair
                        em.set_author(name=str(after) + " ─ Sourd",
                                      icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {} • Salon: {}".format(after.id, before.voice.voice_channel.name))
                        await self.api.publish_log(after.server, "voice_deaf", em)

    async def user_update(self, before, after):
        if type(after) is discord.Member:
            ts = datetime.utcnow()
            if after.name != before.name:
                if self.api.preload_channel(after.server, "member_update_name"):
                    em = discord.Embed(
                        description="**{}** a changé de nom pour **{}**".format(before.name, after.name),
                        color=0xdbe2ef, timestamp=ts) # Bleu-blanc
                    em.set_author(name=str(after) + " ─ Changement de pseudo", icon_url=after.avatar_url)
                    em.set_footer(text="Membre ID: {}".format(after.id))
                    await self.api.publish_log(after.server, "member_update_name", em)

            if after.nick and before.nick:
                if after.nick != before.nick:
                    if self.api.preload_channel(after.server, "member_update_nickname"):
                        em = discord.Embed(
                            description="**{}** a changé de surnom pour **{}**".format(before.nick, after.nick),
                            color=0xfae3d9, timestamp=ts)  # Rose-blanc
                        em.set_author(name=str(after) + " ─ Changement de surnom", icon_url=after.avatar_url)
                        em.set_footer(text="Membre ID: {}".format(after.id))
                        await self.api.publish_log(after.server, "member_update_nickname", em)

            elif after.nick and not before.nick:
                if self.api.preload_channel(after.server, "member_update_nickname"):
                    em = discord.Embed(
                        description="A pris pour surnom **{}**".format(after.nick),
                        color=0xfae3d9, timestamp=ts)  # Rose-blanc
                    em.set_author(name=str(after) + " ─ Ajout d'un surnom", icon_url=after.avatar_url)
                    em.set_footer(text="Membre ID: {}".format(after.id))
                    await self.api.publish_log(after.server, "member_update_nickname", em)

            elif not after.nick and before.nick:
                if self.api.preload_channel(after.server, "member_update_nickname"):
                    em = discord.Embed(
                        description="A retiré son ancien surnom **{}**".format(after.nick),
                        color=0xfae3d9, timestamp=ts)  # Rose-blanc
                    em.set_author(name=str(after) + " ─ Retrait du surnom", icon_url=after.avatar_url)
                    em.set_footer(text="Membre ID: {}".format(after.id))
                    await self.api.publish_log(after.server, "member_update_nickname", em)

            if before.avatar_url != after.avatar_url:
                if self.api.preload_channel(after.server, "member_update_avatar"):
                    em = discord.Embed(description="A changé son avatar", color=0x212121, timestamp=ts)  # Gris foncé
                    em.set_author(name=str(after) + " ─ Retrait du surnom", icon_url=after.avatar_url)
                    em.set_thumbnail(url=after.avatar_url)
                    em.set_footer(text="Membre ID: {} • Nouvel avatar (affiché)".format(after.id))
                    await self.api.publish_log(after.server, "member_update_avatar", em)

            if before.game.name != after.game.name:
                if not before.game.name and after.game.name:
                    if self.api.preload_channel(after.server, "member_update_status"):
                        em = discord.Embed(description="A un nouveau statut `{}`".format(after.game.name), color=0xfff4e1,
                                           timestamp=ts)  # Blanc sale
                        em.set_author(name=str(after) + " ─ Nouveau statut", icon_url=after.avatar_url)
                        em.set_thumbnail(url=after.avatar_url)
                        em.set_footer(text="Membre ID: {}".format(after.id))
                        await self.api.publish_log(after.server, "member_update_status", em)
                elif before.game.name and not after.game.name:
                    if self.api.preload_channel(after.server, "member_update_status"):
                        em = discord.Embed(description="N'a plus son statut `{}`".format(after.game.name), color=0xfff4e1,
                                           timestamp=ts)  # Blanc sale
                        em.set_author(name=str(after) + " ─ Retrait du statut", icon_url=after.avatar_url)
                        em.set_thumbnail(url=after.avatar_url)
                        em.set_footer(text="Membre ID: {}".format(after.id))
                        await self.api.publish_log(after.server, "member_update_status", em)

                elif before.game.name and after.game.name:
                    if self.api.preload_channel(after.server, "member_update_status"):
                        em = discord.Embed(description="A changé son statut de `{}` pour `{}`".format(
                            before.game.name, after.game.name), color=0xfff4e1, timestamp=ts)  # Blanc sale
                        em.set_author(name=str(after) + " ─ Changement de statut", icon_url=after.avatar_url)
                        em.set_thumbnail(url=after.avatar_url)
                        em.set_footer(text="Membre ID: {}".format(after.id))
                        await self.api.publish_log(after.server, "member_update_status", em)

    async def user_join(self, user):
        if type(user) is discord.Member:
            if self.api.preload_channel(user.server, "member_join"):
                ts = datetime.utcnow()
                em = discord.Embed(description="A rejoint le serveur", timestamp=ts, color=0x2c7873)  # vert foncé
                em.set_author(name=str(user) + " ─ Arrivée", icon_url=user.avatar_url)
                em.set_footer(text="Membre ID: {}".format(user.id))
                await self.api.publish_log(user.server, "member_join", em)

    async def user_quit(self, user):
        if type(user) is discord.Member:
            if self.api.preload_channel(user.server, "member_quit"):
                ts = datetime.utcnow()
                em = discord.Embed(description="A quitté le serveur", timestamp=ts, color=0x27496d)  # bleu foncé
                em.set_author(name=str(user) + " ─ Départ", icon_url=user.avatar_url)
                em.set_footer(text="Membre ID: {}".format(user.id))
                await self.api.publish_log(user.server, "member_quit", em)

    async def user_ban(self, user):
        if type(user) is discord.Member:
            if self.api.preload_channel(user.server, "member_ban"):
                ts = datetime.utcnow()
                em = discord.Embed(description="A été banni", timestamp=ts, color=0xf0134d)  # rouge sanguin
                em.set_author(name=str(user) + " ─ Ban", icon_url=user.avatar_url)
                em.set_footer(text="Membre ID: {}".format(user.id))
                await self.api.publish_log(user.server, "member_ban", em)

    def user_unban(self, user):
        if type(user) is discord.Member:
            if self.api.preload_channel(user.server, "member_unban"):
                ts = datetime.utcnow()
                em = discord.Embed(description="A été débanni", timestamp=ts, color=0x40bfc1)  # bleu clair
                em.set_author(name=str(user) + " ─ Déban", icon_url=user.avatar_url)
                em.set_footer(text="Membre ID: {}".format(user.id))
                await self.api.publish_log(user.server, "member_unban", em)

    def server_disconnect(self, server):
        if self.cache["servers_last_warning"] + 7200 <= time.time():
            self.cache["servers_last_warning"] = time.time()

            ts = datetime.utcnow()
            em = discord.Embed(description="Certains serveurs sont devenus indisponibles, "
                                           "des instabilités sont prévoir sous peu.", timestamp=ts, color=0xe84a5f) # rouge
            em.set_author(name="Avertissement ─ Instabilités")
            await self.api.global_publish_log("warning_high", em)

    def __unload(self):
        self.api.save(True)


def check_folders():
    if not os.path.exists("data/sonar"):
        print("Création du dossier SONAR...")
        os.makedirs("data/sonar")


def check_files():
    if not os.path.isfile("data/sonar/data.json"):
        print("Création de Sonar/data.json")
        dataIO.save_json("data/sonar/data.json", {})


def setup(bot):
    check_folders()
    check_files()
    n = Sonar(bot)
    bot.add_listener(n.on_msg_add, "on_message")
    bot.add_listener(n.on_msg_delete, "on_message_delete")
    bot.add_listener(n.on_msg_edit, "on_message_edit")
    bot.add_listener(n.on_voice_update, "on_voice_state_update")
    bot.add_listener(n.user_join, "on_member_join")
    bot.add_listener(n.user_quit, "on_member_remove")
    bot.add_listener(n.user_update, "on_member_update")
    bot.add_listener(n.user_ban, "on_member_ban")
    bot.add_listener(n.user_unban, "on_member_unban")
    bot.add_listener(n.server_disconnect, "on_server_unavailable")
    bot.add_cog(n)