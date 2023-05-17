import argparse
import pickle
import os
import shutil
import subprocess
from pathlib import Path
from smarts.core.sensors import EgoVehicleObservation
from smarts.dataset import traffic_histories_to_observations


class Task:
    """Defines different type of tasks.

    Args:
        raw_path (Path): The path to the raw dataset that is downloaded by the user.
        scenario_id (str): The scenario id of a scenario.
        scenario_path (Path): The path to where the scenario folder will be created.
    """

    def __init__(
        self,
        raw_path: Path,
        scenario_path: Path,
    ) -> None:
        self.raw_path = raw_path
        self.scenario_id = raw_path.name
        self.scenario_path = scenario_path
        self.temp_path = Path(self.scenario_path) / "temp"
        self.temp_scenario_path = Path(self.temp_path) / f"{self.scenario_id}_agents_1"
        self._create_temp_scenario()

    def _create_temp_scenario(self):
        """
        Creates the temp scenario folder and the corresponding scenario.py file in current directory.
        """
        print("Initializing the temp scenario file...")
        if os.path.exists(self.temp_scenario_path):
            shutil.rmtree(self.temp_scenario_path)
        os.mkdir(self.temp_scenario_path)
        temp_file_path = self.temp_scenario_path / "scenario.py"
        with temp_file_path.open("w", encoding="utf-8") as f:
            with open("scenario_quickstart/scenario_template.txt", "r") as t:
                for line in t.readlines():
                    f.write(line)

    def preview(self):
        """
        Previews the scenario without spawning any ego agent.
        """
        print("Previewing the scenario...")
        subprocess.run(
            ["scl", "run", "--envision", "examples/egoless.py", self.temp_scenario_path]
        )

    def extract_ego_mission(self):
        """
        Extracts the ego mission(s) by:
        - inputting the id of vehicle of interest(voi) for hijacking.
        - extracting the begin and end position of voi from the pkl file.
        """
        while True:
            try:
                vehicle_id = input("Enter the vehicle id of interest: ")
                recorder = traffic_histories_to_observations.ObservationRecorder(
                    scenario=self.temp_scenario_path,
                    output_dir=self.temp_scenario_path,
                    seed=42,
                    start_time=None,
                    end_time=None,
                )
                recorder.collect(vehicles_with_sensors=[int(vehicle_id)], headless=True)

                # Load pickle file of observations
                with open(
                    f"{self.temp_scenario_path}/Agent-history-vehicle-{vehicle_id}.pkl",
                    "rb",
                ) as pf:
                    data = pickle.load(pf)
                break
            except FileNotFoundError:
                print("Vehicle id not found. Try again.")
        # Sort the keys of the dict so we can select the first and last times
        keys = list(data.keys())
        keys.sort()

        # Extract vehicle state from first and last times
        first_time = keys[0]
        last_time = keys[-1]
        first_state: EgoVehicleObservation = data[first_time].ego_vehicle_state
        last_state: EgoVehicleObservation = data[last_time].ego_vehicle_state
        self._write_mission(first_state, last_state)

    def _write_mission(
        self,
        first_state,
        last_state,
    ):
        """
        Writes the ego mission(s) to the template scenario.py.
        """
        with self.temp_file_path.open("r+") as f:
            contents = f.readlines()
            for index, line in enumerate(contents):
                if line.startswith("gen_scenario"):
                    ego_mission = f"ego_mission = [t.Mission(route=t.Route(begin=({first_state.road_id}, {first_state.lane_index}, {round(first_state.lane_position.s, 1)}), end=('{last_state.road_id}', {last_state.lane_index}, {round(last_state.lane_position.s, 1)})))]"
                    contents.insert(index - 1, f"\n{ego_mission}\n")
                    indent = "    "
                    contents.insert(
                        index + 2, f"\n{indent*2}'ego_missions=ego_mission',\n"
                    )
                    break
        f.seek(0)
        f.writelines(contents)
        subprocess.run(["black", self.temp_file_path])

    def scenario_check(self):
        """
        Opens the temp scenario file and starts the simulation for checking,
        repeat until it looks good, and then move it to the actual scenario path.
        """
        print("Opening the scenario file...")
        subprocess.run(["code", self.temp_file_path])
        input("Please check the file, if everything look ok, press Enter to continue..")
        while True:
            subprocess.run(
                [
                    "scl",
                    "run",
                    "--envision",
                    "examples/control/chase_via_points.py",
                    self.temp_scenario_path,
                ]
            )

            vis = input(
                "Does it look good? Press any key to continue, otherwise press 'n': "
            )
            if vis != "n":
                break
            else:
                print("replay the scenario")
        shutil.move(self.temp_scenario_path, self.scenario_path)
        shutil.rmtree(self.temp_path)

    def run(self):
        self.preview()
        self.extract_ego_mission()
        self.scenario_check()


class Cruising(Task):
    def __init__(self, raw_path: Path, scenario_path: Path) -> None:
        super().__init__(raw_path, scenario_path)


class Turning(Task):
    def __init__(self, raw_path: Path, scenario_path: Path) -> None:
        super().__init__(raw_path, scenario_path)


class Following(Task):
    def __init__(self, raw_path: Path, scenario_path: Path) -> None:
        super().__init__(raw_path, scenario_path)

    def extract_ego_mission(self):
        """
        Extracts the ego mission(s) by:
        - inputting the id of vehicle of interest(voi) for hijacking.
        - extracting the begin position of voi from the pkl file.
        - specifying the vehicle id as the leader to be followed
        """
        while True:
            try:
                vehicle_id = input("Enter the vehicle id of interest: ")
                recorder = traffic_histories_to_observations.ObservationRecorder(
                    scenario=self.temp_scenario_path,
                    output_dir=self.temp_scenario_path,
                    seed=42,
                    start_time=None,
                    end_time=None,
                )
                recorder.collect(vehicles_with_sensors=[int(vehicle_id)], headless=True)

                # Load pickle file of observations
                with open(
                    f"{self.temp_scenario_path}/Agent-history-vehicle-{vehicle_id}.pkl",
                    "rb",
                ) as pf:
                    data = pickle.load(pf)
                break
            except FileNotFoundError:
                print("Vehicle id not found. Try again.")
        # Sort the keys of the dict so we can select the first and last times
        keys = list(data.keys())
        keys.sort()

        # Extract vehicle state from first and last times
        first_time = keys[0]
        first_state: EgoVehicleObservation = data[first_time].ego_vehicle_state
        leader_id = input("Enter the leader id: ")
        self._write_mission(first_state, leader_id)

    def _write_mission(self, first_state, leader_id):
        """
        Writes the ego mission(s) to the template scenario.py.
        """
        with self.temp_file_path.open("r+") as f:
            contents = f.readlines()
            for index, line in enumerate(contents):
                if line.startswith("gen_scenario"):
                    ego_mission_field = f"ego_mission = [t.EndlessMission(begin=({first_state.road_id}, {first_state.lane_index}, {round(first_state.lane_position.s, 1)}))]"
                    leader_id_field = f"history-vehicle-{leader_id}"
                    contents.insert(index - 1, f"\n{ego_mission_field}\n")
                    contents.insert(index - 1, f"\n{leader_id_field}\n")
                    indent = "    "
                    contents.insert(
                        index + 2, f"\n{indent*2}'ego_missions=ego_mission',\n"
                    )
                    contents.insert(
                        index + 3,
                        f"\n{indent*2}'t.ScenarioMetadata(leader_id, Colors.Blue)',\n",
                    )
                    break
        f.seek(0)
        f.writelines(contents)
        subprocess.run(["black", self.temp_file_path])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "raw_path",
        help="The path to a raw scenario.",
        type=str,
    )
    parser.add_argument(
        "--mode",
    )
    args = parser.parse_args()

    if args.mode == "following":
        task = Following(
            raw_path=args.raw_path, scenario_path=config["path"]["scenario_path"]
        )
    elif args.mode == "cruising":
        task = Cruising(
            raw_path=args.raw_path, scenario_path=config["path"]["scenario_path"]
        )
    elif args.mode == "turning":
        task = Turning(
            raw_path=args.raw_path, scenario_path=config["path"]["scenario_path"]
        )
    else:
        exit()

    task.run()

# python script.py --preview <raw_path>