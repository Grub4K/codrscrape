# codrscrape
A scraper for the website [callofdutyrepo.com](https://www.callofdutyrepo.com/).

## Installing / Running
Use `pip` to install the package (`pip install .`)
then run using `python -m codrscrape`.
Alternatively download the required dependencies through poetry
(`poetry install --no-dev`) then run using `poetry run python -m codrscrape`.

See `codrscrape --help` for more info on the available options on how to run.

## Building
Download the required dependencies (`poetry install`)
then build using `poetry run pyinstaller codrscrape.spec`.
This will create a `dist/` directory where a `codrscrape/`
directory containing the executable can be found.
Alternatively run
`poetry run pyinstaller --onefile --copy-metadata codrscrape --name codrscrape codrscrape/__main__.py`
or provide your own options.
