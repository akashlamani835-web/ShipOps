from app.connectivity.models import ConnectivityState
from app.connectivity.simulation import ConnectivitySimulation


def test_connectivity_simulation_runs_full_recovery_scenario():
    result = ConnectivitySimulation().run()

    assert result.initial_state == ConnectivityState.AVAILABLE
    assert result.degraded_state == ConnectivityState.DEGRADED
    assert result.outage_state == ConnectivityState.UNAVAILABLE
    assert result.recovered_state == ConnectivityState.AVAILABLE


def test_critical_traffic_continues_during_degradation():
    result = ConnectivitySimulation().run()

    assert result.critical_action_during_degradation == "transmit"


def test_bulk_traffic_is_deferred_during_degradation():
    result = ConnectivitySimulation().run()

    assert result.bulk_action_during_degradation == "queue"


def test_outage_causes_local_queueing():
    result = ConnectivitySimulation().run()

    assert result.outage_queued_requests == 1


def test_recovery_transmits_queued_traffic():
    result = ConnectivitySimulation().run()

    assert result.recovered_transmitted_requests == 2


def test_recovery_drains_the_queue():
    result = ConnectivitySimulation().run()

    assert result.final_queued_requests == 0


def test_simulation_reports_bandwidth_usage():
    result = ConnectivitySimulation().run()

    assert result.transmitted_kbps > 0
    assert result.queued_kbps > 0