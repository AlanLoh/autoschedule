__author__ = "Alan Loh"
__copyright__ = "Copyright 2026, frb_autoschedule"
__credits__ = ["Alan Loh"]
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Alan Loh"
__email__ = "alan.loh@obspm.fr"


import logging
import sys
import os
import json
from astropy.time import TimeDelta


# ============================================================= #
# ------------------- Logging configuration ------------------- #
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ============================================================= #
# ----------------------- load_frb_json ----------------------- #
def load_frb_json(json_file: str) -> dict:
    """Read a json file and extract a dictionnary of all sources within.
    This function also adds a new key 'skycoord' to every entry, corresponging to the celestial coordinates in astropy.coordinates.SkyCoord type.

    Parameters
    ----------
    json_file : str
        JSON file containing all the sources and their properties to be transformed in dictionnary.
            
    Returns
    -------
    dict
        Dictionnary of sources.
    """
    with open(json_file) as source_list:
        source_dict = json.load(source_list)

    return source_dict


# ============================================================= #
# ----------------- get_psr_calibration_dict ------------------ #
def get_psr_calibration_dict(source_dict: dict) -> dict:
    return {
        source: details for source, details in source_dict.items() if details["category"].lower() == "cal"
    }


# ============================================================= #
# ----------------- get_frb_calibration_dict ------------------ #
def get_frb_target_dict(source_dict: dict) -> dict:
    return {
        source: details for source, details in source_dict.items() if details["category"].lower() == "frb"
    }


# ============================================================= #
# ------------------------- Load data ------------------------- #
target_file = os.path.join(os.path.dirname(__file__), "LT05_targets.json")
sources_dict = load_frb_json(json_file=target_file)

FRB_DICT = get_frb_target_dict(sources_dict)
PSR_DICT = get_psr_calibration_dict(sources_dict)


# ============================================================= #
# --------------------- Global variables ---------------------- #
KP_CODE = "LT05"
SCHEDULE_DT = TimeDelta(10 * 60, format="sec")
