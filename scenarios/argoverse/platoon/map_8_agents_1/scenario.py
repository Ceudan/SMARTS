from pathlib import Path
from itertools import product
from pathlib import Path
from smarts.sstudio.types import (
    Route,
    Mission,
    SocialAgentActor,
    EndlessMission,
    TrapEntryTactic,
)

from smarts.sstudio import gen_scenario
from smarts.sstudio import types as t

# scenario_path is a directory with the following structure:
# /path/to/dataset/{scenario_id}
# ├── log_map_archive_{scenario_id}.json
# └── scenario_{scenario_id}.parquet

PATH = "/home/kyber/argoverse"
scenario_id = "617a2f19-867c-44f6-829d-078bdf375f56"  # e.g. "0000b6ab-e100-4f6b-aee8-b520b57c0530"
scenario_path = Path(PATH) / scenario_id  # e.g. Path("/home/user/argoverse/train/") / scenario_id

start_road = "road-353630756"
lane_idx = (0,)
end_road = ("road-353630856-353630893","road-353628670-353628461","road-353629511","road-353629710","road-353629847")

route_comb = product(lane_idx,end_road)
leader_mission = []
ego_missions=[]
for route in route_comb:
    leader_mission.append(
        Mission(Route(
            begin=(start_road,0,10),end=(route[1],0,"max")),
        )
    )
    ego_missions.append(
        EndlessMission(
            begin=(start_road,0,5), 
            entry_tactic=TrapEntryTactic(
                wait_to_hijack_limit_s=0,
                default_entry_speed=1,
            ),
        )
    ) 
leader_actor = [
    SocialAgentActor(
        name="Leader-007",
        agent_locator="zoo.policies:chase-via-points-agent-v0",
        initial_speed=1,
    )
]


traffic_histories = [
    t.TrafficHistoryDataset(
        name=f"argoverse_{scenario_id}",
        source_type="Argoverse",
        input_path=scenario_path,
    )
]


gen_scenario(
    t.Scenario(
        social_agent_missions={"leader":(leader_actor, leader_mission)},
        ego_missions=ego_missions,
        map_spec=t.MapSpec(source=f"{scenario_path}", lanepoint_spacing=1.0),
        # traffic_histories=traffic_histories,
    ),
    output_dir=Path(__file__).parent,
)