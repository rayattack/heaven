# Minute 2
A promise is a promise. So it's time to tell you about heaven's objects. **_Don't fret - there are only 4 of them._**


### Mambo number 1: Request
All handlers will receive this as their first argument i.e. **`...(r: Request, ..., ...)`** and all Request objects come with the following bag of goodies.

- **`r.app: Router`** -> An instance of the base heaven application

- **`r.body: bytes`** -> The body sent along with the request

- **`r.cookies: dict`** -> All the cookies sent with request **_[keys in lowercase]_**

- **`r.headers: dict`** -> All the headers sent with request **_[keys in lowercase]_**

- **`r.method: str`** -> `GET`, `POST`, `DELETE`? What method type is the http request

- **`r.params: dict`** -> Querystring parameters and url masks `/customers/:param1` parsed into a dictionary

- **`r.querystring: str`** -> The part after the `?` i.e. example.com**?age=34** parsed in comma separated string form

- **`r.subdomain: str`** -> If request was made to a subdomain i.e. `www.example.org` or `api.example.org` then this holds the subdomain value e.g. `www` and `api`.

- **`r.url: str`** -> The url that matched to this handler as sent by the client

-----------------------
