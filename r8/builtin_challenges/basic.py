from typing import ClassVar

import r8


class StaticChallenge(r8.Challenge):
    """
    A challenge with a single static flag. This is useful to create easter egg challenges
    for example, where the flag is hidden somewhere else.
    """
    flag: ClassVar[str]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.flag:
            raise RuntimeError(f"No flag attribute for {type(self).__name__}.")
        r8.util.create_flag(self.id, 999999, self.flag)


class Attendance(r8.Challenge):
    """
    Challenge type to record class attendance.
    """
    @property
    def title(self):
        return f"Attendance {self.args}"
