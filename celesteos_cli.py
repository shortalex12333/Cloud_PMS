#!/usr/bin/env python3
"""
CelesteOS Local Agent CLI
Command-line interface for agent management and configuration.
"""

import sys
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from tabulate import tabulate

from celesteos_agent.config import ConfigManager, Config
from celesteos_agent.database import Database
from celesteos_agent.keychain import KeychainManager
from celesteos_agent.utils import format_bytes, format_duration, test_nas_connectivity

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """CelesteOS Local Agent - NAS Document Ingestion"""
    pass


@cli.command()
def setup():
    """Run interactive setup wizard."""
    console.print("\n[bold cyan]CelesteOS Local Agent Setup[/bold cyan]\n")

    config_manager = ConfigManager()

    # Yacht Information
    console.print("[bold]Yacht Information[/bold]")
    yacht_signature = click.prompt("Yacht Signature")
    yacht_name = click.prompt("Yacht Name (optional)", default="", show_default=False)

    # API Configuration
    console.print("\n[bold]Cloud API Configuration (Supabase)[/bold]")
    api_endpoint = click.prompt("Supabase URL", default="https://vzsohavtuotocgrfkfyd.supabase.co")

    console.print("\n[yellow]Note: Supabase service role key will be stored securely in macOS Keychain[/yellow]")
    supabase_service_key = click.prompt("Supabase Service Role Key", hide_input=True)

    # NAS Configuration
    console.print("\n[bold]NAS Configuration[/bold]")
    nas_path = click.prompt("NAS Mount Path", default="/Volumes/YachtNAS/Engineering")
    nas_type = click.prompt("NAS Type", type=click.Choice(['smb', 'nfs', 'local']), default='smb')

    nas_host = None
    nas_share = None
    nas_username = None
    nas_password = None

    if nas_type in ['smb', 'nfs']:
        nas_host = click.prompt("NAS Hostname/IP")
        nas_share = click.prompt("NAS Share Name")
        nas_username = click.prompt("NAS Username")
        nas_password = click.prompt("NAS Password", hide_input=True)

    # Test NAS connectivity
    console.print("\n[bold]Testing NAS connectivity...[/bold]")
    if not test_nas_connectivity(nas_path):
        console.print("[red]NAS connectivity test failed![/red]")
        if not click.confirm("Continue anyway?"):
            sys.exit(1)
    else:
        console.print("[green]✓ NAS connected[/green]")

    # Create configuration
    config = Config(
        yacht_signature=yacht_signature,
        yacht_name=yacht_name or None,
        api_endpoint=api_endpoint,
        nas_path=nas_path,
        nas_type=nas_type,
        nas_host=nas_host,
        nas_share=nas_share,
        nas_username=nas_username
    )

    # Save configuration
    config_manager.save(config)
    console.print(f"\n[green]✓ Configuration saved to {config_manager.config_path}[/green]")

    # Store credentials in keychain
    keychain = KeychainManager()

    if nas_password and nas_username:
        keychain.store_nas_password(nas_username, nas_password)
        console.print("[green]✓ NAS password stored in Keychain[/green]")

    if supabase_service_key:
        keychain.store_credential('supabase_service_role_key', supabase_service_key)
        console.print("[green]✓ Supabase service role key stored in Keychain[/green]")

    # Initialize database
    config_manager.ensure_directories()
    db = Database(config.db_path)
    db.init()
    console.print(f"[green]✓ Database initialized at {config.db_path}[/green]")

    # Save yacht identity
    db.set_yacht_identity(yacht_signature, yacht_name or None, api_endpoint)
    console.print("[green]✓ Yacht identity configured[/green]")

    # Save settings
    db.save_settings({
        'nas_path': nas_path,
        'nas_type': nas_type,
        'nas_username': nas_username,
        'nas_host': nas_host,
        'nas_share': nas_share
    })
    console.print("[green]✓ Agent settings saved[/green]")

    console.print("\n[bold green]✓ Setup complete![/bold green]")
    console.print("\nNext steps:")
    console.print("  1. Start the agent: [cyan]celesteos-agent start[/cyan]")
    console.print("  2. Check status: [cyan]celesteos-agent status[/cyan]")


@cli.command()
def status():
    """Show agent status."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load()
        db = Database(config.db_path)

        console.print("\n[bold cyan]CelesteOS Agent Status[/bold cyan]\n")

        # Yacht info
        yacht_identity = db.get_yacht_identity()
        if yacht_identity:
            console.print(f"[bold]Yacht:[/bold] {yacht_identity.get('yacht_name', 'Unknown')}")
            console.print(f"[bold]Signature:[/bold] {yacht_identity['yacht_signature']}")

        # Sync state
        sync_state = db.get_sync_state()
        console.print(f"\n[bold]Daemon Status:[/bold] {sync_state.get('daemon_status', 'unknown').upper()}")

        # Statistics
        stats = db.get_sync_stats()

        table = Table(title="File Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right", style="green")

        table.add_row("Files Uploaded", str(stats.get('files_uploaded', 0)))
        table.add_row("Files Pending", str(stats.get('files_pending', 0)))
        table.add_row("Files Uploading", str(stats.get('files_uploading', 0)))
        table.add_row("Files with Errors", str(stats.get('files_error', 0)))
        table.add_row("Active Uploads", str(stats.get('active_uploads', 0)))

        console.print(table)

        # Bytes
        console.print(f"\n[bold]Bytes Uploaded:[/bold] {format_bytes(stats.get('total_bytes_uploaded', 0))}")
        console.print(f"[bold]Bytes Pending:[/bold] {format_bytes(stats.get('total_bytes_pending', 0))}")

        # Recent errors
        errors = db.get_unresolved_errors(limit=5)
        if errors:
            console.print(f"\n[bold red]Recent Errors ({len(errors)}):[/bold red]")
            for error in errors[:5]:
                console.print(f"  • {error['error_type']}: {error['message']}")

    except FileNotFoundError:
        console.print("[red]Agent not configured. Run: celesteos-agent setup[/red]")
        sys.exit(1)


@cli.command()
def queue():
    """Show upload queue."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load()
        db = Database(config.db_path)

        console.print("\n[bold cyan]Upload Queue[/bold cyan]\n")

        pending = db.get_pending_uploads(limit=50)

        if not pending:
            console.print("[green]Queue is empty[/green]")
            return

        table_data = []
        for job in pending:
            progress = f"{job['uploaded_chunks']}/{job['total_chunks']}"
            status = job['status']
            table_data.append([
                job['filename'][:40],
                format_bytes(job['file_size']),
                progress,
                status,
                job['retry_count']
            ])

        headers = ["Filename", "Size", "Progress", "Status", "Retries"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    except FileNotFoundError:
        console.print("[red]Agent not configured. Run: celesteos-agent setup[/red]")
        sys.exit(1)


@cli.command()
def activity():
    """Show recent activity."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load()
        db = Database(config.db_path)

        console.print("\n[bold cyan]Recent Activity[/bold cyan]\n")

        activities = db.get_recent_activity(limit=20)

        for activity in activities:
            timestamp = activity['created_at']
            activity_type = activity['activity_type']
            message = activity['message']

            console.print(f"[dim]{timestamp}[/dim] [{activity_type}] {message}")

    except FileNotFoundError:
        console.print("[red]Agent not configured. Run: celesteos-agent setup[/red]")
        sys.exit(1)


@cli.command()
def errors():
    """Show recent errors."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load()
        db = Database(config.db_path)

        console.print("\n[bold red]Recent Errors[/bold red]\n")

        errors = db.get_unresolved_errors(limit=50)

        if not errors:
            console.print("[green]No errors[/green]")
            return

        for error in errors:
            console.print(f"\n[bold]{error['error_type']}[/bold] ([{error['severity']}])")
            console.print(f"  {error['message']}")
            if error.get('filename'):
                console.print(f"  File: {error['filename']}")

    except FileNotFoundError:
        console.print("[red]Agent not configured. Run: celesteos-agent setup[/red]")
        sys.exit(1)


@cli.command()
@click.option('--full', is_flag=True, help='Force full scan')
def scan(full):
    """Trigger manual scan."""
    console.print("\n[bold]Triggering scan...[/bold]")
    console.print("[yellow]Note: This requires the daemon to be running[/yellow]")
    console.print("Use the daemon's scheduler for automated scans\n")


@cli.command()
def retry():
    """Retry failed uploads."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load()
        db = Database(config.db_path)

        console.print("\n[bold]Resetting failed uploads...[/bold]")

        # Reset error uploads
        with db.get_connection() as conn:
            result = conn.execute("""
                UPDATE upload_queue
                SET status = 'pending',
                    retry_count = 0,
                    last_error = NULL,
                    next_retry_at = NULL
                WHERE status = 'error'
            """)

            count = result.rowcount

        console.print(f"[green]✓ Reset {count} failed uploads[/green]")
        console.print("They will be retried on next upload cycle\n")

    except FileNotFoundError:
        console.print("[red]Agent not configured. Run: celesteos-agent setup[/red]")
        sys.exit(1)


@cli.command()
def test_nas():
    """Test NAS connectivity."""
    try:
        config_manager = ConfigManager()
        config = config_manager.load()

        console.print(f"\n[bold]Testing NAS connectivity:[/bold] {config.nas_path}\n")

        if test_nas_connectivity(config.nas_path):
            console.print("[green]✓ NAS is accessible[/green]\n")
        else:
            console.print("[red]✗ NAS is not accessible[/red]\n")
            sys.exit(1)

    except FileNotFoundError:
        console.print("[red]Agent not configured. Run: celesteos-agent setup[/red]")
        sys.exit(1)


@cli.command()
@click.option('--confirm', is_flag=True, help='Confirm reset')
def reset(confirm):
    """Reset agent configuration and database."""
    if not confirm:
        console.print("[yellow]This will delete all configuration and database files[/yellow]")
        console.print("Run with --confirm to proceed")
        return

    config_manager = ConfigManager()

    console.print("\n[bold red]Resetting agent...[/bold red]")

    # Delete config
    config_manager.reset()
    console.print("✓ Configuration deleted")

    # Delete database
    db_path = Path("~/.celesteos/celesteos.db").expanduser()
    if db_path.exists():
        db_path.unlink()
        console.print("✓ Database deleted")

    console.print("\n[green]Agent reset complete[/green]")
    console.print("Run: celesteos-agent setup\n")


@cli.command()
def logs():
    """View agent logs."""
    log_path = Path("~/.celesteos/logs/celesteos-agent.log").expanduser()

    if not log_path.exists():
        console.print("[yellow]No log file found[/yellow]")
        return

    console.print(f"\n[bold]Showing last 50 lines of {log_path}[/bold]\n")

    with open(log_path, 'r') as f:
        lines = f.readlines()
        for line in lines[-50:]:
            print(line.rstrip())


def main():
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
