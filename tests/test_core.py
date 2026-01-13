
from heaven import Router
import asyncio
from heaven.request import Request
from heaven.response import Response
from heaven.context import Context

# Mock Request Context for testing
# We need to spin up the app or mock enough of it to run hooks

async def run_middleware(app, scope, receive, send):
    # This simulates app.__call__ roughly just to traverse hooks
    # But since hooks are inside Router logic, we might need a real request flow
    # or just inspect the app state.
    pass

async def test_features():
    print("Testing Core Features Integration...")
    app = Router()
    
    # 1. SETUP
    app.cors(origins="example.com", methods=["GET", "POST"])
    app.sessions(secret_key="secret", cookie_name="mysession")
    
    # Check Hooks Registration
    # We inspect private members just for verification
    # _subdomains['/'].befores should have hooks
    
    engine = app.subdomains['www']
    befores = engine.befores
    afters = engine.afters
    
    print(f"Hooks registered: Before={len(befores)} After={len(afters)}")
    
    # With CORS and Session:
    # CORS registers 1 BEFORE hook
    # Sessions registers 1 BEFORE and 1 AFTER hook
    # Total: Before=2 (wildcard), After=1 (wildcard)
    
    wildcard_befores = befores.get('/*', [])
    wildcard_afters = afters.get('/*', [])
    
    if len(wildcard_befores) >= 2:
        print("CORS and Session BEFORE hooks registered")
    else:
        print(f"Missing BEFORE hooks. Found: {len(wildcard_befores)}")
        
    if len(wildcard_afters) >= 1:
        print("Session AFTER hook registered")
    else:
        print(f"Missing AFTER hooks. Found: {len(wildcard_afters)}")

    # 2. RUNTIME SIMULATION (Unit Test-ish)
    # We will manually invoke the hooks to verify logic
    
    # --- CORS TEST ---
    req = Request({'type': 'http', 'method': 'OPTIONS', 'path': '/', 'headers': [], 'query_string': b''}, b'', None, (None, {}), app)
    res = Response(app, Context(app), req)
    
    # Find the cors hook
    cors_hook = wildcard_befores[0] # Implementation order matters! cors called first?
    # Actually order depends on registration. session before cors?
    # We registered cors first.
    
    # Executing attributes of functions to identify them?
    # They are closures, so hard to id by name 'handle_cors' vs 'load_session'
    # app.cors() registered 'handle_cors'
    # app.sessions() registered 'load_session'
    
    # We need to capture the context used in hooks
    test_ctx = Context(app)

    # Let's just run all BEFORE hooks
    try:
        for hook in wildcard_befores:
            await hook(req, res, test_ctx)
    except Exception as e:
        # AbortException is expected from CORS OPTIONS
        pass
        
    if res._abort and res.headers[0] == (b'Access-Control-Allow-Origin', b'example.com'):
        print("CORS OPTIONS handled correctly")
    else:
        print(f"CORS failed check. Abort={res._abort}, Headers={res.headers}")

    # --- SESSION TEST ---
    # Prepare a signed cookie
    from heaven.security import SecureSerializer
    s = SecureSerializer("secret")
    token = s.dumps({"user": "tersoo"})
    
    req = Request({'type': 'http', 'method': 'GET', 'path': '/', 'headers': [(b'cookie', f'mysession={token}'.encode())], 'query_string': b''}, b'', None, (None, {}), app)
    res = Response(app, Context(app), req)
    
    # Run BEFORE hooks (load session)
    test_ctx = Context(app)
    for hook in wildcard_befores:
        await hook(req, res, test_ctx)
        
    if getattr(test_ctx.session, 'user') == 'tersoo':
        print("Session loaded correctly")
    else:
        print(f"Session load failed. Session={getattr(test_ctx, 'session', None)}")
        if hasattr(test_ctx, 'session') and hasattr(test_ctx.session, '_data'):
            print(f"DEBUG: Session Data: {test_ctx.session._data}")

    # Modify session
    test_ctx.session.visited = True
    
    # Run AFTER hooks (save session)
    for hook in wildcard_afters:
        await hook(req, res, test_ctx)
        
    # Check Set-Cookie
    cookies = [h for h in res.headers if h[0] == b'Set-Cookie']
    if cookies and b'mysession=' in cookies[0][1]:
        print("Session saved correctly (Set-Cookie present)")
    else:
        print("Session save failed (No Set-Cookie)")

    # --- CONTEXT SETATTR TEST ---
    print("Testing Context Setattr...")
    test_ctx.some_data = "hello"
    if test_ctx.some_data == "hello":
        print("Context setattr working (ctx.key = val)")
    else:
        print(f"Context setattr failed. got {test_ctx.some_data}")

    # Test Protection
    try:
        test_ctx.session = "malicious"
        print("Context protection FAILED (Overwrote session)")
    except AttributeError:
        print("Context protection working (AttributeError raised)")

if __name__ == "__main__":
    asyncio.run(test_features())

