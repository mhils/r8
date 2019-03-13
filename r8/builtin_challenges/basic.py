import r8


class Attendance(r8.Challenge):
    """
    Challenge type to record class attendance.
    """
    @property
    def title(self):
        return f"Attendance {self.args}"
