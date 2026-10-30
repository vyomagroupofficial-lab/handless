# Custom hook for webrtcvad-wheels on Python 3.12
# The default hook in _pyinstaller_hooks_contrib calls copy_metadata('webrtcvad')
# which crashes because the distribution package is named 'webrtcvad-wheels'.
from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs('webrtcvad')
datas = []
hiddenimports = ['_webrtcvad']

