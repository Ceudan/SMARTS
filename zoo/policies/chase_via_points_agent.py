from typing import Sequence

import numpy as np
from contrib_policy.helper import plotter3d

from smarts.core.agent import Agent
from smarts.core.agent_interface import RGB
from smarts.core.colors import Colors
from smarts.core.observations import Observation
from smarts.core.sensors import LANE_ID_CONSTANT


class ChaseViaPointsAgent(Agent):
    def __init__(self):
        top_down_rgb = RGB(
            width=256,
            height=256,
            resolution=50 / 256,  # m/pixels
        )
        self._res = top_down_rgb.resolution
        self._flag = -1

    def act(self, obs: Observation):
        assert obs.waypoint_paths, (
            f"Waypoint paths = {obs.waypoint_paths}; "
            "cannot be empty or None. Enable waypoint paths in agent interface."
        )

        # for ind, wp in enumerate(obs.waypoint_paths):
        #     print("+ Waypoint:", ind)
        #     print("    Waypoints= ", wp[0].pos, wp[0].lane_id)
        #     print("    Waypoints= ", wp[-1].pos, wp[-1].lane_id)
        # print(
        #     "+ Leader: ", obs.ego_vehicle_state.lane_id, obs.ego_vehicle_state.position
        # )
        # print("+ NVP= ", obs.via_data.near_via_points)
        # print("+ Hit= ", obs.via_data.hit_via_points)

        LANE_CHANGE_DIST = 80

        # Truncate all paths to be of the same length
        min_len = min(LANE_CHANGE_DIST, min(map(len, obs.waypoint_paths)))
        trunc_waypoints = list(map(lambda x: x[:min_len], obs.waypoint_paths))
        waypoints = [list(map(lambda x: x.pos, path)) for path in trunc_waypoints]
        waypoints = np.array(waypoints, dtype=np.float64)

        # Ego status
        ego_lane_id = obs.ego_vehicle_state.lane_id
        assert ego_lane_id is not LANE_ID_CONSTANT, f"Ego lane cannot be {ego_lane_id}."
        ego_pos = obs.ego_vehicle_state.position[:2]
        dist = np.linalg.norm(waypoints[:, 0, :] - ego_pos, axis=-1)
        ego_wp_inds = np.where(dist == dist.min())[0]

        # Get target via point.
        via_points = np.array(
            [via_point.position for via_point in obs.via_data.near_via_points]
        )
        via_point_wp_ind, via_point_ind = _nearest_waypoint(waypoints, via_points)
        # print("ego_wp_ind=", ego_wp_ind,"; wp_ind=", via_point_wp_ind, "; via_point_ind=", via_point_ind)

        # print("ego_wp_inds", ego_wp_inds)
        # print("via_point_wp_ind", via_point_wp_ind)
        # print("IN", via_point_wp_ind[0] in ego_wp_inds)
        # if obs.ego_vehicle_state.position[0] > 190:
        #     import time
        #     time.sleep(0.8)

        # No nearby via points. Hence, remain in same lane.
        if via_point_ind is None:
            # print("+ No via points within waypoint radius. \n")
            # rgb=filter(obs,res=self._res)
            # plotter3d(obs=rgb,rgb_gray=3,channel_order="first",pause=self._flag)
            # if obs.ego_vehicle_state.position[0] > 190:
            #     self._flag = 0
            #     return (13.89, -1)

            return (obs.waypoint_paths[ego_wp_inds[0]][0].speed_limit, 0)

        # Target via point is in the same path. Hence, remain in same lane.
        if via_point_wp_ind[0] in ego_wp_inds:
            # print("+ Keep lane. \n")
            # rgb=filter(obs,res=self._res)
            # plotter3d(obs=rgb,rgb_gray=3,channel_order="first",pause=self._flag)
            # if obs.ego_vehicle_state.position[0] > 190:
            #     self._flag = 0
                # return (13.89, -1)

            return (obs.via_data.near_via_points[via_point_ind].required_speed, 0)

        # Change to left lane since target via point is on the left lane.
        if ego_wp_inds[0] < via_point_wp_ind[0]:
            # print("+ Change lane left. \n")
            # rgb=filter(obs,res=self._res)
            # plotter3d(obs=rgb,rgb_gray=3,channel_order="first",pause=self._flag)
            # if obs.ego_vehicle_state.position[0] > 190:
            #     self._flag = 0
            #     return (13.89, -1)

            return (obs.via_data.near_via_points[via_point_ind].required_speed, 1)

        # Change to right lane since target via point is on the right lane.
        if ego_wp_inds[0] > via_point_wp_ind[0]:
            # print("+ Change lane right. \n")
            # rgb=filter(obs,res=self._res)
            # plotter3d(obs=rgb,rgb_gray=3,channel_order="first",pause=self._flag)
            # if obs.ego_vehicle_state.position[0] > 190:
            #     self._flag = 0
            #     return (13.89, -1)

            return (obs.via_data.near_via_points[via_point_ind].required_speed, -1)

        raise Exception("ChaseViaPointsAgent did not catch any preprogrammed actions.")


def _nearest_waypoint(
    matrix: np.ndarray, points: np.ndarray, radius: float = 2
):
    cur_point_index = ((np.intp(1e10), np.intp(1e10)), None)

    if points.shape == (0,):
        return cur_point_index

    assert len(matrix.shape) == 3
    assert matrix.shape[2] == 2
    assert len(points.shape) == 2
    assert points.shape[1] == 2

    points_expanded = np.expand_dims(points, (1, 2))
    diff = matrix - points_expanded
    dist = np.linalg.norm(diff, axis=-1)
    for ii in range(points.shape[0]):
        index = np.argmin(dist[ii])
        index_unravel = np.unravel_index(index, dist[ii].shape)
        min_dist = dist[ii][index_unravel]
        if min_dist <= radius and index_unravel[1] < cur_point_index[0][1]:
            cur_point_index = (index_unravel, ii)

    return cur_point_index


def filter(obs: Observation, res):
    wpscolor = np.array(Colors.GreenTransparent.value[0:3]) * 255
    ego_heading = (obs.ego_vehicle_state.heading + np.pi) % (2 * np.pi) - np.pi
    ego_pos = obs.ego_vehicle_state.position

    # Get rgb image, remove road, and replace other egos (if any) as background vehicles
    rgb = obs.top_down_rgb.data
    h, w, _ = rgb.shape
    rgb_ego = rgb.copy()

    # Truncate and pad all paths to be of the same length
    min_len = min(map(len, obs.waypoint_paths))
    trunc_waypoints = list(map(lambda x: x[:min_len], obs.waypoint_paths))
    waypoints = [list(map(lambda x: x.pos, path)) for path in trunc_waypoints]
    waypoints = np.array(waypoints, dtype=np.float64)
    waypoints = np.pad(
        waypoints, ((0, 0), (0, 0), (0, 1)), mode="constant", constant_values=0
    )

    # Superimpose waypoints onto rgb image
    wps = waypoints[0:11, 3:, 0:3]
    for path in wps[:]:
        wps_valid = wps_to_pixels(
            wps=path,
            ego_pos=ego_pos,
            ego_heading=ego_heading,
            w=w,
            h=h,
            res=res,
        )
        for point in wps_valid:
            img_x, img_y = point[0], point[1]
            rgb_ego[img_y, img_x, :] = wpscolor

    # Channel first rgb
    rgb_ego = rgb_ego.transpose(2, 0, 1)

    filtered_obs = np.uint8(rgb_ego)

    return filtered_obs
    # fmt: on


def replace_color(
    rgb: np.ndarray,
    old_color: Sequence[np.ndarray],
    new_color: np.ndarray,
    mask: np.ndarray = np.ma.nomask,
) -> np.ndarray:
    """Convert pixels of value `old_color` to `new_color` within the masked
        region in the received RGB image.

    Args:
        rgb (np.ndarray): RGB image. Shape = (m,n,3).
        old_color (Sequence[np.ndarray]): List of old colors to be removed from the RGB image. Shape = (3,).
        new_color (np.ndarray): New color to be added to the RGB image. Shape = (3,).
        mask (np.ndarray, optional): Valid regions for color replacement. Shape = (m,n,3).
            Defaults to np.ma.nomask .

    Returns:
        np.ndarray: RGB image with `old_color` pixels changed to `new_color`
            within the masked region. Shape = (m,n,3).
    """
    # fmt: off
    assert all(color.shape == (3,) for color in old_color), (
        f"Expected old_color to be of shape (3,), but got {[color.shape for color in old_color]}.")
    assert new_color.shape == (3,), (
        f"Expected new_color to be of shape (3,), but got {new_color.shape}.")

    nc = new_color.reshape((1, 1, 3))
    nc_array = np.full_like(rgb, nc)
    rgb_masked = np.ma.MaskedArray(data=rgb, mask=mask)

    rgb_condition = rgb_masked
    result = rgb
    for color in old_color:
        result = np.ma.where((rgb_condition == color.reshape((1, 1, 3))).all(axis=-1)[..., None], nc_array, result)

    return result
    # fmt: on


def wps_to_pixels(
    wps: np.ndarray, ego_pos: np.ndarray, ego_heading: float, w: int, h: int, res: float
) -> np.ndarray:
    """Converts waypoints into pixel coordinates in order to superimpose the
    waypoints onto the RGB image.

    Args:
        wps (np.ndarray): Waypoints for a single route. Shape (n,3).
        ego_pos (np.ndarray): Ego position. Shape = (3,).
        ego_heading (float): Ego heading in radians.
        w (int): Width of RGB image
        h (int): Height of RGB image.
        res (float): Resolution of RGB image in meters/pixels. Computed as
            ground_size/image_size.

    Returns:
        np.ndarray: Array of waypoint coordinates on the RGB image. Shape = (m,3).
    """
    # fmt: off
    mask = [False if all(point == np.zeros(3,)) else True for point in wps]
    wps_nonzero = wps[mask]
    wps_delta = wps_nonzero - ego_pos
    wps_rotated = rotate_axes(wps_delta, theta=ego_heading)
    wps_pixels = wps_rotated / np.array([res, res, res])
    wps_overlay = np.array([w / 2, h / 2, 0]) + wps_pixels * np.array([1, -1, 1])
    wps_rfloat = np.rint(wps_overlay)
    wps_valid = wps_rfloat[(wps_rfloat[:,0] >= 0) & (wps_rfloat[:,0] < w) & (wps_rfloat[:,1] >= 0) & (wps_rfloat[:,1] < h)] 
    wps_rint = wps_valid.astype(np.uint8)
    return wps_rint
    # fmt: on


def rotate_axes(points: np.ndarray, theta: float) -> np.ndarray:
    """A counterclockwise rotation of the x-y axes by an angle theta θ about
    the z-axis.

    Args:
        points (np.ndarray): x,y,z coordinates in original axes. Shape = (n,3).
        theta (np.float): Axes rotation angle in radians.

    Returns:
        np.ndarray: x,y,z coordinates in rotated axes. Shape = (n,3).
    """
    # fmt: off
    theta = (theta + np.pi) % (2 * np.pi) - np.pi
    ct, st = np.cos(theta), np.sin(theta)
    R = np.array([[ ct, st, 0], 
                  [-st, ct, 0], 
                  [  0,  0, 1]])
    rotated_points = (R.dot(points.T)).T
    return rotated_points
    # fmt: on