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


def get_guardian_angel_html(error: str, snippet: str):  # pragma: no cover
    return f'''
    <html>
        <head>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css">
        </head>
        <body class="container">
            <div class="content pt-3">
                <h3 class="mb-0">Guardian Angel</h3>
                <hr class="m-0 my-1"/>
                <p>
                    Heaven provides helpful tips when an error is encountered via this useful util called <b>Guardian Angel</b>. You will see
                    some error information below in Jesus (red) text
                </p>
            </div>
            
            <ol class="px-5">
                <li class="has-text-danger has-text-weight-bold">{error}</li>
            </ol>
            <pre style="background-color: black"><code style="font-family: verdana; color: #EF8B26;">{snippet}</code></pre>
        </body>
    </html>
    '''
