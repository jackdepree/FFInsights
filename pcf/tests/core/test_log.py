import logging

from pcf.core.log import MASK, MaskingFormatter, get_logger, setup_logging


def _record(msg, exc_info=None):
    return logging.LogRecord("pcf.test", logging.INFO, __file__, 1, msg, None, exc_info)


def test_masks_secret_in_message():
    fmt = MaskingFormatter(["abcdef123456"])
    out = fmt.format(_record("calling https://api.example.com/?apiKey=abcdef123456"))
    assert "abcdef123456" not in out
    assert MASK in out


def test_masks_secret_in_traceback():
    fmt = MaskingFormatter(["abcdef123456"])
    try:
        raise RuntimeError("request failed for key abcdef123456")
    except RuntimeError:
        import sys

        out = fmt.format(_record("boom", sys.exc_info()))
    assert "abcdef123456" not in out


def test_short_values_are_not_masked():
    # Too short to be a real key, and masking them would garble ordinary text.
    fmt = MaskingFormatter(["abc"])
    assert fmt.format(_record("abc")) == "abc"


def test_logger_output_is_masked(capsys):
    setup_logging("INFO", secrets=["secretvalue987"])
    get_logger("pcf.test").info("token is secretvalue987")
    err = capsys.readouterr().err
    assert "secretvalue987" not in err
    assert "token is ****" in err


def test_get_logger_names_under_pcf():
    assert get_logger("anything").name == "pcf.anything"
    assert get_logger("pcf.data").name == "pcf.data"
