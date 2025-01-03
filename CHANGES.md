### 0.5.0
- Major change to the underlying engine and how heaven parses URIs without affecting the API to add support for parameter hinting
    and extremely flexible parameter labels e.g. `/v1/profiles/:id/orders` and `/v1/profiles/:identity` is now possible i.e. you 
    can now label parameters different things on different routes.

### 0.4.2
- Added support for param hints i.e. specifying the data type for heaven to automatically parse params into

### VERSION 0.3.10
- Add the **IP Object** via the `req.ip` object property that provides an `ip.address` and `ip.port` expanded getter for the values.

### VERSION 0.3.9
- Automatically inject `heaven.Request`, `heaven.Response`, and `heaven.Context` objects into jinja2 template scope so it must not be manually added
- Add support for using mock heaven objects for writing testable code

### VERSION 0.3.8
- Add support for `response.interpolate(name: str, **contexts)` to render and return html templates without saving to res.body.

### VERSION 0.3.7
- Add support for `response.cookie(name: str, value: str, **kwargs)` functionality where `kwargs` supports
		all the valid set-cookie header parameters (no case sensitivity).

### VERSION 0.3.6
- Change ASGI websocket response from `websocket.start` to `websocket.http.response.start`

### VERSION 0.3.5
- Add support for `._.` a.k.a lookup helper paradigm to manage heaven global state i.e. global state getter and setter
	```py
	from http import HTTPStatus
	from heaven import App

	app = App()

	# save 'abc' under your app global state under the `save_me` key
	app._.save_me = 'abc'

	# retrieve from your global state using the same `._.` paradigm
	app.GET('/', lambda req, res, ctx: res.out(HTTPStatus.OK, f'This is what you saved: {req.app._.save_me}'))
	```
	think of **app**`._.`**this_field** AS **app** -> `lookup` -> **this_field** where `._. == lookup`

### VERSION 0.3.4
- Add support for `heaven.call` to inject heaven instance into function passed to `.call` which
	can be used to defer routes registration or any other heaven setup activities to other python modules i.e.
	```py
	from heaven import App
	app = App()

	#  src/routes/messages.py -> #up(app: App): app.GET('/messages', 'src.controllers.messages.tables')
	app.call('src.routes.messages.up')
	```

### VERSION 0.3.3
- Fixed bug with query strings by battle pressing to ensure edge cases covered

### VERSION 0.3.2
- Make Heaven Errors more informative and helpful for debugging i.e. UrlDuplicateError should say what URL is the offending URL
- Add support to retrieve `.host` and `.scheme` from the request object
- Implement `Application.listen` allowing the use of `python app.py` to launch the app

#### VERSION 0.3.1

- Add support for adding daemons that run for the entire lifecycle of the application via
	the `Application.daemons` getter and setter fields.


#### VERSION 0.2.6

- Add support for `Response.out` helper function to allow setting status, body, and headers from a single function body


#### VERSION 0.1.0
------------------

Unreleased Jun 25, 2023

- Fix cookie partioning logic to process cookie strings that contain the `=` symbol
- Add synchronous rendering support with Guardian Angel tip for toggling between sync and async renderer
- Remove unimplemented `Response.file` method
- Add support for deferred callables receiving instance of `Application | Router` as sole argument

&nbsp;


#### VERSION 0.0.9
------------------

Released Jun 25, 2023

- Add exception handling to ignore http cookie malformation errors

&nbsp;



#### VERSION 0.0.8
------------------

Released Jun 25, 2023


- Fix bug where params causes images not to load due to it's route traversal utilisation

- Fix parameterisation of querystring not happening when `:dynamic` route param already exists

&nbsp;


#### VERSION 0.0.7
------------------

Released Jun 17, 2023

- Add mount isolation support for router aggregation/code separation

&nbsp;


#### VERSION 0.0.5
------------------

Released Jun 11, 2023

- Remove unnecessary comments to not clutter project

&nbsp;


#### VERSION 0.0.4
------------------

Released Jun 11, 2023

- Add parameterization support for wildcard routes

&nbsp;


#### VERSION 0.0.3
------------------

Released Jun 10, 2023

- Add support for ```str``` to ```bytes``` encoding in ```req.body```
- Change the way single dispatch works on ```body```
- Fix Router wildcard not working due to wildcard typo fixed in earlier release
- Fix no deviation handling for parameterized routes and wildcard routes

&nbsp;


#### VERSION 0.0.2
------------------

Released Jun 1, 2023

- Remove unused variables

&nbsp;


#### VERSION 0.0.1
------------------

Released May 3, 2023

- Initial Release
