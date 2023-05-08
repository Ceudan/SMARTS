from itertools import product
from pathlib import Path

from smarts.sstudio.genscenario import gen_scenario
from smarts.sstudio.types import (
    EndlessMission,
    MapSpec,
    Scenario,
    SocialAgentActor,
    TrapEntryTactic,
    Via,
)

begin_lane_idx = (0, 1)
first_via = (0, 1)
second_via = (0, 1)
third_via = (0, 1)
end_road = ["E_left", "E_right"]

route_comb = product(begin_lane_idx, first_via, second_via, third_via, end_road)

leader_mission = []
for route in route_comb:
    leader_mission.append(
        EndlessMission(
            begin=("E0", route[0], 20),
            via=(
                Via(
                    "E0",
                    lane_offset=100,
                    lane_index=route[1],
                    required_speed=13,
                ),
                Via(
                    "E0",
                    lane_offset=170,
                    lane_index=route[2],
                    required_speed=13,
                ),
                Via(
                    route[4],
                    lane_offset=30,
                    lane_index=route[3],
                    required_speed=13,
                ),
            ),
        )
    )

leader_actor = [
    SocialAgentActor(
        name="777777",
        agent_locator="zoo.policies:chase-via-points-agent-v0",
        initial_speed=0,
    )
]

ego_missions = [
    EndlessMission(
        begin=("E0", 0, 5),
        entry_tactic=TrapEntryTactic(wait_to_hijack_limit_s=0, default_entry_speed=0),
    )
]

scenario = Scenario(
    ego_missions=ego_missions,
    social_agent_missions={"leader": (leader_actor, leader_mission)},
    map_spec=MapSpec(
        source=Path(__file__).parent.absolute(),
        lanepoint_spacing=1.0,
    ),
)

gen_scenario(
    scenario=scenario,
    output_dir=Path(__file__).parent,
)
