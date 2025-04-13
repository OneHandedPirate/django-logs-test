import pytest
from unittest.mock import patch, MagicMock

import main
from reports.handler_report import HandlerReport


@pytest.fixture(autouse=True)
def prevent_exit(mocker):
    """Предотвращает завершение тестов при ошибках argparse"""
    mocker.patch("argparse.ArgumentParser._print_message")


@patch("main.argparse.ArgumentParser")
@patch("main.check_logfiles")
@patch("main.HandlerReport.process")
def test_main_success(mock_report_process, mock_check_logfiles, mock_argparse_cls):
    """Тест успешного выполнения main()"""
    mock_parser_instance = MagicMock()
    mock_args = MagicMock()
    mock_args.logfiles = ["/path/to/file1.log", "/path/to/file2.log"]
    mock_args.report = "handlers"
    mock_parser_instance.parse_args.return_value = mock_args
    mock_argparse_cls.return_value = mock_parser_instance

    mock_check_logfiles.return_value = True

    main.main()

    mock_argparse_cls.assert_called_once()
    mock_parser_instance.add_argument.assert_any_call("logfiles", nargs="+")
    mock_parser_instance.add_argument.assert_any_call(
        "--report", required=True, choices=["handlers"]
    )
    mock_parser_instance.parse_args.assert_called_once()

    mock_check_logfiles.assert_called_once_with(mock_args.logfiles)
    mock_report_process.assert_called_once_with(mock_args.logfiles)


@patch("main.argparse.ArgumentParser")
@patch("main.check_logfiles")
@patch("main.HandlerReport.process")
def test_main_invalid_logfiles(
    mock_report_process, mock_check_logfiles, mock_argparse_cls
):
    """Тест, проверяющий main() с некорректными путями к файлам логов"""
    mock_parser_instance = MagicMock()
    mock_args = MagicMock()
    mock_args.logfiles = ["invalid/path.log"]
    mock_args.report = "handlers"
    mock_parser_instance.parse_args.return_value = mock_args
    mock_argparse_cls.return_value = mock_parser_instance

    mock_check_logfiles.return_value = False

    with pytest.raises(
        ValueError, match="Некорректный путь к одному или нескольким файлам"
    ):
        main.main()

    mock_check_logfiles.assert_called_once_with(mock_args.logfiles)
    mock_report_process.assert_not_called()


@patch("main.argparse.ArgumentParser")
@patch("main.check_logfiles")
@patch("main.HandlerReport.process")
def test_main_unknown_report(
    mock_report_process, mock_check_logfiles, mock_argparse_cls
):
    """Тест, проверяющий выброс ошибки при неизвестном типе отчета"""
    mock_parser_instance = MagicMock()
    mock_args = MagicMock()
    mock_args.logfiles = ["/path/to/file1.log"]
    mock_args.report = "unknown_report"
    mock_parser_instance.parse_args.return_value = mock_args
    mock_argparse_cls.return_value = mock_parser_instance

    mock_check_logfiles.return_value = True

    original_reports = main.REPORTS
    main.REPORTS = {"handlers": HandlerReport()}

    with pytest.raises(ValueError, match="Неизвестный отчет"):
        main.main()

    main.REPORTS = original_reports

    mock_check_logfiles.assert_called_once()
    mock_report_process.assert_not_called()


@patch("sys.argv", ["main.py", "--report"])
@patch("main.check_logfiles")
@patch("main.HandlerReport.process")
def test_main_argparse_missing_args(mock_report_process, mock_check_logfiles):
    """Тест проверки отсутствия обязательных аргументов"""
    with pytest.raises(SystemExit):
        main.main()
    mock_check_logfiles.assert_not_called()
    mock_report_process.assert_not_called()


@patch("sys.argv", ["main.py", "--report", "invalid_choice", "file.log"])
@patch("main.check_logfiles")
@patch("main.HandlerReport.process")
def test_main_argparse_invalid_choice(mock_report_process, mock_check_logfiles):
    """Тест проверки выбора несуществующего отчета"""
    with pytest.raises(SystemExit):
        main.main()
    mock_check_logfiles.assert_not_called()
    mock_report_process.assert_not_called()
