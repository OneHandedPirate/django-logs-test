import argparse
import time

from utils import check_logfiles

from reports import HandlerReport


REPORTS = {report.name: report for report in [HandlerReport()]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "logfiles",
        nargs="+",
    )
    parser.add_argument(
        "--report",
        required=True,
        choices=["handlers"],
    )
    args = parser.parse_args()

    if check_logfiles(args.logfiles) is False:
        raise ValueError("Некорректный путь к одному или нескольким файлам")

    if args.report not in REPORTS:
        raise ValueError("Неизвестный отчет")

    start: float = time.perf_counter()
    REPORTS[args.report].process(args.logfiles)
    print(f"Время выполнения: {time.perf_counter() - start:.5f} c")

if __name__ == "__main__":
    main()
