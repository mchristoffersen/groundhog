# Example Groundhog GPR processor
import argparse

import ghog


def cli():
    parser = argparse.ArgumentParser(description="Process Groundhog GPR data")
    parser.add_argument("files", nargs="+", help="file(s) to convert")

    return parser.parse_args()


def main():
    args = cli()
    for file in args.files:
        # Load
        data = ghog.load(file)

        # Fast time filter (edges in Hz)
        data = ghog.filt(data, (0.5e6, 4e6), axis=0)

        # NMO
        data = ghog.nmo(data, 100)

        # Restack
        data = ghog.restack(data, 5)

        # Slow time filter (edges in wavenumber)
        data = ghog.filt(data, (1 / 1000, 1 / 200), axis=1)

        # Migrate
        data = ghog.stolt(data)

        # Save
        ghog.save(file, data, group="restack")


if __name__ == "__main__":
    main()
