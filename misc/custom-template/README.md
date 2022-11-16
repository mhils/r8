# Customizing the HTML template

r8 can be styled with a custom HTML template.

### Using a custom template

To use a custom template, you need to set the `static_dir` setting in your r8 database using any of the following ways:

New r8 installation:

```shell
r8 sql init --static-dir ./misc/custom-template --static-dir ./r8/static
```

Existing r8 installation:

```shell
r8 settings set static_dir /absolute/path/to/r8/misc/custom-template /absolute/path/to/r8/r8/static
```

`config.sql`:

```sql
INSERT OR REPLACE INTO settings (key, value)
VALUES
       ('static_dir', '["/absolute/path/to/r8/misc/custom-template", "/absolute/path/to/r8/r8/static"]')
;
```

### Writing your own template

In short, r8's website is rendered from [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/templates/) templates.
The `static_dir` setting governs which template directories are used. It is common to pass two directories: First your
custom template directory and second r8's builtin template directory, from which most functionality is inherited.
