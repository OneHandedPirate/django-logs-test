import pytest
from collections import defaultdict
from unittest.mock import (
    patch,
    mock_open,
    MagicMock,
)

from services.handler_service import HandlerReportService
from utils import int_defaultdict


@pytest.fixture
def service():
    """Fixture to provide a HandlerReportService class."""
    return HandlerReportService


@pytest.fixture
def log_lines() -> dict[str, str]:
    return {
        "LOG_LINE_INFO": "2023-10-27 10:00:00 INFO django.request GET /api/users/ 200 OK",
        "LOG_LINE_ERROR": "2023-10-27 10:01:00 ERROR django.request Internal Server Error: /api/orders/create",
        "LOG_LINE_WARNING": "2023-10-27 10:02:00 WARNING django.request GET /api/products/123",
        "LOG_LINE_IRRELEVANT": "2023-10-27 10:03:00 DEBUG some_other_module Doing something else",
        "LOG_LINE_MALFORMED": "2023-10-27 10:04:00 ERROR django.request",
    }


def test_parse_line_info(service, log_lines):
    """Тест на обработку строки с INFO"""
    assert service._parse_line(log_lines["LOG_LINE_INFO"]) == ("/api/users/", "INFO")


def test_parse_line_error_offset(service, log_lines):
    """Тест на обработку строки с оффсетом ключа"""
    assert service._parse_line(log_lines["LOG_LINE_ERROR"]) == (
        "/api/orders/create",
        "ERROR",
    )


def test_parse_line_warning(service, log_lines):
    """Тест на обработку строки с WARNING"""
    assert service._parse_line(log_lines["LOG_LINE_WARNING"]) == (
        "/api/products/123",
        "WARNING",
    )


def test_parse_line_irrelevant_substring(service, log_lines):
    """Тест на обработку строки, не содержащей искомую подстроку"""
    assert service._parse_line(log_lines["LOG_LINE_IRRELEVANT"]) is None


def test_parse_line_malformed_index_error(service, log_lines):
    """Тест на вызов ошибки при некорректной строке (короткая строка)"""
    with pytest.raises(IndexError):
        service._parse_line(log_lines["LOG_LINE_MALFORMED"])


def test_parse_line_no_lookup_substring(service):
    """Тест на отсутствие подстроки для поиска"""
    assert service._parse_line("some other log line") is None


def test_process_file(tmp_path, service, log_lines):
    """Тест на обработку файла"""
    log_file = tmp_path / "dummy_path.log"
    log_file.write_text(
        "\n".join(
            [
                log_lines["LOG_LINE_INFO"],
                log_lines["LOG_LINE_ERROR"],
                log_lines["LOG_LINE_IRRELEVANT"],
                log_lines["LOG_LINE_WARNING"],
            ]
        )
    )

    expected_result = defaultdict(int_defaultdict)
    expected_result["/api/users/"]["INFO"] = 1
    expected_result["/api/orders/create"]["ERROR"] = 1
    expected_result["/api/products/123"]["WARNING"] = 1

    result = service._process_file(str(log_file))

    assert result == expected_result


@patch("builtins.open", new_callable=mock_open, read_data="")
def test_process_empty_file(mock_file, service):
    """Тест на обработку пустого файла"""
    expected_result = defaultdict(int_defaultdict)
    result = service._process_file("empty.log")
    mock_file.assert_called_once_with("empty.log")
    assert result == expected_result


def test_merge_results_empty(service):
    """Тест на склейку пустых результатов"""
    assert service._merge_results() == defaultdict(int_defaultdict)


def test_merge_results_single(service):
    """Тест на склейку результатов со словарем из одного файла"""
    log1 = defaultdict(int_defaultdict)
    log1["/api/users"]["INFO"] = 5
    log1["/api/users"]["WARNING"] = 1
    assert service._merge_results(log1) == log1


def test_merge_results_multiple(service):
    """Тест на склейку результатов из нескольких файлов"""
    log1 = defaultdict(int_defaultdict)
    log1["/api/users"]["INFO"] = 5
    log1["/api/products"]["ERROR"] = 2

    log2 = defaultdict(int_defaultdict)
    log2["/api/users"]["INFO"] = 3
    log2["/api/users"]["ERROR"] = 1
    log2["/api/orders"]["INFO"] = 10

    expected = defaultdict(int_defaultdict)
    expected["/api/users"]["INFO"] = 8
    expected["/api/users"]["ERROR"] = 1
    expected["/api/products"]["ERROR"] = 2
    expected["/api/orders"]["INFO"] = 10

    result = service._merge_results(log1, log2)
    assert result == expected


@patch("pathlib.Path.open", new_callable=mock_open)
@patch("csv.writer")
def test_save_report_to_csv(mock_csv_writer, mock_path_open, service):
    """Тест метода сохранения отчета в CSV"""
    mock_writer_instance = MagicMock()
    mock_csv_writer.return_value = mock_writer_instance

    report_data = defaultdict(lambda: defaultdict(int))
    report_data["/api/users"]["INFO"] = 10
    report_data["/api/users"]["ERROR"] = 1
    report_data["/api/products"]["WARNING"] = 5
    report_data["/api/admin"]["DEBUG"] = 20

    service._save_report_to_csv(report_data)

    mock_path_open.assert_called_once_with("w", newline="")

    mock_csv_writer.assert_called_once_with(mock_path_open.return_value, delimiter="\t")

    expected_headers = ["HANDLER"] + service.LEVELS
    expected_rows = [
        ["/api/admin", 20, 0, 0, 0, 0],
        ["/api/products", 0, 0, 5, 0, 0],
        ["/api/users", 0, 10, 0, 1, 0],
        ["Total requests: 36", 20, 10, 5, 1, 0],
    ]

    mock_writer_instance.writerow.assert_called_once_with(expected_headers)
    mock_writer_instance.writerows.assert_called_once_with(expected_rows)

@patch("services.handler_service.ProcessPoolExecutor")
@patch("services.handler_service.HandlerReportService._merge_results")
@patch("services.handler_service.HandlerReportService._save_report_to_csv")
def test_execute(mock_save, mock_merge, mock_executor_cls, service):
    mock_executor_instance = MagicMock()
    mock_executor_cls.return_value.__enter__.return_value = mock_executor_instance

    processed_results = [
        {"/api/users": {"INFO": 5}},
        {"/api/users": {"ERROR": 1}, "/api/products": {"INFO": 2}},
    ]
    mock_executor_instance.map.return_value = processed_results

    # Что вернёт merge
    merged_data = defaultdict(
        int_defaultdict,
        {"/api/users": {"INFO": 5, "ERROR": 1}, "/api/products": {"INFO": 2}},
    )
    mock_merge.return_value = merged_data

    files = ["file1.log", "file2.log"]

    service.execute(*files)

    mock_executor_cls.assert_called_once()
    mock_executor_instance.map.assert_called_once()

    called_args = mock_executor_instance.map.call_args.args
    assert called_args[0] == service._process_file
    assert list(called_args[1]) == files

    mock_merge.assert_called_once_with(*processed_results)
    mock_save.assert_called_once_with(merged_data)
