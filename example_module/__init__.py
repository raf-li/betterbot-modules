# Copyright (c) 2026 Rafli.
# Author: Rafli (Fli)
# Copyright: © 2026 Rafli.
# Project Philosophy: "A high-end, decoupled, skeleton framework for TeamTalk 5."

"""
modules/example_module/__init__.py — BetterBot Reference Module.

Demonstrates every major framework feature:
  - Context API (ctx.trigger, ctx.args, ctx.arg(), ctx.reply(), ctx.deny())
  - Admin check via ctx.is_admin and self.require_role()
  - Persistent storage (self.store / self.retrieve)
  - Event scheduling (self.schedule / self.cancel_all)
  - EventBus (self.emit / self.subscribe)
  - Middleware registration (self.add_middleware)
  - Conversation wizard (self.bot.conversations.begin)
  - Metrics (self.bot.metrics.record_event)
  - RBAC role check (self.require_role with Role.MODERATOR)

Commands:
    .ping  / /ping   — Latency / liveness check
    .hello / /hello  — Greet the sender
    .info  / /info   — Bot info (uptime, state, modules)
    .count / /count  — Persistent click counter (per user)
    .setup / /setup  — Multi-step wizard demo
    .timer / /timer  — Schedule a one-shot reminder
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, TYPE_CHECKING

from core.base import BaseModule
from core.context import Context
from core.permissions import Role
from core.conversations import ConversationStep

if TYPE_CHECKING:
    from core.engine import BotEngine


class ExampleModule(BaseModule):
    """
    BetterBot reference module — showcases all core framework features.

    This module is safe to delete or replace once you start building your own.
    """

    # ── Initialisation ───────────────────────────────────────────────────────

    def __init__(self, bot: "BotEngine", manifest: Dict[str, Any]) -> None:
        super().__init__(bot, manifest)

        # Restore persistent state
        self._total_commands: int = self.retrieve("total_commands", default=0)

        self.log.info(f"{self.name} v{self.version} loaded.")

    # ── Abstract Methods ─────────────────────────────────────────────────────

    def on_command(self, ctx: Context) -> None:
        """Dispatch incoming commands to handler methods."""
        self._total_commands += 1
        self.bot.metrics.record_event(self.name, "command_received")

        dispatch = {
            "ping":  self._cmd_ping,
            "hello": self._cmd_hello,
            "info":  self._cmd_info,
            "count": self._cmd_count,
            "setup": self._cmd_setup,
            "timer": self._cmd_timer,
        }
        handler = dispatch.get(ctx.command.lower())
        if handler:
            handler(ctx)

    def cleanup(self) -> None:
        """Persist state and release all resources."""
        self.store("total_commands", self._total_commands)
        self.cancel_all()
        self.unsubscribe_all()
        self.remove_all_middleware()
        self.log.info(f"{self.name} cleaned up.")

    # ── Event Hooks ──────────────────────────────────────────────────────────

    def on_cmd_myself_logged_in(self, user_id: int, useraccount) -> None:
        """Register scheduler, subscriptions, and middleware after login."""
        # 1. Recurring task: announce uptime every 6 hours
        self.schedule(
            name            = "uptime_announce",
            func            = self._announce_uptime,
            interval        = 21600,
            run_immediately = False,
        )

        # 2. Listen for state changes emitted by the engine
        self.subscribe("core.state_changed", self._on_state_changed)

        # 3. Register a ban-guard before-middleware
        self.add_middleware(self._ban_guard, phase="before")

        # 4. Register an after-middleware for command logging
        self.add_middleware(self._log_command, phase="after")

        self.log.info("Scheduler, subscriptions and middleware registered.")

    def on_user_join(self, user) -> None:
        """Greet users when they join the bot's channel."""
        if int(user.nUserID) == self.bot.getMyUserID():
            return
        if int(user.nChannelID) != self.bot.getMyChannelID():
            return
        nickname = str(user.szNickname) or str(user.szUsername)
        self.bot.send_channel_msg(
            self.bot.getMyChannelID(),
            f"👋 Welcome, {nickname}! Type .help to see what I can do."
        )

    # ── Command Handlers ─────────────────────────────────────────────────────

    def _cmd_ping(self, ctx: Context) -> None:
        """
        .ping — Liveness check with response latency.

        Usage: .ping
        """
        ctx.reply(self.t("ping"))
        _ = self.t("hidden_message")

    def _cmd_hello(self, ctx: Context) -> None:
        """
        .hello — Personalised greeting.

        Usage: .hello [name]
        """
        name = ctx.arg(0) or ctx.user_display
        ctx.reply(self.t("greeting", name=name))

    def _cmd_info(self, ctx: Context) -> None:
        """
        .info — Bot status summary.

        Usage: .info
        """
        modules  = self.bot.loader.get_all_modules()
        uptime   = self.bot.metrics.uptime_str
        state    = self.bot.state.value
        mod_list = ", ".join(m.name for m in modules.values()) or "(none)"
        
        info_header = self.t("info")
        ctx.reply(
            f"ℹ️ {info_header}\n"
            f"Uptime   : {uptime}\n"
            f"State    : {state}\n"
            f"Modules  : {mod_list}\n"
            f"Commands : {self._total_commands} total"
        )

    def _cmd_count(self, ctx: Context) -> None:
        """
        .count — Per-user persistent click counter.

        Usage: .count          (increment and view)
               .count reset    (reset your counter, admin only)
        """
        key = f"count.{ctx.username}"

        if ctx.arg(0).lower() == "reset":
            if not ctx.is_admin:
                ctx.deny()
                return
            self.delete_stored(key)
            ctx.reply(f"🔄 Counter for {ctx.username} reset.")
            return

        count = self.retrieve(key, default=0) + 1
        self.store(key, count)
        ctx.reply(f"🔢 {ctx.username}: click #{count}")

    def _cmd_setup(self, ctx: Context) -> None:
        """
        .setup — Multi-step wizard demo (conversation system).

        Usage: .setup
        Starts a 2-step wizard collecting a name and a timezone.
        Type .cancel at any step to abort.
        """
        steps = [
            ConversationStep(
                prompt    = "🧙 Step 1/2 — Enter your display name (min 2 chars):",
                key       = "display_name",
                validator = lambda v: (
                    (len(v.strip()) >= 2, "Name must be at least 2 characters.")
                    if len(v.strip()) < 2
                    else (True, "")
                ),
                timeout = 60.0,
            ),
            ConversationStep(
                prompt  = "🧙 Step 2/2 — Enter your timezone (e.g. Asia/Jakarta):",
                key     = "timezone",
                timeout = 60.0,
            ),
        ]
        self.bot.conversations.begin(
            user_id     = ctx.user_id,
            steps       = steps,
            on_complete  = self._on_setup_complete,
            on_cancel   = lambda uid: self.bot.send_pm(uid, "Setup cancelled."),
        )

    def _on_setup_complete(self, user_id: int, data: Dict[str, Any]) -> None:
        """Called when the .setup wizard completes all steps."""
        self.store(f"setup.{data.get('display_name', 'unknown')}", data)
        self.bot.send_pm(
            user_id,
            f"✅ Setup complete!\n"
            f"   Name     : {data.get('display_name')}\n"
            f"   Timezone : {data.get('timezone')}"
        )

    def _cmd_timer(self, ctx: Context) -> None:
        """
        .timer <seconds> [message] — Schedule a one-shot reminder.

        Usage: .timer 30 Meeting starts now!
               .timer 60
        """
        if not ctx.require_args(1, "Usage: .timer <seconds> [message]"):
            return

        try:
            delay = float(ctx.arg(0))
        except ValueError:
            ctx.reply("❌ First argument must be a number of seconds.")
            return

        if delay < 1 or delay > 3600:
            ctx.reply("⏱️  Delay must be between 1 and 3600 seconds.")
            return

        reminder = ctx.raw_args.split(None, 1)[1] if len(ctx.args) > 1 else "⏰ Timer done!"
        uid      = ctx.user_id

        def _fire():
            self.bot.send_pm(uid, f"⏰ Reminder: {reminder}")

        t = threading.Timer(delay, _fire)
        t.daemon = True
        t.start()
        ctx.reply(f"✅ Reminder set for {delay:.0f}s: \"{reminder}\"")

    # ── Middleware ───────────────────────────────────────────────────────────

    def _ban_guard(self, ctx: Context) -> bool:
        """
        Before-middleware: silently block banned users.

        Registered in on_cmd_myself_logged_in().
        """
        if self.bot.permissions.is_banned(ctx.username):
            self.log.warning(f"Blocked banned user: {ctx.username}")
            return False  # abort the command pipeline
        return True

    def _log_command(self, ctx: Context, error=None) -> None:
        """
        After-middleware: log every command with status.

        Registered in on_cmd_myself_logged_in().
        """
        status = "ERROR" if error else "OK"
        self.log.info(
            f"[CMD/{status}] {ctx.username}: {ctx.trigger} {ctx.raw_args}"
        )

    # ── Scheduler Tasks ──────────────────────────────────────────────────────

    def _announce_uptime(self) -> None:
        """Scheduled task: announce uptime to the bot's channel every 6 hours."""
        ch_id  = self.bot.getMyChannelID()
        uptime = self.bot.metrics.uptime_str
        self.bot.send_channel_msg(ch_id, f"🤖 BetterBot has been running for {uptime}.")

    # ── EventBus Callbacks ───────────────────────────────────────────────────

    def _on_state_changed(self, data: Dict[str, Any]) -> None:
        """React to bot state transitions emitted by the engine."""
        old, new = data.get("old"), data.get("new")
        if new == "reconnecting":
            self.log.warning("Bot lost connection — waiting for reconnect.")
        elif new == "in_channel":
            self.log.info("Bot is back in channel — all systems nominal.")
