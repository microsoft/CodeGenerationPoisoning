import pytest
import yaml
import os
import io
from unittest.mock import patch

import mlagents.trainers.trainer_util as trainer_util
from mlagents.trainers.trainer_util import load_config, _load_config
from mlagents.trainers.trainer_metrics import TrainerMetrics
from mlagents.trainers.ppo.trainer import PPOTrainer
from mlagents.trainers.bc.offline_trainer import OfflineBCTrainer
from mlagents.trainers.bc.online_trainer import OnlineBCTrainer
from mlagents.envs.exception import UnityEnvironmentException


@pytest.fixture
def dummy_config():
    return yaml.safe_load(
        """
        default:
            trainer: ppo
            batch_size: 32
            beta: 5.0e-3
            buffer_size: 512
            epsilon: 0.2
            gamma: 0.99
            hidden_units: 128
            lambd: 0.95
            learning_rate: 3.0e-4
            max_steps: 5.0e4
            normalize: true
            num_epoch: 5
            num_layers: 2
            time_horizon: 64
            sequence_length: 64
            summary_freq: 1000
            use_recurrent: false
            memory_size: 8
            use_curiosity: false
            curiosity_strength: 0.0
            curiosity_enc_size: 1
        """
    )


@pytest.fixture
def dummy_online_bc_config():
    return yaml.safe_load(
        """
        default:
            trainer: online_bc
            brain_to_imitate: ExpertBrain
            batches_per_epoch: 16
            batch_size: 32
            beta: 5.0e-3
            buffer_size: 512
            epsilon: 0.2
            gamma: 0.99
            hidden_units: 128
            lambd: 0.95
            learning_rate: 3.0e-4
            max_steps: 5.0e4
            normalize: true
            num_epoch: 5
            num_layers: 2
            time_horizon: 64
            sequence_length: 64
            summary_freq: 1000
            use_recurrent: false
            memory_size: 8
            use_curiosity: false
            curiosity_strength: 0.0
            curiosity_enc_size: 1
        """
    )


@pytest.fixture
def dummy_offline_bc_config():
    return yaml.safe_load(
        """
        default:
            trainer: offline_bc
            demo_path: """
        + os.path.dirname(os.path.abspath(__file__))
        + """/test.demo
            batches_per_epoch: 16
            batch_size: 32
            beta: 5.0e-3
            buffer_size: 512
            epsilon: 0.2
            gamma: 0.99
            hidden_units: 128
            lambd: 0.95
            learning_rate: 3.0e-4
            max_steps: 5.0e4
            normalize: true
            num_epoch: 5
            num_layers: 2
            time_horizon: 64
            sequence_length: 64
            summary_freq: 1000
            use_recurrent: false
            memory_size: 8
            use_curiosity: false
            curiosity_strength: 0.0
            curiosity_enc_size: 1
        """
    )


@pytest.fixture
def dummy_offline_bc_config_with_override():
    base = dummy_offline_bc_config()
    base["testbrain"] = {}
    base["testbrain"]["normalize"] = False
    return base


@pytest.fixture
def dummy_bad_config():
    return yaml.safe_load(
        """
        default:
            trainer: incorrect_trainer
            brain_to_imitate: ExpertBrain
            batches_per_epoch: 16
            batch_size: 32
            beta: 5.0e-3
            buffer_size: 512
            epsilon: 0.2
            gamma: 0.99
            hidden_units: 128
            lambd: 0.95
            learning_rate: 3.0e-4
            max_steps: 5.0e4
            normalize: true
            num_epoch: 5
            num_layers: 2
            time_horizon: 64
            sequence_length: 64
            summary_freq: 1000
            use_recurrent: false
            memory_size: 8
        """
    )


@patch("mlagents.envs.brain.BrainParameters")
def test_initialize_trainer_parameters_override_defaults(BrainParametersMock):
    summaries_dir = "test_dir"
    run_id = "testrun"
    model_path = "model_dir"
    keep_checkpoints = 1
    train_model = True
    load_model = False
    seed = 11

    base_config = dummy_offline_bc_config_with_override()
    expected_config = base_config["default"]
    expected_config["summary_path"] = summaries_dir + f"/{run_id}_testbrain"
    expected_config["model_path"] = model_path + "/testbrain"
    expected_config["keep_checkpoints"] = keep_checkpoints

    # Override value from specific brain config
    expected_config["normalize"] = False

    brain_params_mock = BrainParametersMock()
    external_brains = {"testbrain": brain_params_mock}

    def mock_constructor(self, brain, trainer_parameters, training, load, seed, run_id):
        assert brain == brain_params_mock
        assert trainer_parameters == expected_config
        assert training == train_model
        assert load == load_model
        assert seed == seed
        assert run_id == run_id

    with patch.object(OfflineBCTrainer, "__init__", mock_constructor):
        trainers = trainer_util.initialize_trainers(
            trainer_config=base_config,
            external_brains=external_brains,
            summaries_dir=summaries_dir,
            run_id=run_id,
            model_path=model_path,
            keep_checkpoints=keep_checkpoints,
            train_model=train_model,
            load_model=load_model,
            seed=seed,
        )
        assert "testbrain" in trainers
        assert isinstance(trainers["testbrain"], OfflineBCTrainer)


@patch("mlagents.envs.brain.BrainParameters")
def test_initialize_online_bc_trainer(BrainParametersMock):
    summaries_dir = "test_dir"
    run_id = "testrun"
    model_path = "model_dir"
    keep_checkpoints = 1
    train_model = True
    load_model = False
    seed = 11

    base_config = dummy_online_bc_config()
    expected_config = base_config["default"]
    expected_config["summary_path"] = summaries_dir + f"/{run_id}_testbrain"
    expected_config["model_path"] = model_path + "/testbrain"
    expected_config["keep_checkpoints"] = keep_checkpoints

    brain_params_mock = BrainParametersMock()
    external_brains = {"testbrain": brain_params_mock}

    def mock_constructor(self, brain, trainer_parameters, training, load, seed, run_id):
        assert brain == brain_params_mock
        assert trainer_parameters == expected_config
        assert training == train_model
        assert load == load_model
        assert seed == seed
        assert run_id == run_id

    with patch.object(OnlineBCTrainer, "__init__", mock_constructor):
        trainers = trainer_util.initialize_trainers(
            trainer_config=base_config,
            external_brains=external_brains,
            summaries_dir=summaries_dir,
            run_id=run_id,
            model_path=model_path,
            keep_checkpoints=keep_checkpoints,
            train_model=train_model,
            load_model=load_model,
            seed=seed,
        )
        assert "testbrain" in trainers
        assert isinstance(trainers["testbrain"], OnlineBCTrainer)


@patch("mlagents.envs.brain.BrainParameters")
def test_initialize_ppo_trainer(BrainParametersMock):
    brain_params_mock = BrainParametersMock()
    external_brains = {"testbrain": BrainParametersMock()}
    summaries_dir = "test_dir"
    run_id = "testrun"
    model_path = "model_dir"
    keep_checkpoints = 1
    train_model = True
    load_model = False
    seed = 11
    expected_reward_buff_cap = 1

    base_config = dummy_config()
    expected_config = base_config["default"]
    expected_config["summary_path"] = summaries_dir + f"/{run_id}_testbrain"
    expected_config["model_path"] = model_path + "/testbrain"
    expected_config["keep_checkpoints"] = keep_checkpoints

    def mock_constructor(
        self,
        brain,
        reward_buff_cap,
        trainer_parameters,
        training,
        load,
        seed,
        run_id,
        multi_gpu,
    ):
        self.trainer_metrics = TrainerMetrics("", "")
        assert brain == brain_params_mock
        assert trainer_parameters == expected_config
        assert reward_buff_cap == expected_reward_buff_cap
        assert training == train_model
        assert load == load_model
        assert seed == seed
        assert run_id == run_id
        assert multi_gpu == multi_gpu

    with patch.object(PPOTrainer, "__init__", mock_constructor):
        trainers = trainer_util.initialize_trainers(
            trainer_config=base_config,
            external_brains=external_brains,
            summaries_dir=summaries_dir,
            run_id=run_id,
            model_path=model_path,
            keep_checkpoints=keep_checkpoints,
            train_model=train_model,
            load_model=load_model,
            seed=seed,
        )
        assert "testbrain" in trainers
        assert isinstance(trainers["testbrain"], PPOTrainer)


@patch("mlagents.envs.brain.BrainParameters")
def test_initialize_invalid_trainer_raises_exception(BrainParametersMock):
    summaries_dir = "test_dir"
    run_id = "testrun"
    model_path = "model_dir"
    keep_checkpoints = 1
    train_model = True
    load_model = False
    seed = 11
    bad_config = dummy_bad_config()
    external_brains = {"testbrain": BrainParametersMock()}

    with pytest.raises(UnityEnvironmentException):
        trainer_util.initialize_trainers(
            trainer_config=bad_config,
            external_brains=external_brains,
            summaries_dir=summaries_dir,
            run_id=run_id,
            model_path=model_path,
            keep_checkpoints=keep_checkpoints,
            train_model=train_model,
            load_model=load_model,
            seed=seed,
        )


def test_load_config_missing_file():
    with pytest.raises(UnityEnvironmentException):
        load_config("thisFileDefinitelyDoesNotExist.yaml")


def test_load_config_valid_yaml():
    file_contents = """
this:
  - is fine
    """
    fp = io.StringIO(file_contents)
    res = _load_config(fp)
    assert res == {"this": ["is fine"]}


def test_load_config_invalid_yaml():
    file_contents = """
you:
  - will
- not
  - parse
    """
    with pytest.raises(UnityEnvironmentException):
        fp = io.StringIO(file_contents)
        _load_config(fp)
