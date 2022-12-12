import os
import random
import time
from copy import deepcopy

import numpy as np
import torch
import yaml
from tensorboardX import SummaryWriter
from tqdm import tqdm

from src.data.data_iterator import DataIterator
from src.data.dataset import TextLineDataset, ZipDataset
from src.data.vocabulary import Vocabulary
from src.models import build_model
from src.modules.criterions import NMTCriterion
from src.optim import Optimizer
from src.optim.lr_scheduler import ReduceOnPlateauScheduler, NoamScheduler
from src.utils.common_utils import *
from src.utils.configs import default_configs, pretty_configs
from src.utils.logging import *
from src.utils.moving_average import MovingAverage

BOS = Vocabulary.BOS
EOS = Vocabulary.EOS
PAD = Vocabulary.PAD


def set_seed(seed):
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    random.seed(seed)

    np.random.seed(seed)

    torch.backends.cudnn.deterministic = True


def load_model_parameters(path, map_location="cpu"):
    state_dict = torch.load(path, map_location=map_location)

    if "model" in state_dict:
        return state_dict["model"]
    return state_dict


def split_shard(*inputs, split_size=1):
    if split_size <= 1:
        yield inputs
    else:

        lengths = [len(s) for s in inputs[-1]]  #
        sorted_indices = np.argsort(lengths)

        # sorting inputs

        inputs = [
            [inp[ii] for ii in sorted_indices]
            for inp in inputs
        ]

        # split shards
        total_batch = sorted_indices.shape[0]  # total number of batches

        if split_size >= total_batch:
            yield inputs
        else:
            shard_size = total_batch // split_size

            _indices = list(range(total_batch))[::shard_size] + [total_batch]

            for beg, end in zip(_indices[:-1], _indices[1:]):
                yield (inp[beg:end] for inp in inputs)


def prepare_data(seqs_x, seqs_y=None, cuda=False, batch_first=True):
    """
    Args:
        eval ('bool'): indicator for eval/infer.

    Returns:

    """

    def _np_pad_batch_2D(samples, pad, batch_first=True, cuda=True):

        batch_size = len(samples)

        sizes = [len(s) for s in samples]
        max_size = max(sizes)

        x_np = np.full((batch_size, max_size), fill_value=pad, dtype='int64')

        for ii in range(batch_size):
            x_np[ii, :sizes[ii]] = samples[ii]

        if batch_first is False:
            x_np = np.transpose(x_np, [1, 0])

        x = torch.tensor(x_np)

        if cuda is True:
            x = x.cuda()
        return x

    seqs_x = list(map(lambda s: [BOS] + s + [EOS], seqs_x))
    x = _np_pad_batch_2D(samples=seqs_x, pad=PAD,
                         cuda=cuda, batch_first=batch_first)

    if seqs_y is None:
        return x

    seqs_y = list(map(lambda s: [BOS] + s + [EOS], seqs_y))
    y = _np_pad_batch_2D(seqs_y, pad=PAD,
                         cuda=cuda, batch_first=batch_first)

    return x, y


def compute_forward(model,
                    critic,
                    seqs_y,
                    eval=False,
                    normalization=1.0,
                    norm_by_words=False
                    ):
    """
    :type model: nn.Module

    :type critic: NMTCriterion
    """
    y_inp = seqs_y[:, :-1].contiguous()
    y_label = seqs_y[:, 1:].contiguous()

    words_norm = y_label.ne(PAD).float().sum(1)

    if not eval:
        model.train()
        critic.train()
        # For training
        with torch.enable_grad():
            log_probs = model(y_inp)
            loss = critic(inputs=log_probs, labels=y_label, reduce=False, normalization=normalization)

            if norm_by_words:
                loss = loss.div(words_norm).sum()
            else:
                loss = loss.sum()
        torch.autograd.backward(loss)
        return loss.item()
    else:
        model.eval()
        critic.eval()
        # For compute loss
        with torch.no_grad():
            log_probs = model(y_inp)
            loss = critic(inputs=log_probs, labels=y_label, normalization=normalization, reduce=False)
            if norm_by_words:
                loss = loss.div(words_norm).sum()
            else:
                loss = loss.sum()
        return loss.item()


def loss_validation(model, critic, valid_iterator, norm_by_words=False):
    """
    :type model: LM

    :type critic: NMTCriterion

    :type valid_iterator: DataIterator
    """

    n_sents = 0
    n_tokens = 0.0

    sum_loss = 0.0

    valid_iter = valid_iterator.build_generator()

    for batch in valid_iter:
        _, seqs_y = batch

        n_sents += len(seqs_y)
        n_tokens += sum(len(s) for s in seqs_y)

        y = prepare_data(seqs_y, cuda=GlobalNames.USE_GPU)

        loss = compute_forward(model=model,
                               critic=critic,
                               seqs_y=y,
                               eval=True,
                               norm_by_words=norm_by_words)

        if np.isnan(loss):
            WARN("NaN detected!")

        sum_loss += float(loss)

    return float(sum_loss / n_sents)


def load_pretrained_model(nmt_model, pretrain_path, device, exclude_prefix=None):
    """
    Args:
        nmt_model: model.
        pretrain_path ('str'): path to pretrained model.
        map_dict ('dict'): mapping specific parameter names to those names
            in current model.
        exclude_prefix ('dict'): excluding parameters with specific names
            for pretraining.

    Raises:
        ValueError: Size not match, parameter name not match or others.

    """
    if exclude_prefix is None:
        exclude_prefix = []
    if pretrain_path != "":
        INFO("Loading pretrained model from {}".format(pretrain_path))
        pretrain_params = torch.load(pretrain_path, map_location=device)
        for name, params in pretrain_params.items():
            flag = False
            for pp in exclude_prefix:
                if name.startswith(pp):
                    flag = True
                    break
            if flag:
                continue
            INFO("Loading param: {}...".format(name))
            try:
                nmt_model.load_state_dict({name: params}, strict=False)
            except Exception as e:
                WARN("{}: {}".format(str(Exception), e))

        INFO("Pretrained model loaded.")


def train(FLAGS):
    """
    FLAGS:
        saveto: str
        reload: store_true
        config_path: str
        pretrain_path: str, default=""
        model_name: str
        log_path: str
    """

    # write log of training to file.
    write_log_to_file(os.path.join(FLAGS.log_path, "%s.log" % time.strftime("%Y%m%d-%H%M%S")))

    GlobalNames.USE_GPU = FLAGS.use_gpu

    if GlobalNames.USE_GPU:
        CURRENT_DEVICE = "cpu"
    else:
        CURRENT_DEVICE = "cuda:0"

    config_path = os.path.abspath(FLAGS.config_path)
    with open(config_path.strip()) as f:
        configs = yaml.load(f)

    INFO(pretty_configs(configs))

    # Add default configs
    configs = default_configs(configs)
    data_configs = configs['data_configs']
    model_configs = configs['model_configs']
    optimizer_configs = configs['optimizer_configs']
    training_configs = configs['training_configs']

    GlobalNames.SEED = training_configs['seed']

    set_seed(GlobalNames.SEED)

    best_model_prefix = os.path.join(FLAGS.saveto, FLAGS.model_name + GlobalNames.MY_BEST_MODEL_SUFFIX)

    timer = Timer()

    # ================================================================================== #
    # Load Data

    INFO('Loading data...')
    timer.tic()

    # Generate target dictionary
    vocab_tgt = Vocabulary(**data_configs["vocabularies"][0])

    train_batch_size = training_configs["batch_size"] * max(1, training_configs["update_cycle"])
    train_buffer_size = training_configs["buffer_size"] * max(1, training_configs["update_cycle"])

    train_bitext_dataset = ZipDataset(
        TextLineDataset(data_path=data_configs['train_data'][0],
                        vocabulary=vocab_tgt,
                        max_len=data_configs['max_len'][0],
                        ),
        shuffle=training_configs['shuffle']
    )

    valid_bitext_dataset = ZipDataset(
        TextLineDataset(data_path=data_configs['valid_data'][0],
                        vocabulary=vocab_tgt,
                        )
    )

    training_iterator = DataIterator(dataset=train_bitext_dataset,
                                     batch_size=train_batch_size,
                                     use_bucket=training_configs['use_bucket'],
                                     buffer_size=train_buffer_size,
                                     batching_func=training_configs['batching_key'])

    valid_iterator = DataIterator(dataset=valid_bitext_dataset,
                                  batch_size=training_configs['valid_batch_size'],
                                  use_bucket=True, buffer_size=100000, numbering=True)

    INFO('Done. Elapsed time {0}'.format(timer.toc()))

    lrate = optimizer_configs['learning_rate']
    is_early_stop = False

    # ================================ Begin ======================================== #
    # Build Model & Optimizer
    # We would do steps below on after another
    #     1. build models & criterion
    #     2. move models & criterion to gpu if needed
    #     3. load pre-trained model if needed
    #     4. build optimizer
    #     5. build learning rate scheduler if needed
    #     6. load checkpoints if needed

    # 0. Initial
    model_collections = Collections()
    checkpoint_saver = Saver(save_prefix="{0}.ckpt".format(os.path.join(FLAGS.saveto, FLAGS.model_name)),
                             num_max_keeping=training_configs['num_kept_checkpoints']
                             )
    best_model_saver = Saver(save_prefix=best_model_prefix, num_max_keeping=training_configs['num_kept_best_model'])

    # 1. Build Model & Criterion
    INFO('Building model...')
    timer.tic()
    lm_model = build_model(n_tgt_vocab=vocab_tgt.max_n_words, **model_configs)
    INFO(lm_model)

    params_total = sum([p.numel() for n, p in lm_model.named_parameters()])
    params_with_embedding = sum([p.numel() for n, p in lm_model.named_parameters() if n.find('embedding') == -1])
    INFO('Total parameters: {}'.format(params_total))
    INFO('Total parameters (excluding word embeddings): {}'.format(params_with_embedding))

    critic = NMTCriterion(label_smoothing=model_configs['label_smoothing'])

    INFO(critic)
    INFO('Done. Elapsed time {0}'.format(timer.toc()))

    # 2. Move to GPU
    if GlobalNames.USE_GPU:
        lm_model = lm_model.cuda()
        critic = critic.cuda()

    # 3. Load pretrained model if needed
    lm_model.init_parameters(FLAGS.pretrain_path, device=CURRENT_DEVICE)

    # 4. Build optimizer
    INFO('Building Optimizer...')
    optim = Optimizer(name=optimizer_configs['optimizer'],
                      model=lm_model,
                      lr=lrate,
                      grad_clip=optimizer_configs['grad_clip'],
                      optim_args=optimizer_configs['optimizer_params'])

    # 5. Build scheduler for optimizer if needed
    if optimizer_configs['schedule_method'] is not None:

        if optimizer_configs['schedule_method'] == "loss":

            scheduler = ReduceOnPlateauScheduler(optimizer=optim,
                                                 **optimizer_configs["scheduler_configs"])

        elif optimizer_configs['schedule_method'] == "noam":
            scheduler = NoamScheduler(optimizer=optim, **optimizer_configs['scheduler_configs'])
        else:
            WARN("Unknown scheduler name {0}. Do not use lr_scheduling.".format(optimizer_configs['schedule_method']))
            scheduler = None
    else:
        scheduler = None

    # 6. build moving average

    if training_configs['moving_average_method'] is not None:
        ma = MovingAverage(moving_average_method=training_configs['moving_average_method'],
                           named_params=lm_model.named_parameters(),
                           alpha=training_configs['moving_average_alpha'])
    else:
        ma = None

    INFO('Done. Elapsed time {0}'.format(timer.toc()))

    # Reload from latest checkpoint
    if FLAGS.reload:
        checkpoint_saver.load_latest(model=lm_model, optim=optim, lr_scheduler=scheduler,
                                     collections=model_collections, ma=ma)

    # ================================================================================== #
    # Prepare training

    eidx = model_collections.get_collection("eidx", [0])[-1]
    uidx = model_collections.get_collection("uidx", [0])[-1]
    bad_count = model_collections.get_collection("bad_count", [0])[-1]
    oom_count = model_collections.get_collection("oom_count", [0])[-1]

    summary_writer = SummaryWriter(log_dir=FLAGS.log_path)

    cum_samples = 0
    cum_words = 0
    valid_loss = best_valid_loss = float('inf') # Max Float
    saving_files = []

    # Timer for computing speed
    timer_for_speed = Timer()
    timer_for_speed.tic()

    INFO('Begin training...')

    while True:
        summary_writer.add_scalar("Epoch", (eidx + 1), uidx)

        # Build iterator and progress bar
        training_iter = training_iterator.build_generator()
        training_progress_bar = tqdm(desc=' - (Epc {}, Upd {}) '.format(eidx, uidx),
                                     total=len(training_iterator),
                                     unit="sents"
                                     )
        for batch in training_iter:

            uidx += 1

            if optimizer_configs["schedule_method"] is not None and optimizer_configs["schedule_method"] != "loss":
                scheduler.step(global_step=uidx)

            seqs_y = batch

            n_samples_t = len(seqs_y)
            n_words_t = sum(len(s) for s in seqs_y)

            cum_samples += n_samples_t
            cum_words += n_words_t

            train_loss = 0.
            optim.zero_grad()
            try:
                # Prepare data
                for (seqs_y_t,) in split_shard(seqs_y, split_size=training_configs['update_cycle']):
                    y = prepare_data(seqs_y_t, cuda=GlobalNames.USE_GPU)

                    loss = compute_forward(model=lm_model,
                                           critic=critic,
                                           # seqs_x=x,
                                           seqs_y=y,
                                           eval=False,
                                           normalization=n_samples_t,
                                           norm_by_words=training_configs["norm_by_words"])
                    train_loss += loss / y.size(1) if not training_configs["norm_by_words"] else loss
                optim.step()

            except RuntimeError as e:
                if 'out of memory' in str(e):
                    print('| WARNING: ran out of memory, skipping batch')
                    oom_count += 1
                    optim.zero_grad()
                else:
                    raise e

            if ma is not None and eidx >= training_configs['moving_average_start_epoch']:
                ma.step()

            training_progress_bar.update(n_samples_t)
            training_progress_bar.set_description(' - (Epc {}, Upd {}) '.format(eidx, uidx))
            training_progress_bar.set_postfix_str(
                'TrainLoss: {:.2f}, ValidLoss(best): {:.2f} ({:.2f})'.format(train_loss, valid_loss, best_valid_loss))
            summary_writer.add_scalar("train_loss", scalar_value=train_loss, global_step=uidx)

            # ================================================================================== #
            # Display some information
            if should_trigger_by_steps(uidx, eidx, every_n_step=training_configs['disp_freq']):
                # words per second and sents per second
                words_per_sec = cum_words / (timer.toc(return_seconds=True))
                sents_per_sec = cum_samples / (timer.toc(return_seconds=True))
                lrate = list(optim.get_lrate())[0]

                summary_writer.add_scalar("Speed(words/sec)", scalar_value=words_per_sec, global_step=uidx)
                summary_writer.add_scalar("Speed(sents/sen)", scalar_value=sents_per_sec, global_step=uidx)
                summary_writer.add_scalar("lrate", scalar_value=lrate, global_step=uidx)
                summary_writer.add_scalar("oom_count", scalar_value=oom_count, global_step=uidx)

                # Reset timer
                timer.tic()
                cum_words = 0
                cum_samples = 0

            # ================================================================================== #
            # Saving checkpoints
            if should_trigger_by_steps(uidx, eidx, every_n_step=training_configs['save_freq'], debug=FLAGS.debug):
                model_collections.add_to_collection("uidx", uidx)
                model_collections.add_to_collection("eidx", eidx)
                model_collections.add_to_collection("bad_count", bad_count)

                if not is_early_stop:
                    checkpoint_saver.save(global_step=uidx, model=lm_model, optim=optim, lr_scheduler=scheduler,
                                          collections=model_collections, ma=ma)

            # ================================================================================== #
            # Loss Validation & Learning rate annealing
            if should_trigger_by_steps(global_step=uidx, n_epoch=eidx, every_n_step=training_configs['loss_valid_freq'],
                                       debug=FLAGS.debug):

                if ma is not None:
                    origin_state_dict = deepcopy(lm_model.state_dict())
                    lm_model.load_state_dict(ma.export_ma_params(), strict=False)

                valid_loss = loss_validation(model=lm_model,
                                             critic=critic,
                                             valid_iterator=valid_iterator,
                                             norm_by_words=training_configs["norm_by_words"])

                model_collections.add_to_collection("history_losses", valid_loss)

                min_history_loss = np.array(model_collections.get_collection("history_losses")).min()

                summary_writer.add_scalar("loss", valid_loss, global_step=uidx)
                summary_writer.add_scalar("best_loss", min_history_loss, global_step=uidx)

                if ma is not None:
                    lm_model.load_state_dict(origin_state_dict)
                    del origin_state_dict

                if optimizer_configs["schedule_method"] == "loss":
                    scheduler.step(metric=best_valid_loss)

                # If model get new best valid loss
                if valid_loss < best_valid_loss:
                    bad_count = 0

                    if is_early_stop is False:
                        # 1. save the best model
                        torch.save(lm_model.state_dict(), best_model_prefix + ".final")

                        # 2. record all several best models
                        best_model_saver.save(global_step=uidx, model=lm_model)
                else:
                    bad_count += 1

                    # At least one epoch should be traversed
                    if bad_count >= training_configs['early_stop_patience'] and eidx > 0:
                        is_early_stop = True
                        WARN("Early Stop!")

                best_valid_loss = min_history_loss

                summary_writer.add_scalar("bad_count", bad_count, uidx)

                INFO("{0} Loss: {1:.2f} lrate: {2:6f} patience: {3}".format(
                    uidx, valid_loss, lrate, bad_count)
                )

        training_progress_bar.close()

        eidx += 1
        if eidx > training_configs["max_epochs"]:
            break
