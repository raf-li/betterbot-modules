from __future__ import annotations
import smtplib
import os
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import TYPE_CHECKING, Any, Dict, List

from core.base import BaseModule
from core.conversations import ConversationStep
from core.permissions import Role

if TYPE_CHECKING:
    from core.engine import BotEngine

# Usernames blocked from opening tickets
BANNED_USERNAMES = ["baduser123", "spammer_pro"]


class TicketSystem(BaseModule):
    """
    Ticket support module for BetterBot.
    SMTP credentials are configured via the Web Dashboard, not .env files.
    """

    # ── Web Dashboard Configuration Schema ──────────────────────────────────
    web_schema = [
        {
            "id":      "mail_host",
            "label":   "SMTP Host",
            "type":    "text",
            "default": "smtp-relay.brevo.com",
            "help":    "e.g. smtp.gmail.com or smtp-relay.brevo.com"
        },
        {
            "id":      "mail_port",
            "label":   "SMTP Port",
            "type":    "number",
            "default": "587",
            "help":    "Usually 587 (STARTTLS) or 465 (SSL)"
        },
        {
            "id":      "mail_username",
            "label":   "SMTP Username",
            "type":    "text",
            "default": "",
            "help":    "Your SMTP login username / email"
        },
        {
            "id":      "mail_password",
            "label":   "SMTP Password",
            "type":    "password",
            "default": "",
            "help":    "Your SMTP password or app-specific password"
        },
        {
            "id":      "mail_from_address",
            "label":   "From Address",
            "type":    "text",
            "default": "support@example.com",
            "help":    "The sender email address visible to users"
        },
        {
            "id":      "mail_from_name",
            "label":   "From Name",
            "type":    "text",
            "default": "Server Administration",
            "help":    "The sender display name visible to users"
        },
    ]

    def __init__(self, bot: "BotEngine", manifest: Dict[str, Any]) -> None:
        super().__init__(bot, manifest)
        self._last_id: int = self.retrieve("last_ticket_id", default=0)
        self._digest_queue: List[int] = self.retrieve("digest_queue", default=[])

    # ── Web Config Callback ─────────────────────────────────────────────────

    def on_web_config_saved(self, data: Dict[str, Any]) -> None:
        """Called by the Web Dashboard when settings are saved."""
        self.log.info("Ticket module SMTP settings updated via Web Dashboard.")

    # ── Bot Lifecycle ────────────────────────────────────────────────────────

    def on_cmd_myself_logged_in(self, user_id: int, account) -> None:
        self.schedule(
            name="admin_digest",
            func=self._process_digest,
            interval=7200,
            run_immediately=False
        )

    def on_command(self, ctx) -> None:
        if not ctx.args:
            self._start_ticket_flow(ctx)
            return

        sub = ctx.arg(0).lower()
        if sub == "list":
            if not self.require_role(ctx, Role.MODERATOR): return
            self._list_tickets(ctx)
        elif sub == "done":
            if not self.require_role(ctx, Role.MODERATOR): return
            self._close_ticket(ctx)
        elif sub == "reply":
            if not self.require_role(ctx, Role.MODERATOR): return
            self._admin_reply(ctx)
        else:
            ctx.reply("❓ Usage: .ticket | .ticket list | .ticket done <id> | .ticket reply <id> <msg>")

    # ── Ticket Flow ──────────────────────────────────────────────────────────

    def _start_ticket_flow(self, ctx):
        username = ctx.username

        if username.lower() in BANNED_USERNAMES:
            ctx.reply_pm("❌ Access Denied: You are restricted from creating tickets.")
            return

        # One-ticket-per-user policy
        all_keys = self.storage.list_keys(self.name)
        for key in all_keys:
            if key.startswith("ticket_"):
                t = self.retrieve(key)
                if t and t["user"].lower() == username.lower() and t["status"] == "OPEN":
                    ctx.reply_pm(f"❌ You already have an active ticket (#{key.split('_')[1]}).")
                    return

        steps = [
            ConversationStep(
                prompt="Step 1/4: Issue Category? (Audio/Connection/Account/Other)",
                key="category"
            ),
            ConversationStep(
                prompt="Step 2/4: Your Email Address? (For offline updates)",
                key="email",
                validator=lambda v: ("@" in v and "." in v, "Invalid email format. Please try again.")
            ),
            ConversationStep(
                prompt="Step 3/4: Priority? (1: Low, 2: Medium, 3: URGENT)",
                key="priority",
                validator=lambda v: (v in ["1", "2", "3"], "Please enter 1, 2, or 3.")
            ),
            ConversationStep(
                prompt="Step 4/4: Describe your problem in detail:",
                key="detail"
            )
        ]
        self.bot.conversations.begin(ctx.user_id, steps, self._on_ticket_complete)
        ctx.reply_pm("📝 Ticket Wizard started. Please answer the questions above.")

    def _on_ticket_complete(self, user_id, data):
        self._last_id += 1
        ticket_id = self._last_id

        username = "Unknown"
        try:
            u = self.bot.getUser(user_id)
            username = str(u.szUsername)
        except: pass

        ticket_data = {
            "id":       ticket_id,
            "user":     username,
            "email":    data.get("email"),
            "category": data.get("category"),
            "priority": data.get("priority"),
            "detail":   data.get("detail"),
            "status":   "OPEN",
            "replies":  []
        }

        self.store(f"ticket_{ticket_id}", ticket_data)
        self.store("last_ticket_id", ticket_id)

        self._digest_queue.append(ticket_id)
        self.store("digest_queue", self._digest_queue)

        self.bot.send_pm(user_id, f"✅ Ticket #{ticket_id} created. We will notify you once an Admin responds.")

    # ── Admin Commands ───────────────────────────────────────────────────────

    def _admin_reply(self, ctx):
        if len(ctx.args) < 3:
            ctx.reply("⚠️ Usage: .ticket reply <id> <message>")
            return

        tid = ctx.arg(1)
        reply_msg = " ".join(ctx.args[2:])
        ticket = self.retrieve(f"ticket_{tid}")

        if not ticket:
            ctx.reply(f"❌ Ticket #{tid} not found.")
            return

        ticket["replies"].append({"admin": ctx.username, "msg": reply_msg})
        self.store(f"ticket_{tid}", ticket)

        target_uid = self._get_user_id_by_name(ticket["user"])
        if target_uid:
            self.bot.send_pm(target_uid, f"📩 Support Response (Ticket #{tid}):\n{reply_msg}")
            ctx.reply("✅ User is online. Response sent via PM.")
        else:
            from_name = self.retrieve("mail_from_name", "Server Administration")
            email_body = (
                f"Hello {ticket['user']},\n\n"
                f"An administrator has responded to your ticket #{tid}:\n\n"
                f"\"{reply_msg}\"\n\n"
                f"Status: {ticket['status']}\n"
                f"---\n{from_name}"
            )
            import threading
            threading.Thread(
                target=self._send_email_async,
                args=(ticket["email"], f"Support Update - Ticket #{tid}", email_body, ctx, tid),
                daemon=True
            ).start()
            ctx.reply(f"⏳ User is offline. Sending email to {ticket['email']}...")

    def _send_email_async(self, to_addr, subject, body, ctx, tid):
        success = self._send_email(to_addr, subject, body)
        if success:
            ctx.reply_pm(f"✅ Email sent for ticket #{tid}.")
        else:
            ctx.reply_pm(f"❌ Failed to send email for ticket #{tid}. Check SMTP settings in the Web Dashboard.")

    def _close_ticket(self, ctx):
        if not ctx.require_args(2, "Usage: .ticket done <id>"): return
        tid = ctx.arg(1)
        ticket = self.retrieve(f"ticket_{tid}")

        if ticket:
            ticket["status"] = "CLOSED"
            self.store(f"ticket_{tid}", ticket)

            msg = f"🔒 Your Ticket #{tid} has been marked as RESOLVED/CLOSED."
            uid = self._get_user_id_by_name(ticket["user"])
            if uid:
                self.bot.send_pm(uid, msg)
            else:
                self._send_email(ticket["email"], f"Ticket #{tid} Closed", msg)

            ctx.reply(f"✅ Ticket #{tid} closed successfully.")
        else:
            ctx.reply("❌ Ticket not found.")

    # ── Digest Scheduler ─────────────────────────────────────────────────────

    def _process_digest(self) -> None:
        if not self._digest_queue: return

        admins = self._get_online_admins()
        if not admins: return

        report = [f"📊 Pending Tickets Digest ({len(self._digest_queue)} new)"]
        for tid in self._digest_queue:
            t = self.retrieve(f"ticket_{tid}")
            if t:
                report.append(f"- #{tid} [{t['user']}] Prio:{t['priority']} - {t['category']}")

        for admin_id in admins:
            self.bot.send_pm(admin_id, "\n".join(report))

        self._digest_queue = []
        self.store("digest_queue", [])

    # ── Email ─────────────────────────────────────────────────────────────────

    def _send_email(self, to_addr: str, subject: str, body: str) -> bool:
        """Send email using SMTP credentials stored in the bot's persistent storage."""
        host     = self.retrieve("mail_host",         "smtp-relay.brevo.com")
        port     = int(self.retrieve("mail_port",     587))
        username = self.retrieve("mail_username",     "")
        password = self.retrieve("mail_password",     "")
        from_addr= self.retrieve("mail_from_address", "support@example.com")
        from_name= self.retrieve("mail_from_name",    "Server Administration")

        if not host or not username or not password:
            self.log.error("SMTP not configured. Set credentials in the Web Dashboard under Ticket Support settings.")
            return False

        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From']    = formataddr((from_name, from_addr))
            msg['To']      = to_addr

            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(username, password)
                server.sendmail(from_addr, [to_addr], msg.as_string())
            return True
        except Exception as e:
            self.log.error(f"Email failed: {e}")
            return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_all_users(self):
        try:
            res = self.bot.getServerUsers()
            if isinstance(res, tuple):
                return res[1] if len(res) > 1 else []
            return res if res else []
        except Exception as e:
            self.log.error(f"Failed to fetch users: {e}")
            return []

    def _get_user_id_by_name(self, username: str) -> int | None:
        for u in self._get_all_users():
            if str(u.szUsername).lower() == username.lower():
                return u.nUserID
        return None

    def _get_online_admins(self) -> List[int]:
        admin_names = self.bot._config.get("acl", {}).get("admin_usernames", [])
        online_admins = []
        for u in self._get_all_users():
            uname = str(u.szUsername).lower()
            if uname in [a.lower() for a in admin_names] or u.uUserType == 2:
                online_admins.append(u.nUserID)
        return online_admins

    def _list_tickets(self, ctx):
        all_keys = self.storage.list_keys(self.name)
        lines = ["🎫 Open Tickets:"]
        for key in all_keys:
            if key.startswith("ticket_"):
                t = self.retrieve(key)
                if t and t["status"] == "OPEN":
                    lines.append(f"- #{t['id']} [{t['priority']}] {t['user']}: {t['category']}")
        ctx.reply("\n".join(lines) if len(lines) > 1 else "📭 No open tickets.")

    def cleanup(self) -> None:
        self.store("digest_queue", self._digest_queue)
        self.cancel_all()
        self.unsubscribe_all()