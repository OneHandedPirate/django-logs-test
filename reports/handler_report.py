from reports.base import BaseReport
from services import HandlerReportService


class HandlerReport(BaseReport):
    name: str = "handlers"

    def process(self, files: list[str]) -> None:
        HandlerReportService.execute(*files)
