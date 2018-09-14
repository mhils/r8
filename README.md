<p align="center">
<img src="misc/logo.svg" width=200 />
<br>
<strong>r8 - /ɹeɪt/</strong>
</p>

r8 is a ctf-style autograding system. 

# Installation

r8 requires Python 3.6 or above.

```shell
pip3 install -e .
```

# Usage

```shell
r8 --help
```

# Quick Start

```shell
r8 sql init           # Create database.
r8 sql file dev.sql   # Fill database with dummy values.
r8 run                # Start r8.
```

# Development

### Architecture

r8 consists of the following parts:
  1. The core **`r8` application** written in Python, which manages the currently active challenges. 
     It provides a command-line API for administration (`r8.cli`), a REST API for users (`r8.server`), 
     and a Python API for challenges (`r8.Challenge`).
  2. A collection of **CTF challenges** implemented in Python 3.6+. See `r8.builtin_challenges`.
  3. An SQLite **database** that contains information on users, groups, challenge scheduling, and flags.
     There also is an event log that can be used to e.g. detect indicators of plagiarism.
  4. A **web interface** that allows users to view challenges and enter flags, implemented using React and Bootstrap.
     To simplify development, there is no compilation step.

To speed up development, the server can be automatically reloaded on changes using [modd](https://github.com/cortesi/modd).

