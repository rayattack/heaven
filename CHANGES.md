### VERSION 0.3.2
- Make Heaven Errors more informative and helpful for debugging i.e. UrlDuplicateError should say what URL is the offending URL

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

