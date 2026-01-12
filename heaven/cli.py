import os
import sys
import importlib
import inspect
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
        for subdomain, routes_obj in app.subdomains.items():
            for method, paths in routes_obj.cache.items():
                for path, handler in paths.items():
                    if path == target_path:
                        found = True
                        try:
                            # Deeply follow the breadcrumbs through decorators and partials
                            original_handler = _deep_unwrap(handler)
                            source = inspect.getsource(original_handler)
                            file = inspect.getsourcefile(original_handler)
                            line = inspect.getsourcelines(original_handler)[1]
                            
                            syntax = Syntax(source, "python", theme="monokai", line_numbers=True, start_line=line)
                            with console.pager(styles=True):
                                console.print(Panel(
                                    syntax,
                                    title=f"[bold green]{method} {path}[/bold green]",
                                    subtitle=f"[dim]{file}:{line}[/dim]",
                                    expand=False
                                ))
                        except Exception as e:
                             console.print(f"[bold yellow]Handler found but source unavailable:[/bold yellow] {handler}")
                             console.print(f"[dim]Reason: {e}[/dim]")
        if not found:
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
    args = sys.argv[1:]
    
    if not args or args[0] == "fly":
        fly()
    elif args[0] == "run":
        if len(args) < 2:
            console.print("[bold red]Error:[/bold red] Please specify an app path (e.g., [bold cyan]heaven run app:router[/bold cyan])")
            sys.exit(1)
        # Simple run wrapper
        app_path = args[1]
        uvicorn.run(app_path, host="127.0.0.1", port=8000, reload=True)
    elif args[0] == "routes":
        routes()
    elif args[0] == "handlers":
        path = args[1] if len(args) > 1 else None
        handlers(path)
    elif args[0] == "schema":
        output = args[1] if len(args) > 1 else "swagger.json"
        schema(output)
    else:
        console.print(f"[bold yellow]Usage:[/bold yellow]")
        console.print("  [bold cyan]heaven fly[/bold cyan]              - Zero-config auto-discovery run")
        console.print("  [bold cyan]heaven run <app>[/bold cyan]        - Run a specific app")
        console.print("  [bold cyan]heaven routes[/bold cyan]           - Show all registered routes")
        console.print("  [bold cyan]heaven handlers [path][/bold cyan]   - Deep inspection of handlers")
        console.print("  [bold cyan]heaven schema [file][/bold cyan]     - Export OpenAPI spec to JSON")

if __name__ == "__main__":
    main()
