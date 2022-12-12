import random
import os
import pickle

import librosa as lb
import numpy as np
import musdb
import yaml


# ignore warning about unsafe loaders in pyYAML 5.1 (used in musdb)
# https://github.com/yaml/pyyaml/wiki/PyYAML-yaml.load(input)-Deprecation
yaml.warnings({'YAMLLoadWarning': False})


def musdb_pre_processing(path_to_musdb, path_to_save_data, target_sr,
                         frame_length):
    """
    This function splits all MUSDB tracks in frames of a given length, downsamples them to a given sampling rate,
    converts them to mono and saves each frame as .npy-file. It randomly splits the training partition into a training
    (80 tracks) and a validation (20 tracks) set.
    """

    path_to_save_train_set = os.path.join(path_to_save_data, 'train')
    path_to_save_val_set = os.path.join(path_to_save_data, 'val')
    path_to_save_test_set = os.path.join(path_to_save_data, 'test')

    if not os.path.exists(path_to_save_data):
        os.makedirs(path_to_save_data)
    if not os.path.exists(path_to_save_train_set):
        os.makedirs(path_to_save_train_set)
    if not os.path.exists(path_to_save_val_set):
        os.makedirs(path_to_save_val_set)
    if not os.path.exists(path_to_save_test_set):
        os.makedirs(path_to_save_test_set)

    # load the musdb train and test partition with the parser musdb (https://github.com/sigsep/sigsep-mus-db)
    musdb_corpus = musdb.DB(root_dir=path_to_musdb)
    training_tracks = musdb_corpus.load_mus_tracks(subsets=['train'])
    test_tracks = musdb_corpus.load_mus_tracks(subsets=['test'])

    # randomly select 20 tracks from the training partition that will be the validation set
    all_idx = list(np.arange(0, 100))
    random.seed(1)
    val_idx = random.sample(population=all_idx, k=20)  # track indices of validation set tracks
    train_idx = [idx for idx in all_idx if idx not in val_idx]  # track indices of training set tracks

    # process and save training set
    train_file_list = []
    for idx in train_idx:

        track = training_tracks[idx]

        track_name = track.name.split('-')
        track_name = track_name[0][0:6] + "_" + track_name[1][1:6]
        track_name = track_name.replace(" ", "_")

        track_audio = track.targets['accompaniment'].audio
        track_audio_mono = lb.to_mono(track_audio.T)
        track_audio_mono_resampled = lb.core.resample(track_audio_mono, track.rate, target_sr)

        frames = lb.util.frame(y=track_audio_mono_resampled, frame_length=frame_length, hop_length=frame_length)
        number_of_frames = frames.shape[1]

        for n in range(number_of_frames):
            file_name = track_name + '_{}.npy'.format(n)

            np.save(os.path.join(path_to_save_train_set, file_name), frames[:, n])
            train_file_list.append(file_name)

    pickle_out = open(os.path.join(path_to_save_train_set, "train_file_list.pickle"), "wb")
    pickle.dump(train_file_list, pickle_out)
    pickle_out.close()

    # process and save validation set
    val_file_list = []
    for idx in val_idx:

        track = training_tracks[idx]

        track_name = track.name.split('-')
        track_name = track_name[0][0:6] + "_" + track_name[1][1:6]
        track_name = track_name.replace(" ", "_")

        track_audio = track.targets['accompaniment'].audio
        track_audio_mono = lb.to_mono(track_audio.T)
        track_audio_mono_resampled = lb.core.resample(track_audio_mono, track.rate, target_sr)

        frames = lb.util.frame(y=track_audio_mono_resampled, frame_length=frame_length, hop_length=frame_length)
        number_of_frames = frames.shape[1]

        for n in range(number_of_frames):
            file_name = track_name + '_{}.npy'.format(n)

            np.save(os.path.join(path_to_save_val_set, file_name), frames[:, n])
            val_file_list.append(file_name)

    pickle_out = open(os.path.join(path_to_save_val_set, "val_file_list.pickle"), "wb")
    pickle.dump(val_file_list, pickle_out)
    pickle_out.close()

    # process and save test set
    test_file_list = []
    for idx in range(50):

        track = test_tracks[idx]

        track_name = track.name.split('-')
        track_name = track_name[0][0:6] + "_" + track_name[1][1:6]
        track_name = track_name.replace(" ", "_")

        track_audio = track.targets['accompaniment'].audio
        track_audio_mono = lb.to_mono(track_audio.T)
        track_audio_mono_resampled = lb.core.resample(track_audio_mono, track.rate, target_sr)

        frames = lb.util.frame(y=track_audio_mono_resampled, frame_length=frame_length, hop_length=frame_length)
        number_of_frames = frames.shape[1]

        for n in range(number_of_frames):
            file_name = track_name + '_{}.npy'.format(n)

            np.save(os.path.join(path_to_save_test_set, file_name), frames[:, n])
            test_file_list.append(file_name)

    pickle_out = open(os.path.join(path_to_save_test_set, "test_file_list.pickle"), "wb")
    pickle.dump(test_file_list, pickle_out)
    pickle_out.close()


if __name__ == '__main__':

    path_to_musdb = '../Datasets/MUSDB18'
    path_to_save_data = '../Datasets/MUSDB_accompaniments'

    target_sr = 16000
    frame_length = 131584

    musdb_pre_processing(path_to_musdb, path_to_save_data, target_sr=target_sr, frame_length=frame_length)
