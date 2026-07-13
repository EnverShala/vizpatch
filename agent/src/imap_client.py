"""IMAP-Client Wrapper. Login, INBOX-Fetch, Drafts-APPEND."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterator, Optional

from imap_tools import MailBox, MailBoxUnencrypted, MailMessage, MailMessageFlags, AND
from imap_tools import OR
from imap_tools.query import H
from imap_tools.errors import MailboxAppendError

from .config import Config


class ImapClient:
    def __init__(self, config: Config, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger("vizpatch.imap")
        self._mailbox: Optional[MailBox] = None

    def __enter__(self) -> "ImapClient":
        if self.config.imap_use_ssl:
            self._mailbox = MailBox(host=self.config.imap_host, port=self.config.imap_port)
        else:
            self._mailbox = MailBoxUnencrypted(host=self.config.imap_host, port=self.config.imap_port)
        self._mailbox.login(self.config.imap_user, self.config.imap_password, initial_folder=self.config.imap_inbox_folder)
        self.logger.info("imap_connected", extra={"host": self.config.imap_host, "user": self.config.imap_user})
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._mailbox is not None:
            try:
                self._mailbox.logout()
            except Exception as e:
                self.logger.warning("imap_logout_failed", extra={"error": str(e)})
            self._mailbox = None

    def fetch_new_messages(self, since: datetime, own_address: str) -> Iterator[MailMessage]:
        """Fetch INBOX messages since `since`, excluding messages from own_address."""
        assert self._mailbox is not None, "Use inside 'with' block"
        self._mailbox.folder.set(self.config.imap_inbox_folder)
        criteria = AND(date_gte=since.date())
        for msg in self._mailbox.fetch(criteria, mark_seen=False, reverse=False):
            if msg.from_ and msg.from_.lower() == own_address.lower():
                continue
            yield msg

    def append_to_drafts(self, raw_msg_bytes: bytes) -> None:
        """APPEND mit Auto-CREATE-Fallback bei fehlendem Drafts-Ordner (D-25)."""
        assert self._mailbox is not None, "Use inside 'with' block"
        try:
            self._mailbox.append(
                raw_msg_bytes,
                folder=self.config.imap_drafts_folder,
                flag_set=[MailMessageFlags.DRAFT],
            )
            self.logger.info("draft_appended", extra={"folder": self.config.imap_drafts_folder})
        except MailboxAppendError as err:
            err_lower = str(err).lower()
            is_missing = any(p in err_lower for p in (
                "[trycreate]", "does not exist", "no such mailbox",
                "non-existent", "trying to append to non-existent mailbox",
            ))
            if not is_missing:
                raise  # anderer Fehler (Auth, Quota) — nicht self-heilen
            self.logger.warning("drafts_folder_missing_creating",
                                extra={"folder": self.config.imap_drafts_folder})
            self._mailbox.folder.create(self.config.imap_drafts_folder)
            self.logger.info("drafts_folder_created",
                             extra={"folder": self.config.imap_drafts_folder})
            # Retry — MailboxFolderCreateError propagiert unbehandelt
            self._mailbox.append(
                raw_msg_bytes,
                folder=self.config.imap_drafts_folder,
                flag_set=[MailMessageFlags.DRAFT],
            )
            self.logger.info("draft_appended", extra={"folder": self.config.imap_drafts_folder})

    def fetch_thread_history(
        self, references: list[str], max_messages: int = 6
    ) -> list[MailMessage]:
        """Sucht INBOX + Sent nach Thread-Messages via In-Reply-To / References."""
        assert self._mailbox is not None, "Use inside 'with' block"
        if not references:
            return []
        results: list[MailMessage] = []

        for folder in [self.config.imap_inbox_folder, self.config.imap_sent_folder]:
            try:
                self._mailbox.folder.set(folder)
            except Exception:
                self.logger.warning("history_folder_not_found", extra={"folder": folder})
                continue
            for ref_id in references:
                q = OR(
                    AND(header=H("In-Reply-To", ref_id)),
                    AND(header=H("References", ref_id)),
                )
                try:
                    for msg in self._mailbox.fetch(q, mark_seen=False, charset="UTF-8"):
                        results.append(msg)
                except Exception:
                    self.logger.warning("history_search_failed", extra={"folder": folder})

        # INBOX wiederherstellen damit der äußere fetch_new_messages-Generator stabil bleibt
        try:
            self._mailbox.folder.set(self.config.imap_inbox_folder)
        except Exception:
            pass

        # Chronologisch sortieren, Message-ID-Dedup
        seen_ids: set[str] = set()
        unique: list[MailMessage] = []
        for msg in sorted(results, key=lambda m: m.date or datetime.min):
            mid = (msg.headers.get("message-id") or [""])[0] or str(msg.uid)
            if mid not in seen_ids:
                seen_ids.add(mid)
                unique.append(msg)
        return unique[-max_messages:]

    def fetch_sender_history(
        self, from_address: str, days: int = 30, max_messages: int = 6
    ) -> list[MailMessage]:
        """Absender-Fallback: FROM x in INBOX, TO x in Sent, max 30 Tage."""
        assert self._mailbox is not None, "Use inside 'with' block"
        since = (datetime.utcnow() - timedelta(days=days)).date()
        results: list[MailMessage] = []
        for folder, query in [
            (self.config.imap_inbox_folder, AND(from_=from_address, date_gte=since)),
            (self.config.imap_sent_folder,  AND(to=from_address,   date_gte=since)),
        ]:
            try:
                self._mailbox.folder.set(folder)
                for msg in self._mailbox.fetch(query, mark_seen=False, charset="UTF-8"):
                    results.append(msg)
            except Exception:
                self.logger.warning("history_fetch_failed", extra={"folder": folder})

        # INBOX wiederherstellen damit der äußere fetch_new_messages-Generator stabil bleibt
        try:
            self._mailbox.folder.set(self.config.imap_inbox_folder)
        except Exception:
            pass

        seen_ids: set[str] = set()
        unique: list[MailMessage] = []
        for msg in sorted(results, key=lambda m: m.date or datetime.min):
            mid = (msg.headers.get("message-id") or [""])[0] or str(msg.uid)
            if mid not in seen_ids:
                seen_ids.add(mid)
                unique.append(msg)
        return unique[-max_messages:]
