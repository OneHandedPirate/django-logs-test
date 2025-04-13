from abc import ABC, abstractmethod


class BaseReport(ABC):
    name: str

    @abstractmethod
    def process(self, files: list[str]) -> None: ...
