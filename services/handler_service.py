import csv
from collections import defaultdict, Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from os import cpu_count

from utils import int_defaultdict


class HandlerReportService:
    """
    Сервис отчетов для обработчиков

    LOOKUP_SUBSTRING - подстрока, которая должна присутствовать в строке для
    обработки
    REPORT_FILENAME - имя файла для сохранения отчета
    KEY_SUBSTRING_INDEX - индекс подстроки, которая содержит ключ (эндпоинт)
    VALUE_SUBSTRING_INDEX - индекс подстроки, которая содержит значение
    (уровень логирования)
    KEY_OFFSET_ON_VALUE - смещение индекса подстроки, которая содержит ключ,
    в зависимости от значения (в примерах логов на уровне ERROR вместо
    HTTP-метода идет подстрока Internal Server Error:, значит при разбитии
    строки по пробелам применяем смещение 2, чтобы получить подстроку с эндпоинтом)
    LEVELS - уровни логирования (используются для формирования заголовков таблицы)
    """

    LOOKUP_SUBSTRING: str = "django.request"
    REPORT_FILENAME: str = "handlers"
    KEY_SUBSTRING_INDEX: int = 5
    VALUE_SUBSTRING_INDEX: int = 2
    KEY_OFFSET_ON_VALUE: dict[str, int] = {
        "ERROR": 2,
    }
    LEVELS = [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ]

    @classmethod
    def execute(cls, *files: str) -> None:
        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
            results = executor.map(cls._process_file, files)

        report: dict[str, dict[str, int]] = cls._merge_results(*results)

        cls._save_report_to_csv(report)

    @classmethod
    def _merge_results(
        cls, *logs: dict[str, dict[str, int]]
    ) -> dict[str, dict[str, int]]:
        report = defaultdict(int_defaultdict)

        for log in logs:
            for key, value in log.items():
                for v, count in value.items():
                    report[key][v] += count

        return report

    @classmethod
    def _process_file(cls, file_path: str) -> dict[str, dict[str, int]]:
        result = defaultdict(int_defaultdict)

        with open(file_path) as file:
            for line in file:
                parsed = cls._parse_line(line)
                if parsed:
                    result[parsed[0]][parsed[1]] += 1

        return result

    @classmethod
    def _parse_line(cls, line: str) -> tuple[str, str] | None:
        if cls.LOOKUP_SUBSTRING not in line:
            return None

        parts = line.split()
        value = parts[cls.VALUE_SUBSTRING_INDEX]
        key = parts[cls.KEY_SUBSTRING_INDEX + cls.KEY_OFFSET_ON_VALUE.get(value, 0)]

        return key, value

    @classmethod
    def _save_report_to_csv(cls, report: dict[str, dict[str, int]]) -> None:
        headers = ["HANDLER"] + cls.LEVELS
        output_file = Path(f"{cls.REPORT_FILENAME}.csv")

        sorted_handlers = sorted(report.keys())

        rows = []
        totals = Counter()

        for handler in sorted_handlers:
            row = [handler]
            for value in cls.LEVELS:
                count = report[handler].get(value, 0)
                totals[value] += count
                row.append(count)
            rows.append(row)

        total_row = [f"Total requests: {sum(totals.values())}"] + [
            totals[level] for level in cls.LEVELS
        ]
        rows.append(total_row)

        with output_file.open("w", newline="") as csvfile:
            writer = csv.writer(csvfile, delimiter="\t")
            writer.writerow(headers)
            writer.writerows(rows)
