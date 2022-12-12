"""Console script for raptor."""
import sys
import yaml
from yaml.error import YAMLError
import click
from raptor.reports import Reports


@click.command()
@click.argument("infile", type=click.File("rb"), nargs=1)
def main(infile):
    try:
        content = infile.read()
        yobj = yaml.safe_load(content)
        report = Reports(**yobj)
        content = report.render()
        print(content)
    except YAMLError:
        print("Invalid config file!")


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
