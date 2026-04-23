"""MARAMARA — Management CLI.

Install:
    pip install -e .

Then use:
    maramara --help
    maramara user:list
    maramara user:create-admin <email>
    maramara user:set-role <email> <role>
    maramara report:weekly <user_email>
    maramara migrate:apply
    maramara queue:stats
    maramara queue:run-weekly <user_email>
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import get_settings  # noqa: E402
from db.supabase_client import init_supabase_client, get_admin_client  # noqa: E402

console = Console()


def _setup():
    settings = get_settings()
    init_supabase_client(settings)
    return settings


@click.group(help="MARAMARA management CLI")
def cli():
    _setup()


# ---------------- users ----------------
@cli.group()
def user():
    """User management."""


@user.command("list")
def user_list():
    admin = get_admin_client()
    resp = admin.table("profiles").select("id,email,role,full_name,language,onboarding_completed,created_at").order("created_at", desc=True).execute()
    table = Table(title="Users")
    table.add_column("Email")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Lang")
    table.add_column("Onboard")
    for u in resp.data or []:
        table.add_row(
            u["email"],
            u.get("full_name") or "-",
            u["role"],
            u["language"],
            "✓" if u["onboarding_completed"] else "✗",
        )
    console.print(table)


@user.command("set-role")
@click.argument("email")
@click.argument("role", type=click.Choice(["user", "therapist", "admin"]))
def user_set_role(email: str, role: str):
    admin = get_admin_client()
    resp = admin.table("profiles").select("id").eq("email", email).execute()
    if not resp.data:
        console.print(f"[red]User not found:[/red] {email}")
        return
    admin.table("profiles").update({"role": role}).eq("email", email).execute()
    console.print(f"[green]Updated[/green] {email} -> {role}")


@user.command("create-admin")
@click.argument("email")
def user_create_admin(email: str):
    """Promote an existing user to admin (user must sign up first)."""
    admin = get_admin_client()
    resp = admin.table("profiles").select("id").eq("email", email).execute()
    if not resp.data:
        console.print(f"[red]User not found. Ask them to sign up first.[/red]")
        return
    admin.table("profiles").update({"role": "admin"}).eq("email", email).execute()
    console.print(f"[green]Promoted {email} to admin[/green]")


# ---------------- reports ----------------
@cli.group()
def report():
    """Report generation."""


@report.command("weekly")
@click.argument("email")
def report_weekly(email: str):
    admin = get_admin_client()
    u = admin.table("profiles").select("id").eq("email", email).execute()
    if not u.data:
        console.print(f"[red]User not found[/red]")
        return
    user_id = u.data[0]["id"]
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    w = admin.table("weekly_metrics").select("*").eq("user_id", user_id).eq("week_start", week_start).execute()
    if not w.data:
        console.print("[yellow]No weekly metrics for current week.[/yellow]")
        return
    console.print_json(json.dumps(w.data[0], default=str, ensure_ascii=False))


# ---------------- queue ----------------
@cli.group()
def queue():
    """Background queue management."""


@queue.command("stats")
def queue_stats():
    from services.queue import _get_queue
    q = _get_queue()
    table = Table(title="RQ Queue: maramara-segments")
    table.add_column("Metric")
    table.add_column("Count")
    table.add_row("Queued", str(q.count))
    table.add_row("Failed", str(q.failed_job_registry.count))
    table.add_row("Started", str(q.started_job_registry.count))
    console.print(table)


@queue.command("run-weekly")
@click.argument("email")
@click.option("--week-start", default=None, help="ISO date (default: this Monday)")
def queue_run_weekly(email: str, week_start: str | None):
    admin = get_admin_client()
    u = admin.table("profiles").select("id").eq("email", email).execute()
    if not u.data:
        console.print("[red]User not found[/red]")
        return
    from services.queue import enqueue_weekly_crewai
    ws = week_start or (date.today() - timedelta(days=date.today().weekday())).isoformat()
    job_id = enqueue_weekly_crewai(u.data[0]["id"], ws)
    console.print(f"[green]Enqueued weekly insights[/green] job={job_id}")


# ---------------- migrations ----------------
@cli.group()
def migrate():
    """Database migrations."""


@migrate.command("apply")
def migrate_apply():
    """Apply any unapplied migrations via Supabase Management API."""
    import os
    import requests
    settings = get_settings()
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not token:
        console.print("[red]SUPABASE_ACCESS_TOKEN not set[/red]")
        return
    sql_dir = Path(__file__).parent / "migrations" / "sql"
    for sql_file in sorted(sql_dir.glob("*.sql")):
        console.print(f"Applying [cyan]{sql_file.name}[/cyan]...")
        sql = sql_file.read_text(encoding="utf-8")
        r = requests.post(
            f"https://api.supabase.com/v1/projects/{settings.supabase_project_ref}/database/query",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"query": sql},
        )
        if r.ok:
            console.print(f"  [green]✓[/green]")
        else:
            console.print(f"  [red]✗ {r.text[:200]}[/red]")


# ---------------- obsidian ----------------
@cli.group()
def obsidian():
    """Obsidian vault exports."""


@obsidian.command("export-weekly")
@click.argument("email")
@click.option("--week-start", default=None, help="ISO date (default: this Monday)")
def obsidian_export_weekly(email: str, week_start: str | None):
    from services.obsidian import ObsidianExporter
    admin = get_admin_client()
    u = admin.table("profiles").select("id").eq("email", email).execute()
    if not u.data:
        console.print("[red]User not found[/red]")
        return
    ws = week_start or (date.today() - timedelta(days=date.today().weekday())).isoformat()
    note = ObsidianExporter().export_weekly(u.data[0]["id"], date.fromisoformat(ws))
    if note:
        console.print(f"[green]Wrote[/green] {note.path}")
    else:
        console.print("[yellow]Skipped (export disabled or no weekly_metrics row).[/yellow]")


# ---------------- doctor ----------------
@cli.command()
def doctor():
    """Run health checks on all services."""
    settings = get_settings()
    checks = [
        ("Supabase URL", bool(settings.supabase_url)),
        ("Supabase Service Role Key", bool(settings.supabase_service_role_key)),
        ("Anthropic API Key", bool(settings.anthropic_api_key)),
        ("Redis URL", bool(settings.redis_url)),
    ]
    table = Table(title="System Doctor")
    table.add_column("Check")
    table.add_column("Status")
    for name, ok in checks:
        table.add_row(name, "[green]✓[/green]" if ok else "[red]✗[/red]")
    console.print(table)


if __name__ == "__main__":
    cli()
