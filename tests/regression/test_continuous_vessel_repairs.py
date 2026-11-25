"""Regression tests for in-situ work during a 24-hour vessel shift."""

import polars as pl
import pytest

from wombat.windfarm import Windfarm
from wombat.core.library import load_yaml
from wombat.core.data_classes import Maintenance
from wombat.core.repair_management import RepairManager
from wombat.core.service_equipment import ServiceEquipment


@pytest.mark.parametrize(
    ("maintenance_hours", "weather_delay_hours"),
    [
        pytest.param(9, 1, id="partial-work-after-weather-delay"),
        pytest.param(0.25, 0, id="shorter-than-crew-transfer-buffer"),
        pytest.param(9, 26, id="weather-delay-across-midnight"),
    ],
)
def test_continuous_vessel_keeps_maintenance_progress(
    env_setup, monkeypatch, maintenance_hours, weather_delay_hours
):
    """The vessel should complete exactly the requested work plus any weather delay."""
    env = env_setup
    arrival = 24  # Mobilize for one day starting at the beginning of the simulation.
    weather_delay_start = arrival + 2
    bad_weather = pl.int_range(pl.len()).is_between(
        weather_delay_start, weather_delay_start + weather_delay_hours, closed="left"
    )
    env.weather = env.weather.with_columns(
        windspeed=pl.lit(5.0),
        waveheight=pl.when(bad_weather).then(3.0).otherwise(0.5),
    )
    monkeypatch.setattr(env, "get_random_seconds", lambda **_: 0.0)

    manager = RepairManager(env)
    windfarm = Windfarm(env, "layout_simulation.csv", manager)
    equipment = load_yaml(env.data_dir / "vessels", "fsv_scheduled.yaml")
    equipment.update(
        start_month=1,
        start_day=2,
        end_month=1,
        end_day=4,
        end_year=2002,
        mobilization_days=1,
        crew_transfer_time=0.25,
    )
    vessel = ServiceEquipment(env, windfarm, manager, equipment)
    vessel.finish_setup_with_environment_variables()

    windfarm.system("S00T1").generator.trigger_request(
        Maintenance(
            time=maintenance_hours,
            frequency=0,
            materials=0,
            service_equipment="SCN",
            system_value=0,
        )
    )
    request = manager.items[0]
    env.run(until=72)

    events = env.load_events_log_dataframe()
    job = events.loc[events.request_id == request.request_id]
    assert job.loc[job.action == "maintenance", "duration"].sum() == pytest.approx(
        maintenance_hours
    )
    completion = arrival + maintenance_hours + weather_delay_hours + 0.5
    assert job.loc[job.action == "maintenance complete", "env_time"].tolist() == [
        pytest.approx(completion)
    ]
    assert manager.completed_requests.items == [request]
