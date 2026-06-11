#! /usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = "Alan Loh"
__copyright__ = "Copyright 2026, frb_autoschedule"
__credits__ = ["Alan Loh"]
__maintainer__ = "Alan"
__email__ = "alan.loh@obspm.fr"
__status__ = "Production"
__all__ = [
    "build_observation_blocks",
    "schedule_from_vcr",
    "book_observations",
    "plot_schedule"
]


from astropy.time import TimeDelta, Time
import astropy.units as u
from astropy.coordinates import SkyCoord

import numpy as np
import operator
from ics import Event
from typing import List, Tuple
import logging
log = logging.getLogger("frb_autoschedule")


from nenupy.schedule import (
    Schedule,
    ObsBlock,
    ReservedBlock,
    ESTarget,
    Constraints,
    ElevationCnst,
    MeridianTransitCnst,
    SolarProximityCnst,
    UTCHourCnst
)
from nenupy.schedule.open_time import NenuCalendar, NenuEvent

from frb_autoschedule import KP_CODE, SCHEDULE_DT


# ============================================================= #
# ----------------- build_observation_blocks ------------------ #
def build_observation_blocks(source_dict: dict, time_min: Time, time_max: Time) -> ObsBlock:
    """Construct the set of observation blocks request to be passed to nenupy scheduler.

    Parameters
    ----------
    source_dict : dict
        Source dictionnary containing the list of all sources and their properties to observed.
    time_min : Time
        Starting time of the schedule aimed ot be populated by the observation blocks.
        This is required while defining observation blocks related to periodic target for whiche a starting time of the cycle is defined in the JSON.
    time_max : Time
        End time of the schedule.

    Returns
    -------
    ObsBlock
        Observation blocks
    """

    frb_blocks = []

    for frb, config in source_dict.items():

        frb_target = ESTarget(SkyCoord(ra=config["ra"], dec=config["dec"], unit=(u.hourangle, u.deg)))

        if "periodicity_jd" in config:

            # Find the first occurence of the periodic cycle that overlaps with the schedule
            # And stop to optimize the number of blocks defined.
            cycle_start = Time(config["periodicity_start"])
            periodicity = TimeDelta(config["periodicity_jd"], format="jd")
            number_of_cycles_until_start = int(np.floor((time_min - cycle_start).jd / periodicity.jd))
            start = cycle_start + (number_of_cycles_until_start) * periodicity
            stop = time_max + periodicity

            blk = ObsBlock(
                name=frb,
                program=KP_CODE,
                target=frb_target,
                duration=TimeDelta(config["duration_hours"] * 3600, format="sec"),
                constraints=Constraints(
                    ElevationCnst(elevationMin=config["min_elevation_deg"] * u.deg, scale_elevation=True, weight=1),
                    SolarProximityCnst(closer=False, min_separation_deg=config["min_angular_distance_from_sun_deg"])
                )
            )
            blks = blk.periodic_observation(
                start_time=start,
                stop_time=stop,
                periodicity=TimeDelta(config["periodicity_jd"], format="jd"),
                tolerance=TimeDelta(config["tolerance_jd"], format="jd"),
                repetition_max=config["repetitions"] + 1 # + 1 because we are starting the cycle before the schedule start
            )

            frb_blocks.append(blks)

        else:

            blk = ObsBlock(
                name=frb,
                program=KP_CODE,
                target=frb_target,
                duration=TimeDelta(config["duration_hours"] * 3600, format="sec"),
                # max_extended_duration=TimeDelta(source_dict[frb]["nominal_obs_time"] * 60, format="sec"),
                constraints=Constraints(
                    ElevationCnst(elevationMin=config["min_elevation_deg"] * u.deg, scale_elevation=True, weight=1),
                    SolarProximityCnst(closer=False, min_separation_deg=config["min_angular_distance_from_sun_deg"])
                )
            )

            frb_blocks.append(blk * config["repetitions"])

    return sum(frb_blocks)


# ============================================================= #
# --------------------- schedule_from_vcr --------------------- #
def schedule_from_vcr(
        start_time: Time,
        stop_time: Time,
        vcr_current_booking: str = None,
        constrained_obs_file: str = None
    ) -> Schedule:
    """Computes a list of free booking slots from the current VCR booking schedule.

    The rules are:
    * No booking less than MIN_DURATION (by default 1 hour)
    * No booking in the UTC interval MID_DAY_START_HOUR -- MID_DAY_STOP_HOUR unless Saturday or Sunday

    Parameters
    ----------
    vcr_current_booking : str
        VCR booking file (that can be downloaded via 'https://gui-nenufar.obs-nancay.fr/' > 'Booking' > 'Current Booking.csv')
    constrained_obs_file: str
        Excel file containing time slots to be converted to ReservedBlocks.
    start_time : Time
        Start time at which a new booking will be considered
    stop_time : Time
        Stop time at which a new booking will be considered

    Returns
    -------
    List[Tuple[Time, Time]]
        List of bookings in the shape [(start_0, stop_0), (start_1, stop_1), ...].
    """
    # Generate an instance of Schedule at the SCHEDULE_DT resolution and 
    # in between start and stop times.
    schedule = Schedule(time_min=start_time, time_max=stop_time, dt=SCHEDULE_DT)

    if not (vcr_current_booking is None):
        schedule.match_booking(
            booking_file=vcr_current_booking,
            key_program=KP_CODE
        )

    if not (constrained_obs_file is None):
        contrained_calendar = NenuCalendar.from_xls(constrained_obs_file)
        for evt in contrained_calendar.events:
            schedule.insert(
                ReservedBlock(
                    time_min=Time(evt.event.begin.datetime, format="datetime"),
                    time_max=Time(evt.event.end.datetime, format="datetime")
                )
            )

    return schedule


# ============================================================= #
# --------------------- book_observations --------------------- #
def book_observations(schedule: Schedule, observation_blocks: ObsBlock, day_hours: float, night_hours: float) -> Schedule:

    schedule.insert(observation_blocks)

    schedule.book(
        very_strict=False,
        reset_booking=True,
        day_hours=day_hours,
        night_hours=night_hours,
        sort_by_availability=True
    )

    results = schedule.export()
    log.info(f"Schedule proposed:\n{results}")

    return schedule


# ============================================================= #
# ----------------------- plot_schedule ----------------------- #
def plot_schedule(schedule: Schedule, fig_name: str) -> None:
    events = []
    for blk in schedule.observation_blocks:
        if not blk.isBooked:
            continue
        event = Event()
        event.name = blk.name
        event.begin = blk.time_min.datetime
        event.end = blk.time_max.datetime
        events.append(
            NenuEvent(
                event=event,
                kp_name=KP_CODE,
                color="tab:blue"
            )
        )
    cal = NenuCalendar(events)
    cal.month_plot(fig_name=fig_name)