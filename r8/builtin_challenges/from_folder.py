from pathlib import Path

import r8


class FromFolder(r8.Challenge):
    """
    A challenge that is defined by HTML and text files in a folder.
    Folder structure:

        /title.txt - The challenge title
        /{team_id}/description.html - The challenge description for a team.
        /{team_id}/flag.txt - The flag for a given team.
    """

    path: Path
    title = ""

    def __init__(self, cid: str) -> None:
        super().__init__(cid)
        self.path = Path(self.args).absolute()

    async def start(self):
        self.title = (self.path / "title.txt").read_text()
        flags = list(self.path.glob("*/flag.txt"))
        for flag in flags:
            with open(flag) as f:
                r8.util.create_flag(self.id, 1, f.read().strip())
        self.echo(f"Created {len(flags)} flags.")

    async def description(self, user: str, solved: bool):
        desc = self.path / r8.util.get_team(user) / "description.html"
        try:
            return desc.read_text()
        except IOError:
            return """
            <div class="alert alert-danger">
                No challenge created for your group. Please report a bug!
            </div>
            """
