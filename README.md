# FRB Autoschedule

Schedule FRBs listed in LT05_targets.json.

## Installation

[nenupy](https://nenupy.readthedocs.io/en/latest/) is a requirement:
```
pip install --upgrade https://github.com/AlanLoh/nenupy/tarball/master
```

Then, you may install the `autoschedule` package
```
pip install https://github.com/AlanLoh/autoschedule/tarball/master --upgrade
```

## Usage

To produce a schedule:
```
frbschedule -t0 2026-06-01T00:00:00 -t1 2026-12-01T00:00:00  -o /path/to/store/results/
```

