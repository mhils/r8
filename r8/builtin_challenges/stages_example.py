import r8


class MultiStageExample(r8.Challenge):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        r8.util.create_flag(self.id, 999999, "__flag__{first-stage}")
        r8.util.create_flag(f"Stage({self.id})", 999999, "__flag__{second-stage}")
        # There is also self.log_and_create_flag() for less static settings.

    title = "MultiStage Example"

    async def description(self, user: str, solved: bool):
        return """
        This is a challenge with multiple stages. 
        Enter "__flag__{first-stage}" to solve the first stage,
        and then "__flag__{second-stage}" for the second one. 
        Support for this is really limited and hacky, but you should get by.
        """

