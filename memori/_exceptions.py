r"""
 _  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""


class QuotaExceededError(Exception):
    def __init__(
        self,
        message=(
            "your IP address is over quota; register for an API key now: "
            + "https://app.memorilabs.ai/signup"
        ),
    ):
        self.message = message
        super().__init__(self.message)
