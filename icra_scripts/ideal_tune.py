# Created by William Edwards

# Standard library includes

# External project includes
import numpy as np
import torch
from smac.scenario.scenario import Scenario
from smac.facade.smac_hpo_facade import SMAC4HPO
from joblib import Memory, Parallel, delayed
from pdb import set_trace
memory = Memory("cache")

# Internal project includes
import autompc as ampc
from autompc.evaluators import FixedSetEvaluator
from autompc.metrics import RmseKstepMetric
from autompc.sysid import MLP
from utils import save_result
import ConfigSpace as CS

default_cfg_vals = {
        "n_hidden_layers" : "2",
        "hidden_size_1" : 64,
        "hidden_size_2" : 64,
        "lr_log10" : -3,
        "nonlintype" : "relu"
        }


@memory.cache
def train_mlp_inner(system, trajs, cfg_vals, torch_seed):
    cs = MLP.get_configuration_space(system)
    cfg = CS.Configuration(cs, cfg_vals)
    model = ampc.make_model(system, MLP, cfg, use_cuda=True)
    model.train(trajs)
    return model.get_parameters()

def train_mlp(system, trajs, cfg_vals=default_cfg_vals, torch_seed=0,
        move_to_cpu=True):
    cs = MLP.get_configuration_space(system)
    cfg = CS.Configuration(cs, cfg_vals)
    model = ampc.make_model(system, MLP, cfg, use_cuda=True)
    params = train_mlp_inner(system, trajs, cfg_vals, torch_seed)
    model.set_parameters(params)
    if move_to_cpu:
        model.net = model.net.to("cpu")
        model._device = "cpu"
    return model


def runsim(tinf, simsteps, sim_model, controller, dynamics=None):
    sim_traj = ampc.zeros(tinf.system, 1)
    x = np.copy(tinf.init_obs)
    sim_traj[0].obs[:] = x
    
    constate = controller.traj_to_state(sim_traj)
    if dynamics is None:
        simstate = sim_model.traj_to_state(sim_traj)
    for _  in range(simsteps):
        u, constate = controller.run(constate, sim_traj[-1].obs)
        if dynamics is None:
            simstate = sim_model.pred(simstate, u)
            x = simstate[:tinf.system.obs_dim]
        else:
            x = dynamics(x, u)
        print(f"{u=} {x=}")
        sim_traj[-1].ctrl[:] = u
        sim_traj = ampc.extend(sim_traj, [x], np.zeros((1, tinf.system.ctrl_dim)))
    return sim_traj

def run_smac(cs, eval_cfg, tune_iters, seed):
    rng = np.random.RandomState(seed)
    scenario = Scenario({"run_obj": "quality",  
                         "runcount-limit": tune_iters,  
                         "cs": cs,  
                         "deterministic": "true",
                         "limit_resources" : False,
                         "execdir" : "./smac"
                         })

    smac = SMAC4HPO(scenario=scenario, rng=rng,
            tae_runner=eval_cfg)
    
    incumbent = smac.optimize()

    ret_value = dict()
    ret_value["incumbent"] = incumbent
    inc_cost = float("inf")
    inc_truedyn_cost = None
    inc_costs = []
    inc_truedyn_costs = []
    inc_cfgs = []
    inc_cfg = None
    cfgs = []
    costs = []
    truedyn_costs = []
    for key, val in smac.runhistory.data.items():
        cfg = smac.runhistory.ids_config[key.config_id]
        if val.cost < inc_cost:
            inc_cost = val.cost
            inc_truedyn_cost = val.additional_info
            inc_cfg = cfg
        inc_costs.append(inc_cost)
        inc_truedyn_costs.append(inc_truedyn_cost)
        inc_cfgs.append(inc_cfg)
        cfgs.append(cfg)
        costs.append(val.cost)
        truedyn_costs.append(val.additional_info)
    ret_value["inc_costs"] = inc_costs
    ret_value["inc_truedyn_costs"] = inc_truedyn_costs
    ret_value["inc_cfgs"] = inc_cfgs
    ret_value["cfgs"] = cfgs
    ret_value["costs"] = costs
    ret_value["truedyn_costs"] = truedyn_costs

    return ret_value

def runexp_ideal_tune(pipeline, tinf, tune_iters, ensemble_size, seed, 
        n_trajs, int_file=None, subexp=1):
    print(f"{seed=}")
    rng = np.random.default_rng(seed)
    sysid_trajs = tinf.gen_sysid_trajs(rng.integers(1 << 30), n_trajs=n_trajs)

    root_pipeline_cfg = pipeline.get_configuration_space().get_default_configuration()
    root_pipeline_cfg["_model:n_hidden_layers"] = "3"
    root_pipeline_cfg["_model:hidden_size_1"] = 69
    root_pipeline_cfg["_model:hidden_size_2"] = 256
    root_pipeline_cfg["_model:hidden_size_3"] = 256
    root_pipeline_cfg["_model:lr_log10"] = -3.323534
    root_pipeline_cfg["_model:nonlintype"] = "tanh"

    surr_cfg_vals = default_cfg_vals

    eval_seed = rng.integers(1 << 30)
    #surrogates = []
    #for _ in range(ensemble_size):
    #    surr_trajs = tinf.gen_surr_trajs(rng.integers(1 << 30), n_trajs=n_trajs)
    #    torch_seed = rng.integers(1 << 30)
    #    torch.manual_seed(torch_seed)
    #    surrogate = train_mlp(tinf.system, surr_trajs, surr_cfg_vals, torch_seed)
    #    surrogates.append(surrogate)
    print(f"{eval_seed=}")

    #cs = pipeline.get_configuration_space_fixed_model()
    #cfg = cs.get_default_configuration()
    #cfg["_controller:horizon"] = 25
    #cfg["_task_transformer_0:x_log10Qgain"] = 1.0
    #print(pipeline.set_configuration_fixed_model(root_pipeline_cfg, cfg))
    #set_trace()

    @memory.cache
    def train_model(sysid_trajs):
        model = ampc.make_model(tinf.system, pipeline.Model, 
                pipeline.get_model_cfg(root_pipeline_cfg), n_train_iters=50,
                use_cuda=False)
        torch.manual_seed(eval_seed)
        model.train(sysid_trajs)
        return model.get_parameters()
    model = ampc.make_model(tinf.system, pipeline.Model, 
            pipeline.get_model_cfg(root_pipeline_cfg), n_train_iters=5,
            use_cuda=True)
    model_params = train_model(sysid_trajs)
    model.set_parameters(model_params)

    def get_surrogate(traj_seed, torch_seed):
        surr_trajs = tinf.gen_surr_trajs(traj_seed, n_trajs=n_trajs)
        torch.manual_seed(torch_seed)
        surrogate = train_mlp(tinf.system, surr_trajs, surr_cfg_vals, 
                torch_seed, move_to_cpu=False)
        return surrogate

    def eval_cfg(cfg):
        # Train surrogates
        surrogates = []
        surr_traj_seeds = []
        surr_torch_seeds = []
        for _ in range(ensemble_size):
            surr_traj_seed = int(rng.integers(1 << 30))
            surr_torch_seed = int(rng.integers(1 << 30))
            #surrogate = get_surrogate(surr_traj_seed, surr_torch_seed)
            #surrogates.append(surrogate)
            surr_traj_seeds.append(surr_traj_seed)
            surr_torch_seeds.append(surr_torch_seed)
        surrogates = Parallel(n_jobs=10)(delayed(get_surrogate)(traj_seed, torch_seed)
                for traj_seed, torch_seed in zip(surr_traj_seeds, surr_torch_seeds))

        torch.manual_seed(eval_seed)
        #pipeline_cfg = pipeline.set_tt_cfg(root_pipeline_cfg, 0, cfg)
        pipeline_cfg = pipeline.set_configuration_fixed_model(root_pipeline_cfg, cfg)
        controller, _ = pipeline(pipeline_cfg, sysid_trajs, model=model)
        surr_trajs = Parallel(n_jobs=10)(delayed(runsim)(tinf, 200, surrogate, controller)
                for surrogate in surrogates)
        surr_scores = []
        for surr_traj in surr_trajs:
            surr_score = tinf.perf_metric(surr_traj)
            surr_scores.append(surr_score)
        median_surr_score = float(np.median(surr_scores))
        truedyn_traj = runsim(tinf, 200, None, controller, tinf.dynamics)
        truedyn_score = tinf.perf_metric(truedyn_traj)
        if not int_file is None:
            with open(int_file, "a") as f:
                print(cfg, file=f)
                print(f"Surrogate scores are {surr_scores}", file=f)
                print(f"Median surrogate score is {median_surr_score}", file=f)
                print(f"True dynamics score is {truedyn_score}", file=f)
                print("==========\n\n", file=f)
        return median_surr_score, (truedyn_score, surr_scores, 
                                     surr_traj_seeds, surr_torch_seeds)

    #cs = pipeline.task_transformers[0].get_configuration_space(tinf.system)
    cs = pipeline.get_configuration_space_fixed_model()
    result = run_smac(cs, eval_cfg, tune_iters, rng.integers(1 << 30))
    baseline_res = eval_cfg(cs.get_default_configuration())
    return result, baseline_res

