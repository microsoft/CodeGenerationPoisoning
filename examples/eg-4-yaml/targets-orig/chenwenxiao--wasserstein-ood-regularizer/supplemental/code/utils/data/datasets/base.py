import codecs
import os
import pickle as pkl
from typing import *

import mltk
import numpy as np
import yaml
from mltk.data import MapperDataStream
from tqdm import tqdm

from ..mappers import ArrayMapper, ArrayMapperList
from ..types import *
from .utils import *

__all__ = [
    'DataSet', 'TransformedDataSet', 'ArrayDataSet', 'MMapDataSet',
    'print_dataset_info',
]

ArrayMapperOrMapperSeq = Union[ArrayMapper, List[ArrayMapper]]


class StreamArraysMapper(object):
    """Map the batch arrays in a stream using `ArrayMapper`."""

    mappers: List[Optional[ArrayMapper]]

    def __init__(self, mappers: Sequence[Optional[ArrayMapper]]):
        self.mappers = list(mappers)

    def __call__(self, *arrays) -> Tuple[mltk.Array, ...]:
        ret = []
        for arr, mapper in zip(arrays, self.mappers):
            if mapper is not None:
                arr = mapper.transform(arr)
            ret.append(arr)
        if len(ret) < len(arrays):
            ret.extend(arrays[len(ret):])
        return tuple(ret)


class DataSet(object):

    splits: Dict[str, SplitInfo]
    slots: Dict[str, ArrayInfo]
    name: Optional[str] = None

    def __init__(self,
                 splits: Dict[str, SplitInfo],
                 slots: Dict[str, ArrayInfo],
                 name: Optional[str] = None):
        self.splits = splits
        self.slots = slots
        self.name = name or self.name

    def _sample(self,
                split: str,
                slots: Sequence[str],
                n: int,
                with_replacement: bool = True) -> Tuple[mltk.Array, ...]:
        raise NotImplementedError()

    def sample(self,
               split: str,
               slots: Sequence[str],
               n: int,
               with_replacement: bool = True) -> Tuple[mltk.Array, ...]:
        if split not in self.splits:
            raise ValueError(f'Unknown split: {split!r}')
        if not with_replacement and n > self.splits[split].data_count:
            raise ValueError(f'`n` too large.')
        return self._sample(split, slots, n, with_replacement)

    def _get_arrays(self,
                    split: str,
                    slots: Sequence[str]) -> Tuple[mltk.Array, ...]:
        raise NotImplementedError()

    def get_arrays(self,
                   split: str,
                   slots: Sequence[str]) -> Tuple[mltk.Array, ...]:
        if split not in self.splits:
            raise ValueError(f'Unknown split: {split!r}')
        for slot in slots:
            if slot not in self.slots:
                raise ValueError(f'Unknown slot: {slot!r}')
        return self._get_arrays(split, slots)

    def get_array(self, split: str, slot: str) -> mltk.Array:
        return self.get_arrays(split, [slot])[0]

    def _get_stream(self,
                    split: str,
                    slots: Sequence[str],
                    batch_size: int,
                    shuffle: bool = False,
                    skip_incomplete: bool = False) -> mltk.DataStream:
        raise NotImplementedError()

    def get_stream(self,
                   split: str,
                   slots: Sequence[str],
                   batch_size: int,
                   shuffle: bool = False,
                   skip_incomplete: bool = False,
                   mappers: Optional[Dict[str, ArrayMapperOrMapperSeq]] = None
                   ) -> mltk.DataStream:
        if split not in self.splits:
            raise ValueError(f'Unknown split: {split!r}')
        for slot in slots:
            if slot not in self.slots:
                raise ValueError(f'Unknown slot: {slot!r}')
        # build the mappers
        if mappers:
            the_mappers = []
            the_shapes = []
            for slot in slots:
                slot_info = self.slots[slot]
                slot_mappers = mappers.get(slot)
                if not isinstance(slot_mappers, ArrayMapper) and \
                        hasattr(slot_mappers, '__iter__'):
                    slot_mappers = ArrayMapperList(slot_mappers)
                if slot_mappers is not None:
                    if not slot_mappers.fitted:
                        slot_mappers.fit(slot_info)
                    if slot_info != slot_mappers.input_info:
                        raise ValueError(
                            f'`input_info` of the array mapper for slot '
                            f'{slot!r} does not match the slot array info: '
                            f'{slot_mappers.input_info} vs {slot_info}.')
                    slot_info = slot_mappers.output_info
                the_mappers.append(slot_mappers)
                the_shapes.append(slot_info.shape)
        else:
            the_mappers = the_shapes = []

        if the_mappers and not all(m is None for m in the_mappers):
            stream_mapper = StreamArraysMapper(the_mappers)
        else:
            stream_mapper = None

        # build the stream
        stream = self._get_stream(split, slots, batch_size, shuffle, skip_incomplete)
        if stream_mapper is not None:
            stream = MapperDataStream(
                source=stream,
                mapper=stream_mapper,
                batch_size=stream.batch_size,
                array_count=stream.array_count,
                data_shapes=tuple(the_shapes),
                data_length=stream.data_length,
                random_state=stream.random_state,
            )

        return stream

    def apply_mappers(self,
                      **mappers: ArrayMapperOrMapperSeq
                      ) -> 'TransformedDataSet':
        return TransformedDataSet(self, mappers)

    def to_array_dataset(self) -> 'ArrayDataSet':
        return ArrayDataSet(
            splits=self.splits,
            slots=self.slots,
            arrays={
                split: {
                    slot: self.get_array(split, slot)
                    for slot in self.slots
                }
                for split in self.splits
            }
        )


class TransformedDataSet(DataSet):

    source: DataSet
    mappers: Dict[str, ArrayMapper]

    def __init__(self,
                 source: DataSet,
                 mappers: Dict[str, ArrayMapperOrMapperSeq]):
        splits = source.splits
        slots = dict(source.slots)
        mappers = dict(mappers)

        for slot_key in slots:
            slot_mappers = mappers.get(slot_key)
            if slot_mappers:
                if not isinstance(slot_mappers, ArrayMapper) and \
                        hasattr(slot_mappers, '__iter__'):
                    mappers[slot_key] = slot_mappers = ArrayMapperList(slot_mappers)
                if not slot_mappers.fitted:
                    slot_mappers.fit(source.slots[slot_key])
                if slot_mappers.input_info != source.slots[slot_key]:
                    raise RuntimeError(
                        f'`input_info` of the array mapper for slot '
                        f'{slot_key!r} does not match the slot array info: '
                        f'{slot_mappers.input_info} vs {source.slots[slot_key]}.')
                slots[slot_key] = slot_mappers.output_info
            else:
                mappers.pop(slot_key, None)

        super().__init__(splits, slots)
        self.source = source
        self.mappers = mappers

    def _apply_mappers_on_arrays(self,
                                 slots: Sequence[str],
                                 arrays: Sequence[mltk.Array]
                                 ) -> Tuple[mltk.Array, ...]:
        arrays = list(arrays)
        for i, slot in enumerate(slots):
            slot_mapper = self.mappers.get(slot)
            if slot_mapper is not None:
                arrays[i] = slot_mapper.transform(arrays[i])
        return tuple(arrays)

    def _sample(self,
                split: str,
                slots: Sequence[str],
                n: int,
                with_replacement: bool = True) -> Tuple[mltk.Array, ...]:
        arrays = self.source.sample(split, slots, n, with_replacement)
        return self._apply_mappers_on_arrays(slots, arrays)

    def _get_arrays(self,
                    split: str,
                    slots: Sequence[str]) -> Tuple[mltk.Array, ...]:
        arrays = self.source.get_arrays(split, slots)
        return self._apply_mappers_on_arrays(slots, arrays)

    def _get_stream(self,
                    split: str,
                    slots: Sequence[str],
                    batch_size: int,
                    shuffle: bool = False,
                    skip_incomplete: bool = False) -> mltk.DataStream:
        return self.source.get_stream(
            split=split, slots=slots, batch_size=batch_size, shuffle=shuffle,
            skip_incomplete=skip_incomplete, mappers=self.mappers,
        )

    def apply_mappers(self,
                      **mappers: ArrayMapperOrMapperSeq
                      ) -> 'TransformedDataSet':
        merged_mappers = dict(self.mappers)
        for slot in mappers:
            slot_mapper = mappers[slot]
            if slot not in merged_mappers:
                if not isinstance(slot_mapper, ArrayMapper) and \
                        hasattr(slot_mapper, '__iter__'):
                    slot_mapper = ArrayMapperList(slot_mapper)
                merged_mappers[slot] = slot_mapper
            else:
                old_mapper = merged_mappers[slot]
                old_mapper = (
                    [old_mapper] if not hasattr(old_mapper, '__iter__')
                    else list(old_mapper)
                )
                new_mapper = (
                    [slot_mapper] if not hasattr(slot_mapper, '__iter__')
                    else list(slot_mapper)
                )
                merged_mappers[slot] = ArrayMapperList(old_mapper + new_mapper)
        return TransformedDataSet(self, mappers)


class ArrayDataSet(DataSet):
    """Datasets whose data values are stored in memory."""

    arrays: Dict[str, Dict[str, mltk.Array]]

    def __init__(self,
                 splits: Dict[str, SplitInfo],
                 slots: Dict[str, ArrayInfo],
                 arrays: Dict[str, Dict[str, mltk.Array]],
                 name: Optional[str] = None,
                 ):
        super().__init__(splits=splits, slots=slots, name=name)
        self.arrays = arrays

    def split(self,
              from_split: str,
              to_portions: Dict[str, float],
              shuffle: bool = True,
              name: Optional[str] = None,) -> 'ArrayDataSet':
        if from_split not in self.splits:
            raise ValueError(f'`from_split` does not exist: {from_split}')
        for to_key in to_portions:
            if to_key in self.splits and to_key != from_split:
                raise ValueError(f'`to_portions` contains existing key: {to_key}')

        to_portions = dict(to_portions)
        if abs(sum(to_portions.values()) - 1) > 1e-5:
            if from_split not in to_portions:
                tmp = {from_split: 1. - sum(to_portions.values())}  # such that `from_split` will be the first item
                tmp.update(to_portions)
                to_portions = tmp
            else:
                raise ValueError(f'`to_portions` must sum up to 1.')

        from_length = self.splits[from_split].data_count
        to_keys = list(to_portions)
        to_lengths = np.asarray([int(round(from_length * to_portions[k]))
                                 for k in to_keys])

        while True:
            to_length = np.sum(to_lengths)
            if to_length < from_length:
                to_lengths[np.argmin(to_lengths)] += 1
            elif to_length > from_length:
                to_lengths[np.argmax(to_lengths)] -= 1
            else:
                break

        indexes = np.arange(from_length)
        if shuffle:
            np.random.shuffle(indexes)
        splits = dict(self.splits)
        splits.pop(from_split)
        arrays = dict(self.arrays)
        from_arr = arrays.pop(from_split)
        pos = 0
        for to_key, to_length in zip(to_keys, to_lengths):
            if to_length > 0:
                splits[to_key] = SplitInfo(data_count=to_length)
                arrays[to_key] = {}
                for slot in from_arr:
                    arrays[to_key][slot] = from_arr[slot][pos: pos + to_length]
                pos += to_length

        return ArrayDataSet(splits=splits, slots=dict(self.slots), arrays=arrays, name=name)

    def _sample(self,
                split: str,
                slots: Sequence[str],
                n: int,
                with_replacement: bool = True) -> Tuple[mltk.Array, ...]:
        data_count = self.splits[split].data_count
        indexes = arg_sample(data_count, n, with_replacement)
        ret = []
        for slot in slots:
            ret.append(self.arrays[split][slot][indexes])
        return tuple(ret)

    def _get_arrays(self,
                    split: str,
                    slots: Sequence[str]) -> Tuple[mltk.Array, ...]:
        return tuple(self.arrays[split][slot] for slot in slots)

    def _get_stream(self,
                    split: str,
                    slots: Sequence[str],
                    batch_size: int,
                    shuffle: bool = False,
                    skip_incomplete: bool = False) -> mltk.DataStream:
        return mltk.DataStream.arrays(
            self.get_arrays(split, slots),
            batch_size=batch_size,
            shuffle=shuffle,
            skip_incomplete=skip_incomplete,
        )


class MMapDataSet(ArrayDataSet):
    """
    Specialized `ArrayDataSet` that uses mmap to share the memory.

    In some situations, there is a GPU farm, where each machine in the farm
    has tens or even more GPU cards.  Many experiments may run simultaneously
    on these machines.  To save memory, this class can be used to share
    the memory of the same dataset among different processes.
    """

    root_dir: str
    mode: str

    def __init__(self, root_dir: str, mode: str = 'r'):
        if mode not in ('r', 'w'):
            raise ValueError(f'Invalid mode: {mode!r}')
        self.mode = mode
        self.root_dir = root_dir = os.path.abspath(root_dir)

        # load the meta information
        with codecs.open(os.path.join(root_dir, 'meta.yml'), 'rb', 'utf-8') as f:
            obj = yaml.load(f, Loader=yaml.SafeLoader)

        def make_dict(dict_array, item_class):
            ret = {}
            for item in dict_array:
                key = item.pop('name')
                ret[key] = item_class(**item)
            return ret

        splits: Dict[str, SplitInfo] = make_dict(obj['splits'], SplitInfo)
        slots: Dict[str, ArrayInfo] = make_dict(obj['slots'], ArrayInfo)
        name: Optional[str] = obj.get('name', None)

        # load the mmap arrays
        arrays = {}
        for split_key in splits:
            arrays[split_key] = {}
            for slot_key in slots:
                slot_info = slots[slot_key]
                arr_shape = tuple([splits[split_key].data_count] + slot_info.shape)
                data_path = os.path.join(root_dir, f'{split_key}__{slot_key}.dat')
                if slot_info.is_numeric:
                    slot_info.require_shape(deterministic=True)
                    arrays[split_key][slot_key] = np.memmap(
                        filename=data_path,
                        dtype=slot_info.dtype,
                        mode='r' if mode == 'r' else 'w+',
                        shape=arr_shape,
                    )
                else:
                    if os.path.exists(data_path):
                        with open(data_path, 'rb') as f:
                            arrays[split_key][slot_key] = pkl.load(f)
                    elif mode == 'r':
                        raise IOError(f'Data file not exist: {data_path}')
                    else:
                        arrays[split_key][slot_key] = None

        # construct the object
        super().__init__(splits=splits, slots=slots, arrays=arrays, name=name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        for split_key in self.splits:
            for slot_key in self.slots:
                slot_info = self.slots[slot_key]
                arr = self.arrays[split_key][slot_key]
                arr_path = os.path.join(self.root_dir, f'{split_key}__{slot_key}.dat')
                if arr is not None:
                    if slot_info.is_numeric:
                        arr.flush()
                    else:
                        if self.mode == 'w':
                            with open(arr_path, 'wb') as f:
                                pkl.dump(arr, f, protocol=pkl.HIGHEST_PROTOCOL)
                self.arrays[split_key][slot_key] = None

    @staticmethod
    def create(root_dir: str,
               splits: Dict[str, SplitInfo],
               slots: Dict[str, ArrayInfo],
               name: Optional[str] = None
               ) -> 'MMapDataSet':
        # the meta information
        def make_dict_array(d):
            ret = []
            for key, val in d.items():
                v = {'name': key}
                v.update(val.__dict__)
                ret.append(v)
            return ret

        meta = {
            'splits': make_dict_array(splits),
            'slots': make_dict_array(slots),
        }
        if name:
            meta['name'] = name

        # create the directory
        os.makedirs(root_dir, exist_ok=True)

        # write the meta information
        with codecs.open(os.path.join(root_dir, 'meta.yml'), 'wb', 'utf-8') as f:
            yaml.dump(meta, f, Dumper=yaml.SafeDumper)

        # now create the object
        return MMapDataSet(root_dir, mode='w')

    @staticmethod
    def populate_dir(root_dir: str,
                     dataset: DataSet,
                     splits: Optional[Sequence[str]] = None,
                     slots: Optional[Sequence[str]] = None,
                     name: Optional[str] = None):
        # write mmap data
        splits = {s: dataset.splits[s] for s in (splits or dataset.splits)}
        total_count = sum([dataset.splits[s].data_count for s in splits])
        slots = {s: dataset.slots[s] for s in (slots or dataset.slots)}
        slot_keys = list(slots)

        with MMapDataSet.create(root_dir, splits, slots, name) as target, \
                tqdm(desc='Write mmap file', total=total_count) as q:
            for split_key in splits:
                stream = dataset.get_stream(
                    split_key, slot_keys, batch_size=500, shuffle=False,
                    skip_incomplete=False
                )
                non_numeric_arrays = {
                    k: [] for k in dataset.slots
                    if not dataset.slots[k].is_numeric
                }
                g = iter(stream)
                pos = 0
                try:
                    for batch_arr in g:
                        batch_size = mltk.utils.get_array_shape(batch_arr[0])[0]
                        for slot_key, arr in zip(slot_keys, batch_arr):
                            if slot_key in non_numeric_arrays:
                                non_numeric_arrays[slot_key].extend(list(arr))
                            else:
                                target.arrays[split_key][slot_key][pos: pos+batch_size] = arr
                        q.update(batch_size)
                        pos += batch_size

                    for slot_key, arr in non_numeric_arrays.items():
                        target.arrays[split_key][slot_key] = \
                            np.asarray(arr, dtype=dataset.slots[slot_key].dtype)
                finally:
                    g.close()


def print_dataset_info(dataset: DataSet,
                       splits: Optional[Sequence[str]] = None,
                       slots: Optional[Sequence[str]] = None):
    splits = {s: dataset.splits[s] for s in (splits or dataset.splits)}
    slots = {s: dataset.slots[s] for s in (slots or dataset.slots)}
    title_prefix = 'DataSet'
    if dataset.name:
        title_prefix = f'{title_prefix} {dataset.name!r}'
    print(mltk.format_key_values(splits, title=f'Splits of {title_prefix}'))
    print('')
    print(mltk.format_key_values(slots, title=f'Slots of {title_prefix}'))
    print('')
