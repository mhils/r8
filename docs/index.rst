r8 API Reference
################

.. autoclass:: r8.Challenge

    .. raw:: html

        <h3>Challenge Display</h3>

    .. autoattribute:: title
        :annotation: : str = "Hello World"
    .. autoattribute:: tags
        :annotation: : list[str] = []
    .. autoattribute:: flag
        :annotation: : str = "__flag__{...}"
    .. automethod:: description
    .. automethod:: visible

    .. raw:: html

        <h3>Challenge Lifecycle</h3>

    .. autoattribute:: active
        :annotation: : bool
    .. autoattribute:: args
        :annotation: : str
    .. automethod:: start
    .. automethod:: stop

    .. raw:: html

        <h3>Logging and Flag Creation</h3>

    .. automethod:: echo
    .. automethod:: log
    .. automethod:: log_and_create_flag

    .. raw:: html

        <h3>HTTP API</h3>

    Challenges can expose an HTTP API. This is for example used to serve static files (such as challenge icons)
    that accompany the challenge.

    .. autoattribute:: static_dir
        :annotation: = "<challenge file directory>/static"
    .. automethod:: api_url
    .. automethod:: handle_get_request
    .. automethod:: handle_post_request

    .. raw:: html

        <h3>Key-Value Storage</h3>

    Challenges can store additional data in a persistent key value storage in the database.

    .. automethod:: get_data
    .. automethod:: set_data

Utilities
=========

.. autofunction:: r8.util.get_team
.. autofunction:: r8.util.has_solved

Challenge Description Helpers
-----------------------------

.. autofunction:: r8.util.media
.. autofunction:: r8.util.spoiler
.. autofunction:: r8.util.challenge_form_js
.. autofunction:: r8.util.challenge_invoke_button
.. autofunction:: r8.util.url_for
.. autofunction:: r8.util.get_host

TCP Server Challenge Helpers
----------------------------

.. autofunction:: r8.util.connection_timeout
.. autofunction:: r8.util.tolerate_connection_error
.. autofunction:: r8.util.format_address

Low-Level Helpers
-----------------

.. seealso:: For challenge development, it is recommended to use the equivalent methods
    exposed by the challenge class instead:
    :meth:`r8.Challenge.echo`, :meth:`r8.Challenge.log` and :meth:`r8.Challenge.log_and_create_flag`.
.. autofunction:: r8.echo
.. autofunction:: r8.log
.. autofunction:: r8.util.create_flag
.. class:: r8.util.THasIP

    An object from which we can derive an IP address,.
    e.g. a `web.Request`, an `asyncio.StreamWriter`, a `str`  or an `(ip, port)` tuple.
