from __future__ import annotations

import copy
import math
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.matrix import load_protocol_config
from scripts.reviewer_experiments.protocol.schema import ProtocolValidationError
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)
from scripts.reviewer_experiments.protocol.workload_profile import (
    CANONICAL_PROFILES,
    load_profile_set,
)


REPOSITORY = Path(__file__).resolve().parents[4]


class FrozenWorkloadProfileTests(unittest.TestCase):
    def test_default_profiles_are_the_exact_canonical_set(self) -> None:
        config = load_protocol_config()
        loaded = load_profile_set(config["workload_profiles"], repository=REPOSITORY)

        self.assertEqual(set(loaded), {"low", "middle", "high"})
        for load, expected in CANONICAL_PROFILES.items():
            with self.subTest(load=load):
                profile = loaded[load]
                self.assertEqual(profile.sha256, expected["sha256"])
                self.assertEqual(profile.profile_id, expected["profile_id"])
                self.assertEqual(
                    profile.dag_call_frequency_sha256,
                    expected["dag_call_frequency_sha256"],
                )
                self.assertEqual(
                    profile.expected_arrival_rate_rps,
                    expected["expected_arrival_rate_rps"],
                )

    def test_expected_rates_are_recomputed_from_all_dag_parameters(self) -> None:
        config = load_protocol_config()
        for load, expected in {
            "low": 1934.66,
            "middle": 2533.14,
            "high": 7000.0,
        }.items():
            with self.subTest(load=load):
                path = (
                    REPOSITORY / config["workload_profiles"]["profiles"][load]["path"]
                )
                document = read_json(path)
                calculated = 0.0
                for mean, cv in document["dag_call_frequency"].values():
                    if cv == 0.0:
                        conditional_mean = mean
                    else:
                        z = 1.0 / cv
                        density = math.exp(-(z * z) / 2.0) / math.sqrt(2.0 * math.pi)
                        positive_probability = 0.5 * (
                            1.0 + math.erf(z / math.sqrt(2.0))
                        )
                        conditional_mean = (
                            mean + mean * cv * density / positive_probability
                        )
                    calculated += conditional_mean
                calculated *= document["rate_audit"]["request_frequency_scale"] * 1000.0
                self.assertAlmostEqual(calculated, expected, places=2)

    def test_high_profile_is_a_uniform_mean_only_normalization(self) -> None:
        config = load_protocol_config()
        high_path = REPOSITORY / config["workload_profiles"]["profiles"]["high"]["path"]
        document = read_json(high_path)
        source = document["source"]
        multiplier = source["uniform_mean_multiplier"]
        reconstructed = {
            dag_id: [pair[0] / multiplier, pair[1]]
            for dag_id, pair in document["dag_call_frequency"].items()
        }

        self.assertEqual(document["profile_id"], "submission-era-azure-cdf-high-7k-v1")
        self.assertTrue(
            math.isclose(
                source["pre_normalization_expected_arrival_rate_rps"] * multiplier,
                7000.0,
                rel_tol=0.0,
                abs_tol=1e-3,
            )
        )
        self.assertEqual(source["submission_actual_arrival_rate_rps"], 27924.0)
        self.assertEqual(source["formal_target_arrival_rate_rps"], 7000.0)
        self.assertEqual(
            object_hash(reconstructed),
            source["pre_normalization_dag_call_frequency_sha256"],
        )

    def test_self_consistent_alternate_profile_is_not_formal(self) -> None:
        protocol = load_protocol_config()
        profile_set = copy.deepcopy(protocol["workload_profiles"])
        source_path = REPOSITORY / profile_set["profiles"]["low"]["path"]
        document = read_json(source_path)
        document["profile_id"] = "alternate-low-profile"

        with tempfile.TemporaryDirectory() as temporary:
            alternate_path = Path(temporary) / "low.alternate.json"
            write_json_atomic(alternate_path, document)
            alternate = profile_set["profiles"]["low"]
            alternate["path"] = str(alternate_path)
            alternate["sha256"] = file_hash(alternate_path)
            alternate["profile_id"] = document["profile_id"]

            with self.assertRaisesRegex(
                ProtocolValidationError, "not the frozen canonical artifact"
            ):
                load_profile_set(profile_set, repository=REPOSITORY)


if __name__ == "__main__":
    unittest.main()
