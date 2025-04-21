# nuitka-project: --onefile
# nuitka-project: --include-data-dir={MAIN_DIRECTORY}/app/data=app/data
# nuitka-project: --windows-console-mode=disable
# nuitka-project: --include-module=app.main

import uvicorn

uvicorn.run("app.main:app")