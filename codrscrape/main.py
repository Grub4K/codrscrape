import argparse
import itertools
import json
import logging
import shutil
from pathlib import Path, PurePosixPath

from codrscrape import info, pretty_log
from codrscrape.scraper import Scraper

logger = logging.getLogger(__name__)


def get_args():
    parser = argparse.ArgumentParser(
        prog=info.NAME,
        description=info.SUMMARY,
        epilog=info.__copyright__,
        add_help=False,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("urls", nargs="+", metavar="URL", help="a list urls to process")
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="provided urls are list urls, not mod/map urls",
    )
    parser.add_argument(
        "--path",
        "-p",
        type=Path,
        default="output/",
        help="base directory for the output",
    )
    parser.add_argument(
        "--archive",
        "-a",
        type=Path,
        default="output/archive.txt",
        help="a file to store processed entries so they will not be processed again",
    )
    parser.add_argument(
        "--write",
        "-w",
        action="store_true",
        help="write data to disk. This creates metadata.json, raw.html and the thumbnail + preview images",
    )
    misc_options = parser.add_argument_group("misc. options")
    misc_options.add_argument(
        "--help", "-h", action="help", help="show this help message and exit"
    )
    misc_options.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"{info.NAME} v{info.__version__}",
        help="show the version and exit",
    )
    misc_options.add_argument(
        "--to-screen",
        "-s",
        action="store_true",
        help="output log to the screen instead of a file",
    )
    misc_options.add_argument(
        "--debug", "-d", action="store_true", help="set the loglevel to debug"
    )
    return parser.parse_args()


def data_file_results(data, base_path):
    def file_result(name, source):
        suffix = PurePosixPath(source).suffix or ".jpg"
        result = base_path / f"{name}{suffix}"
        return result, source

    yield file_result("thumbnail", data["thumbnail"])
    for index, image in enumerate(data["images"], 1):
        yield file_result(f"image-{index}", image)


def _open(file, mode, encoding=None):
    logger.info(f"Writing to file '{file.as_posix()}'")
    return file.open(mode, encoding=encoding)


def write_results(data, raw_data, path, session):
    base_path = path.joinpath(data["type"], data["id"])
    base_path.mkdir(parents=True, exist_ok=True)

    with _open(base_path / "metadata.json", "w") as file:
        json.dump(data, file)

    with _open(base_path / "raw.html", "w", "utf8") as file:
        file.write(raw_data)

    for file, source in data_file_results(data, base_path):
        with (
            session.get(source, stream=True) as response,
            _open(file, "wb") as file,
        ):
            shutil.copyfileobj(response.raw, file)


def _real_main():
    args = get_args()

    file, stream = (False, True) if args.to_screen else (True, False)
    pretty_log.setup(file=file, stream=stream, debug=args.debug, name_length=25)

    # Read archive
    if isinstance(args.archive, Path):
        if not args.archive.is_file():
            args.archive.parent.mkdir(exist_ok=True, parents=True)
            args.archive.touch(exist_ok=True)
        with args.archive.open("r") as file:
            archive = set(map(str.strip, file))

        logger.info(f"Loaded {len(archive)} entries from archive")

    else:
        logger.warning("Not using archive file.")
        archive = set()

    # Scrape data
    scraper = Scraper()
    if args.list:
        urls = itertools.chain.from_iterable(map(scraper.extract_list, args.urls))
    else:
        urls = args.urls

    for url in urls:
        content_id = scraper.make_id(url)
        if content_id in archive:
            logger.info(f"{content_id}: Skipped, already in archive")
            continue
        try:
            data, raw_data = scraper.extract_single(url)
            logger.debug(f"{content_id}: Extracted data: {data}")
            if args.write:
                write_results(data, raw_data, args.path, scraper.session)
            else:
                print(json.dumps(data))

        except Exception:
            logger.exception(f"{content_id}: Unexpected Error while extracting")

        else:
            if args.archive:
                with args.archive.open("a") as file:
                    file.write(f"{content_id}\n")

            archive.add(content_id)
            logger.info(f"{content_id}: Done processing")


def run_main():
    try:
        _real_main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception:
        logger.exception("Unexpected error in main funcion")


if __name__ == "__main__":
    run_main()
