# Customizing the HTML template

This repository shows an example on how the r8 HTML interface can be styled.

In short, r8's website is rendered from [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/templates/) templates.
The `static_dir` setting governs which template directories are used. It is common to pass two directories: First your
custom template directory and second r8's builtin template directory, from which most functionality is inherited.

### Usage

New installation:

```shell
r8 sql init --static-dir ./misc/custom-template --static-dir ./r8/static
```

Existing installation:

```shell
r8 settings set static_dir /absolute/path/to/r8/misc/custom-template /absolute/path/to/r8/r8/static
```
