import discord
from discord import Role, Interaction
from discord.ext import commands

from g.classes import update_manager_roles_for_guild, fetch_manager_roles_for_guild
from g.util import check_admin, send_error_message


class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    user_group = discord.app_commands.Group(name="user", description="Polecenia menedżerów")

    @user_group.command(name="set", description="Ustaw role menedżerów dla tego serwera")
    @discord.app_commands.check(check_admin)
    async def set(self, interaction: discord.Interaction):
        roles = fetch_manager_roles_for_guild(interaction.guild)
        await interaction.response.send_modal(SetUserRoles(roles))

    @set.error
    async def set_error(self, interaction: discord.Interaction, error):
        await send_error_message(interaction, error)


async def setup(bot):
    await bot.add_cog(UserCog(bot))


class SetUserRoles(discord.ui.Modal, title="Zarządzaj rolami menedżerów"):
    def __init__(self, user_roles: list[Role]):
        super().__init__()
        self.manager_roles = discord.ui.RoleSelect(placeholder="Role menedżerów kalendarza",
                                                   default_values=user_roles,
                                                   max_values=25)

        self.add_item(discord.ui.Label(text="Wybierz role menedżerów",
                                       description="Osoby z tymi rolami będą mogły zarządzać kalendarzem (MAX 25)",
                                       component=self.manager_roles))
        self.add_item(discord.ui.TextDisplay("Użytkownicy posiadający wybrane role powinni mieć możliwość pisania na kanale kalendarza"))

    async def on_submit(self, interaction: Interaction) -> None:
        update_manager_roles_for_guild(interaction.guild_id, self.manager_roles.values)

        roles_list = [role.name for role in self.manager_roles.values]
        await interaction.response.send_message("Osoby z tymi rolami będą miały dostęp do komend kalendarza:\n"
                                                f"{roles_list}", ephemeral=True)
