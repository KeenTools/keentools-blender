import pytest
import keentools_facebuilder.pkt as pkt


def test_wrong_installations():
    with pytest.raises(FileNotFoundError):
        pkt.install_from_file('some/non/existing/file.zip')
    with pytest.raises(Exception):
        pkt.install_from_file(__file__)
    assert(not pkt.is_installed())


def test_uninstall():
    pkt.uninstall()
    assert(not pkt.is_installed())


def test_download_non_existing_version():
    with pytest.raises(Exception):
        pkt.install_from_download('1.0.1')


def test_non_loaded_uninstalled_load():
    if pkt.loaded():
        return
    pkt.uninstall()
    with pytest.raises(ImportError):
        pkt.module()


def test_download_latest_nightly():
    try:
        pkt.install_from_download(nightly=True)
    except Exception:
        # can fail with no network
        return
    assert(pkt.is_installed())
    pykeentools = pkt.module()
    assert(isinstance(pykeentools.__version__, str))
    pkt.uninstall()
