from collections import defaultdict

from utils import check_logfiles, int_defaultdict


def test_int_defaultdict_returns_defaultdict():
    """Тест на возвращаемое значение int_defaultdict"""
    d = int_defaultdict()
    assert isinstance(d, defaultdict)


def test_int_defaultdict_defaults_to_zero():
    """Тест на значение по умолчанию в int_defaultdict"""
    d = int_defaultdict()
    assert d["non_existent_key"] == 0


def test_check_logfiles_all_exist(tmp_path):
    """Тест на check_logfiles при наличии всех файлов"""
    file1 = tmp_path / "log1.txt"
    file2 = tmp_path / "log2.log"
    file1.write_text("content1")
    file2.write_text("content2")

    logfiles = [str(file1), str(file2)]
    assert check_logfiles(logfiles) is True


def test_check_logfiles_one_does_not_exist(tmp_path):
    """Тест на check_logfiles при отсутствии файла"""
    file1 = tmp_path / "log1.txt"
    file1.write_text("content1")
    non_existent_file = tmp_path / "non_existent.log"

    logfiles = [str(file1), str(non_existent_file)]
    assert check_logfiles(logfiles) is False


def test_check_logfiles_one_is_directory(tmp_path):
    """Тест на check_logfiles при наличии директории вместо файла"""
    file1 = tmp_path / "log1.txt"
    file1.write_text("content1")
    dir1 = tmp_path / "log_dir"
    dir1.mkdir()

    logfiles = [str(file1), str(dir1)]
    assert check_logfiles(logfiles) is False
