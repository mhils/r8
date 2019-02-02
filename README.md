<p align="center">
<img src="misc/logo.svg" width=200 />
<br>
<strong>r8 - /ɹeɪt/</strong>
</p>

r8 is a ctf-style autograding system. 

# Quick Start

Clone the repository:

```shell
git clone https://github.com/mhils/r8.git
```

Install r8 using Python 3.6 or above:

```shell
cd r8
pip3 install -e . 
```

Initialize r8:

```shell
r8 sql init --origin http://localhost:8000 # Create database and config.
r8 sql file dev.sql                        # Initialize with dummy values.
r8 run                                     # Start r8.
```

You can now browse to <http://localhost:8000/> and log in as `user1` with password `test`.

To get an overview of available features, check out the command line documentation:`r8 --help`, 
`r8 users --help`, etc.

# Development

### Challenges

To get started with challenge development, check out the 
[r8-example](https://github.com/mhils/r8-example) repository.

### Architecture

r8 consists of the following parts:
  1. The core **`r8` application** written in Python, which manages the currently active challenges. 
     It provides a command-line API for administration (`r8.cli`), a REST API for users (`r8.server`), 
     and a Python API for challenges (`r8.Challenge`).
  2. A collection of **CTF challenges** implemented in Python 3.6+. See `r8.builtin_challenges` and `r8_example`.
  3. An SQLite **database** that contains information on users, groups, challenge scheduling, and flags.
     There also is an event log that can be used to e.g. detect indicators of plagiarism.
  4. A **web interface** that allows users to view challenges and enter flags, implemented using React and Bootstrap.
     To simplify development, there is no compilation step.

To speed up development, the server can be automatically reloaded on changes using [modd](https://github.com/cortesi/modd).

