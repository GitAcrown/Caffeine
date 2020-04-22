import os

import discord
from discord.ext import commands

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class Misc:
    """Outils divers destinés à faciliter certaines actions"""
    def __init__(self, bot):
        self.bot = bot
        self.data = dataIO.load_json("data/misc/data.json")

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


    @commands.group(name="iam", aliases=["iamnot"], pass_context=True, invoke_without_command=True, no_pm=True)
    async def _iam(self, ctx, role: discord.Role):
        """Auto-attribution de rôles

        Pour configurer la liste des rôles -> ;iam set"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.get, role=role)

    @commands.command(pass_context=True)
    async def list(self, ctx):
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

    @commands.command(aliases=["iamnot"], pass_context=True, no_pm=True)
    async def get(self, ctx, role: discord.Role = None):
        """Permet de s'attribuer ou se retirer un rôle"""
        server = ctx.message.server
        user = ctx.message.author
        sys = self.get_setting(server, "iam_roles", [])
        self.purge_iam_roles(server)
        if sys:
            if role:
                if role.id in sys and role in server.roles:
                    if role in user.roles:
                        await self.bot.remove_roles(user, role)
                        await self.bot.say("**Rôle `{}` retiré** ─ Vous ne disposez désormais plus de ce rôle.".format(role.name))
                    else:
                        await self.bot.add_roles(user, role)
                        await self.bot.say("**Rôle `{}` ajouté** ─ Vous disposez désormais de ce rôle.".format(role.name))
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
                    i = [str(i[0]) for i in rolelist if str(i[0]) == rep.content][0]
                    role = i[1]
                    if role in user.roles:
                        await self.bot.remove_roles(user, role)
                        await self.bot.say("**Rôle `{}` retiré** ─ Vous ne disposez désormais plus de ce rôle.".format(role.name))
                    else:
                        await self.bot.add_roles(user, role)
                        await self.bot.say("**Rôle `{}` ajouté** ─ Vous disposez désormais de ce rôle.".format(role.name))
                elif rep.content.lower() in ["stop", "quit", "quitter", "0"]:
                    await self.bot.delete_message(msg)
                else:
                    await self.bot.say("**Réponse invalide** ─ Réessayez en tapant un nombre après avoir fait `;iam`")
                    await self.bot.delete_message(msg)
        else:
            await self.bot.say("Aucun rôle n'a encore été configuré pour être attribuable par ce biais.")

    @commands.command(pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def set(self, ctx, action: str, role: discord.Role):
        """Configure un rôle (add/remove) pour qu'il puisse être ajouté et retiré seul par un membre"""
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


def check_folders():
    folders = ("data", "data/misc/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Création du fichier " + folder)
            os.makedirs(folder)


def check_files():
    if not os.path.isfile("data/misc/data.json"):
        fileIO("data/nooknet/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Misc(bot)
    bot.add_cog(n)