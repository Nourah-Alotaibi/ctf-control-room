
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
from .core.parallel import create_parallel_plan
from .core.recovery import build_recovery_prompt
from .core.power import load_settings




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
                "5. Watch the shared terminal and results live.\n"
                "6. [b]T[/b] → Take Over: you control the SAME terminal manually.\n"
                "7. [b]R[/b] → Return to AI: give the same terminal back so the AI can continue.\n\n"

                "[b cyan]CONTROL[/b cyan]\n"
                "T  Take Over      → Human controls the shared terminal.\n"
                "R  Return to AI   → Give terminal control back to the AI.\n"
                "I  Interrupt      → Send Ctrl-C to stop the current running command.\n\n"

                "[b yellow]TOOLS & FEATURES[/b yellow]\n"
                "H  Handoff        → Package progress, scripts, context, and tried commands for another agent.\n"
                "X  Snapshot       → Save context, scripts, metrics, commands, notes, and findings.\n"
                "Y  Stuck Recovery → Optional fresh reasoning when an approach loops; may use extra tokens.\n"
                "P  Parallel Plan  → Optional multi-agent investigation; can use more tokens.\n"
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
                "AI is optional. Control Room never installs Claude, Codex, Gemini, Ollama, CAI, or another AI automatically.\n"
                "Standard profile → Router + Tool Planner + Hypothesis Board.\n"
                "Advanced profile → Standard + optional Stuck Recovery.\n"
                "Max profile      → enables all advanced switches; Parallel/CAI can cost more tokens.\n\n"

                "[b]SYSTEM[/b]\n"
                "W  Welcome  → Return to the Welcome page anytime.\n"
                "F  Refresh  → Refresh challenge list/status.\n"
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
        width: 31%;
        min-width: 42;
        border: round #8f5cff;
        background: #0d1016;
    }
    #right {
        width: 69%;
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
        height: 8;
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
    #agent-select {
        width: 36;
        height: 3;
        background: #12151d;
        color: #f1ecfa;
        border: round #8f5cff;
    }
    #agent-detected {
        height: 2;
        content-align: left middle;
        color: #75d7ff;
    }
    #scan-status {
        height: 5;
        padding: 0 2;
        border-bottom: solid #3b2b50;
        background: #0e1118;
    }
    #ai-status {
        height: 5;
        padding: 0 2;
        content-align: left middle;
        border-bottom: solid #3b2b50;
        background: #0d1016;
        color: #e8e8ee;
    }
    #terminal-label {
        height: 2;
        padding-left: 1;
        color: #c99cff;
        text-style: bold;
    }
    #terminal {
        height: 1fr;
        padding: 1;
        border-bottom: solid #3b2b50;
        background: #07090d;
        color: #e9e9ee;
    }
    #command-input {
        height: 3;
        margin: 0 1 1 1;
        border: round #8f5cff;
        background: #0d1016;
        color: #f2eff8;
    }
    #activity {
        height: 6;
        padding: 1;
        background: #10131a;
        border-top: solid #2c2238;
    }
    DataTable {
        height: 1fr;
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
        Binding("p","parallel","Parallel Plan"),
        Binding("f","refresh","Refresh"),
        Binding("w","welcome","Welcome"),
        Binding("question_mark","help","Help"),
        Binding("q","quit","Quit"),
    ]

    def __init__(self, ctf_root: Path, default_agent="codex"):
        super().__init__()
        self.ctf_root=Path(ctf_root); self.default_agent=default_agent
        self.challenges=[]; self.selected=None; self.last_agent_by_challenge={}
        self.sessions={}; self.takeover=False; self._last_stuck_warn={}
        self._latest_terminal_text={}

    def compose(self)->ComposeResult:
        yield Header(show_clock=True)
        yield Static("CTF CONTROL ROOM", id="title")
        with Horizontal(id="body"):
            with Vertical(id="left"):
                yield Label(" COMPETITION DASHBOARD ", classes="muted")
                yield DataTable(id="challenge-table")
            with Vertical(id="right"):
                yield Static("Select a challenge.", id="challenge-info")
                with Vertical(id="agent-panel"):
                    yield Static("AI AGENT", id="agent-label")
                    detected_agents = available_agents()
                    detected_options = (
                        [(agent.title(), agent) for agent in detected_agents]
                        if detected_agents
                        else [("No runnable AI agent detected", "")]
                    )
                    initial_agent = (
                        self.default_agent
                        if self.default_agent in detected_agents
                        else (detected_agents[0] if detected_agents else Select.NULL)
                    )
                    yield Select(
                        detected_options,
                        value=initial_agent,
                        id="agent-select",
                        allow_blank=True,
                        prompt="Select AI agent",
                    )
                    yield Static(
                        "Detected: " + (", ".join(a.title() for a in detected_agents) if detected_agents else "None"),
                        id="agent-detected",
                    )
                yield Static("Automatic Smart Pre-Scan (No AI) has not run.", id="scan-status")
                yield Static("AI status: idle", id="ai-status")
                yield Static(" SHARED TERMINAL ", id="terminal-label")
                yield RichLog(id="terminal", wrap=True, highlight=False, markup=False)
                yield Input(placeholder="Take over: command, or L: lesson text", id="command-input", disabled=True)
                yield RichLog(id="activity", wrap=True, highlight=True, markup=True)
        yield Footer()

    def on_mount(self):
        table=self.query_one("#challenge-table",DataTable); table.cursor_type="row"
        table.add_columns("Challenge","Category","Status","Agent","Cmds","Dup","Time")
        self.refresh_agent_select(); self.refresh_challenges()
        self.set_interval(2.0,self._tick)
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
        agents = available_agents()
        select = self.query_one("#agent-select", Select)
        detected = self.query_one("#agent-detected", Static)

        select.set_options(
            [(a.title(), a) for a in agents]
            if agents
            else [("No runnable AI agent detected", "")]
        )

        if self.default_agent in agents:
            select.value = self.default_agent
        elif agents:
            select.value = agents[0]
        else:
            select.value = Select.NULL

        detected.update(
            "Detected: " + (", ".join(a.title() for a in agents) if agents else "None")
        )

    def _selected_agent(self):
        v=self.query_one("#agent-select",Select).value
        return str(v) if v else None

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

    def _render_selected(self):
        c=self.selected
        if not c: return
        m=load_metrics(c.path); sess=self.current_session()
        status=m.get("status","Ready"); agent=self.last_agent_by_challenge.get(self._key(c),"none")
        runtime=float(m.get("agent_runtime_seconds",0))
        if sess and sess.running and sess.started_at: runtime += time.time()-sess.started_at
        lessons=related_lessons(self.ctf_root,c.category,3)
        self.query_one("#challenge-info",Static).update(
            f"[b]{c.name}[/b] • {c.category.upper()}\n"
            f"Status: {status} • Agent: {agent}\n"
            f"Scan: {m.get('scan_seconds',0):.1f}s • AI runtime: {runtime:.0f}s • Commands: {m.get('commands',0)}\n"
            f"Duplicates blocked: {m.get('duplicates_blocked',0)} • Handoffs: {m.get('handoffs',0)} • Takeovers: {m.get('takeovers',0)}\n"
            + (f"Memory: {lessons[0][:90]}" if lessons else "Memory: no saved category lessons yet")
        )
        mode="[b green]HUMAN TAKEOVER[/b green]" if self.takeover else "[dim]AI CONTROL[/dim]"
        self.query_one("#terminal-label",Static).update(f" SHARED TERMINAL • {mode} ")
        current=self._infer_activity()
        self.query_one("#ai-status",Static).update(
            f"[b]WHAT AI IS DOING[/b]\n{current}\n"
            f"Tool levels: FAST → DEEP → EXPENSIVE"
        )

    def _infer_activity(self):
        sess=self.current_session()
        if not sess or not sess.running: return "Idle."
        text=" ".join(sess.output_history[-12:]).replace("\r"," ").replace("\n"," ")
        # Lightweight, non-AI status inference only.
        commands=re.findall(r"(?:^|\\s)([\\w./-]+(?:\\s+[-\\w./=:'\"]+){0,5})", text)
        last=commands[-1][:120] if commands else "Agent is active in the terminal."
        return f"Active. Recent terminal activity: {last}"

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
        term.write("Connected to active PTY." if sess and sess.running else "No active agent. Press A to start one.")

    def action_welcome(self):
        self.push_screen(WelcomeScreen(), self._welcome_done)

    def action_help(self):
        self.push_screen(HelpScreen(), self._help_done)

    def action_refresh(self):
        self.refresh_agent_select(); self.refresh_challenges()

    async def action_scan(self):
        if not self.selected: return
        c=self.selected; log=self.query_one("#activity",RichLog); status=self.query_one("#scan-status",Static)
        log.write(f"[b magenta]Automatic Smart Pre-Scan: {c.name}[/b magenta]")
        status.update("[b]AUTOMATIC SMART PRE-SCAN — NO AI[/b]\nRunning adaptive FAST tools • hard limit 60s")
        def cb(ev: ScanEvent):
            sym="✓" if ev.ok else "!"
            self.call_from_thread(log.write,f"[{'green' if ev.ok else 'yellow'}]{sym} {ev.tool}[/] → {ev.target}")
        try:
            events=await asyncio.to_thread(scan_challenge,c,cb)
            m=load_metrics(c.path)
            status.update(
                f"[b]AUTOMATIC SMART PRE-SCAN — NO AI[/b]\n✓ complete in {m.get('scan_seconds',0):.1f}s • "
                f"{len(events)} events\nRaw: .ctf/raw/ • Context: .ctf/context.md"
            )
        except Exception as exc:
            set_status(c.path,"Scan Error"); log.write(f"[red]Scan error: {exc}[/red]")

    def _start_session(self,agent,handoff=False):
        c=self.selected; key=self._key(c)
        old=self.sessions.get(key)
        if old and old.running: raise RuntimeError("An agent is already running for this challenge.")
        argv,env=build_agent_invocation(agent,c.path,handoff=handoff)
        env["CTF_CONTROL_TOOL_REGISTRY"]=str(c.path/".ctf"/"tool_registry.md")
        env["CTF_CONTROL_COMMAND_LOG"]=str(c.path/".ctf"/"commands.jsonl")
        term=self.query_one("#terminal",RichLog); term.clear()

        def on_output(text):
            clean=text.replace("\r","")
            self._latest_terminal_text[key]=clean[-4000:]
            self.call_from_thread(term.write,clean.rstrip("\n"))

        sess=PTYSession(argv,c.path,env,on_output); sess.start()
        self.sessions[key]=sess; self.last_agent_by_challenge[key]=agent
        bump(c.path,"agent_runs"); set_status(c.path,"AI Working")
        self.query_one("#activity",RichLog).write(f"[b cyan]Started {agent} in shared PTY.[/b cyan]")

    async def action_agent(self):
        if not self.selected: return
        if not (self.selected.path/".ctf"/"context.md").exists():
            self.query_one("#activity",RichLog).write("[yellow]Run S first. It uses no AI.[/yellow]"); return
        agent=self._selected_agent()
        if not agent: return
        try: self._start_session(agent)
        except Exception as exc: self.query_one("#activity",RichLog).write(f"[red]{exc}[/red]")

    def action_takeover(self):
        sess=self.current_session()
        if not sess or not sess.running or self.takeover: return
        self.takeover=True
        inp=self.query_one("#command-input",Input); inp.disabled=False
        bump(self.selected.path,"takeovers"); set_status(self.selected.path,"Human Working")
        inp.focus()
        self.query_one("#activity",RichLog).write("[b magenta]T → You now control the shared terminal.[/b magenta]")
        self._render_selected()

    def action_return_ai(self):
        sess=self.current_session()
        if not sess or not sess.running or not self.takeover: return
        self.takeover=False
        inp=self.query_one("#command-input",Input); inp.disabled=True
        set_status(self.selected.path,"AI Working")
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
            log_command(self.selected.path,value,"human")
            sess.send_line(value)
            self.query_one("#activity",RichLog).write(f"[dim]YOU › {value}[/dim]")
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
            if current.started_at: add_seconds(c.path,"agent_runtime_seconds",time.time()-current.started_at)
            current.terminate()
        handoff=build_handoff(c.path,source,target)
        self.query_one("#activity",RichLog).write(f"[b magenta]Handoff package: {handoff}[/b magenta]")
        try: self._start_session(target,True)
        except Exception as exc: self.query_one("#activity",RichLog).write(f"[red]{exc}[/red]")

    def action_recover(self):
        if not self.selected: return
        settings=load_settings(self.ctf_root)
        if not settings.get("stuck_recovery"):
            self.query_one("#activity",RichLog).write(
                "[yellow]Stuck Recovery is optional/off. Enable with: ctf-power enable stuck_recovery[/yellow]"
            )
            return
        prompt=build_recovery_prompt(self.selected.path)
        path=self.selected.path/".ctf"/"recovery_prompt.md"
        path.write_text(prompt)
        self.query_one("#activity",RichLog).write(
            f"[magenta]Recovery prompt prepared: {path}. "
            "Use it with your current AI agent when you want a fresh reasoning pass.[/magenta]"
        )

    def action_parallel(self):
        if not self.selected: return
        settings=load_settings(self.ctf_root)
        if not settings.get("parallel_agents"):
            self.query_one("#activity",RichLog).write(
                "[yellow]Parallel Agents are optional/off because they can multiply token use. "
                "Enable with: ctf-power enable parallel_agents[/yellow]"
            )
            return
        path=create_parallel_plan(self.selected.path)
        self.query_one("#activity",RichLog).write(
            f"[magenta]Parallel investigation plan prepared: {path}[/magenta]"
        )

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
                add_seconds(c.path,"agent_runtime_seconds",time.time()-sess.started_at)
            if sess:
                try: sess.close()
                except Exception: pass
