# Learning Rolling Shutter Correction from Real Data without Camera Motion Assumption
# Copyright (C) <2020> <Jiawei Mo, Md Jahidul Islam, Junaed Sattar>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function
import numpy as np
import os
from tqdm import tqdm
from numpy import linalg as LA


def projectPoint(ua, va, da, cam_a, T_b_a, cam_b):
    Xa = np.ones([3, 1], dtype=np.float32)
    Xa[0] = (ua-cam_a[2]) / cam_a[0]
    Xa[1] = (va-cam_a[3]) / cam_a[1]
    Xa = Xa*da
    Xb = np.matmul(T_b_a[0:3, 0:3], Xa)+np.expand_dims(T_b_a[0:3, 3], -1)
    ub = Xb[0, 0]/Xb[2, 0]*cam_b[0] + cam_b[2]
    vb = Xb[1, 0]/Xb[2, 0]*cam_b[1] + cam_b[3]
    return [ub, vb]


def getGS2RSFlow(depth_rs, cam1, T_cam0_v1, v1_lut):
    h, w = depth_rs.shape[:2]
    flow_gs2rs = np.empty([h, w, 2], dtype=np.float32)
    flow_gs2rs[:] = np.nan

    T_gs_rs = np.empty_like(T_cam0_v1)
    for v1 in range(h):
        T_gs_rs[v1] = np.matmul(LA.inv(T_cam0_v1[0]), T_cam0_v1[v1])

    # Project from rs to gs
    for v1rs in range(h):
        for u1rs in range(w):
            if np.isnan(depth_rs[v1rs, u1rs]):
                continue

            [u1gs, v1gs] = projectPoint(
                u1rs, v1rs, depth_rs[v1rs, u1rs], cam1, T_gs_rs[v1_lut[v1rs, u1rs]], cam1)
            if not np.isnan(u1gs):
                u1gsi, v1gsi = int(u1gs+0.5), int(v1gs+0.5)
                if 0 <= u1gsi < w and 0 <= v1gsi < h:
                    flow_gs2rs[v1gsi, u1gsi, 0] = u1rs-u1gs
                    flow_gs2rs[v1gsi, u1gsi, 1] = v1rs-v1gs

    return flow_gs2rs


def getGS2RSFlows(save_path, ns_per_v):
    depth1_path = save_path+"cam1/depth/"
    cam1 = np.load(save_path+"cam1/camera.npy")
    flows_gs2rs_path = save_path+"cam1/flows_gs2rs/"
    if not os.path.exists(flows_gs2rs_path):
        os.makedirs(flows_gs2rs_path)

    # Load poses
    T_cam0_v1 = np.load(save_path+"poses_cam0_v1.npy")
    v1_lut = np.load(save_path+"cam1/v1_lut.npy")

    img_count = T_cam0_v1.shape[0]
    for i in tqdm(range(img_count)):
        depth1 = np.load('{}{}.npy'.format(depth1_path, i))
        flow_gs2rs = getGS2RSFlow(depth1, cam1, T_cam0_v1[i], v1_lut)
        gs2rs_name = os.path.join(flows_gs2rs_path, str(i))
        np.save(gs2rs_name, flow_gs2rs)
