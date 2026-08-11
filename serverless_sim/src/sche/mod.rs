use bp_balance::BpBalanceScheduler;

use crate::{config::Config, sim_run::Scheduler};

use self::{
    consistenthash::ConsistentHashScheduler, ensure_scheduler::EnsureScheduler,
    faasflow::FaasFlowScheduler, fnsche::FnScheScheduler, greedy::GreedyScheduler,
    hash::HashScheduler, load_least::LoadLeastScheduler, pass::PassScheduler, pos::PosScheduler,
    random::RandomScheduler, rotate::RotateScheduler, sche_FaaSRank::FaaSRankScheduler,
    sche_Hiku::HikuScheduler, sche_OCS::OCSScheduler, sche_cp_br::CPBRScheduler,
    sche_jiagu::JiaguScheduler, sche_nash::ScheNashScheduler, sche_onsocmax::OnSocMaxScheduler,
    sche_orion::OrionScheduler,
};

pub mod bp_balance;
pub mod consistenthash;
pub mod ensure_scheduler;
pub mod faasflow;
pub mod fnsche;
pub mod greedy;
pub mod hash;
pub mod load_least;
pub mod pass;
pub mod pos;
pub mod random;
pub mod rotate;
pub mod sche_FaaSRank;
pub mod sche_Hiku;
pub mod sche_OCS;
pub mod sche_cp_br;
pub mod sche_jiagu;
pub mod sche_nash;
pub mod sche_onsocmax;
pub mod sche_orion;

pub fn prepare_spec_scheduler(config: &Config) -> Option<Box<dyn Scheduler + Send>> {
    let es = &config.mech;
    let (sche_name, sche_attr) = es.sche_conf();
    match &*sche_name {
        "faasflow" => {
            return Some(Box::new(FaasFlowScheduler::new()));
        }
        "pass" => {
            return Some(Box::new(PassScheduler::new()));
        }
        "pos" => {
            return Some(Box::new(PosScheduler::new(&sche_attr)));
        }
        "fnsche" => {
            return Some(Box::new(FnScheScheduler::new()));
        }
        "random" => {
            return Some(Box::new(RandomScheduler::new(config)));
        }
        "greedy" => {
            return Some(Box::new(GreedyScheduler::new()));
        }
        "bp_balance" => {
            return Some(Box::new(BpBalanceScheduler::new()));
        }
        "consistenthash" => {
            return Some(Box::new(ConsistentHashScheduler::new()));
        }
        "hash" => {
            return Some(Box::new(HashScheduler::new()));
        }
        "rotate" => {
            return Some(Box::new(RotateScheduler::new()));
        }
        "ensure_scheduler" => {
            return Some(Box::new(EnsureScheduler::new()));
        }
        "load_least" => {
            return Some(Box::new(LoadLeastScheduler::new()));
        }
        "sche_nash" => {
            return Some(Box::new(ScheNashScheduler::new()));
        }
        "sche_orion" => {
            return Some(Box::new(OrionScheduler::new()));
        }
        "sche_jiagu" => {
            return Some(Box::new(JiaguScheduler::new()));
        }
        "sche_Hiku" => {
            return Some(Box::new(HikuScheduler::new()));
        }
        "sche_OCS" => {
            return Some(Box::new(OCSScheduler::new()));
        }
        "sche_FaaSRank" => {
            return Some(Box::new(FaaSRankScheduler::new(
                &config.experiment.faasrank_model,
            )));
        }
        "cp_br" => {
            return Some(Box::new(CPBRScheduler::new()));
        }
        "onsocmax" => {
            return Some(Box::new(OnSocMaxScheduler::new()));
        }
        _ => {
            return None;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mechanism::ConfigNewMec;

    fn config_for(scheduler: &str) -> Config {
        let mut config = Config::new_test();
        for selected in config.mech.sche.values_mut() {
            *selected = None;
        }
        config
            .mech
            .sche
            .insert(scheduler.to_string(), Some(String::new()));
        config
    }

    #[test]
    fn e6_schedulers_register_under_separated_hpa() {
        for scheduler in ["cp_br", "onsocmax"] {
            let config = config_for(scheduler);
            assert_eq!(config.mech.mech_type().0, "scale_sche_separated");
            assert_eq!(config.mech.scale_num_conf().0, "hpa");
            assert!(prepare_spec_scheduler(&config).is_some());
            assert!(config.new_mec().is_some());
        }
    }
}
