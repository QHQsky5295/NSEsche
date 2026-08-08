import os
import sys
CUR_FPATH = os.path.abspath(__file__)
CUR_FDIR = os.path.dirname(CUR_FPATH)
os.chdir(CUR_FDIR)

import yaml, time

# 支持自定义配置文件路径
if len(sys.argv) > 1:
    config_file = sys.argv[1]
else:
    config_file = "batch_run.yml"

print(f"使用配置文件: {config_file}")

with open(config_file, 'r', encoding='utf-8') as stream:
    batchconf = yaml.safe_load(stream)

run_time = batchconf['run_time']
mech_scale_sche = batchconf['mech_scale_sche']
mech_other = batchconf['mech_other']

import records_read
from proxy_env3 import ProxyEnv3
env = ProxyEnv3()

def apply_mech(env, mechkey, mechconf):
    if isinstance(mechconf, list):
        for mechconf_one in mechconf:
            apply_mech(env, mechkey, mechconf_one)
        return
    
    # 处理字符串类型的配置
    if isinstance(mechconf, str):
        # 如果是字符串，直接使用 mechkey 作为配置键
        env.config['mech'][mechkey][mechkey] = mechconf
        return
    
    # 处理字典类型的配置
    if isinstance(mechconf, dict):
        mechconfkey = mechconf.keys().__iter__().__next__()
        mechconfval = mechconf[mechconfkey]
        if mechconfval is None:
            mechconfval = ''
        mechconfval = str(mechconfval)
        env.config['mech'][mechkey][mechconfkey] = mechconfval
        return
    
    # 其他类型直接转换为字符串
    env.config['mech'][mechkey][mechkey] = str(mechconf)
    
def unapply_mech(env, mechkey):
    for mechconfkey in env.config['mech'][mechkey]:
        env.config['mech'][mechkey][mechconfkey] = None

compose_cnt = 0

params = ['request_freq', 'dag_type', 'no_mech_latency']
def dfs_params(paramsconf, i, cb):
    if i == len(params):
        cb()
        return
    for paramsconf_one in paramsconf[params[i]]:
        env.config[params[i]] = paramsconf_one.keys().__iter__().__next__()
        dfs_params(paramsconf, i+1, cb)

mech_other_params = ['instance_cache_policy']
def dfs_mech_other(mech_otherconf, i, cb):
    if i == len(mech_other):
        cb()
        return
    for mech_otherconf_one in mech_otherconf[mech_other_params[i]]:
        apply_mech(env, mech_other_params[i], mech_otherconf_one)
        dfs_mech_other(mech_otherconf, i+1, cb)
        unapply_mech(env, mech_other_params[i])

def params_compistion():
    for mech_scale_sche_one in mech_scale_sche:
        print('mech type', mech_scale_sche_one)
        mech_scale_sche_conf = mech_scale_sche[mech_scale_sche_one]

        unapply_mech(env, 'mech_type')
        apply_mech(env, 'mech_type', {mech_scale_sche_one: ''})
        
        mech_scale_sche_args = ['scale_num', 'scale_down_exec', 'scale_up_exec', 'sche', 'filter']
        def dfs(mech_scale_sche_conf, i, cb):
            if i == len(mech_scale_sche_args):
                cb()
                return
            for mech_scale_sche_conf_one in mech_scale_sche_conf[mech_scale_sche_args[i]]:
                apply_mech(env, mech_scale_sche_args[i], mech_scale_sche_conf_one)
                dfs(mech_scale_sche_conf, i+1, cb)
                unapply_mech(env, mech_scale_sche_args[i])

        def compose_mech_other():
            def one_composition():
                global compose_cnt
                compose_cnt += 1
                print("composition_cnt:", compose_cnt)
                print(records_read.conf_str(env.config))
                cnt = records_read.spec_conf_cnt(env.config)
                needrun = 0
                if run_time > cnt:
                    needrun = run_time - cnt
                print(f"need to run {needrun}")
                print("")
                print("-" * 40)

                for i in range(needrun):
                    env.reset()
                    env.step(1)
                
                print("")
                print("-" * 40)
                print("")
                time.sleep(1)
                
            dfs_mech_other(mech_other, 0, one_composition)

        dfs(mech_scale_sche_conf, 0, compose_mech_other)

dfs_params(batchconf['params'], 0, params_compistion)