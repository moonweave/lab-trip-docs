from .config import load_config
from .web import run


def main() -> None:
    config = load_config()
    run(config)


if __name__ == "__main__":
    main()

