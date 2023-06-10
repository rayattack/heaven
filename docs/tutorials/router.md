# Quickstart Tutorial

<div class="termy">

```console
$ uvicorn main:app --reload

<span style="color: green;">INFO</span>:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
<span style="color: green;">INFO</span>:     Started reloader process [28720]
<span style="color: green;">INFO</span>:     Started server process [28722]
<span style="color: green;">INFO</span>:     Waiting for application startup.
<span style="color: green;">INFO</span>:     Application startup complete.
---> 100%
```

</div>

There are 4 ways to query your data using SuperSQL

- Identifier Interpolation
- Manually create a _**Table**_ schema
- Automatically reflect tables from the database
- Use _`dict`_ and _`list`_ with **variables**


&nbsp;
#### Identifier Interpolation

```py
from os import environ
from supersql import Query

user = environ.get('DB_USER')
pwd = environ.get('DB_PWD')
dialect = environ.get('DB_ENGINE')

query = Query(vendor=dialect, user=user, password=pwd)

results = query.SELECT(
    "first_name", "last_name", "email"
).FROM(
    "employees"
).WHERE(
    "email = 'someone@example.com'"  # WARNING: don't inject user provided values (SQL Injection Possible)
).run()

```

!!!warning "Magic Literals Are Bad"
    It is usually not advisable to repeat string or other constants in multiple places across your codebase.
    If you notice string or literal values repeating more than once consider turning them into constants.


!!!info "Identifiers ONLY"
    It is advisable to limit use of strings to only identifiers e.g. `column names`, `table names`, `...`
    and operators `=`, `<>` etc.



&nbsp;
#### Manually Create Table Schema
```py
from supersql import Table


class Employee(Table):...


emp = Employee()


results = query.SELECT(
    emp.first_name, emp.last_name, emp.email
).FROM(
    emp
).WHERE(
    emp.email == 'someone@example.com'
).execute()  # `execute` fetches all data into memory

```

!!!danger "Run vs Execute"
    `execute()` fetches all data into memory. Do not use with unsafe queries to large tables
    e.g. `SELECT * FROM very_large_table`. Use `run()` as it fetches data in chunks and
    reconnects as necessary to fetch more data.



&nbsp;
#### Auto-Reflect Table Schema
```py
...


tables = query.database("dbname").tables()
emp = tables.get("employees")


results = query.SELECT(
    emp.first_name, emp.last_name, emp.email
).FROM(
    emp
).WHERE(
    emp.email == 'someone@example.com'
).execute()

```

&nbsp;

#### Use Dict &amp; Lists with Variables
```py

from supersql import Query

query = Query(...)  # connection parameters as required

def example(table, *args, **kwargs)
    alt_results = query.SELECT(*args).FROM(table).WHERE(**kwargs).run()
```


&nbsp;
&nbsp;
## Okay... How about inserting Data?

Adding or inserting data with SuperSQL is just as easy as querying data.

However it is important for you to understand that __SuperSQL is NOT AN ORM__, and that means you
can't use some magical `table.save()` method to insert data to the database.

That's now how we roll... &nbsp; &nbsp; :smile:

So how then do you insert data? Let's look at some code.

```py
# borrowing Query and Employee code from above
...

def insert(**kwargs):
    result = query.INSERT(
        emp
    ).VALUES(
        **kwargs
    ).execute()


def bulk_insert(*args):
    result = query.INSERT(
        emp.first_name,
        emp.last_name,
        emp.email
    ).VALUES(
        args
    ).execute()


def insert_with_into(*args):
    # Use of INTO(table) used here is 100% optional but arguably
    # adds readability
    results = Query.INSERT(
        emp.first_name, emp.last_name, emp.email
    ).INTO(
        emp
    ).VALUES(
        ["John", "Doe", "john.doe@example.net"] if not args else args
    ).execute()

query.INSERT().INTO().VALUES().WHERE_NOT_EXISTS()
```
