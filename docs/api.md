# Minute 1
We are assuming you have installed **routerling** via `pip install routerling`. If no, then go ahead and install it, otherwise let's dive in.


## 30,000 Foot View...

```

from routerling import Router


router = Router()


router.GET('/v1/customers', lambda r, w, c: pass)
```
