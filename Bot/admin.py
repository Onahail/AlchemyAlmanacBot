import discord
from discord.ext import commands
import sys, io
from typing import Literal, Optional
import utils

from db import db


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='reload', hidden=True)
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, *, cog: str):
        """Reloads a cog."""
        try:
            await self.bot.reload_extension(cog)
            await ctx.send(f'Reloaded {cog} successfully.')
        except commands.ExtensionNotLoaded:
            await ctx.send(f'Cog {cog} is not loaded.')
        except commands.ExtensionNotFound:
            await ctx.send(f'Cog {cog} not found.')
        except commands.ExtensionFailed as e:
            await ctx.send(f'Failed to reload cog {cog}: {e}')

    @commands.command(name='clear_all_commands', hidden=True)
    @commands.is_owner()
    async def clear_all_commands(self, ctx):
        await ctx.bot.tree.clear_commands(guild=None)
        await ctx.bot.tree.sync(guild=None)

        for guild in ctx.bot.guilds:
            ctx.bot.tree.clear_commands(GUILD)
            await ctx.bot.tree.sync(GUILD)

        await ctx.send("Cleared all commands globally and per-guild.")


    @commands.command(name='sync', hidden=True)
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        if not guilds:
            if spec == "~":  # Sync commands only to the current guild (ctx.guild)
                synced = await ctx.bot.tree.sync(guild=GUILD)
            elif spec == "*":  # Copy global commands to current guild, then sync them there
                ctx.bot.tree.copy_global_to(guild=GUILD)
                synced = await ctx.bot.tree.sync(guild=GUILD)
            elif spec == "^":  # Clear commands from the current guild and sync (removes overrides)
                ctx.bot.tree.clear_commands(guild=GUILD)
                await ctx.bot.tree.sync(guild=GUILD)
                synced = []
            else:  # No spec provided — sync global commands
                synced = await ctx.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @commands.command(name='_eval', hidden=True)
    @commands.is_owner()
    async def _eval(self, ctx, *, code: str):
        output = "Temp - This should change"
        try:
            if code.startswith('```python') and code.endswith('```'):
                code = code[9:-3].strip()
            elif code.startswith('```') and code.endswith('```'):
                code = code[3:-3].strip()

            old_stdout = sys.stdout
            new_stdout = io.StringIO()
            sys.stdout = new_stdout

            exec_globals = {
                "ctx": ctx,
                "bot": self.bot,
                "commands": commands,
                "utils": utils,
                "db": db,
                "sys": sys,   # Ensure 'sys' is included in the globals
                "io": io      # Ensure 'io' is included in the globals
            }
            exec_locals = {}

            if "await " in code:
                exec(
                    f"async def __ex(ctx):\n" +
                    "\n".join(f"    {line}" for line in code.split("\n")),
                    exec_globals,
                )
                result = await exec_globals["__ex"](ctx)
            else:
                exec(code, exec_globals, exec_locals)

            output = new_stdout.getvalue()
            sys.stdout = old_stdout

            if len(output) > 2000:
                raise ValueError("Output too long")

            if output:
                await ctx.send(f'```py\n{output}\n```')
            else:
                await ctx.send('No output')
        except ValueError as e:
            if str(e) == "Output too long":
                print(output)
                await ctx.send("Printed to console, message body too big for Discord message.")
            else:
                await ctx.send(f'Error: {str(e)}')
        except Exception as e:
            await ctx.send(f'Error: {str(e)}')


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
