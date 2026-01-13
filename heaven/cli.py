import os
import sys
import importlib
import inspect
import argparse
from typing import Optional, Any
import uvicorn
import json
from functools import partial
from rich.syntax import Syntax
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from heaven import App, Router

console = Console()

def _deep_unwrap(func: Any) -> Any:
    """Recursively unwrap both @wraps decorators and functools.partial objects."""
    while True:
        if hasattr(func, "func") and isinstance(func, partial):
            func = func.func
        elif hasattr(func, "__wrapped__"):
            func = func.__wrapped__
        else:
            break
    return func

def find_app() -> Optional[Any]:
    """Search for an App or Router instance in common files."""
    files_to_check = ['app.py', 'main.py', 'application.py', 'index.py']
    
    # Also check all .py files in current directory if common ones not found
    all_py_files = [f for f in os.listdir('.') if f.endswith('.py') and f not in files_to_check]
    files_to_check.extend(all_py_files)

    for filename in files_to_check:
        if not os.path.exists(filename):
            continue
            
        module_name = filename[:-3]
        try:
            # Add current directory to path
            sys.path.insert(0, os.getcwd())
            module = importlib.import_module(module_name)
            
            # Look for App or Router instances
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, (App, Router)):
                    return f"{module_name}:{name}"
        except Exception:
            continue
            
    return None

def fly(port: int = 8000, host: str = "127.0.0.1", reload: bool = True):
    """The zero-config 'fly' command."""
    app_path = find_app()
    
    if not app_path:
        console.print("[bold red]Error:[/bold red] Could not find a Heaven App or Router instance in the current directory.")
        console.print("Try creating an [bold cyan]app.py[/bold cyan] with [bold green]app = App()[/bold green].")
        sys.exit(1)

    console.print(Panel(
        f"[bold yellow]Heaven is taking flight![/bold yellow]\n\n"
        f"🚀 [bold white]Source:[/bold white] {app_path}\n"
        f"📡 [bold white]Address:[/bold white] http://{host}:{port}\n"
        f"♻️ [bold white]Reload:[/bold white] {'Enabled' if reload else 'Disabled'}",
        title="[bold cyan]Heaven CLI[/bold cyan]",
        expand=False
    ))

    uvicorn.run(app_path, host=host, port=port, reload=reload, factory=False)

def routes(app_path: Optional[str] = None):
    """Visualize all registered routes."""
    if not app_path:
        app_path = find_app()
        
    if not app_path:
        console.print("[bold red]Error:[/bold red] Could not find an app to inspect.")
        sys.exit(1)

    try:
        module_name, obj_name = app_path.split(':')
        module = importlib.import_module(module_name)
        app = getattr(module, obj_name)
    except Exception as e:
        console.print(f"[bold red]Error loading app:[/bold red] {e}")
        sys.exit(1)

    table = Table(title="[bold cyan]Heaven API Routes[/bold cyan]")
    table.add_column("Method", style="bold magenta")
    table.add_column("Path", style="bold white")
    table.add_column("Subdomain", style="dim")
    table.add_column("Protection", style="green")

    # Access internal routes
    for subdomain, routes_obj in app.subdomains.items():
        # Iterate over all methods in cache
        for method, paths in routes_obj.cache.items():
            for path, handler in paths.items():
                original = _deep_unwrap(handler)
                handler_name = ""
                if hasattr(original, '__name__'):
                    handler_name = f" ({original.__name__})"
                elif isinstance(handler, str):
                    handler_name = f" ({handler})"
                
                table.add_row(
                    method, 
                    path + handler_name, 
                    subdomain, 
                    "Enabled" if app._protect_output else "Disabled"
                )
 
    with console.pager(styles=True):
        console.print(table)
 
def handlers(target_path: Optional[str] = None):
    """Deep inspection of handlers, showing source code if a path is provided."""
    app_path = find_app()
    if not app_path:
        console.print("[bold red]Error:[/bold red] Could not find an app.")
        sys.exit(1)

    try:
        module_name, obj_name = app_path.split(':')
        module = importlib.import_module(module_name)
        app = getattr(module, obj_name)
    except Exception as e:
        console.print(f"[bold red]Error loading app:[/bold red] {e}")
        sys.exit(1)

    if target_path:
        # Find specific handler
        found = False
        matches = []
        for subdomain, routes_obj in app.subdomains.items():
            for method, paths in routes_obj.cache.items():
                for path, handler in paths.items():
                    if path == target_path:
                        found = True
                        matches.append((method, path, handler))
        
        if found:
            with console.pager(styles=True):
                for method, path, handler in matches:
                    try:
                        # Deeply follow the breadcrumbs through decorators and partials
                        original_handler = _deep_unwrap(handler)
                        source = inspect.getsource(original_handler)
                        file = inspect.getsourcefile(original_handler)
                        line = inspect.getsourcelines(original_handler)[1]
                        
                        syntax = Syntax(
                            source, 
                            "python", 
                            theme="monokai", 
                            line_numbers=True, 
                            start_line=line,
                            word_wrap=True
                        )
                        console.print(Panel(
                            syntax,
                            title=f"[bold green]{method} {path}[/bold green]",
                            subtitle=f"[dim]{file}:{line}[/dim]",
                            expand=False
                        ))
                    except Exception as e:
                         console.print(f"[bold yellow]Handler found but source unavailable:[/bold yellow] {handler}")
                         console.print(f"[dim]Reason: {e}[/dim]")
        else:
            console.print(f"[bold red]Error:[/bold red] No handler found for path [bold cyan]{target_path}[/bold cyan]")
    else:
        # Show all handlers with locations
        table = Table(title="[bold cyan]Heaven Handler Map[/bold cyan]")
        table.add_column("Method", style="bold magenta")
        table.add_column("Path", style="bold white")
        table.add_column("Handler", style="green")
        table.add_column("Location", style="dim")

        for subdomain, routes_obj in app.subdomains.items():
            for method, paths in routes_obj.cache.items():
                for path, handler in paths.items():
                    try:
                        # Deeply follow breadcrumbs for accurate metadata
                        original = _deep_unwrap(handler)
                        file = os.path.relpath(inspect.getsourcefile(original))
                        line = inspect.getsourcelines(original)[1]
                        loc = f"{file}:{line}"
                        name = getattr(original, '__name__', str(original))
                    except:
                        loc = "unknown"
                        name = getattr(handler, '__name__', str(handler))
                    
                    table.add_row(method, path, name, loc)
        
        with console.pager(styles=True):
            console.print(table)

def schema(output: str = "swagger.json"):
    """Export OpenAPI specification to a JSON file."""
    app_path = find_app()
    if not app_path:
        console.print("[bold red]Error:[/bold red] Could not find an app.")
        sys.exit(1)
        
    try:
        module_name, obj_name = app_path.split(':')
        module = importlib.import_module(module_name)
        app = getattr(module, obj_name)
        
        spec = app.openapi()
        with open(output, 'w') as f:
            json.dump(spec, f, indent=2)
            
        console.print(f"[bold green]Success![/bold green] OpenAPI spec exported to [bold cyan]{output}[/bold cyan]")
    except Exception as e:
        console.print(f"[bold red]Error exporting schema:[/bold red] {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Heaven CLI - The divine interface for your web framework.",
        prog="heaven"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Fly Command
    fly_parser = subparsers.add_parser("fly", help="Zero-config auto-discovery run")
    fly_parser.add_argument("--host", default="127.0.0.1", help="Bind socket to this host.")
    fly_parser.add_argument("--port", type=int, default=8000, help="Bind socket to this port.")
    fly_parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload.")
    fly_parser.add_argument("--no-reload", action="store_false", dest="reload", help="Disable auto-reload.")

    # Run Command
    run_parser = subparsers.add_parser("run", help="Run a specific application")
    run_parser.add_argument("app", help="Application import path (e.g. main:app)")
    run_parser.add_argument("--host", default="127.0.0.1", help="Bind socket to this host.")
    run_parser.add_argument("--port", type=int, default=8000, help="Bind socket to this port.")
    run_parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload.")
    run_parser.add_argument("--no-reload", action="store_false", dest="reload", help="Disable auto-reload.")

    # Routes Command
    routes_parser = subparsers.add_parser("routes", help="Show all registered routes")
    routes_parser.add_argument("--app", help="Application import path (optional, auto-discovered otherwise)")

    # Handlers Command
    handlers_parser = subparsers.add_parser("handlers", help="Deep inspection of handlers")
    handlers_parser.add_argument("path", nargs="?", help="Specific route path to inspect")
    handlers_parser.add_argument("--app", help="Application import path (optional, auto-discovered otherwise)")

    # Schema Command
    schema_parser = subparsers.add_parser("schema", help="Export OpenAPI spec to JSON")
    schema_parser.add_argument("output", nargs="?", default="swagger.json", help="Output file path")
    schema_parser.add_argument("--app", help="Application import path (optional, auto-discovered otherwise)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "fly":
        fly(port=args.port, host=args.host, reload=args.reload)
    
    elif args.command == "run":
        # Check if the file/module exists first to give better error method
        if ":" not in args.app:
            console.print(f"[bold red]Error:[/bold red] Invalid app format '{args.app}'. Use 'module:attribute' (e.g. main:app)")
            sys.exit(1)
            
        # Ensure current directory is in python path
        sys.path.insert(0, os.getcwd())
        uvicorn.run(args.app, host=args.host, port=args.port, reload=args.reload)
    
    elif args.command == "routes":
        routes(app_path=args.app)

    elif args.command == "handlers":
        # We need to temporarily patch/adapt 'handlers' to accept app_path if we want to support it,
        # but the current implementation relies on generic find_app.
        # Ideally, we update find_app to accept an optional path or environment variable.
        # For now, we'll retain the existing behavior but allow the 'path' argument.
        handlers(target_path=args.path)
    
    elif args.command == "schema":
        schema(output=args.output)

if __name__ == "__main__":
    main()
