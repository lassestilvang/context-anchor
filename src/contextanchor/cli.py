"""CLI entry point for ContextAnchor."""

import click


@click.group()
@click.version_option()
def main() -> None:
    """ContextAnchor: Developer workflow state management system."""
    pass


if __name__ == "__main__":
    main()
