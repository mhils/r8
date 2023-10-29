<p align="center">
<img src="misc/logo.svg" width=200 />
<br>
<strong>r8 - /ɹeɪt/</strong>
</p>

r8 is a simple [jeopardy-style](https://ctftime.org/ctf-wtf/) CTF system. What sets it apart from other platforms?

1. r8 is intentionally simple. It won't support multi-server deployments or provide an LDAP integration.
3. r8 is designed to support CTF events, but also entire university courses. 
   It can be deployed for an entire semester and includes challenge scheduling functionality and logging capabilities to detect cheating.
3. r8 is written in modern Python 3. This generally makes it easy to spawn additional network services or interface with other tools and languages.

r8 is successfully being used for teaching at the University of California, Berkeley, the University of Innsbruck,
as well as some other places for hiring assessments.

# Quick Start

In short, install r8 as a Python package using your preferred way. We recommend the following:

Make sure you have Python 3.9 or above. Clone the repository, create a Python virtual environment 
into which we install all dependencies, and finally install r8:

```shell
python3 -m venv venv
git clone https://github.com/mhils/r8.git
venv/bin/pip install -e ./r8
```

Activate the virtual environment. This always needs to be done to make the `r8` command available:

```shell
source venv/bin/activate
```

Create r8's SQLite database in the current directory. 

```shell
r8 sql init
```

r8 is typically configured with a plain SQL file. Let's add some demo challenges and users:

```shell
r8 sql file r8/config.sql
```

We can now start r8:

```shell
r8 run
```

You can now browse to <http://localhost:8000/> and log in as `user1` with password `test`.

## Next Steps

 1. `r8` has a comprehensive command line interface. Check out `r8 --help`, `r8 users --help`, etc.
 2. Take a look at `config.sql` to learn how r8 can be configured.
 3. Install additional challenges and create new ones (see next section).

## Installing additional challenges

We likely want to install additional challenges, for example from the [r8-example](https://github.com/mhils/r8-example) 
repository. To make challenges available to r8, we need to install the corresponding Python package into our Python 
environment. Let's get the example repository and add it:

```shell
git clone https://github.com/mhils/r8-example.git
venv/bin/pip install -e r8-example
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
Go back to the SQL configuration file (`config.sql` in the example above) and add the following:
```sql
INSERT INTO challenges (cid, team, t_start, t_stop) VALUES
  ('HelloWorld', 0, datetime('now'), datetime('now','+1 month'));
```

Finally, we can apply our configuration changes and run r8 again:
```shell
r8 sql file config.sql
r8 run
```

The *Hello World* challenge is now visible to users! 🎉

## Creating new challenges

The API Documentation for challenge development can be found at https://mhils.github.io/r8/.

It is recommended to use [r8-example](https://github.com/mhils/r8-example) as a template
and place challenges in a new separate repository. See `r8.builtin_challenges` and `r8_example` 
for challenge examples.

## Customizing the HTML template

r8 provides some simple means to modify the default HTML template, for example to add a custom logo.
An example can be found in the [`misc/custom-template`](misc/custom-template) directory.

## Architecture

r8 consists of the following parts:
  1. The core **`r8` application** written in Python, which manages the currently active challenges. 
     It provides a command-line API for administration (`r8.cli`), a REST API for users (`r8.server`), 
     and a Python API for challenges (`r8.Challenge`).
  2. **CTF challenges** implemented in Python. All challenges need to inherit from `r8.Challenge` 
     and must be registered using entrypoints so that they are imported on start. 
     See `r8.builtin_challenges` and `r8_example` for challenge examples and each repo's `setup.py` for entrypoint declaration.
  3. An SQLite **database** that contains information on users, groups, challenge scheduling, and flags.
     There also is an event log that can be used to help students or detect indicators of plagiarism.
  4. A **web interface** that allows users to view challenges and enter flags, implemented using React and Bootstrap.
     To simplify development, there is no compilation step.

To speed up development, the server can be automatically reloaded on changes using [modd](https://github.com/cortesi/modd).

## User Provisioning

r8 can be set up to allow users to register themselves (by enabling the `register` setting, see `config.sql`), 
but you may also use it with a fixed set of users.
The following workflow works well to provision accounts for a class:

1. Create a text file with one username per line. Those should be email addresses or the local part of an email address.
   For example, add `john.doe` and `jane.doe` if their email addresses are `john.doe@example.com` and `jane.doe@example.com`.
   If they are on different domains, use complete email addresses, e.g. `john@example.com` and `jane@other.example.org`.
2. Run `r8 users make-sql usernames.txt` (optionally with `--teams r8/misc/teamnames.txt`).  
   Put the output into your `config.sql` file.
3. Run `r8 sql file config.sql` to apply the changes to the database.
4. Run `r8 users send-credentials` to send out emails with login details.

## Deployment

For production use, it is recommended to run r8 on a throwaway VM behind a TLS-terminating reverse 
proxy such as Caddy or nginx. A couple of auxiliary configuration examples are provided in the [./misc](./misc) folder:

 - `Caddyfile`: Caddyfile configuration example for an HTTPS-only deployment.
 - `r8.service`: systemd service file example.
