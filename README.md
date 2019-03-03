<p align="center">
<img src="misc/logo.svg" width=200 />
<br>
<strong>r8 - /ɹeɪt/</strong>
</p>

r8 is a simple [jeopardy-style](https://ctftime.org/ctf-wtf/) CTF system. What sets it apart from other platforms?

1. r8 is intentionally simple. It won't send emails, support multi-server deployments, 
or provide an LDAP integration.
2. r8 is designed to support university courses. It is usually deployed for an entire semester and
includes challenge scheduling functionality and logging capabilities to detect cheating.
3. r8 is written in modern Python 3. This generally makes it easy to spawn additional network 
services or interface with other tools and languages.

r8 is successfully being used for teaching at the University of California, Berkeley and the University of Innsbruck, Austria.

# Quick Start

Clone the repository and install r8. We need Python 3.6 or above and [pipenv](https://docs.pipenv.org/):

```shell
git clone https://github.com/mhils/r8.git
cd r8
pipenv install
```

Enter the pipenv environment. 
This always needs to be done to make the `r8` command available:

```shell
pipenv shell
```

Create r8's SQLite database in the current directory. 
We also need to let r8 know under which origin it will be hosted at this step:

```shell
r8 sql init --origin http://localhost:8000
```

r8 is typically configured with a plain SQL file. Let's add some demo challenges and users:

```shell
r8 sql file dev.sql
```

We can now start r8:

```shell
r8 run
```

You can now browse to <http://localhost:8000/> and log in as `user1` with password `test`.

## Next Steps

 1. `r8` has a comprehensive command line interface. Check out `r8 --help`, `r8 users --help`, etc.
 2. Take a look at `dev.sql` to learn how r8 can be configured.
 3. Install additional challenges and create new ones (see next section).

## Installing additional challenges

We likely want to install additional challenges, for example from the [r8-example](https://github.com/mhils/r8-example) repository.

First, let's make sure that we have activated the r8 virtualenv created by pipenv:

```shell
cd r8
pipenv shell
```


r8 challenges are always placed in Python packages. To make challenges available to r8, 
we need to install the corresponding package into our Python environment. Let's get the example
repository and add it:

```shell
cd ..
git clone https://github.com/mhils/r8-example.git
cd r8-example
pip install -e .  # install package in editable mode.
```

We can now verify that r8 has picked up the new challenges:

```shell
r8 challenges list-available
# Output:
#   r8.builtin_challenges:
#    [...]
#   r8_example:
#    - HelloWorld
```

To make the challenge available to users, we also need to instantiate it by adding it to the database. 
Go back to the SQL configuration file (`dev.sql` in the example above) and add the following:
```sql
INSERT INTO challenges (cid, team, t_start, t_stop) VALUES
  ('HelloWorld', 0, datetime('now'), datetime('now','+1 month'));
```

Finally, we can apply our configuration changes and run r8 again:
```shell
r8 sql file dev.sql
r8 run
```

The *Hello World* challenge is now visible to users! 🎉

## Creating new challenges

The API Documentation for challenge development can be found at https://mhils.github.io/r8/.

It is recommended to use [r8-example](https://github.com/mhils/r8-example) as a template
and place challenges in a new separate repository. See `r8.builtin_challenges` and `r8_example` 
for challenge examples.

## Architecture

r8 consists of the following parts:
  1. The core **`r8` application** written in Python, which manages the currently active challenges. 
     It provides a command-line API for administration (`r8.cli`), a REST API for users (`r8.server`), 
     and a Python API for challenges (`r8.Challenge`).
  2. **CTF challenges** implemented in Python 3.6+. All challenges need to inherit from `r8.Challenge` 
     and must be registered using entrypoints so that they are imported on start. 
     See `r8.builtin_challenges` and `r8_example` for challenge examples and each repo's `setup.py` for entrypoint declaration.
  3. An SQLite **database** that contains information on users, groups, challenge scheduling, and flags.
     There also is an event log that can be used to e.g. detect indicators of plagiarism.
  4. A **web interface** that allows users to view challenges and enter flags, implemented using React and Bootstrap.
     To simplify development, there is no compilation step.

To speed up development, the server can be automatically reloaded on changes using [modd](https://github.com/cortesi/modd).

## Deployment

For production use, it is recommended to place it behind a TLS-terminating reverse 
proxy such as nginx. A couple of auxiliary examples are provided in the [./misc](./misc) folder:

 - `crontab`: crontab example to make daily backups.
 - `nginx.conf`: nginx configuration example for a HTTPS-only deployment.
 - `r8.service`: systemd service file example.
