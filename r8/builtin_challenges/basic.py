import r8


class Basic(r8.Challenge):
    """
    A *very* basic challenge that only has a title.
    This can be useful to for example record class attendance.
    """
    @property
    def title(self):
        return self.args
