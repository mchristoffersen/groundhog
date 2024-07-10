# groundhog
Control and processing software for a ground-based radar sounder using an impulse source and an Ettus N210 to receive.

## Control
Control code lives in the `control` directory. The `manual` directory contains the LaTeX source for an operation and maitnance manual.

## Processing

The processing software is set up as a Python library named `ghog` with a few command line tools. To install:
```
pip install git@https://github.com/mchristoffersen/groundhog.git
```
[Link to documentation](https://mchristoffersen.github.io/groundhog/). See the `examples` directory for a usage examples.
