# Welcome To Heaven
You are probably here because you want to build a web application using Python. Well, Welcome to heaven - the super
simple, extremely fast, web framework for purists.

Building a web application with heaven is stupid simple as the code snippet below


```py
from heaven import Router

# create your web app i.e. a simple router/multiplexer
app = Router()
```

And to run your new app from heaven?

```sh
$ uvicorn app:app --port 5000 --reload
```

# define a handler function, handler functions accept 3 arguments always
def hello(request, response, context):
    id = request.params.get('customer_id')
    response.body = f'hello customer {id}'


# connect your handler function to an endpoint
app.GET('/customers/:customer_id', hello)

```


## Why Another Python Web Framework?
Because we needed something small enough to be learnt completely by new engineers in less than 5
minutes. Complete mastery with no gray spots.
