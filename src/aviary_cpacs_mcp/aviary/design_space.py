"""Design parameter metadata for the Aviary mission solver.

Adapted from cmudrc/aviary-mcp (Jessica Ezemba).
"""

DESIGN_PARAMETERS = [
    {
        "name": "Aircraft.Wing.ASPECT_RATIO",
        "category": "wing",
        "default": 11.22,
        "units": "unitless",
        "min": 7.0,
        "max": 14.0,
    },
    {
        "name": "Aircraft.Wing.AREA",
        "category": "wing",
        "default": 124.6,
        "units": "m^2",
        "min": 100.0,
        "max": 160.0,
    },
    {
        "name": "Aircraft.Wing.SWEEP",
        "category": "wing",
        "default": 25.0,
        "units": "deg",
        "min": 15.0,
        "max": 40.0,
    },
    {
        "name": "Aircraft.Wing.TAPER_RATIO",
        "category": "wing",
        "default": 0.278,
        "units": "unitless",
        "min": 0.15,
        "max": 0.45,
    },
    {
        "name": "Aircraft.Fuselage.LENGTH",
        "category": "fuselage",
        "default": 37.79,
        "units": "m",
        "min": 28.0,
        "max": 50.0,
    },
    {
        "name": "Aircraft.Engine.SCALE_FACTOR",
        "category": "engine",
        "default": 1.0,
        "units": "unitless",
        "min": 0.8,
        "max": 1.5,
    },
]

DEFAULT_MISSION_CONFIG = {
    "range_nmi": 1500,
    "num_passengers": 162,
    "cruise_mach": 0.785,
    "cruise_altitude_ft": 35000,
    "optimizer_max_iter": 200,
}

PASSENGER_MASS_KG = 90.7
MAX_PASSENGERS = 200
