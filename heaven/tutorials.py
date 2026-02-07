NO_TEMPLATING = '''
    from heaven import Application

    application = Application({'optional_config': 'if you want'})
    application.TEMPLATES('templates')
'''


ASYNC_RENDER = '''
    # html template rendering is async by default, don't disable it to use async rendering
    # i.e. don't do this ↓↓↓↓↓
    
    application.TEMPLATES('templates', asynchronous=False)
'''


SYNC_RENDER = '''
    # to render files synchronously disable async renderer
    
    application.TEMPLATES('templates', asynchronous=False)
'''




import sys

def get_guardian_angel_html(req, exc: Exception, tb: str):  # pragma: no cover
    error_type = type(exc).__name__
    error_msg = str(exc)
    
    return f'''
    <!DOCTYPE html>
    <html>
        <head>
            <title>Guardian Angel - {error_type}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                    background-color: #0f172a;
                    color: #e2e8f0;
                    margin: 0;
                    padding: 40px;
                    line-height: 1.5;
                }}
                .container {{
                    max_width: 1000px;
                    margin: 0 auto;
                }}
                .header {{
                    border-bottom: 1px solid #334155;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                h1 {{
                    font-size: 2.5rem;
                    color: #f87171;
                    margin: 0 0 10px 0;
                    font-weight: 700;
                }}
                .subtitle {{
                    font-size: 1.25rem;
                    color: #94a3b8;
                }}
                .card {{
                    background-color: #1e293b;
                    border-radius: 8px;
                    padding: 24px;
                    margin-bottom: 24px;
                    border: 1px solid #334155;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                }}
                .card-title {{
                    font-size: 0.875rem;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                    color: #64748b;
                    margin-bottom: 12px;
                    font-weight: 600;
                }}
                pre {{
                    background-color: #0f172a;
                    padding: 16px;
                    border-radius: 6px;
                    overflow-x: auto;
                    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
                    font-size: 0.9rem;
                    border: 1px solid #334155;
                    color: #e2e8f0;
                }}
                .traceback {{
                    color: #ef4444;
                    white-space: pre-wrap;
                }}
                .info-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                }}
                .info-item {{
                    background: #28374e; 
                    padding: 12px;
                    border-radius: 4px;
                }}
                .badge {{
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.75rem;
                    font-weight: 600;
                }}
                .badge-method {{ background: #3b82f6; color: white; }}
                .badge-url {{ background: #22d3ee; color: #0f172a; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{error_type}</h1>
                    <div class="subtitle">{error_msg}</div>
                </div>

                <div class="card">
                    <div class="card-title">Request Context</div>
                    <div class="info-grid">
                        <div class="info-item">
                            <span class="badge badge-method">{req.method}</span>
                            <code style="margin-left: 10px; color: #38bdf8;">{req.url}</code>
                        </div>
                        <div class="info-item">
                            <strong>Client:</strong> {getattr(req, 'ip', 'Unknown')}
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-title">Traceback</div>
                    <pre class="traceback">{tb}</pre>
                </div>

                <div class="card">
                    <div class="card-title">Environment</div>
                    <pre>Python: {sys.version.split()[0]}
Platform: {sys.platform}</pre>
                </div>
            </div>
        </body>
    </html>
    '''

