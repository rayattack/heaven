# Going to Production 🚀

You've built your application. It runs locally. Now let's make it bulletproof for the real world.

## Security Headers 🛡️

By default, Heaven does not set opinionated security headers. In production, you absolutely should.

Copy this snippet into your application:

```python
async def security_headers(req, res, ctx):
    # Prevent MIME-Sniffing
    res.headers = 'X-Content-Type-Options', 'nosniff'
    
    # Clickjacking Protection (Same Origin Only)
    res.headers = 'X-Frame-Options', 'SAMEORIGIN'
    
    # Cross-Site Scripting Protection (Legacy Browsers)
    res.headers = 'X-XSS-Protection', '1; mode=block'
    
    # HTTP Strict Transport Security (HSTS) - Enforce HTTPS
    # Max-age: 1 year (31536000 seconds)
    # includeSubDomains: Apply to all subdomains
    # preload: Allow inclusion in browser HSTS preload list
    res.headers = 'Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload'
    
    # Referrer Policy - Don't leak paths to other sites
    res.headers = 'Referrer-Policy', 'strict-origin-when-cross-origin'

# Apply globally
app.AFTER('/*', security_headers)

# OR

app.AFTER('/*', 'path.to.security_headers')
```

## Content Security Policy (CSP) 👮

CSP is the heavy artillery of web security. It prevents script injection (XSS) by whitelisting exactly where content can come from.

> [!WARNING]
> A strict CSP can break your app if you use inline scripts or external CDNs not whitelisted. Test thoroughly!

### Strict Default Example
This policy allows scripts/styles only from your own domain (`'self'`).

```python
async def csp_header(req, res, ctx):
    policy = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; " # Allow images from self and base64 data URIs
        "font-src 'self'; "
        "object-src 'none'; "     # Block Flash/Plugins
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none';" # Prevent embedding (Clickjacking)
    )
    res.headers = 'Content-Security-Policy', policy

app.AFTER('/*', csp_header)
```

## Secrets & Sessions 🔑

Never hardcode secrets in your code. Use Environment Variables.

```python
import os
from heaven import Router

# Load from environment (or .env file using python-dotenv)
SECRET_KEY = os.getenv('SECRET_KEY')

if not SECRET_KEY:
    raise ValueError("No SECRET_KEY set for production application")

app = Router()

# Enable sessions with the secure key
app.sessions(secret_key=SECRET_KEY, max_age=86400, cookie_name='__Secure-Session')
```

## Deployment 🏭

### Running with Gunicorn (Process Manager)
While `python main.py` uses Uvicorn, in production you should use Gunicorn to manage multiple worker processes.

**Install Gunicorn:**
```bash
pip install gunicorn
```

**Run Command:**
```bash
# -w 4: Run 4 worker processes
# -k uvicorn.workers.UvicornWorker: Use Uvicorn for async
# main:app : The file `main.py` and the variable `app`
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Nginx Configuration (Reverse Proxy)
Put Nginx in front of Gunicorn to handle SSL termination and static files.

```nginx
server {
    listen 80;
    server_name example.com;

    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Serve Static Assets directly
    # This bypasses Heaven for maximum performance
    location /public {
        alias /var/www/my-app/public;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Websocket Support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
