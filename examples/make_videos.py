import time
from pdb import set_trace
import sys, os, io
sys.path.append(os.getcwd() + "/..")
sys.path.append(os.getcwd() + "/../icra_scripts")

import numpy as np
import autompc as ampc
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy.linalg as la
import argparse
import pickle
from joblib import Memory
import torch

from scipy.integrate import solve_ivp
from cartpole_control_test import animate_cartpole
from test_shared import animate_pendulum
from tuning1 import runsim
from pendulum_task import pendulum_swingup_task
from cartpole_task import cartpole_swingup_task
from halfcheetah_task import halfcheetah_task, env
from pipelines import init_mlp_ilqr, init_halfcheetah
from gym.wrappers import Monitor

memory = Memory("cache")


@memory.cache
def get_cartpole_traj():
    eval_seed = 471242136 
    sysid_seed = 95832482 
    tinf = cartpole_swingup_task()
    sysid_trajs = tinf.gen_sysid_trajs(sysid_seed)
    pipeline = init_mlp_ilqr(tinf)
    cs = pipeline.get_configuration_space()
    cfg = cs.get_default_configuration()
    cfg["_controller:horizon"] = 7
    cfg["_model:n_hidden_layers"] = '3'
    cfg["_model:hidden_size_1"] = 164
    cfg["_model:hidden_size_2"] = 32
    cfg["_model:hidden_size_3"] = 32
    cfg["_model:lr_log10"] = -1.9849343199878176
    cfg["_model:nonlintype"] = 'sigmoid'
    cfg["_task_transformer_0:dx_log10Fgain"] = 2.3443526613082177
    cfg["_task_transformer_0:dx_log10Qgain"] = -2.527453816285304
    cfg["_task_transformer_0:omega_log10Fgain"] = 2.1122143039990195
    cfg["_task_transformer_0:omega_log10Qgain"] = -2.951999061464214
    cfg["_task_transformer_0:theta_log10Fgain"] = 3.9971799274332973
    cfg["_task_transformer_0:theta_log10Qgain"] = -0.018173603865086374
    cfg["_task_transformer_0:u_log10Rgain"] = 0.9340417319521195
    cfg["_task_transformer_0:x_log10Fgain"] = -2.3903216713888717
    cfg["_task_transformer_0:x_log10Qgain"] = -1.3294040483448015
    torch.manual_seed(eval_seed)
    controller, model = pipeline(cfg, sysid_trajs)
    truedyn_traj = runsim(tinf, 200, None, controller, tinf.dynamics)
    print("True score is ", tinf.perf_metric(truedyn_traj))

    return truedyn_traj

@memory.cache
def get_pendulum_traj():
    eval_seed = 471242136 
    sysid_seed = 95832482 
    tinf = pendulum_swingup_task()
    sysid_trajs = tinf.gen_sysid_trajs(sysid_seed)
    pipeline = init_mlp_ilqr(tinf)
    cs = pipeline.get_configuration_space()
    cfg = cs.get_default_configuration()
    cfg["_controller:horizon"] = 19
    cfg["_model:n_hidden_layers"] = '4'
    cfg["_model:hidden_size_1"] = 237
    cfg["_model:hidden_size_2"] = 16
    cfg["_model:hidden_size_3"] = 49
    cfg["_model:hidden_size_4"] = 58
    cfg["_model:lr_log10"] = -3.19686373088281
    cfg["_model:nonlintype"] = 'tanh'
    cfg["_task_transformer_0:ang_log10Fgain"] = -2.8258747593349773
    cfg["_task_transformer_0:ang_log10Qgain"] = 2.2741663880622083
    cfg["_task_transformer_0:angvel_log10Fgain"] = -2.0413800509631113
    cfg["_task_transformer_0:angvel_log10Qgain"] = 0.03623480183756156
    cfg["_task_transformer_0:torque_log10Rgain"] = -0.8660987537498146
    torch.manual_seed(eval_seed)
    controller, model = pipeline(cfg, sysid_trajs)
    truedyn_traj = runsim(tinf, 200, None, controller, tinf.dynamics)
    print("True score is ", tinf.perf_metric(truedyn_traj))

    return truedyn_traj

@memory.cache
def get_halfcheetah_traj():
    eval_seed = 831028979 
    sysid_seed = 95832482 
    tinf = halfcheetah_task()
    sysid_trajs = tinf.gen_sysid_trajs(sysid_seed)
    pipeline = init_halfcheetah(tinf)
    cs = pipeline.get_configuration_space()
    cfg = cs.get_default_configuration()
    cfg["_controller:horizon"] = 24
    cfg["_model:n_hidden_layers"] = "3"
    cfg["_model:hidden_size_1"] = 69
    cfg["_model:hidden_size_2"] = 256
    cfg["_model:hidden_size_3"] = 256
    cfg["_model:lr_log10"] = -3.323534
    cfg["_model:nonlintype"] = "tanh"
    cfg["_task_transformer_0:target_velocity"] = 3.321886089075155
    cfg["_task_transformer_0:u0_log10Rgain"] = 1.5017695879038584
    cfg["_task_transformer_0:u1_log10Rgain"] = -0.5395536435085289
    cfg["_task_transformer_0:u2_log10Rgain"] = 2.748537321425771
    cfg["_task_transformer_0:u3_log10Rgain"] = 3.720361655907287
    cfg["_task_transformer_0:u4_log10Rgain"] = -2.9800602041994115
    cfg["_task_transformer_0:u5_log10Rgain"] = 0.48324062220374575
    cfg["_task_transformer_0:x1_log10Fgain"] = -2.0506520078257227
    cfg["_task_transformer_0:x1_log10Qgain"] = 3.998363281679719
    cfg["_task_transformer_0:x6_log10Qgain"] = -2.9437444440024487
    cfg["_task_transformer_0:x7_log10Qgain"] = -0.229595492726137
    cfg["_task_transformer_0:x8_log10Qgain"] = -2.5092520566006327
    cfg["_task_transformer_0:x9_log10Fgain"] = 1.496412254774678
    cfg["_task_transformer_0:x9_log10Qgain"] = 1.9821459898060656
    torch.manual_seed(eval_seed)
    controller, model = pipeline(cfg, sysid_trajs)
    truedyn_traj = runsim(tinf, 200, None, controller, tinf.dynamics)
    print("True score is ", tinf.perf_metric(truedyn_traj))

    return truedyn_traj

def gen_cartpole_video():
    sim_traj = get_cartpole_traj()
    fig = plt.figure()
    ax = fig.gca()
    ax.set_xlim((-1.0, 7.0))
    ax.set_ylim((-1.1, 1.1))
    ax.set_aspect("equal")
    ani = animate_cartpole(fig, ax, dt=0.05, traj=sim_traj)
    ani.save("out/dec02_cartpole.mp4")

def gen_pendulum_video():
    sim_traj = get_pendulum_traj()
    fig = plt.figure()
    ax = fig.gca()
    ax.set_xlim((-1.1, 1.1))
    ax.set_ylim((-1.1, 1.1))
    ax.set_aspect("equal")
    ani = animate_pendulum(fig, ax, dt=0.05, traj=sim_traj)
    ani.save("out/dec02_pendulum.mp4")

def gen_halfcheetah_video():
    eval_seed = 831028979 
    sysid_seed = 95832482 
    tinf = halfcheetah_task()
    sysid_trajs = tinf.gen_sysid_trajs(sysid_seed)
    #sim_traj = get_halfcheetah_traj()
    sim_traj = sysid_trajs[0]
    while True:
        env.reset()
        qpos = sim_traj[0].obs[:9]
        qvel = sim_traj[0].obs[9:]
        env.set_state(qpos, qvel)
        for i in range(len(sim_traj)):
            u = sim_traj[i].ctrl
            env.step(u)
            env.render()
            time.sleep(env.dt)

if __name__ == "__main__":
    #gen_cartpole_video()
    #gen_pendulum_video()
    gen_halfcheetah_video()

