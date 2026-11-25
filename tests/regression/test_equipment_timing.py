"""Test the ServiceEquipment class."""

from __future__ import annotations

import pandas as pd
import pytest

from wombat.windfarm import Windfarm
from wombat.core.environment import WombatEnvironment
from wombat.core.data_classes import Maintenance
from wombat.core.repair_management import RepairManager
from wombat.core.service_equipment import ServiceEquipment


def test_onsite_scheduled_equipment_logic(env_setup_full_profile):
    """Test the simulation logic of a scheduled CTV."""
    env = env_setup_full_profile
    manager = RepairManager(env)
    windfarm = Windfarm(env, "layout_simulation.csv", manager)

    ctv = ServiceEquipment(env, windfarm, manager, "ctv.yaml")
    ctv.finish_setup_with_environment_variables()
    fsv = ServiceEquipment(env, windfarm, manager, "fsv_scheduled.yaml")
    fsv.finish_setup_with_environment_variables()
    hlv = ServiceEquipment(env, windfarm, manager, "hlv_scheduled.yaml")
    hlv.finish_setup_with_environment_variables()

    # Start the simulation to ensure everything is in place as required
    env.run(1)
    assert (
        ctv.at_port
        is ctv.at_site
        is ctv.at_system
        is ctv.transferring_crew
        is ctv.enroute
        is ctv.onsite
        is False
    )
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.transferring_crew
        is fsv.enroute
        is fsv.onsite
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.transferring_crew
        is hlv.enroute
        is hlv.onsite
        is False
    )

    # Fast-forward to the start of the environment workshift to ensure all are
    # non-operational (CTV has no tasks, nor mobilization to check)
    env.run(7)
    assert (
        ctv.at_port
        is ctv.at_site
        is ctv.at_system
        is ctv.transferring_crew
        is ctv.enroute
        is ctv.onsite
        is False
    )
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.transferring_crew
        is fsv.enroute
        is fsv.onsite
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.transferring_crew
        is hlv.enroute
        is hlv.onsite
        is False
    )

    # Check that at Day 15 there are 6 turbine generator maintenance tasks requested
    timeout = 15 * 24 + 1
    env.run(timeout)
    assert len(manager.items) == 6
    assert all(isinstance(el.details, Maintenance) for el in manager.items)
    assert all(el.details.description == "ctv call" for el in manager.items)

    # The first maintenance task is at day 15 for the CTV, fast forward to this point in
    # time to check for operations to be running and inspect every step of the task
    timeout += 6 + 1 / 60  # Shift start is 7AM, but it's already 1AM
    env.run(timeout + 0.01)
    assert ctv.onsite is ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert not ctv.enroute
    assert ctv.current_system == "S00T1"
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.onsite
        is fsv.enroute
        is fsv.transferring_crew
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.onsite
        is hlv.enroute
        is hlv.transferring_crew
        is False
    )

    # Move to just before the 15 minute transfer is complete to ensure it hasn't ended
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T1"
    assert not ctv.enroute

    # Move to the end of the 15 minute to ensure the transfer is complete
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T1"
    assert ctv.enroute is ctv.at_port is ctv.transferring_crew is False

    # The weather window is clear on 1/16/2002, so there will not be weather delays, so
    # the CTV should be transferring the crew back onto the vessel
    timeout += 1
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.at_port is ctv.enroute is False
    assert ctv.current_system == "S00T1"
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.onsite
        is fsv.enroute
        is fsv.transferring_crew
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.onsite
        is hlv.enroute
        is hlv.transferring_crew
        is False
    )

    # Check the transfer is still progressing
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T1"
    assert ctv.enroute is ctv.at_port is False
    assert len(manager.items) == 5

    ## TURBINE 2 GENERATOR CTV repair

    # Move to the end of the 15 minute to ensure the transfer is complete, and there is
    # no travel time between site objects, so the crew should be transferring again
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.current_system == "S00T2"
    assert ctv.at_port is ctv.enroute is False

    # Move to just before the 15 minute transfer is complete to ensure it hasn't ended
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T2"
    assert ctv.at_port is ctv.enroute is False

    # Move to the end of the 15 minute to ensure the transfer is complete
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T2"
    assert ctv.enroute is ctv.at_port is ctv.transferring_crew is False

    # The weather window is clear on 1/16/2002, so there will not be weather delays, so
    # the CTV should be transferring the crew back onto the vessel
    timeout += 1
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.enroute is ctv.at_port is False
    assert ctv.current_system == "S00T2"
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.onsite
        is fsv.enroute
        is fsv.transferring_crew
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.onsite
        is hlv.enroute
        is hlv.transferring_crew
        is False
    )

    # Check the transfer is still progressing
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T2"
    assert ctv.enroute is ctv.at_port is False
    assert len(manager.items) == 4

    ## TURBINE 3 GENERATOR CTV repair

    # Move to the end of the 15 minute to ensure the transfer is complete, and there is
    # no travel time between site objects, so the crew should be transferring again
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.current_system == "S00T3"
    assert ctv.enroute is ctv.at_port is False

    # Move to just before the 15 minute transfer is complete to ensure it hasn't ended
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T3"
    assert ctv.enroute is ctv.at_port is False

    # Move to the end of the 15 minute to ensure the transfer is complete
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T3"
    assert ctv.enroute is ctv.at_port is ctv.transferring_crew is False

    # The weather window is clear on 1/16/2002, so there will not be weather delays, so
    # the CTV should be transferring the crew back onto the vessel
    timeout += 1
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.enroute is ctv.at_port is False
    assert ctv.current_system == "S00T3"
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.onsite
        is fsv.enroute
        is fsv.transferring_crew
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.onsite
        is hlv.enroute
        is hlv.transferring_crew
        is False
    )

    # Check the transfer is still progressing
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S00T3"
    assert ctv.enroute is ctv.at_port is False
    assert len(manager.items) == 3

    ## TURBINE 4 GENERATOR CTV repair

    # Move to the end of the 15 minute to ensure the transfer is complete, and there is
    # no travel time between site objects, so the crew should be transferring again
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.current_system == "S01T4"
    assert ctv.enroute is ctv.at_port is False

    # Move to just before the 15 minute transfer is complete to ensure it hasn't ended
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.onsite is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T4"
    assert ctv.enroute is ctv.at_port is False

    # Move to the end of the 15 minute to ensure the transfer is complete
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.onsite is ctv.at_system is True
    assert ctv.current_system == "S01T4"
    assert ctv.enroute is ctv.transferring_crew is False

    # The weather window is clear on 1/16/2002, so there will not be weather delays, so
    # the CTV should be transferring the crew back onto the vessel
    timeout += 1
    env.run(timeout)
    assert ctv.onsite is ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.enroute is ctv.at_port is False
    assert ctv.current_system == "S01T4"
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.onsite
        is fsv.enroute
        is fsv.transferring_crew
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.onsite
        is hlv.enroute
        is hlv.transferring_crew
        is False
    )

    # Check the transfer is still progressing
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.onsite is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T4"
    assert ctv.enroute is ctv.at_port is False
    assert len(manager.items) == 2

    ## TURBINE 5 GENERATOR CTV repair

    # Move to the end of the 15 minute to ensure the transfer is complete, and there is
    # no travel time between site objects, so the crew should be transferring again
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.onsite is ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.current_system == "S01T5"
    assert ctv.enroute is ctv.at_port is False

    # Move to just before the 15 minute transfer is complete to ensure it hasn't ended
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.onsite is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T5"
    assert ctv.enroute is ctv.at_port is False

    # Move to the end of the 15 minute to ensure the transfer is complete
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.onsite is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T5"
    assert ctv.enroute is ctv.at_port is ctv.transferring_crew is False

    # The weather window is clear on 1/16/2002, so there will not be weather delays, so
    # the CTV should be transferring the crew back onto the vessel
    timeout += 1
    env.run(timeout)
    assert ctv.onsite is ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.enroute is ctv.at_port is False
    assert ctv.current_system == "S01T5"
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.onsite
        is fsv.enroute
        is fsv.transferring_crew
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.onsite
        is hlv.enroute
        is hlv.transferring_crew
        is False
    )

    # Check the transfer is still progressing
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.onsite is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T5"
    assert ctv.enroute is ctv.at_port is False
    assert len(manager.items) == 1

    ## TURBINE 6 GENERATOR CTV repair

    # Move to the end of the 15 minute to ensure the transfer is complete, and there is
    # no travel time between site objects, so the crew should be transferring again
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.onsite is ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.current_system == "S01T6"
    assert ctv.enroute is ctv.at_port is False

    # Move to just before the 15 minute transfer is complete to ensure it hasn't ended
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.onsite is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T6"
    assert ctv.enroute is ctv.at_port is False

    # Move to the end of the 15 minute to ensure the transfer is complete
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T6"
    assert ctv.enroute is ctv.transferring_crew is False

    # The weather window is clear on 1/16/2002, so there will not be weather delays, so
    # the CTV should be transferring the crew back onto the vessel
    timeout += 1
    env.run(timeout)
    assert ctv.onsite is ctv.at_site is ctv.at_system is ctv.transferring_crew is True
    assert ctv.enroute is ctv.at_port is False
    assert ctv.current_system == "S01T6"
    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.onsite
        is fsv.enroute
        is fsv.transferring_crew
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.onsite
        is hlv.enroute
        is hlv.transferring_crew
        is False
    )

    # Check the transfer is still progressing
    timeout += 13 / 60
    env.run(timeout)
    assert ctv.transferring_crew is ctv.onsite is ctv.at_site is ctv.at_system is True
    assert ctv.current_system == "S01T6"
    assert ctv.enroute is ctv.at_port is False
    assert len(manager.items) == 0

    # The CTV process will repeat every 15 days (as this is a maintenance task), but no
    # more events will be checked as this process is considered "vetted".
    timeout += 2 / 60
    env.run(timeout)
    assert ctv.at_port and ctv.onsite
    assert ctv.current_system is None
    assert (
        ctv.at_site
        is ctv.transferring_crew
        is ctv.at_site
        is ctv.enroute
        is ctv.at_system
        is False
    )

    current = env.simulation_time
    assert current.date().day == 16
    assert current.date().month == 1
    assert current.date().year == 2002
    assert current.hour == 16
    assert current.minute == 1


@pytest.fixture
def scheduled_equipment_environment(tmp_path, monkeypatch, workday_start):
    """Provide hourly weather with a one-hour interruption during the first job."""
    weather = pd.DataFrame(
        {
            "datetime": pd.date_range("2002-01-01", periods=6 * 24, freq="h"),
            "windspeed": 5.0,
            "waveheight": 0.5,
        }
    )
    weather.loc[2 * 24 + workday_start + 2, "waveheight"] = 3.0
    weather_dir = tmp_path / "weather"
    weather_dir.mkdir()
    weather.to_csv(weather_dir / "scheduled_equipment.csv", index=False)
    env = WombatEnvironment(
        data_dir=tmp_path,
        weather_file="scheduled_equipment.csv",
        workday_start=8,
        workday_end=16,
    )
    # With one vessel, no dispatch jitter is needed to break ties.
    monkeypatch.setattr(env, "get_random_seconds", lambda **_: 0.0)
    yield env
    env.cleanup_log_files()


@pytest.mark.parametrize(
    ("capability", "workday_start", "workday_end", "first_completion_offset"),
    [
        pytest.param("LCN", 8, 16, 26.5, id="heavy-lift-vessel"),
        pytest.param("SCN", 0, 24, 10.0, id="field-support-vessel"),
    ],
)
def test_scheduled_equipment_logic(
    scheduled_equipment_environment,
    capability,
    workday_start,
    workday_end,
    first_completion_offset,
):
    """Follow scheduled mobilization, interrupted maintenance, and demobilization."""
    env = scheduled_equipment_environment
    manager = RepairManager(env)
    layout = pd.DataFrame.from_records(
        [
            ("OSS1", "OSS1", "OSS1", "substation", 0, 0, "substation", "cable"),
            ("WTG1", "OSS1", "WTG1", "turbine", 0, 0, "turbine", "cable"),
            ("WTG2", "OSS1", "WTG2", "turbine", 0, 1, "turbine", "cable"),
        ],
        columns=[
            "id",
            "substation_id",
            "name",
            "type",
            "string",
            "order",
            "subassembly",
            "upstream_cable",
        ],
    )
    # Only the maintenance requests submitted below can trigger vessel work.
    windfarm = Windfarm(
        env,
        layout,
        manager,
        turbines={
            "turbine": {
                "capacity_kw": 3000,
                "capex_kw": 0,
                "generator": {"name": "generator", "maintenance": [], "failures": []},
            }
        },
        substations={
            "substation": {
                "capacity_kw": 0,
                "capex_kw": 0,
                "transformer": {
                    "name": "transformer",
                    "maintenance": [],
                    "failures": [],
                },
            }
        },
        cables={"cable": {"name": "cable", "maintenance": [], "failures": []}},
    )
    vessel = ServiceEquipment(
        env,
        windfarm,
        manager,
        {
            "name": "Scheduled vessel",
            "equipment_rate": 0,
            "n_crews": 1,
            "crew": {
                "day_rate": 0,
                "n_day_rate": 0,
                "hourly_rate": 0,
                "n_hourly_rate": 0,
            },
            "capability": capability,
            "speed": 10,
            "max_windspeed_transport": 10,
            "max_windspeed_repair": 10,
            "max_waveheight_transport": 2,
            "max_waveheight_repair": 2,
            "crew_transfer_time": 0.25,
            "mobilization_days": 1,
            "start_year": 2002,
            "start_month": 1,
            "start_day": 3,
            "end_year": 2002,
            "end_month": 1,
            "end_day": 4,
            "workday_start": workday_start,
            "workday_end": workday_end,
            "strategy": "scheduled",
        },
    )
    vessel.finish_setup_with_environment_variables()

    for turbine, hours in [("WTG1", 8.5), ("WTG2", 2)]:
        windfarm.system(turbine).generator.trigger_request(
            Maintenance(
                time=hours,
                materials=0,
                frequency=0,
                service_equipment=capability,
                system_value=0,
            )
        )
    first, second = manager.items

    mobilization_start = 24 + workday_start
    first_shift = mobilization_start + 24
    margin = 1 / 60  # Observe both sides of each event.
    env.run(until=mobilization_start - margin)
    assert not vessel.enroute and not vessel.onsite
    env.run(until=mobilization_start + margin)
    assert vessel.enroute and not vessel.onsite
    env.run(until=first_shift - margin)
    assert vessel.enroute and not vessel.onsite
    env.run(until=first_shift + margin)
    assert vessel.onsite and vessel.transferring_crew and not vessel.enroute
    assert vessel.current_system == first.system_id

    # Continuous work ends 8.5 + 1 + 2 * 0.25 hours after arrival.
    # The day shift does 6.5 hours of work by 16:00 and finishes the
    # remaining two hours, plus crew transfers, on the next shift.
    completion = first_shift + first_completion_offset
    env.run(until=completion - margin)
    assert manager.completed_requests.items == []
    env.run(until=completion + margin)
    assert manager.completed_requests.items == [first]

    env.run(until=5 * 24)
    assert manager.completed_requests.items == [first, second]
    assert not manager.items
    assert not manager.in_process_requests.items
    assert not vessel.onsite and not vessel.enroute
    assert vessel.current_system is None

    events = env.load_events_log_dataframe()
    first_job = events.loc[events.request_id == first.request_id]
    work = first_job.loc[first_job.action == "maintenance", "duration"]
    assert work.sum() == pytest.approx(first.details.time)
    weather_delays = first_job.loc[first_job.additional == "weather delay"]
    assert weather_delays.env_time.tolist() == [pytest.approx(first_shift + 2)]
    assert weather_delays.duration.tolist() == [pytest.approx(1.0)]


def test_unscheduled_service_equipment_call(env_setup_full_profile):
    """Tests the calling of downtime-based and requests-based service equipment. This
    test will only consider that the equipment is mobilized when required, arrives at
    site, and leaves as the previous tests will cover repair logics.
    """
    env = env_setup_full_profile
    manager = RepairManager(env)
    windfarm = Windfarm(env, "layout_simulation.csv", manager)

    # ctv = ServiceEquipment(env, windfarm, manager, "ctv.yaml")
    fsv = ServiceEquipment(env, windfarm, manager, "fsv_requests.yaml")
    fsv.finish_setup_with_environment_variables()
    hlv = ServiceEquipment(env, windfarm, manager, "hlv_downtime.yaml")
    hlv.finish_setup_with_environment_variables()

    # Start the simulation to ensure everything is in place as required
    env.run(1)

    # for system in windfarm.system_list:
    #     system = windfarm.system(system)
    #     for pname, p in system.subassemblies[0].processes.items():
    #         if not isinstance(pname, tuple):
    #             continue
    #         if pname[1] != "catastrophic failure":
    #             continue
    #         print(system.id, pname, f"{p._target._delay:,.10f}")

    assert (
        fsv.at_port
        is fsv.at_site
        is fsv.at_system
        is fsv.transferring_crew
        is fsv.enroute
        is fsv.onsite
        is False
    )
    assert (
        hlv.at_port
        is hlv.at_site
        is hlv.at_system
        is hlv.transferring_crew
        is hlv.enroute
        is hlv.onsite
        is False
    )

    # The FSV has a 10 request threshold, with a request being submitted simultaneously
    # by each turbine every 25 days, so at day 50, the FSV will be mobilized
    timeout = 50 * 24 + 1 / 60
    env.run(timeout)
    assert fsv.enroute
    assert (
        fsv.transferring_crew
        is fsv.at_system
        is fsv.at_site
        is fsv.onsite
        is fsv.at_port
        is False
    )
    assert fsv.current_system is None

    # After 21 days the FSV will arrive at site, but have to wait until the start of the
    # work shift before repairs can happen
    timeout += 21 * 24
    env.run(timeout)
    assert fsv.at_port is fsv.onsite is True
    assert fsv.transferring_crew is fsv.at_system is fsv.at_site is fsv.enroute is False
    assert fsv.current_system is None

    # Check that the FSV is working at the start of the work shift
    timeout += 9
    env.run(timeout)
    assert fsv.onsite is fsv.at_site is fsv.transferring_crew is fsv.at_system is True
    assert fsv.at_port is fsv.enroute is False
    assert fsv.current_system == "S00T1"

    # The FSV should no longer be on site after 28 days, plus the time to finish the
    # repair that it's started
    timeout += 28 * 24 + 2 + 1  # 28 days + 2 hour repair + 1 hour in crew transfer
    env.run(timeout)
    assert (
        fsv.transferring_crew
        is fsv.at_system
        is fsv.onsite
        is fsv.at_site
        is fsv.at_port
        is fsv.enroute
        is False
    )
    assert fsv.current_system is None

    # The first HLV call is at 14012.2435309168 hours when S00T2's generator has a
    # catastrophic failure putting the windfarm at 83.3% operations, which is less than
    # the 90% threshold. However, because the timing will be delayed during repairs,
    # realized timeout will be at 14185.753253
    request_time = 14084.24
    timeout = request_time + 1 / 60
    env.run(timeout)
    # For checking in on the actual timing when it eventually changes
    # df = env.load_events_log_dataframe()
    # print(
    #     df.loc[
    #         df.agent == "Heavy Lift Vessel",
    #         [
    #             "env_datetime", "env_time", "agent", "action", "reason", "additional",
    #             "duration", "system_id", "part_id", "request_id"
    #         ]
    #     ].tail(20).to_string()
    # )
    assert hlv.enroute
    assert (
        hlv.transferring_crew
        is hlv.at_system
        is hlv.at_site
        is hlv.onsite
        is hlv.at_port
        is False
    )
    assert hlv.current_system is None

    # Test that the HLV was successfully mobilized
    timeout += 60 * 24
    env.run(timeout)
    assert hlv.at_port
    assert not hlv.enroute

    timeout += 52.25
    env.run(timeout)
    assert hlv.transferring_crew is hlv.at_site is hlv.at_system is hlv.onsite is True
    assert hlv.enroute is hlv.at_port is False
    assert hlv.current_system == "S00T1"

    # Ensure it's still here at the end, accounting for completing its last request
    timeout = request_time + 60 * 24 + 30 * 24 + 1.25
    env.run(timeout)
    assert hlv.onsite is hlv.at_site is hlv.at_system is True
    assert hlv.transferring_crew is hlv.at_port is hlv.enroute is False
    assert hlv.current_system == "S00T1"

    # Check that it's gone
    timeout += 0.02
    env.run(timeout)
    assert hlv.onsite is False
