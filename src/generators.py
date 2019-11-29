import os

os.environ["MKL_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"
os.environ["OMP_NUM_THREADS"] = "2"
import numpy as np

from torch.utils import data
from datasetManager import DatasetManager


class Generator(data.Dataset):
    def __init__(self, corpus, augments=()):
        super().__init__()

        self.corpus = corpus
        self.augments = augments

        # dataset access (combine weak and synthetic)
        self.x = self.corpus.audio["train"]
        self.y = self.corpus.meta["train"]

        self.filenames = list(self.x.keys())

        # Validation
        self.X_val, self.y_val = None, None

        # alias for verbose mode
        self.tqdm_func = self.corpus.tqdm_func

    @property
    def validation(self):
        if self.X_val is not None and self.y_val is not None:
            return self.X_val, self.y_val

        # Need to ensure that the data are store in the same order.
        self.X_val, self.y_val = [], []
        filenames = self.corpus.audio["val"].keys()

        for filename in self.tqdm_func(filenames):
            raw_audio = self.corpus.audio["val"][filename]
            feature = self.corpus.extract_feature(raw_audio, DatasetManager.SR)
            target = self.corpus.meta["val"].at[filename, "classID"]

            self.X_val.append(feature)
            self.y_val.append(target)

        self.X_val = np.asarray(self.X_val)
        self.y_val = np.asarray(self.y_val)
        return self.X_val, self.y_val


    def __len__(self):
        nb_file = len(self.filenames)
        return nb_file

    def __getitem__(self, index):
        filename = self.filenames[index]
        return self._generate_data(filename)

    def _generate_data(self, filename: str):
        LENGTH = DatasetManager.LENGTH
        SR = DatasetManager.SR

        # load the raw_audio
        raw_audio = self.x[filename]

        # recover ground truth
        y = self.y.at[filename, "classID"]

        # data augmentation
        for augment_func in self.augments:
            raw_audio = augment_func(raw_audio)

        # padding and cropping
        if len(raw_audio) < LENGTH * SR:
            missing = (LENGTH * SR) - len(raw_audio)
            raw_audio = np.concatenate((raw_audio, [0] * missing))

        if len(raw_audio) > LENGTH * SR:
            raw_audio = raw_audio[:LENGTH * SR]

        # extract feature
        feat = self.corpus.extract_feature(raw_audio, SR)
        y = np.asarray(y)

        return feat, y


class CoTrainingGenerator(data.Dataset):
    """Must be used with the CoTrainingSampler"""

    def __init__(self, dataset, sampler, augments=()):
        self.dataset = dataset
        self.sampler = sampler
        self.augments = augments

        self.S_weak_filenames = list(self.dataset.audio["weak"].keys())
        self.U_filenames = list(self.dataset.audio["unlabel_in_domain"].keys())

    def __len__(self) -> int:
        return len(self.sampler)

    def __getitem__(self, batch_idx):
        views_indexes = batch_idx[:-1]
        U_indexes = batch_idx[-1]

        # Prepare views
        X, y = [], []
        for vi in views_indexes:
            X_V, y_V = self._generate_data(
                vi,
                target_filenames=self.S_weak_filenames,
                target_raw=self.dataset.audio["weak"],
                target_meta=self.dataset.meta["weak"],
            )
            X.append(X_V)
            y.append(y_V)

        # Prepare U
        X_U, y_U = self._generate_data(
            U_indexes,
            target_filenames=self.U_filenames,
            target_raw=self.dataset.audio["unlabel_in_domain"],
            target_meta=None
        )
        X.append(X_U)
        y.append(y_U)


        return X, y

    def _generate_data(self, indexes: list, target_filenames: list, target_raw: dict, target_meta: dict = None):
        LENGTH = DatasetManager.LENGTH
        SR = DatasetManager.SR

        # Get the corresponding filenames
        # filenames = [target_filenames[i] for i in indexes]
        filenames = []
        for i in indexes:
            filenames.append(target_filenames[i])

        # Get the raw_adio
        raw_audios = [target_raw[name] for name in filenames]

        # Get the ground truth
        # For unlabel set, create a fake ground truth (batch collate error otherwise)
        targets = [[0] * DatasetManager.NB_CLASS for _ in range(len(filenames))]
        if target_meta is not None:
            targets = [target_meta.at[name, "weak"] for name in filenames]

        # Data augmentation ?
        for i in range(len(raw_audios)):
            for augment_func in self.augments:
                raw_audios[i] = augment_func(raw_audios[i])

        # Padding and cropping
        for i in range(len(raw_audios)):
            if len(raw_audios[i]) < LENGTH * SR:
                missing = (LENGTH * SR) - len(raw_audios[i])
                raw_audios[i] = np.concatenate((raw_audios[i], [0] * missing))

            if len(raw_audios[i]) > LENGTH * SR:
                raw_audios[i] = raw_audios[i][:LENGTH * SR]

        # Extract the features
        features = [self.dataset.extract_feature(raw, SR) for raw in raw_audios]

        # Convert to np array
        return np.array(features), np.array(targets)
