import os

class Config:
    def __init__(self):
        # Default base directory is '.evals' or can be configured via environment variable
        self._base_dir = os.environ.get("EVAL_FACTORY_DIR", ".evals")

    @property
    def base_dir(self) -> str:
        return self._base_dir

    @base_dir.setter
    def base_dir(self, value: str):
        self._base_dir = value

# Global config instance
config = Config()
