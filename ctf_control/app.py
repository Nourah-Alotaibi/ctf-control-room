
from pathlib import Path
import asyncio
import time
import re

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, RichLog, Label, Select, Input, Button
from textual.binding import Binding
from textual.screen import ModalScreen, Screen
from textual.containers import Center, Middle
from rich.text import Text
from rich.markup import escape as rich_escape

from .core.detector import discover_challenges
from .core.scanner import scan_challenge
from .core.agents import build_agent_invocation, available_agents
from .core.handoff import build_handoff
from .core.exporter import export_challenge
from .core.models import Challenge, ScanEvent
from .core.pty_session import PTYSession
from .core.metrics import load_metrics, bump, set_status, add_seconds, log_command
from .core.memory import related_lessons, save_lesson
from .core.snapshot import create_snapshot
from .core.compatibility import detect_agent_compatibility
from .core.parallel import (
    DEFAULT_STRATEGIES,
    create_parallel_run, extract_candidate_flags,
    choose_candidate_flag, build_parallel_summary,
)
from .core.recovery import build_recovery_prompt, write_recovery_prompt, recovery_resume_instruction
from .core.power import load_settings
from .core.hypothesis import update_from_visible_output, record_command, add_item, record_parallel_result
from .core.session_workspace import (
    create_session_workspace, session_env, append_transcript,
    update_screen, finalize_session,
)




class WelcomeScreen(ModalScreen):
    CSS = """
    WelcomeScreen {
        align: center middle;
        background: #07090d;
        color: #efeff5;
    }
    #welcome-box {
        width: 142;
        height: 39;
        border: round #8f5cff;
        background: #090b10;
        padding: 1 3;
    }
    #welcome-icon {
        height: 2;
        text-align: center;
        content-align: center middle;
        color: #c99cff;
    }
    #welcome-word {
        height: 7;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        color: #f5f2fa;
    }
    #welcome-title {
        height: 7;
        text-align: center;
        content-align: center middle;
        text-style: bold;
        color: #c99cff;
    }
    #welcome-subtitle {
        height: 2;
        text-align: center;
        color: #aeb2bc;
    }
    #ctf-explainer {
        height: 8;
        border: round #5f3f88;
        padding: 1 2;
        background: #080a0f;
        color: #ececf2;
    }
    #welcome-menu {
        height: 5;
        padding: 1 3 0 3;
    }
    #welcome-menu Static {
        height: 1;
        color: #e8e8ee;
    }
    #welcome-footer {
        height: 3;
        text-align: center;
        color: #9993a2;
    }
    """

    BINDINGS = [
        Binding("enter", "open_dashboard", "Enter"),
        Binding("question_mark", "show_help", "Help"),
        Binding("q", "quit_app", "Quit"),
    ]

    def compose(self):
        with Vertical(id="welcome-box"):
            yield Static("🤖  💜", id="welcome-icon")
            yield Static(
                "[b]██╗    ██╗███████╗██╗      ██████╗ ██████╗ ███╗   ███╗███████╗[/b]\n"
                "[b]██║    ██║██╔════╝██║     ██╔════╝██╔═══██╗████╗ ████║██╔════╝[/b]\n"
                "[b]██║ █╗ ██║█████╗  ██║     ██║     ██║   ██║██╔████╔██║█████╗  [/b]\n"
                "[b]██║███╗██║██╔══╝  ██║     ██║     ██║   ██║██║╚██╔╝██║██╔══╝  [/b]\n"
                "[b]╚███╔███╔╝███████╗███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║███████╗[/b]\n"
                "[b] ╚══╝╚══╝ ╚══════╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝[/b]",
                id="welcome-word",
            )
            yield Static(
                "[b magenta] ██████╗████████╗███████╗     ██████╗ ██████╗ ███╗   ██╗████████╗██████╗  ██████╗ ██╗         ██████╗  ██████╗  ██████╗ ███╗   ███╗[/b magenta]\n"
                "[b magenta]██╔════╝╚══██╔══╝██╔════╝    ██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔══██╗██╔═══██╗██║         ██╔══██╗██╔═══██╗██╔═══██╗████╗ ████║[/b magenta]\n"
                "[b magenta]██║        ██║   █████╗      ██║     ██║   ██║██╔██╗ ██║   ██║   ██████╔╝██║   ██║██║         ██████╔╝██║   ██║██║   ██║██╔████╔██║[/b magenta]\n"
                "[b magenta]██║        ██║   ██╔══╝      ██║     ██║   ██║██║╚██╗██║   ██║   ██╔══██╗██║   ██║██║         ██╔══██╗██║   ██║██║   ██║██║╚██╔╝██║[/b magenta]\n"
                "[b magenta]╚██████╗   ██║   ██║         ╚██████╗╚██████╔╝██║ ╚████║   ██║   ██║  ██║╚██████╔╝███████╗    ██║  ██║╚██████╔╝╚██████╔╝██║ ╚═╝ ██║[/b magenta]\n"
                "[b magenta] ╚═════╝   ╚═╝   ╚═╝          ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝[/b magenta]",
                id="welcome-title",
            )
            yield Static("Smart AI workspace for CTF players", id="welcome-subtitle")
            yield Static(
                "[b magenta]What is CTF?[/b magenta]\n"
                "Capture The Flag is a cybersecurity competition where you solve\n"
                "challenges and find hidden flags.\n\n"
                "[dim]Categories[/dim]  "
                "[cyan]Web[/cyan]  •  [yellow]Crypto[/yellow]  •  "
                "[green]Forensics[/green]  •  [red]Pwn[/red]  •  "
                "[magenta]Reverse[/magenta]  •  [blue]Network[/blue]  •  "
                "OSINT  •  Mobile  •  Malware",
                id="ctf-explainer",
            )
            with Vertical(id="welcome-menu"):
                yield Static("[magenta]ENTER[/magenta]  Enter Control Room")
                yield Static("[magenta]?[/magenta]      Help & Guide")
                yield Static("[magenta]Q[/magenta]      Quit")
            yield Static(
                "💜 Good luck on your CTF!\n"
                "[dim]by Nourah Alotaibi[/dim]\n"
                "[dim][ W ] Return to Welcome anytime[/dim]",
                id="welcome-footer",
            )

    def action_open_dashboard(self):
        self.dismiss("open")

    def action_show_help(self):
        self.dismiss("help")

    def action_quit_app(self):
        self.app.exit()

class HelpScreen(ModalScreen):
    CSS = """
    HelpScreen {
        align: center middle;
        background: #090510;
        color: #f4f0ff;
    }
    #help-box {
        width: 92%;
        height: 88%;
        border: round #8f5cff;
        background: #0f0c16;
        padding: 1 2;
    }
    #help-title {
        height: 3;
        text-style: bold;
        color: #c99cff;
    }
    #help-content {
        height: 1fr;
        border: round #3f3159;
        padding: 1 2;
        background: #11101a;
    }
    #help-footer {
        height: 3;
        text-align: center;
        color: #b8b0c8;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("w", "welcome", "Welcome"),
        Binding("q", "quit_app", "Quit"),
    ]

    def compose(self):
        with Vertical(id="help-box"):
            yield Static("💜 HELP & GUIDE", id="help-title")
            yield Static(
                "[b green]GET STARTED[/b green]\n"
                "1. Add your challenge files to the correct category folder.\n"
                "2. Select the challenge from the dashboard.\n"
                "3. [b]S[/b] → Smart Pre-Scan: quick automatic checks with NO AI; prepares useful context.\n"
                "4. [b]A[/b] → Start AI: starts the AI agent you installed and sends the prepared context.\n"
                "5. Start AI opens a large popup live shared terminal automatically.\n"
                "6. V → AI View: reopen the Claude/Gemini popup at any time.\n"
                "7. [b]T[/b] → Take Over: you control the SAME terminal manually.\n"
                "8. [b]R[/b] → Return to AI: give the same terminal back so the AI can continue.\n\n"

                "[b cyan]CONTROL[/b cyan]\n"
                "T  Take Over      → Human controls the shared terminal.\n"
                "R  Return to AI   → Give terminal control back to the AI.\n"
                "I  Interrupt      → Send Ctrl-C to stop the current running command.\n\n"

                "[b yellow]TOOLS & FEATURES[/b yellow]\n"
                "H  Handoff        → Package progress, scripts, context, and tried commands for another agent.\n"
                "X  Snapshot       → Save context, scripts, metrics, commands, notes, and findings.\n"
                "Y  Stuck Recovery → Build recovery context and send a genuinely different path to the active AI.\n"
                "P  Parallel Agents → Run two independent methods concurrently in isolated workspace copies; uses more AI.\n"
                "L  Save Lesson    → Save a reusable CTF technique for later challenges.\n"
                "E  Write-up       → Prepare a local write-up without calling AI.\n\n"

                "[b magenta]SMART FEATURES[/b magenta]\n"
                "Smart Agent Router → chooses the most relevant specialist role from category/context.\n"
                "Tool Planner       → ranks a short list of useful installed tools instead of showing everything.\n"
                "Hypothesis Board   → tracks evidence, failed ideas, and next steps to reduce repeated work.\n"
                "Tool Cache         → reuses the same result when the command/files are unchanged.\n"
                "Tool Discovery     → detects tools on WSL/PATH and optional repos in ~/CTF/tools/.\n"
                "Reference Search   → searches local HackTricks/PayloadsAllTheThings-style repos without dumping full files.\n"
                "MCP                → optional structured bridge for compatible AI clients.\n\n"

                "[b blue]AI & MODES[/b blue]\n"
                "AI is optional. Control Room never installs Claude, Codex, Gemini, CAI, or another AI automatically.\n"
                "Standard profile → Router + Tool Planner + Hypothesis Board.\n"
                "Advanced profile → Standard + optional Stuck Recovery.\n"
                "Max profile      → enables all advanced switches; Parallel/CAI can cost more tokens.\n\n"

                "[b]SYSTEM[/b]\n"
                "W  Welcome  → Return to the Welcome page anytime.\n"
                "F  Refresh  → Refresh challenge list/status.\n"
                "V  AI View  → Open the popup live shared terminal.\n"
                "?  Help     → Open this Help & Guide page.\n"
                "Q  Quit     → Exit Control Room. Saved work remains.",
                id="help-content",
            )
            yield Static(
                "ESC = Back   •   W = Welcome   •   Q = Quit\n"
                "[dim]Tip: Smart Pre-Scan first, then AI. Take over whenever you need manual control.[/dim]",
                id="help-footer",
            )

    def action_back(self):
        self.dismiss("back")

    def action_welcome(self):
        self.dismiss("welcome")

    def action_quit_app(self):
        self.app.exit()


class SmartScanScreen(ModalScreen):
    """Small progress popup for the local no-AI Smart Pre-Scan."""

    CSS = """
    SmartScanScreen {
        align: center middle;
        background: rgba(7, 9, 13, 0.68);
        color: #efeff5;
    }
    #scan-shell {
        width: 72;
        height: 20;
        padding: 1 2;
        background: #090b10;
        border: round #8f5cff;
    }
    #scan-popup-title {
        height: 2;
        content-align: center middle;
        text-style: bold;
        color: #c99cff;
        border-bottom: solid #5f3f88;
    }
    #scan-spinner {
        height: 3;
        content-align: center middle;
        text-align: center;
        text-style: bold;
        color: #75d7ff;
    }
    #scan-popup-status {
        height: 8;
        padding: 0 1;
        background: #0d1016;
        border: round #3b2b50;
    }
    #scan-popup-footer {
        height: 3;
        margin-top: 1;
        content-align: center middle;
        text-align: center;
        color: #9aa0aa;
    }
    """

    _FRAMES = ("◐", "◓", "◑", "◒")

    def __init__(self, challenge_name: str):
        super().__init__()
        self.challenge_name = challenge_name
        self.started_at = time.time()
        self.event_count = 0
        self.current_tool = "Preparing local checks…"
        self.current_target = "—"
        self.finished = False
        self.failed = False
        self.finish_message = ""
        self._frame = 0
        self._ready = False

    def compose(self):
        with Vertical(id="scan-shell"):
            yield Static("◆ SMART PRE-SCAN • NO AI ◆", id="scan-popup-title")
            yield Static("◐  SCANNING", id="scan-spinner")
            yield Static("Starting…", id="scan-popup-status")
            yield Static(
                "Local tools only • compact context is prepared for the AI",
                id="scan-popup-footer",
            )

    def on_mount(self):
        self._ready = True
        self.set_interval(0.16, self._animate)
        self._refresh_scan_ui()

    def _animate(self):
        if not self.finished:
            self._frame = (self._frame + 1) % len(self._FRAMES)
        self._refresh_scan_ui()

    def _refresh_scan_ui(self):
        if not self._ready:
            return
        elapsed = max(0.0, time.time() - self.started_at)
        if self.finished:
            if self.failed:
                spinner = "!  SCAN ERROR"
            else:
                spinner = "✓  SCAN COMPLETE"
        else:
            spinner = f"{self._FRAMES[self._frame]}  SCANNING"
        self.query_one("#scan-spinner", Static).update(spinner)
        if self.finished:
            body = self.finish_message
        else:
            body = (
                f"[b]Challenge:[/b] {rich_escape(self.challenge_name)}\n"
                f"[b]Phase:[/b] FAST local analysis\n"
                f"[b]Current:[/b] {rich_escape(self.current_tool)} → {rich_escape(self.current_target)}\n"
                f"[b]Events:[/b] {self.event_count}\n"
                f"[b]Elapsed:[/b] {elapsed:.1f}s / 60s hard limit"
            )
        self.query_one("#scan-popup-status", Static).update(body)

    def update_event(self, ev: ScanEvent):
        self.event_count += 1
        self.current_tool = str(ev.tool)
        self.current_target = str(ev.target)
        self._refresh_scan_ui()

    def finish_ok(self, seconds: float, events: int):
        self.finished = True
        self.failed = False
        self.finish_message = (
            f"[b green]✓ Smart Pre-Scan complete[/b green]\n"
            f"[b]Challenge:[/b] {rich_escape(self.challenge_name)}\n"
            f"[b]Events:[/b] {events}\n"
            f"[b]Time:[/b] {seconds:.1f}s\n"
            "[b]Context:[/b] .ctf/context.md"
        )
        self._refresh_scan_ui()

    def finish_error(self, message: str):
        self.finished = True
        self.failed = True
        self.finish_message = (
            "[b red]! Smart Pre-Scan failed[/b red]\n"
            f"{rich_escape(message)}\n\n"
            "Return to the dashboard and retry with S."
        )
        self._refresh_scan_ui()


class AgentSessionScreen(ModalScreen):
    """Popup live view of the shared AI PTY."""

    CSS = """
    AgentSessionScreen {
        align: center middle;
        background: rgba(7, 9, 13, 0.72);
        color: #efeff5;
    }
    #live-shell {
        width: 94%;
        height: 90%;
        padding: 1 2;
        background: #090b10;
        border: round #8f5cff;
    }
    #live-title {
        height: 2;
        text-style: bold;
        color: #c99cff;
        border-bottom: solid #5f3f88;
    }
    #live-status {
        height: 8;
        padding: 0 1;
        background: #0d1016;
        border-bottom: solid #3b2b50;
    }
    #live-terminal-label {
        height: 2;
        color: #c99cff;
        text-style: bold;
    }
    #live-terminal {
        height: 1fr;
        padding: 1;
        background: #05070a;
        border: round #5f3f88;
        color: #f2eff8;
        overflow-y: auto;
    }
    #live-input {
        height: 3;
        margin-top: 1;
        border: round #8f5cff;
        background: #0d1016;
        color: #f2eff8;
    }
    #live-help {
        height: 2;
        color: #aeb2bc;
        content-align: left middle;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Dashboard"),
        Binding("t", "takeover", "Take Over"),
        Binding("r", "return_ai", "Return to AI"),
        Binding("ctrl+r", "return_ai", "Return to AI"),
        Binding("i", "interrupt_agent", "Interrupt"),
        Binding("ctrl+c", "interrupt_agent", "Interrupt"),
        Binding("enter", "enter_key", "Confirm / Send", show=False, priority=True),
        Binding("c", "confirm_prompt", "Confirm Prompt"),
        Binding("x", "snapshot", "Snapshot"),
        Binding("y", "recover", "Stuck Recovery"),
        Binding("p", "parallel", "Parallel Agents"),
    ]

    def __init__(self):
        super().__init__()
        self._last_screen = None

    def compose(self):
        with Vertical(id="live-shell"):
            yield Static("AI SESSION • LIVE SHARED TERMINAL", id="live-title")
            yield Static("Waiting for agent…", id="live-status")
            yield Static("LIVE TERMINAL", id="live-terminal-label")
            yield Static("Waiting for terminal output…", id="live-terminal", markup=False)
            yield Input(
                placeholder="Press T to take control, then type to the AI / terminal",
                id="live-input",
                disabled=True,
            )
            yield Static(
                "ESC Dashboard • T Take Over • C Confirm • Ctrl+R Return AI • Ctrl+C Interrupt • X Snapshot • Y Recovery • P Parallel",
                id="live-help",
            )

    def on_mount(self):
        self.set_interval(0.40, self._refresh_view)
        self._refresh_view()

    def _refresh_view(self):
        app = self.app
        c = getattr(app, "selected", None)
        sess = app.current_session() if c else None
        fields = app._activity_fields() if c else {
            "goal": "No challenge selected",
            "action": "Idle",
            "tool": "—",
            "finding": "—",
            "next": "Return to dashboard and select a challenge.",
        }
        mode = "HUMAN TAKEOVER" if getattr(app, "takeover", False) else "AI CONTROL"
        agent_name = "AI"
        if c:
            agent_name = app.last_agent_by_challenge.get(app._key(c), "AI").title()
        self.query_one("#live-title", Static).update(
            f"◆ {rich_escape(agent_name)} • LIVE SHARED TERMINAL ◆"
        )
        self.query_one("#live-status", Static).update(
            f"[b]Goal:[/b] {rich_escape(str(fields['goal']))}\n"
            f"[b]Current action:[/b] {rich_escape(str(fields['action']))}\n"
            f"[b]Tool:[/b] {rich_escape(str(fields['tool']))}\n"
            f"[b]Finding:[/b] {rich_escape(str(fields['finding']))}\n"
            f"[b]Next:[/b] {rich_escape(str(fields['next']))}\n"
            f"[dim]Mode: {mode} • Visible progress only, not private chain-of-thought.[/dim]"
        )
        help_line = self.query_one("#live-help", Static)
        if self._confirmation_visible(sess):
            help_line.update(
                "ENTER Confirm highlighted Yes • C Confirm • ESC Dashboard • T Take Over • Ctrl+C Interrupt"
            )
        else:
            help_line.update(
                "ESC Dashboard • T Take Over • Ctrl+R Return AI • Ctrl+C Interrupt • X Snapshot • Y Recovery • P Parallel"
            )

        live_input = self.query_one("#live-input", Input)
        live_input.disabled = not getattr(app, "takeover", False)
        if not live_input.disabled:
            live_input.placeholder = "Type a prompt or terminal input, then Enter"
        else:
            live_input.placeholder = "Press T to take control, then type to the AI / terminal"

        if sess and sess.running:
            screen = sess.screen_snapshot()
        elif sess:
            screen = sess.screen_snapshot() + "\n\n[agent process exited]"
        else:
            screen = "No active agent. ESC → dashboard, then A to start one."
        signature = (screen, app._terminal_event_signature())
        if signature != self._last_screen:
            self._last_screen = signature
            self.query_one("#live-terminal", Static).update(app._styled_terminal_view(screen))

    def action_back(self):
        self.dismiss()
        try:
            self.app._sync_dashboard_takeover_ui()
        except Exception:
            pass

    def action_takeover(self):
        app = self.app
        sess = app.current_session()
        if not sess or not sess.running:
            return
        if not app.takeover:
            app.takeover = True
            bump(app.selected.path, "takeovers")
            set_status(app.selected.path, "Human Working")
            app._record_terminal_event("system", "Human takeover enabled.")
        inp = self.query_one("#live-input", Input)
        inp.disabled = False
        inp.focus()
        self._refresh_view()

    def action_return_ai(self):
        app = self.app
        sess = app.current_session()
        if not sess or not sess.running:
            return
        app.takeover = False
        set_status(app.selected.path, "AI Working")
        app._record_terminal_event("system", "Terminal returned to AI control.")
        inp = self.query_one("#live-input", Input)
        inp.disabled = True
        self._refresh_view()

    def action_interrupt_agent(self):
        app = self.app
        sess = app.current_session()
        if sess and sess.running:
            sess.interrupt()
            bump(app.selected.path, "interrupts")

    def _confirmation_visible(self, sess=None):
        app = self.app
        return app._trust_prompt_visible(sess)

    def _send_confirmation_enter(self):
        sess = self.app.current_session()
        if not sess or not sess.running:
            self._popup_notice("No active AI session.", "warning")
            return False
        if not self._confirmation_visible(sess):
            return False
        self.app._record_terminal_event("system", "Confirmed the highlighted Claude prompt.")
        sess.send("\r")
        self._popup_notice("Enter sent. Claude should continue.")
        return True

    def action_enter_key(self):
        """Make Enter behave like a real shared terminal Enter.

        At Claude's workspace trust screen it confirms the highlighted option.
        During human takeover it submits the live input field.
        """
        if self._send_confirmation_enter():
            return

        app = self.app
        sess = app.current_session()
        if not getattr(app, "takeover", False) or not sess or not sess.running:
            return

        inp = self.query_one("#live-input", Input)
        value = inp.value
        if value.strip():
            app._send_human_line(value)
        else:
            sess.send("\r")
        inp.value = ""

    def action_confirm_prompt(self):
        """C is kept as an alternate confirmation shortcut."""
        if not self._send_confirmation_enter():
            self._popup_notice("No confirmation prompt is currently visible.", "warning")

    def _popup_notice(self, message: str, severity: str = "information"):
        try:
            self.app.notify(message, title="CTF Control Room", severity=severity, timeout=4)
        except Exception:
            pass

    def action_snapshot(self):
        app = self.app
        if not app.selected:
            return
        try:
            out = create_snapshot(app.selected.path)
            self._popup_notice(f"Snapshot saved: {out}")
        except Exception as exc:
            self._popup_notice(f"Snapshot failed: {exc}", "error")

    def action_recover(self):
        app = self.app
        if not app.selected:
            return
        try:
            ok = app.action_recover()
            if ok:
                self._popup_notice("Stuck Recovery sent. Watch the same live terminal for the new path.")
            else:
                self._popup_notice("Recovery was not started. Check the dashboard message/settings.", "warning")
        except Exception as exc:
            self._popup_notice(f"Recovery failed: {exc}", "error")

    def action_parallel(self):
        app = self.app
        if not app.selected:
            return
        try:
            app._open_parallel_mode()
        except Exception as exc:
            self._popup_notice(f"Parallel Agents failed: {exc}", "error")

    def on_input_submitted(self, event):
        if event.input.id != "live-input":
            return
        value = event.value
        if self.app.takeover:
            sess = self.app.current_session()
            if value.strip():
                self.app._send_human_line(value)
            elif sess and sess.running:
                # Preserve terminal semantics: an empty submit is still Enter.
                sess.send("\r")
        event.input.value = ""


class ParallelAgentsScreen(ModalScreen):
    """Configure and run two truly concurrent, isolated CTF branches."""

    CSS = """
    ParallelAgentsScreen {
        align: center middle;
        background: rgba(7, 9, 13, 0.78);
        color: #efeff5;
    }
    #parallel-shell {
        width: 97%;
        height: 94%;
        padding: 1 2;
        background: #090b10;
        border: round #8f5cff;
    }
    #parallel-title {
        height: 2;
        color: #c99cff;
        text-style: bold;
        border-bottom: solid #5f3f88;
    }

    #parallel-config {
        height: 1fr;
        padding: 1 2;
        background: #0b0e14;
    }
    #parallel-config-note {
        height: 4;
        color: #cfd3dc;
        border-bottom: solid #3b2b50;
        margin-bottom: 1;
    }
    .parallel-config-branch {
        height: 11;
        border: round #5f3f88;
        padding: 1;
        margin-bottom: 1;
        background: #0d1016;
    }
    .parallel-config-title {
        height: 2;
        color: #ffffff;
        text-style: bold;
    }
    .parallel-config-label {
        height: 2;
        color: #aeefff;
    }
    .parallel-agent-buttons, .parallel-method-buttons {
        height: 3;
    }
    .parallel-agent-buttons Button, .parallel-method-buttons Button {
        min-width: 16;
        height: 3;
        margin-right: 1;
        border: round #5f3f88;
    }
    .parallel-selected {
        background: #6f3cff;
        color: #ffffff;
        border: round #c99cff;
        text-style: bold;
    }
    #parallel-selection-summary {
        height: 4;
        padding: 0 1;
        color: #8cffc1;
        border-top: solid #3b2b50;
    }
    #parallel-config-actions {
        height: 4;
        align: center middle;
    }
    #parallel-start {
        min-width: 30;
        height: 3;
        background: #6f3cff;
        color: #ffffff;
        border: round #c99cff;
        text-style: bold;
        margin-right: 2;
    }
    #parallel-cancel {
        min-width: 16;
        height: 3;
    }

    #parallel-live {
        height: 1fr;
    }
    #parallel-status {
        height: 4;
        padding: 0 1;
        background: #0d1016;
        border-bottom: solid #3b2b50;
    }
    #parallel-panes { height: 1fr; }
    .parallel-branch {
        width: 1fr;
        margin: 0 1;
        border: round #5f3f88;
        background: #07090d;
    }
    .parallel-branch-title {
        height: 3;
        padding: 0 1;
        color: #ffffff;
        background: #151020;
        text-style: bold;
        border-bottom: solid #5f3f88;
    }
    .parallel-branch-state {
        height: 4;
        padding: 0 1;
        color: #aeefff;
        border-bottom: solid #2c2238;
    }
    .parallel-terminal {
        height: 1fr;
        padding: 1;
        background: #05070a;
        color: #f2eff8;
        overflow-y: auto;
    }
    #parallel-summary {
        height: 7;
        padding: 0 1;
        margin-top: 1;
        background: #0d1016;
        border-top: solid #8f5cff;
    }
    #parallel-help {
        height: 2;
        color: #aeb2bc;
        content-align: left middle;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Dashboard"),
        Binding("c", "confirm_all", "Confirm Trust"),
        Binding("enter", "confirm_all", "Confirm Trust", show=False),
        Binding("i", "interrupt_all", "Interrupt Both"),
        Binding("ctrl+c", "interrupt_all", "Interrupt Both"),
        Binding("x", "save_summary", "Save Summary"),
        Binding("n", "new_pair", "New Pair"),
    ]

    def __init__(self):
        super().__init__()
        self._last = None
        self.available = []
        self.agent_a = None
        self.agent_b = None
        self.method_a = "reasoning-first"
        self.method_b = "tool-first"

    def compose(self):
        with Vertical(id="parallel-shell"):
            yield Static("◆ PARALLEL AGENTS • CHOOSE TWO WORKERS + METHODS ◆", id="parallel-title")

            with Vertical(id="parallel-config"):
                yield Static(
                    "[b]Choose the two workers before spending AI usage.[/b]\n"
                    "You may choose Claude + Gemini, Claude + Claude, Gemini + Gemini, etc. "
                    "Each branch runs at the same time in its own isolated workspace.",
                    id="parallel-config-note",
                )

                with Vertical(classes="parallel-config-branch"):
                    yield Static("BRANCH A", classes="parallel-config-title")
                    yield Static("1) Choose agent", classes="parallel-config-label")
                    with Horizontal(classes="parallel-agent-buttons"):
                        yield Button("CLAUDE", id="pa-a-claude")
                        yield Button("GEMINI", id="pa-a-gemini")
                        yield Button("CODEX", id="pa-a-codex")
                        yield Button("CAI", id="pa-a-cai")
                    yield Static("2) Choose method", classes="parallel-config-label")
                    with Horizontal(classes="parallel-method-buttons"):
                        yield Button("REASONING FIRST", id="pm-a-reasoning-first")
                        yield Button("TOOL FIRST", id="pm-a-tool-first")

                with Vertical(classes="parallel-config-branch"):
                    yield Static("BRANCH B", classes="parallel-config-title")
                    yield Static("1) Choose agent", classes="parallel-config-label")
                    with Horizontal(classes="parallel-agent-buttons"):
                        yield Button("CLAUDE", id="pa-b-claude")
                        yield Button("GEMINI", id="pa-b-gemini")
                        yield Button("CODEX", id="pa-b-codex")
                        yield Button("CAI", id="pa-b-cai")
                    yield Static("2) Choose method", classes="parallel-config-label")
                    with Horizontal(classes="parallel-method-buttons"):
                        yield Button("REASONING FIRST", id="pm-b-reasoning-first")
                        yield Button("TOOL FIRST", id="pm-b-tool-first")

                yield Static("Selection: —", id="parallel-selection-summary")
                with Horizontal(id="parallel-config-actions"):
                    yield Button("◆ START TWO AGENTS ◆", id="parallel-start")
                    yield Button("CANCEL", id="parallel-cancel")

            with Vertical(id="parallel-live"):
                yield Static("Preparing two independent branches…", id="parallel-status")
                with Horizontal(id="parallel-panes"):
                    with Vertical(classes="parallel-branch"):
                        yield Static("BRANCH A", id="parallel-a-title", classes="parallel-branch-title")
                        yield Static("Starting…", id="parallel-a-state", classes="parallel-branch-state")
                        yield Static("Waiting for terminal output…", id="parallel-a-terminal", classes="parallel-terminal", markup=False)
                    with Vertical(classes="parallel-branch"):
                        yield Static("BRANCH B", id="parallel-b-title", classes="parallel-branch-title")
                        yield Static("Starting…", id="parallel-b-state", classes="parallel-branch-state")
                        yield Static("Waiting for terminal output…", id="parallel-b-terminal", classes="parallel-terminal", markup=False)
                yield Static("Comparing branch results…", id="parallel-summary")
                yield Static(
                    "ESC Dashboard • C/ENTER Confirm any Claude trust prompt • Ctrl+C Interrupt both • X Save summary • N Choose a new pair after completion",
                    id="parallel-help",
                )

    def on_mount(self):
        self.available = self.app._runnable_agents()
        try:
            pair = self.app._parallel_agent_pair()
        except Exception:
            pair = []

        if pair:
            self.agent_a = pair[0]
            self.agent_b = pair[1] if len(pair) > 1 else pair[0]
        elif self.available:
            self.agent_a = self.available[0]
            self.agent_b = self.available[0]

        self._refresh_config_buttons()
        self.set_interval(0.50, self._refresh_view)

        if self.app._parallel_metadata_for_selected():
            self._show_live()
            self._refresh_view()
        else:
            self._show_config()

    def _show_config(self):
        self.query_one("#parallel-config").styles.display = "block"
        self.query_one("#parallel-live").styles.display = "none"
        self._refresh_config_buttons()

    def _show_live(self):
        self.query_one("#parallel-config").styles.display = "none"
        self.query_one("#parallel-live").styles.display = "block"

    def _method_label(self, method_id: str) -> str:
        for strategy in DEFAULT_STRATEGIES:
            if strategy.get("id") == method_id:
                return str(strategy.get("label") or method_id)
        return method_id.replace("-", " ").title()

    def _strategy(self, method_id: str) -> dict:
        for strategy in DEFAULT_STRATEGIES:
            if strategy.get("id") == method_id:
                return dict(strategy)
        raise RuntimeError(f"Unknown parallel method: {method_id}")

    def _refresh_config_buttons(self):
        # Buttons are used instead of dropdowns so selections are always visible.
        for branch, selected in (("a", self.agent_a), ("b", self.agent_b)):
            for agent in ("claude", "gemini", "codex", "cai"):
                button = self.query_one(f"#pa-{branch}-{agent}", Button)
                button.disabled = agent not in self.available
                if selected == agent:
                    button.label = f"✓ {agent.upper()}"
                    button.add_class("parallel-selected")
                else:
                    button.label = agent.upper()
                    button.remove_class("parallel-selected")

        for branch, selected in (("a", self.method_a), ("b", self.method_b)):
            for method in ("reasoning-first", "tool-first"):
                button = self.query_one(f"#pm-{branch}-{method}", Button)
                label = self._method_label(method).upper()
                if selected == method:
                    button.label = f"✓ {label}"
                    button.add_class("parallel-selected")
                else:
                    button.label = label
                    button.remove_class("parallel-selected")

        a = (self.agent_a or "NONE").upper()
        b = (self.agent_b or "NONE").upper()
        self.query_one("#parallel-selection-summary", Static).update(
            f"[b green]A:[/b green] {a} • {rich_escape(self._method_label(self.method_a))}\n"
            f"[b green]B:[/b green] {b} • {rich_escape(self._method_label(self.method_b))}\n"
            "Same agent twice is allowed. Different methods are recommended to reduce duplicate work."
        )

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id or ""

        if bid == "parallel-cancel":
            self.dismiss()
            return

        if bid == "parallel-start":
            self._start_selected_pair()
            return

        if bid.startswith("pa-a-"):
            agent = bid.removeprefix("pa-a-")
            if agent in self.available:
                self.agent_a = agent
                self._refresh_config_buttons()
            return

        if bid.startswith("pa-b-"):
            agent = bid.removeprefix("pa-b-")
            if agent in self.available:
                self.agent_b = agent
                self._refresh_config_buttons()
            return

        if bid.startswith("pm-a-"):
            self.method_a = bid.removeprefix("pm-a-")
            self._refresh_config_buttons()
            return

        if bid.startswith("pm-b-"):
            self.method_b = bid.removeprefix("pm-b-")
            self._refresh_config_buttons()
            return

    def _start_selected_pair(self):
        if not self.agent_a or not self.agent_b:
            self.app.notify(
                "Choose an available agent for both branches.",
                title="Parallel Agents",
                severity="warning",
                timeout=4,
            )
            return
        try:
            self.app._start_parallel_run(
                force_new=True,
                agent_pair=[self.agent_a, self.agent_b],
                strategies=[self._strategy(self.method_a), self._strategy(self.method_b)],
            )
            self._show_live()
            self._refresh_view()
        except Exception as exc:
            self.app.notify(str(exc), title="Parallel Agents", severity="error", timeout=6)

    def _refresh_view(self):
        # Do not replace the setup UI while the user is still choosing a pair.
        if self.query_one("#parallel-config").styles.display != "none":
            return

        app = self.app
        data = app._parallel_view_data()
        if not data:
            self.query_one("#parallel-status", Static).update("No parallel run is available.")
            return
        meta, branches = data
        run_id = meta.get("run_id", "—")
        running = sum(1 for b in branches if b["status"] == "RUNNING")
        waiting = sum(1 for b in branches if b["waiting_for_trust"])
        self.query_one("#parallel-status", Static).update(
            f"[b]Run:[/b] {rich_escape(str(run_id))}  •  "
            f"[b]Running:[/b] {running}/2  •  [b]Trust prompts:[/b] {waiting}\n"
            "Independent workspaces • two chosen methods • results compared locally • extra AI usage is expected"
        )

        slots = ("a", "b")
        signature_parts = [run_id, running, waiting]
        for slot, branch in zip(slots, branches):
            candidate = branch.get("candidate_flag") or "—"
            agent = str(branch.get("agent", "AI")).title()
            label = str(branch.get("label", branch.get("id", "Branch")))
            state = branch["status"]
            if branch["waiting_for_trust"]:
                state += " • WAITING FOR TRUST (press C/Enter)"
            self.query_one(f"#parallel-{slot}-title", Static).update(
                f"{slot.upper()} • {rich_escape(agent)} • {rich_escape(label)}"
            )
            self.query_one(f"#parallel-{slot}-state", Static).update(
                f"Status: {state}\nRuntime: {branch['runtime_seconds']:.1f}s • Candidate: {rich_escape(candidate)}"
            )
            screen = branch.get("screen") or "Waiting for terminal output…"
            self.query_one(f"#parallel-{slot}-terminal", Static).update(Text(screen))
            signature_parts.extend([state, candidate, screen[-500:]])

        summary = app._parallel_summary(save_if_complete=True)
        verdict = summary.get("verdict", "running") if summary else "running"
        candidate = summary.get("candidate_flag") if summary else None
        if verdict == "agreement":
            headline = f"[b green]✓ BOTH BRANCHES AGREE[/b green] • {rich_escape(str(candidate))}"
        elif verdict == "disagreement":
            headline = "[b yellow]! BRANCHES DISAGREE[/b yellow] • inspect both terminals before accepting a flag"
        elif verdict == "single-branch-candidate":
            headline = f"[b cyan]One branch has a candidate[/b cyan] • {rich_escape(str(candidate))}"
        elif verdict == "no-flag-candidate" and running == 0:
            headline = "[b yellow]Both branches finished without a confirmed flag candidate.[/b yellow]"
        else:
            headline = "[b magenta]Branches are investigating concurrently…[/b magenta]"
        run_dir = meta.get("run_dir", "")
        self.query_one("#parallel-summary", Static).update(
            f"{headline}\n"
            f"Branch A: {rich_escape(str(branches[0].get('candidate_flag') or '—'))}\n"
            f"Branch B: {rich_escape(str(branches[1].get('candidate_flag') or '—'))}\n"
            f"Comparison file: {rich_escape(str(run_dir))}/summary.md (written when complete or when you press X)"
        )
        self._last = tuple(signature_parts)

    def action_confirm_all(self):
        # Enter only acts as trust confirmation while the live view is shown.
        if self.query_one("#parallel-live").styles.display == "none":
            return
        count = self.app._confirm_parallel_trust()
        if count:
            self.app.notify(f"Confirmed {count} waiting branch(es).", title="Parallel Agents", timeout=3)

    def action_interrupt_all(self):
        if self.query_one("#parallel-live").styles.display == "none":
            return
        count = self.app._interrupt_parallel_sessions()
        if count:
            self.app.notify(f"Interrupt sent to {count} branch(es).", title="Parallel Agents", timeout=3)

    def action_save_summary(self):
        if self.query_one("#parallel-live").styles.display == "none":
            return
        summary = self.app._parallel_summary(save_if_complete=False)
        if summary:
            meta = self.app._parallel_metadata_for_selected()
            self.app.notify(f"Summary saved in {meta['run_dir']}", title="Parallel Agents", timeout=4)

    def action_new_pair(self):
        if self.app._parallel_any_running():
            self.app.notify(
                "Both current branches must finish or be stopped before choosing a new pair.",
                title="Parallel Agents",
                severity="warning",
                timeout=4,
            )
            return
        self.app._clear_parallel_selected()
        self._show_config()

    def action_back(self):
        self.dismiss()


class ControlRoom(App):
    TITLE = "CTF Control Room"
    SUB_TITLE = ""
    CSS = """
    Screen {
        background: #090b10;
        color: #e8e8ee;
    }
    Header {
        background: #0f1118;
        color: #f4f0ff;
    }
    #body { height: 1fr; }
    #left {
        width: 38%;
        min-width: 52;
        border: round #8f5cff;
        background: #0d1016;
    }
    #right {
        width: 62%;
        border: round #8f5cff;
        background: #0b0e14;
    }
    #title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: #f2eff8;
        background: #0f1118;
        border-bottom: solid #5f3f88;
    }
    #challenge-info {
        height: 6;
        padding: 0 2;
        border-bottom: solid #3b2b50;
        background: #0e1118;
    }
    #agent-panel {
        height: 13;
        padding: 0 2;
        border-bottom: solid #3b2b50;
        background: #0d1016;
    }
    #agent-label {
        height: 2;
        content-align: left middle;
        color: #c99cff;
        text-style: bold;
    }
    #agent-choices {
        width: 1fr;
        height: 4;
    }
    .agent-choice {
        width: 1fr;
        height: 3;
        margin-right: 1;
        background: #12151d;
        color: #e9e6f2;
        border: round #5f3f88;
        text-style: bold;
    }
    .agent-choice:hover {
        background: #21182e;
        border: round #8f5cff;
    }
    .agent-choice.selected-agent {
        background: #6f3cff;
        color: #ffffff;
        border: round #c99cff;
        text-style: bold;
    }
    .agent-choice:disabled {
        color: #666a75;
        background: #0c0e13;
        border: round #30333d;
    }
    #agent-selected {
        height: 2;
        content-align: left middle;
        color: #8cffc1;
        text-style: bold;
    }
    #agent-detected {
        height: 2;
        content-align: left middle;
        color: #75d7ff;
    }
    #open-ai-window {
        width: 42;
        height: 3;
        margin-top: 0;
        background: #6f3cff;
        color: #ffffff;
        border: round #c99cff;
        text-style: bold;
    }
    #open-ai-window:focus {
        background: #8f5cff;
        border: round #ffffff;
    }
    #scan-status {
        height: 5;
        padding: 0 2;
        border-bottom: solid #3b2b50;
        background: #0e1118;
    }
    #ai-status {
        height: 8;
        padding: 0 2;
        content-align: left middle;
        border-bottom: solid #3b2b50;
        background: #0d1016;
        color: #e8e8ee;
    }
    #terminal-label {
        height: 3;
        padding: 0 1;
        content-align: left middle;
        color: #ffffff;
        background: #151020;
        border-top: solid #8f5cff;
        border-bottom: solid #5f3f88;
        text-style: bold;
    }
    #terminal {
        height: 1fr;
        min-height: 12;
        margin: 0 1;
        padding: 1;
        border: round #5f3f88;
        background: #05070b;
        color: #f4f4f7;
    }
    #command-input {
        height: 3;
        margin: 0 1 1 1;
        border: round #8f5cff;
        background: #0d1016;
        color: #ffffff;
    }
    #activity-label {
        height: 2;
        padding-left: 1;
        content-align: left middle;
        color: #c99cff;
        text-style: bold;
        border-top: solid #3b2b50;
    }
    #activity {
        height: 1fr;
        min-height: 6;
        padding: 1;
        background: #10131a;
        border-top: solid #2c2238;
    }
    #challenge-table {
        height: 38%;
        min-height: 9;
        background: #0d1016;
        color: #e7e7ed;
        border-bottom: solid #3b2b50;
    }
    DataTable {
        background: #0d1016;
        color: #e7e7ed;
    }
    Select {
        height: 3;
        background: #12151d;
        color: #f1ecfa;
        border: round #5f3f88;
    }
    Footer {
        background: #0f1118;
        color: #d4ccdf;
    }
    .muted { color: #9aa0aa; }
    """

    BINDINGS = [
        Binding("s","scan","Smart Pre-Scan"),
        Binding("a","agent","Start AI"),
        Binding("t","takeover","Take Over"),
        Binding("r","return_ai","Return to AI"),
        Binding("i","interrupt_agent","Interrupt"),
        Binding("h","handoff","Handoff"),
        Binding("e","export","Prepare Write-up"),
        Binding("l","learn","Save Lesson"),
        Binding("x","snapshot","Snapshot"),
        Binding("y","recover","Stuck Recovery"),
        Binding("p","parallel","Parallel Agents"),
        Binding("f","refresh","Refresh"),
        Binding("v","ai_view","AI View"),
        Binding("w","welcome","Welcome"),
        Binding("question_mark","help","Help"),
        Binding("q","quit","Quit"),
    ]

    def __init__(self, ctf_root: Path, default_agent="codex"):
        super().__init__()
        self.ctf_root=Path(ctf_root); self.default_agent=default_agent
        self.challenges=[]; self.selected=None; self.last_agent_by_challenge={}
        self.sessions={}; self.takeover=False; self._last_stuck_warn={}
        self.session_dirs={}
        self.session_names={}
        self._finalized_main_sessions=set()
        self._latest_terminal_text={}
        self._latest_terminal_screen={}
        self._last_rendered_terminal={}
        self._terminal_events={}
        self.parallel_sessions={}
        self.parallel_metadata={}
        self.parallel_output={}
        self._parallel_finalized=set()
        self._scan_running=False
        self._scan_screen=None

    def _runnable_agents(self) -> list[str]:
        """Runnable agents filtered by Control Room feature switches."""
        agents = list(available_agents())
        settings = load_settings(self.ctf_root)
        if "cai" in agents and not settings.get("cai_backend"):
            agents.remove("cai")
        return agents

    def compose(self)->ComposeResult:
        yield Header(show_clock=True)
        yield Static("CTF CONTROL ROOM", id="title")
        with Horizontal(id="body"):
            with Vertical(id="left"):
                yield Label(" COMPETITION DASHBOARD ", classes="muted")
                yield DataTable(id="challenge-table")
                yield Static(" LIVE SHARED TERMINAL • AI CONTROL ", id="terminal-label")
                yield RichLog(id="terminal", wrap=True, highlight=False, markup=False)
                yield Input(
                    placeholder="T = take over • type command/message • Enter to send",
                    id="command-input",
                    disabled=True,
                )
            with Vertical(id="right"):
                yield Static("Select a challenge.", id="challenge-info")
                with Vertical(id="agent-panel"):
                    yield Static("AI AGENT", id="agent-label")
                    detected_agents = self._runnable_agents()
                    initial_agent = (
                        self.default_agent
                        if self.default_agent in detected_agents
                        else (detected_agents[0] if detected_agents else None)
                    )
                    if initial_agent:
                        self.default_agent = initial_agent
                    with Horizontal(id="agent-choices"):
                        yield Button(
                            "CLAUDE",
                            id="agent-claude",
                            classes="agent-choice" + (" selected-agent" if initial_agent == "claude" else ""),
                            disabled="claude" not in detected_agents,
                        )
                        yield Button(
                            "GEMINI",
                            id="agent-gemini",
                            classes="agent-choice" + (" selected-agent" if initial_agent == "gemini" else ""),
                            disabled="gemini" not in detected_agents,
                        )
                        yield Button(
                            "CODEX",
                            id="agent-codex",
                            classes="agent-choice" + (" selected-agent" if initial_agent == "codex" else ""),
                            disabled="codex" not in detected_agents,
                        )
                        yield Button(
                            "CAI",
                            id="agent-cai",
                            classes="agent-choice" + (" selected-agent" if initial_agent == "cai" else ""),
                            disabled="cai" not in detected_agents,
                        )
                    yield Static(
                        "✓ SELECTED: " + (str(initial_agent).upper() if initial_agent else "NONE"),
                        id="agent-selected",
                    )
                    yield Static(
                        "Detected: " + (", ".join(a.title() for a in detected_agents) if detected_agents else "None"),
                        id="agent-detected",
                    )
                    yield Button(
                        "◆ OPEN LIVE AI WINDOW  [V] ◆",
                        id="open-ai-window",
                    )
                yield Static("Automatic Smart Pre-Scan (No AI) has not run.", id="scan-status")
                yield Static("AI status: idle", id="ai-status")
                yield Static(" ACTIVITY / TOOL EVENTS ", id="activity-label")
                yield RichLog(id="activity", wrap=True, highlight=True, markup=True)
        yield Footer()

    def on_mount(self):
        table=self.query_one("#challenge-table",DataTable); table.cursor_type="row"
        table.add_columns("Challenge","Category","Status","Agent","Cmds","Dup","Time")
        self.refresh_agent_select(); self.refresh_challenges()
        self.set_interval(2.0,self._tick)
        self.set_interval(0.25,self._refresh_live_terminal)
        self.push_screen(WelcomeScreen(), self._welcome_done)

    def _welcome_done(self, result):
        if result == "help":
            self.push_screen(HelpScreen(), self._help_done)
        elif result == "open":
            self.refresh_agent_select()
            self.refresh_challenges()

    def _help_done(self, result):
        if result == "welcome":
            self.push_screen(WelcomeScreen(), self._welcome_done)
        else:
            self.refresh_agent_select()

    def refresh_agent_select(self):
        raw_agents = available_agents()
        agents = self._runnable_agents()
        detected = self.query_one("#agent-detected", Static)

        preferred = self.default_agent if self.default_agent in agents else None
        if not preferred and agents:
            preferred = agents[0]
        self.default_agent = preferred

        for agent in ("claude", "gemini", "codex", "cai"):
            button = self.query_one(f"#agent-{agent}", Button)
            button.disabled = agent not in agents

        suffix = ""
        if "cai" in raw_agents and "cai" not in agents:
            suffix = " • CAI installed / backend OFF"
        detected.update(
            "Detected: " + (", ".join(a.title() for a in agents) if agents else "None") + suffix
        )
        self._update_agent_display()

    def _update_agent_display(self):
        try:
            agent = self._selected_agent()
            selected = self.query_one("#agent-selected", Static)
            open_button = self.query_one("#open-ai-window", Button)

            for name in ("claude", "gemini", "codex", "cai"):
                choice = self.query_one(f"#agent-{name}", Button)
                if name == agent:
                    choice.add_class("selected-agent")
                    choice.label = f"✓ {name.upper()}"
                else:
                    choice.remove_class("selected-agent")
                    choice.label = name.upper()

            if agent:
                selected.update(f"✓ SELECTED: {agent.upper()}")
                open_button.label = f"◆ OPEN {agent.upper()} LIVE WINDOW  [V] ◆"
            else:
                selected.update("✓ SELECTED: NONE")
                open_button.label = "◆ OPEN LIVE AI WINDOW  [V] ◆"
        except Exception:
            pass

    def _choose_agent(self, agent: str):
        agents = self._runnable_agents()
        if agent not in agents:
            return
        self.default_agent = agent
        self._update_agent_display()
        try:
            self.query_one("#activity", RichLog).write(
                f"[b green]Selected AI agent: {agent.title()}[/b green]"
            )
        except Exception:
            pass

    def _selected_agent(self):
        agents = self._runnable_agents()
        if self.default_agent in agents:
            return self.default_agent
        if agents:
            self.default_agent = agents[0]
            return self.default_agent
        return None

    def _key(self,c): return str(c.path)
    def current_session(self): return self.sessions.get(self._key(self.selected)) if self.selected else None

    def refresh_challenges(self):
        self.challenges=discover_challenges(self.ctf_root)
        table=self.query_one("#challenge-table",DataTable); table.clear()
        for c in self.challenges:
            m=load_metrics(c.path); sess=self.sessions.get(self._key(c))
            agent=self.last_agent_by_challenge.get(self._key(c),"—")
            status=m.get("status",c.status)
            if sess and sess.running: status="AI Working"
            runtime=int(m.get("agent_runtime_seconds",0))
            if sess and sess.running and sess.started_at: runtime += int(time.time()-sess.started_at)
            table.add_row(c.name,c.category.upper(),status,agent,str(m.get("commands",0)),
                          str(m.get("duplicates_blocked",0)),f"{runtime//60:02d}:{runtime%60:02d}")
        if self.challenges and not self.selected:
            table.move_cursor(row=0); self.select_index(0)

    def _tick(self):
        self._finalize_main_session_if_needed()
        # Do not rebuild the hidden dashboard while a modal is actively
        # rendering live progress. This keeps both AI and scan popups smooth.
        if isinstance(self.screen, AgentSessionScreen):
            if self.selected:
                self._detect_stuck()
            return
        if isinstance(self.screen, ParallelAgentsScreen):
            self._finalize_parallel_if_complete()
            return
        if isinstance(self.screen, SmartScanScreen):
            return
        self.refresh_challenges()
        if self.selected:
            self._render_selected()
            self._detect_stuck()

    def select_index(self,index):
        if not (0<=index<len(self.challenges)): return
        self.selected=self.challenges[index]; self.takeover=False
        self.query_one("#command-input",Input).disabled=True
        self._render_selected(); self._replay_session_hint()

    def on_data_table_row_highlighted(self,event):
        if event.cursor_row is not None: self.select_index(event.cursor_row)

    def _record_terminal_event(self, kind: str, message: str):
        """Keep a short UI-only mirror of human/system events for the shared PTY."""
        if not self.selected:
            return
        key = self._key(self.selected)
        events = self._terminal_events.setdefault(key, [])
        clean = re.sub(r"\s+", " ", str(message)).strip()
        if not clean:
            return
        events.append((kind, clean[:500]))
        self._terminal_events[key] = events[-8:]

    def _terminal_event_signature(self):
        if not self.selected:
            return ()
        return tuple(self._terminal_events.get(self._key(self.selected), []))

    def _styled_terminal_view(self, screen: str):
        """Render USER and SYSTEM lines distinctly above the real AI PTY screen.

        Terminal TUIs cannot reliably switch font families per line, so we use
        labels, weight, and color to make authorship immediately obvious.
        """
        view = Text()
        events = list(self._terminal_event_signature())
        if events:
            view.append("CONTROL ROOM MIRROR\n", style="bold magenta")
            for kind, message in events[-5:]:
                if kind == "user":
                    view.append("YOU › ", style="bold bright_green")
                    view.append(message + "\n", style="bold bright_green")
                elif kind == "system":
                    view.append("SYSTEM › ", style="bold magenta")
                    view.append(message + "\n", style="dim magenta")
                else:
                    view.append(f"{kind.upper()} › ", style="bold cyan")
                    view.append(message + "\n", style="cyan")
            view.append("─" * 58 + "\n", style="dim")
        view.append(screen or "")
        return view

    def _render_selected(self):
        c=self.selected
        if not c: return
        m=load_metrics(c.path); sess=self.current_session()
        key=self._key(c)
        status=m.get("status","Ready"); agent=self.last_agent_by_challenge.get(key,"none")
        session_name=self.session_names.get(key,"—")
        runtime=float(m.get("agent_runtime_seconds",0))
        if sess and sess.running and sess.started_at: runtime += time.time()-sess.started_at
        lessons=related_lessons(self.ctf_root,c.category,3)
        self.query_one("#challenge-info",Static).update(
            f"[b]{c.name}[/b] • {c.category.upper()}\n"
            f"Status: {status} • Agent: {agent} • Session: {session_name}\n"
            f"Scan: {m.get('scan_seconds',0):.1f}s • AI runtime: {runtime:.0f}s • Commands: {m.get('commands',0)}\n"
            f"Duplicates blocked: {m.get('duplicates_blocked',0)} • Handoffs: {m.get('handoffs',0)} • Takeovers: {m.get('takeovers',0)}\n"
            + (f"Memory: {lessons[0][:90]}" if lessons else "Memory: no saved category lessons yet")
        )
        mode="[b green]HUMAN TAKEOVER[/b green]" if self.takeover else "[dim]AI CONTROL[/dim]"
        self.query_one("#terminal-label",Static).update(f" LIVE SHARED TERMINAL • {mode} ")
        current=self._infer_activity()
        self.query_one("#ai-status",Static).update(
            f"[b]AI LIVE STATUS[/b]\n{current}"
        )

    def _recent_visible_lines(self):
        sess=self.current_session()
        if not sess: return []
        text="\n".join(sess.output_history[-80:])
        lines=[]
        seen=set()
        for raw in text.splitlines():
            line=re.sub(r"\s+"," ",raw).strip()
            if not line or len(line)<2: continue
            if line in seen and len(lines)>10: continue
            seen.add(line)
            lines.append(line[:220])
        return lines[-80:]

    def _trust_prompt_visible(self, sess=None):
        """Return True only while Claude's workspace trust prompt is currently active.

        We intentionally inspect only the bottom of the emulated terminal so old
        trust text in scrollback cannot hijack a later Enter key.
        """
        sess = sess or self.current_session()
        if not sess or not sess.running:
            return False
        lines = [line.strip().lower() for line in sess.screen_snapshot().splitlines() if line.strip()]
        tail = "\n".join(lines[-14:])
        if not tail:
            return False
        return (
            "enter to confirm" in tail
            and "yes, i trust this folder" in tail
            and ("quick safety check" in tail or "security guide" in tail)
        )

    def _activity_fields(self):
        c=self.selected
        if not c:
            return {"goal":"No challenge selected","action":"Idle","tool":"—","finding":"—","next":"Select a challenge."}
        sess=self.current_session()
        goal=f"Solve {c.name} ({c.category}) and recover the challenge flag"
        if not sess:
            scan_ready=(c.path/".ctf"/"context.md").exists()
            return {
                "goal":goal,
                "action":"Smart Pre-Scan complete" if scan_ready else "Waiting for Smart Pre-Scan",
                "tool":"—",
                "finding":"Compact context is ready." if scan_ready else "No AI session yet.",
                "next":"Press A to start the selected AI agent." if scan_ready else "Press S first.",
            }
        if not sess.running:
            return {"goal":goal,"action":"Agent process exited","tool":"—","finding":"Session output is preserved.","next":"ESC to dashboard, then press A to start a new session."}

        screen_text=sess.screen_snapshot()
        low_screen=screen_text.lower()
        if self._trust_prompt_visible(sess):
            return {
                "goal":goal,
                "action":"Claude is waiting for workspace trust confirmation.",
                "tool":"Claude workspace trust",
                "finding":"Challenge analysis has not started yet.",
                "next":"If this is your trusted CTF folder, press Enter (or C) to confirm the highlighted Yes option.",
            }
        if self.takeover:
            return {"goal":goal,"action":"Human is controlling the shared PTY","tool":"manual input","finding":"AI session remains connected.","next":"Type input, or press R to return control to AI."}

        # If the visible terminal clearly contains a finished solution, show a
        # stable result instead of trying to infer status from Claude UI chrome.
        candidate_flag = choose_candidate_flag(screen_text)
        solved_markers = ("solution chain", "challenge solved", "flag recovered", "cooked for")
        if candidate_flag and any(marker in low_screen for marker in solved_markers):
            return {
                "goal":goal,
                "action":"Challenge solution produced",
                "tool":"completed terminal workflow",
                "finding":f"Flag recovered: {candidate_flag}",
                "next":"Review the solution, then use X for a snapshot or E to prepare the write-up.",
            }

        lines=self._recent_visible_lines()
        lower=[x.lower() for x in lines]
        tools=[
            "exiftool","binwalk","file","strings","xxd","hexdump","unzip","7z","tshark","tcpdump",
            "grep","rg","find","python","python3","gdb","r2","radare2","objdump","readelf","nm",
            "nmap","curl","wget","sqlmap","john","hashcat","steghide","foremost","yara","adb","apktool",
        ]
        tool="—"
        for line in reversed(lower):
            for candidate in tools:
                if re.search(rf"(?<![\w-]){re.escape(candidate)}(?![\w-])", line):
                    tool=candidate
                    break
            if tool!="—": break

        noise=(
            "esc dashboard","take over","return to ai","ctrl-c","tokens","context left","shift+tab",
            "mousesupport","clicktomove","expandresults","fullscreen renderer","auto mode on",
            "claude can make mistakes","isolated environments","bypass permissions",
        )
        user_prompts = [
            message.lower().strip()
            for kind, message in self._terminal_event_signature()
            if kind == "user"
        ]

        def is_user_echo(line: str) -> bool:
            low = line.lower().strip()
            normalized = low.lstrip(">›•- ").strip()
            for prompt in user_prompts:
                if not prompt:
                    continue
                if normalized == prompt:
                    return True
                if prompt in normalized and len(normalized) <= len(prompt) + 24:
                    return True
            return False

        useful=[
            line for line in lines
            if len(line) <= 180
            and not any(n in line.lower() for n in noise)
            and not is_user_echo(line)
        ]
        action="Agent is active in the terminal."
        action_words=("inspect","check","read","analy","extract","decode","search","run","look","open","test","investigat","trying","using")
        for line in reversed(useful):
            if any(w in line.lower() for w in action_words):
                action=line
                break
        if action=="Agent is active in the terminal." and useful:
            action=useful[-1]

        finding="No clear finding yet."
        finding_words=("found","detected","result","flag","metadata","archive","zip","signature","error","failed","success","contains","reveals","appears")
        for line in reversed(useful):
            if any(w in line.lower() for w in finding_words):
                finding=line
                break

        next_step="Watch the live terminal; take over with T if needed."
        next_words=("next","i'll","i will","let me","now i","then","try ","need to","going to")
        for line in reversed(useful):
            if any(w in line.lower() for w in next_words):
                next_step=line
                break

        return {"goal":goal,"action":action[:180],"tool":tool,"finding":finding[:180],"next":next_step[:180]}

    def _infer_activity(self):
        fields=self._activity_fields()
        return (
            f"Goal: {rich_escape(str(fields['goal']))}\n"
            f"Current action: {rich_escape(str(fields['action']))}\n"
            f"Tool: {rich_escape(str(fields['tool']))}\n"
            f"Finding: {rich_escape(str(fields['finding']))}\n"
            f"Next: {rich_escape(str(fields['next']))}\n"
            "Visible progress only — private chain-of-thought is not shown."
        )

    def _detect_stuck(self):
        c=self.selected; sess=self.current_session()
        if not c or not sess or not sess.running: return
        recent="".join(sess.output_history[-40:]).lower()
        # Mechanical loop detection only: repeated error/command-like lines.
        lines=[re.sub(r"\\s+"," ",x.strip()) for x in recent.splitlines() if x.strip()]
        if len(lines)<8: return
        counts={}
        for x in lines[-25:]:
            if len(x)<8: continue
            counts[x]=counts.get(x,0)+1
        repeated=max(counts.values(),default=0)
        key=self._key(c)
        if repeated>=3 and time.time()-self._last_stuck_warn.get(key,0)>30:
            self._last_stuck_warn[key]=time.time()
            bump(c.path,"stuck_warnings"); set_status(c.path,"Possible Stuck")
            self.query_one("#activity",RichLog).write(
                "[yellow]⚠ Possible repeated approach detected. Control Room did NOT stop the agent. "
                "Press T to take over, R to return to AI, I to interrupt, or H to hand off.[/yellow]"
            )

    def _replay_session_hint(self):
        term=self.query_one("#terminal",RichLog); term.clear()
        sess=self.current_session()
        if sess and sess.running:
            term.write(self._styled_terminal_view(sess.screen_snapshot()))
        elif sess:
            term.write(self._styled_terminal_view(sess.screen_snapshot()+"\n[agent process exited]"))
        else:
            term.write("No active agent. Press A to start one.")

    def _refresh_live_terminal(self):
        # The popup renders the same PTY itself. Avoid rendering it a second
        # time into the dashboard behind the modal.
        if isinstance(self.screen, AgentSessionScreen): return
        if not self.selected: return
        sess=self.current_session()
        if not sess: return
        key=self._key(self.selected)
        screen=sess.screen_snapshot()
        signature=(screen,self._terminal_event_signature())
        if self._last_rendered_terminal.get(key)==signature: return
        self._last_rendered_terminal[key]=signature
        try:
            term=self.query_one("#terminal",RichLog)
            term.clear(); term.write(self._styled_terminal_view(screen))
        except Exception:
            pass


    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id or ""
        if bid.startswith("agent-") and bid != "agent-panel":
            agent = bid.removeprefix("agent-")
            if agent in ("claude", "gemini", "codex", "cai"):
                self._choose_agent(agent)
                return
        if bid == "open-ai-window":
            self.action_ai_view()

    def action_ai_view(self):
        if not self.selected:
            return
        self.push_screen(AgentSessionScreen())

    def action_welcome(self):
        self.push_screen(WelcomeScreen(), self._welcome_done)

    def action_help(self):
        self.push_screen(HelpScreen(), self._help_done)

    def action_refresh(self):
        self.refresh_agent_select(); self.refresh_challenges()

    async def action_scan(self):
        if not self.selected: return
        c=self.selected; log=self.query_one("#activity",RichLog); status=self.query_one("#scan-status",Static)
        if self._scan_running:
            log.write("[yellow]Smart Pre-Scan is already running.[/yellow]")
            return

        self._scan_running=True
        scan_screen=SmartScanScreen(c.name)
        self._scan_screen=scan_screen
        self.push_screen(scan_screen)
        log.write(f"[b magenta]Automatic Smart Pre-Scan: {c.name}[/b magenta]")
        status.update(
            "[b]AUTOMATIC SMART PRE-SCAN — NO AI[/b]\n"
            "◐ Scanning local evidence… • FAST tools • 60s hard limit"
        )

        def cb(ev: ScanEvent):
            sym="✓" if ev.ok else "!"
            self.call_from_thread(log.write,f"[{'green' if ev.ok else 'yellow'}]{sym} {ev.tool}[/] → {ev.target}")
            self.call_from_thread(scan_screen.update_event, ev)

        try:
            events=await asyncio.to_thread(scan_challenge,c,cb)
            m=load_metrics(c.path)
            seconds=float(m.get('scan_seconds',0) or 0)
            status.update(
                f"[b]AUTOMATIC SMART PRE-SCAN — NO AI[/b]\n✓ complete in {seconds:.1f}s • "
                f"{len(events)} events\nRaw: .ctf/raw/ • Context: .ctf/context.md"
            )
            scan_screen.finish_ok(seconds, len(events))
            await asyncio.sleep(0.85)
        except Exception as exc:
            set_status(c.path,"Scan Error")
            log.write(f"[red]Scan error: {exc}[/red]")
            status.update(
                "[b red]AUTOMATIC SMART PRE-SCAN — ERROR[/b red]\n"
                f"{rich_escape(str(exc))}"
            )
            scan_screen.finish_error(str(exc))
            await asyncio.sleep(1.4)
        finally:
            self._scan_running=False
            self._scan_screen=None
            if self.screen is scan_screen:
                scan_screen.dismiss()
            self.refresh_challenges()

    def _start_session(
        self,
        agent,
        handoff=False,
        *,
        initial_prompt: str | None = None,
        purpose: str | None = None,
    ):
        c=self.selected; key=self._key(c)
        old=self.sessions.get(key)
        if old and old.running:
            raise RuntimeError("An agent is already running for this challenge.")

        startup_prompt = initial_prompt or (
            "You are working inside CTF Control Room on an authorized Capture The Flag challenge. "
            "Read .ctf/context.md and .ctf/hypothesis.md before acting. Investigate the challenge and work toward the flag. "
            "Use local tools only as needed. Keep the user informed with concise visible progress updates "
            "(current action, tool, finding, next step). Do not reveal private chain-of-thought. "
            + ("Also read .ctf/handoff.md and continue from the previous agent. " if handoff else "")
        )
        session_purpose = purpose or ("handoff" if handoff else "normal")
        session_name, session_dir = create_session_workspace(
            c.path,
            agent,
            purpose=session_purpose,
            prompt=startup_prompt,
        )

        try:
            argv,env=build_agent_invocation(
                agent,c.path,handoff=handoff,initial_prompt=startup_prompt
            )
        except Exception:
            finalize_session(
                session_dir,
                status="start-error",
                runtime_seconds=0.0,
            )
            raise

        env.update(session_env(c.path, session_name))
        env["CTF_CONTROL_TOOL_REGISTRY"]=str(c.path/".ctf"/"tool_registry.md")
        env["CTF_CONTROL_COMMAND_LOG"]=str(c.path/".ctf"/"commands.jsonl")
        term=self.query_one("#terminal",RichLog); term.clear()

        def on_output(clean,screen):
            if clean:
                self._latest_terminal_text[key]=(self._latest_terminal_text.get(key,"")+"\\n"+clean)[-12000:]
                append_transcript(session_dir, clean)
                try:
                    update_from_visible_output(c.path, clean)
                except Exception:
                    pass
            self._latest_terminal_screen[key]=screen
            try:
                update_screen(session_dir, screen)
            except Exception:
                pass

        sess=PTYSession(argv,c.path,env,on_output,cols=120,rows=28)
        sess.start()
        self.sessions[key]=sess
        self.session_dirs[key]=session_dir
        self.session_names[key]=session_name
        self.last_agent_by_challenge[key]=agent
        self._terminal_events[key]=[]
        self._record_terminal_event(
            "system",
            f"Started {agent.title()} in shared PTY • persistent session {session_name}.",
        )
        bump(c.path,"agent_runs"); set_status(c.path,"AI Working")
        self.query_one("#activity",RichLog).write(
            f"[b cyan]Started {agent} in shared PTY.[/b cyan] "
            f"[dim]session: .ctf/sessions/{session_name}/[/dim]"
        )

    def _finalize_main_session_if_needed(self, *, forced_status: str | None = None):
        if not self.selected:
            return
        key = self._key(self.selected)
        sess = self.sessions.get(key)
        session_dir = self.session_dirs.get(key)
        if not sess or not session_dir:
            return
        marker = f"{key}|{session_dir}"
        if marker in self._finalized_main_sessions:
            return
        if sess.running and forced_status is None:
            return

        candidate = None
        try:
            candidate = choose_candidate_flag(sess.screen_snapshot())
        except Exception:
            pass
        status = forced_status or "finished"
        try:
            finalize_session(
                session_dir,
                status=status,
                runtime_seconds=float(getattr(sess, "runtime_seconds", 0.0) or 0.0),
                candidate_flag=candidate,
            )
            self._finalized_main_sessions.add(marker)
        except Exception:
            pass


    async def action_agent(self):
        if not self.selected: return
        if not (self.selected.path/".ctf"/"context.md").exists():
            self.query_one("#activity",RichLog).write("[yellow]Run S first. It uses no AI.[/yellow]"); return
        agent=self._selected_agent()
        if not agent: return
        try:
            self._start_session(agent)
            self.push_screen(AgentSessionScreen())
        except Exception as exc: self.query_one("#activity",RichLog).write(f"[red]{exc}[/red]")

    def _sync_dashboard_takeover_ui(self):
        try:
            inp=self.query_one("#command-input",Input)
            inp.disabled=not self.takeover
            if self.takeover: inp.focus()
        except Exception:
            pass
        self._render_selected()

    def _send_human_line(self,value):
        sess=self.current_session()
        if self.takeover and sess and sess.running and value:
            log_command(self.selected.path,value,"human")
            try:
                record_command(self.selected.path, value, "human")
            except Exception:
                pass
            self._record_terminal_event("user", value)
            session_dir=self.session_dirs.get(self._key(self.selected))
            if session_dir:
                try: append_transcript(session_dir, f"YOU > {value}")
                except Exception: pass
            sess.send_line(value)
            try:
                self.query_one("#activity",RichLog).write(f"[b bright_green]YOU › {rich_escape(value)}[/b bright_green]")
            except Exception:
                pass

    def action_takeover(self):
        sess=self.current_session()
        if not sess or not sess.running or self.takeover: return
        self.takeover=True
        inp=self.query_one("#command-input",Input); inp.disabled=False
        bump(self.selected.path,"takeovers"); set_status(self.selected.path,"Human Working")
        inp.focus()
        self._record_terminal_event("system", "Human takeover enabled.")
        self.query_one("#activity",RichLog).write("[b magenta]T → You now control the shared terminal.[/b magenta]")
        self._render_selected()

    def action_return_ai(self):
        sess=self.current_session()
        if not sess or not sess.running or not self.takeover: return
        self.takeover=False
        inp=self.query_one("#command-input",Input); inp.disabled=True
        set_status(self.selected.path,"AI Working")
        self._record_terminal_event("system", "Terminal returned to AI control.")
        self.query_one("#activity",RichLog).write("[b cyan]R → Terminal returned to AI.[/b cyan]")
        self._render_selected()

    def on_input_submitted(self,event):
        if event.input.id!="command-input": return
        value=event.value.strip()
        if event.input.has_class("lesson-mode"):
            event.input.remove_class("lesson-mode")
            event.input.disabled=True
            event.input.placeholder="Take over: command"
            if value and self.selected:
                path=save_lesson(self.ctf_root,self.selected.category,self.selected.name,value)
                self.query_one("#activity",RichLog).write(f"[green]Saved category lesson: {path}[/green]")
            event.input.value=""
            return
        sess=self.current_session()
        if self.takeover and sess and sess.running and value:
            self._send_human_line(value)
        event.input.value=""

    def action_interrupt_agent(self):
        sess=self.current_session()
        if sess and sess.running:
            sess.interrupt(); bump(self.selected.path,"interrupts")
            self.query_one("#activity",RichLog).write("[yellow]Ctrl-C sent.[/yellow]")

    async def action_handoff(self):
        if not self.selected: return
        target=self._selected_agent()
        if not target: return
        c=self.selected; key=self._key(c); current=self.sessions.get(key)
        source=self.last_agent_by_challenge.get(key,"unknown")
        if current and current.running:
            if current.started_at: add_seconds(c.path,"agent_runtime_seconds",float(getattr(current, "runtime_seconds", 0.0) or 0.0))
            current.terminate()
            self._finalize_main_session_if_needed(forced_status="handoff")
        handoff=build_handoff(c.path,source,target)
        self.query_one("#activity",RichLog).write(f"[b magenta]Handoff package: {handoff}[/b magenta]")
        try: self._start_session(target,True,purpose="handoff")
        except Exception as exc: self.query_one("#activity",RichLog).write(f"[red]{exc}[/red]")

    def action_recover(self):
        if not self.selected:
            return False
        settings=load_settings(self.ctf_root)
        if not settings.get("stuck_recovery"):
            self.query_one("#activity",RichLog).write(
                "[yellow]Stuck Recovery is optional/off. Enable with: ctf-power enable stuck_recovery[/yellow]"
            )
            return False

        try:
            path=write_recovery_prompt(self.selected.path)
            instruction=recovery_resume_instruction()
            sess=self.current_session()

            if sess and sess.running:
                # Recovery continues in the SAME shared PTY, preserving tool/shell context.
                try:
                    record_command(self.selected.path, instruction, "recovery")
                except Exception:
                    pass
                self.takeover=False
                try:
                    self.query_one("#command-input",Input).disabled=True
                except Exception:
                    pass
                self._record_terminal_event(
                    "system",
                    "Stuck Recovery context sent to the current AI; requested a genuinely different path.",
                )
                session_dir=self.session_dirs.get(self._key(self.selected))
                if session_dir:
                    try: append_transcript(session_dir, f"SYSTEM RECOVERY > {instruction}")
                    except Exception: pass
                sess.send_line(instruction)
                bump(self.selected.path,"recovery_runs")
                set_status(self.selected.path,"Recovery Working")
                self.query_one("#activity",RichLog).write(
                    f"[b magenta]Y → Recovery sent to the active AI in the same PTY.[/b magenta] "
                    f"[dim]{rich_escape(str(path))}[/dim]"
                )
                return True

            agent=self._selected_agent()
            if not agent:
                raise RuntimeError("No runnable AI agent is available for recovery.")
            startup=(
                "You are resuming an authorized CTF challenge specifically for Stuck Recovery. "
                "Read `.ctf/context.md`, `.ctf/hypothesis.md`, and `.ctf/recovery_prompt.md`. "
                "Do not repeat the failed path. Choose and execute a genuinely different approach. "
                "Keep visible progress concise and do not reveal private chain-of-thought."
            )
            self._start_session(
                agent,
                initial_prompt=startup,
                purpose="recovery",
            )
            bump(self.selected.path,"recovery_runs")
            set_status(self.selected.path,"Recovery Working")
            self.query_one("#activity",RichLog).write(
                f"[b magenta]Y → Started a new recovery session with {agent.title()}.[/b magenta]"
            )
            if not isinstance(self.screen, AgentSessionScreen):
                self.push_screen(AgentSessionScreen())
            return True
        except Exception as exc:
            self.query_one("#activity",RichLog).write(
                f"[red]Recovery failed: {rich_escape(str(exc))}[/red]"
            )
            return False


    def action_parallel(self):
        if not self.selected:
            return
        try:
            self._open_parallel_mode()
        except Exception as exc:
            self.query_one("#activity",RichLog).write(f"[red]Parallel Agents failed: {rich_escape(str(exc))}[/red]")

    def _parallel_key(self):
        return self._key(self.selected) if self.selected else None

    def _parallel_metadata_for_selected(self):
        key = self._parallel_key()
        return self.parallel_metadata.get(key) if key else None

    def _parallel_sessions_for_selected(self):
        key = self._parallel_key()
        return self.parallel_sessions.get(key, {}) if key else {}

    def _parallel_any_running(self):
        return any(sess.running for sess in self._parallel_sessions_for_selected().values())

    def _parallel_branch_result(self, branch: dict) -> dict:
        key = self._parallel_key()
        bid = branch["id"]
        sess = self.parallel_sessions.get(key, {}).get(bid) if key else None
        transcript = self.parallel_output.get(key, {}).get(bid, "") if key else ""
        screen = sess.screen_snapshot() if sess else ""
        combined = (transcript + "\n" + screen)[-30000:]
        flags = extract_candidate_flags(combined)
        candidate = choose_candidate_flag(combined)
        waiting = self._trust_prompt_visible(sess) if sess and sess.running else False
        if sess and sess.running:
            status = "RUNNING"
        elif sess:
            rc = sess.proc.poll() if sess.proc else None
            status = "FINISHED" if rc in (0, None) else f"EXIT {rc}"
        else:
            status = "NOT STARTED"
        return {
            "id": bid,
            "label": branch.get("label", bid),
            "agent": branch.get("agent", "AI"),
            "status": status,
            "waiting_for_trust": waiting,
            "runtime_seconds": float(getattr(sess, "runtime_seconds", 0.0) or 0.0) if sess else 0.0,
            "flags": flags,
            "candidate_flag": candidate,
            "screen": screen,
        }

    def _parallel_view_data(self):
        meta = self._parallel_metadata_for_selected()
        if not meta:
            return None
        branches = [self._parallel_branch_result(branch) for branch in meta.get("branches", [])[:2]]
        if len(branches) < 2:
            return None
        return meta, branches

    def _write_parallel_transcripts(self, meta: dict, branches: list[dict]):
        key = self._parallel_key()
        if not key:
            return
        run_dir = Path(meta["run_dir"])
        run_dir.mkdir(parents=True, exist_ok=True)
        for branch in branches:
            bid = branch["id"]
            transcript = self.parallel_output.get(key, {}).get(bid, "")
            (run_dir / f"{bid}-transcript.txt").write_text(transcript[-50000:] or branch.get("screen", ""), errors="replace")

    def _parallel_summary(self, save_if_complete: bool = True):
        data = self._parallel_view_data()
        if not data:
            return None
        meta, branches = data
        branch_results = {
            b["id"]: {
                "agent": b["agent"],
                "status": b["status"],
                "runtime_seconds": round(float(b["runtime_seconds"]), 3),
                "flags": b["flags"],
                "candidate_flag": b["candidate_flag"],
            }
            for b in branches
        }
        complete = all(b["status"] != "RUNNING" for b in branches)
        if complete or not save_if_complete:
            self._write_parallel_transcripts(meta, branches)
            return build_parallel_summary(meta, branch_results)
        # Still return a transient comparison for the live UI without writing it.
        nonempty = [b["candidate_flag"] for b in branches if b["candidate_flag"]]
        if len(nonempty) >= 2 and len(set(nonempty)) == 1:
            verdict, candidate = "agreement", nonempty[0]
        elif len(nonempty) >= 2:
            verdict, candidate = "disagreement", None
        elif len(nonempty) == 1:
            verdict, candidate = "single-branch-candidate", nonempty[0]
        else:
            verdict, candidate = "running", None
        return {"verdict": verdict, "candidate_flag": candidate, "branch_results": branch_results}

    def _finalize_parallel_if_complete(self):
        meta = self._parallel_metadata_for_selected()
        if not meta:
            return
        run_id = meta.get("run_id")
        if not run_id or run_id in self._parallel_finalized:
            return
        data = self._parallel_view_data()
        if not data:
            return
        _, branches = data
        if any(b["status"] == "RUNNING" for b in branches):
            return
        summary = self._parallel_summary(save_if_complete=True)
        if self.selected and summary:
            try:
                record_parallel_result(self.selected.path, summary)
            except Exception:
                pass
        total_runtime = sum(float(b["runtime_seconds"]) for b in branches)
        if self.selected:
            add_seconds(self.selected.path, "parallel_agent_runtime_seconds", total_runtime)
            set_status(self.selected.path, "Parallel Complete")
        self._parallel_finalized.add(run_id)
        try:
            verdict = summary.get("verdict", "complete") if summary else "complete"
            self.query_one("#activity", RichLog).write(
                f"[b magenta]Parallel Agents complete[/b magenta] • verdict: {rich_escape(str(verdict))} • summary: {rich_escape(str(meta['run_dir']))}/summary.md"
            )
        except Exception:
            pass

    def _confirm_parallel_trust(self) -> int:
        count = 0
        for sess in self._parallel_sessions_for_selected().values():
            if sess and sess.running and self._trust_prompt_visible(sess):
                sess.send("\r")
                count += 1
        return count

    def _interrupt_parallel_sessions(self) -> int:
        count = 0
        for sess in self._parallel_sessions_for_selected().values():
            if sess and sess.running:
                sess.interrupt()
                count += 1
        if count and self.selected:
            bump(self.selected.path, "parallel_interrupts", count)
        return count

    def _terminate_parallel_sessions(self):
        count = 0
        for sess in self._parallel_sessions_for_selected().values():
            if sess and sess.running:
                sess.terminate()
                count += 1
        return count

    def _clear_parallel_selected(self):
        key = self._parallel_key()
        if not key:
            return
        for sess in self.parallel_sessions.get(key, {}).values():
            if sess and sess.running:
                raise RuntimeError("Cannot clear a running parallel pair.")
        self.parallel_sessions.pop(key, None)
        self.parallel_metadata.pop(key, None)
        self.parallel_output.pop(key, None)

    def _parallel_agent_pair(self) -> list[str]:
        runnable = self._runnable_agents()
        if not runnable:
            raise RuntimeError("No runnable AI agents detected.")
        primary = self._selected_agent() or runnable[0]
        order = [primary]
        for candidate in ("claude", "gemini", "codex", "cai"):
            if candidate in runnable and candidate not in order:
                order.append(candidate)
        for candidate in runnable:
            if candidate not in order:
                order.append(candidate)
        return order[:2] if len(order) >= 2 else [order[0]]

    def _start_parallel_run(
        self,
        force_new: bool = False,
        agent_pair: list[str] | None = None,
        strategies: list[dict] | None = None,
    ):
        if not self.selected:
            raise RuntimeError("Select a challenge first.")
        c = self.selected
        if not (c.path / ".ctf" / "context.md").exists():
            raise RuntimeError("Run Smart Pre-Scan (S) first so both branches receive compact context.")
        settings = load_settings(self.ctf_root)
        if not settings.get("parallel_agents"):
            raise RuntimeError(
                "Parallel Agents are off because they can multiply AI usage. "
                "Enable with: ctf-power enable parallel_agents"
            )

        key = self._key(c)
        main_session = self.current_session()
        if main_session and main_session.running:
            # P means switch to exactly two parallel workers, not add two more
            # on top of the current single-agent session. Preserve its output,
            # account for runtime, then stop it before launching the pair.
            if main_session.started_at:
                add_seconds(c.path, "agent_runtime_seconds", float(getattr(main_session, "runtime_seconds", 0.0) or 0.0))
            main_session.terminate()
            self.takeover = False
            self._record_terminal_event("system", "Single-agent session stopped to launch exactly two parallel branches.")
            try:
                self.query_one("#activity", RichLog).write(
                    "[b magenta]P → Switching from single AI to exactly two parallel branches.[/b magenta]"
                )
            except Exception:
                pass

        existing = self.parallel_sessions.get(key, {})
        if any(sess.running for sess in existing.values()):
            if not force_new:
                return self.parallel_metadata.get(key)
            raise RuntimeError("A parallel pair is already running. Stop or finish it before starting another pair.")

        pair = list(agent_pair or self._parallel_agent_pair())
        if len(pair) != 2:
            if len(pair) == 1:
                pair = [pair[0], pair[0]]
            else:
                raise RuntimeError("Parallel Mode needs exactly two agent assignments.")

        runnable = set(self._runnable_agents())
        unavailable = [agent for agent in pair if agent not in runnable]
        if unavailable:
            raise RuntimeError(
                "Selected agent is not runnable: " + ", ".join(sorted(set(unavailable)))
            )

        meta = create_parallel_run(c.path, pair, strategies=strategies)
        sessions = {}
        outputs = {}
        started = []
        try:
            for branch in meta["branches"]:
                bid = branch["id"]
                workspace = Path(branch["workspace"])
                prompt = (
                    "You are one branch of CTF Control Room Parallel Mode on an authorized Capture The Flag challenge. "
                    "Work independently from the other branch and stay inside this branch workspace copy. "
                    "Read .ctf/context.md first. Do not modify the original challenge directory or sibling branch. "
                    f"Your assigned strategy is: {branch['instruction']} "
                    "Use local tools as needed. Give concise visible progress, verify any flag candidate, and do not reveal private chain-of-thought."
                )
                argv, env = build_agent_invocation(branch["agent"], workspace, initial_prompt=prompt)
                env["CTF_CONTROL_PARALLEL_RUN"] = str(meta["run_id"])
                env["CTF_CONTROL_PARALLEL_BRANCH"] = bid
                env["CTF_CONTROL_TOOL_REGISTRY"] = str(workspace / ".ctf" / "tool_registry.md")
                env["CTF_CONTROL_COMMAND_LOG"] = str(workspace / ".ctf" / "commands.jsonl")

                def make_output(branch_id, branch_workspace):
                    def on_output(clean, screen):
                        if clean:
                            outputs[branch_id] = (outputs.get(branch_id, "") + "\n" + clean)[-50000:]
                            try:
                                update_from_visible_output(branch_workspace, clean)
                            except Exception:
                                pass
                    return on_output

                sess = PTYSession(argv, workspace, env, make_output(bid, workspace), cols=86, rows=26)
                sess.start()
                sessions[bid] = sess
                started.append(sess)
        except Exception:
            for sess in started:
                try:
                    sess.close()
                except Exception:
                    pass
            raise

        self.parallel_sessions[key] = sessions
        self.parallel_output[key] = outputs
        self.parallel_metadata[key] = meta
        bump(c.path, "parallel_runs")
        bump(c.path, "agent_runs", len(sessions))
        set_status(c.path, "Parallel Working")
        try:
            branch_text = " + ".join(
                f"{b['agent'].title()} ({b['label']})" for b in meta["branches"]
            )
            self.query_one("#activity", RichLog).write(
                f"[b magenta]Parallel Agents started:[/b magenta] {rich_escape(branch_text)}"
            )
        except Exception:
            pass
        return meta

    def _open_parallel_mode(self):
        if not self.selected:
            return
        settings = load_settings(self.ctf_root)
        if not settings.get("parallel_agents"):
            self.notify(
                "Parallel Agents are off. Enable with: ctf-power enable parallel_agents",
                title="Parallel Agents",
                severity="warning",
                timeout=5,
            )
            return
        key = self._key(self.selected)
        if self.parallel_metadata.get(key) and not self._parallel_any_running():
            # Reopen a completed comparison. Press N there to choose another pair.
            self._parallel_summary(save_if_complete=True)
        # No AI usage begins merely by pressing P. The modal lets the user
        # explicitly choose Agent A, Agent B, and each branch method first.
        self.push_screen(ParallelAgentsScreen())

    def action_snapshot(self):
        if not self.selected: return
        out=create_snapshot(self.selected.path)
        self.query_one("#activity",RichLog).write(f"[green]Snapshot saved: {out}[/green]")

    def action_export(self):
        if not self.selected: return
        out=export_challenge(self.selected.path)
        self.query_one("#activity",RichLog).write(f"[green]Local no-AI write-up draft: {out}[/green]")

    def action_learn(self):
        if not self.selected: return
        inp=self.query_one("#command-input",Input)
        self.takeover=False; inp.disabled=False; inp.placeholder="Type a reusable lesson, then press Enter"
        inp.focus()
        # Use one-shot listener state.
        inp.add_class("lesson-mode")

    def on_input_changed(self,event):
        pass

    def on_unmount(self):
        for c in self.challenges:
            sess=self.sessions.get(self._key(c))
            if sess and sess.running and sess.started_at:
                add_seconds(c.path,"agent_runtime_seconds",float(getattr(sess, "runtime_seconds", 0.0) or 0.0))
            if sess:
                try:
                    # Persist final normal-session metadata before closing.
                    self.selected = c
                    self._finalize_main_session_if_needed(
                        forced_status="closed-by-control-room" if sess.running else None
                    )
                except Exception:
                    pass
                try: sess.close()
                except Exception: pass
            for psess in self.parallel_sessions.get(self._key(c), {}).values():
                if psess:
                    try: psess.close()
                    except Exception: pass
