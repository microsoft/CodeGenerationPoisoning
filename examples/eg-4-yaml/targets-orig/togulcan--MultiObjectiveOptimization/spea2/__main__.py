import argparse
import atexit
import logging
import time
import yaml

from .filehandler import FileHandler
from .IC import *
from .algorithm import EvolutionaryAlgorithm, Individual


def get_logger():
    # Set logger configurations.
    log_format = "%(levelname)s %(asctime)s - %(message)s"
    logging.basicConfig(filename='logs.log',
                        format=log_format,
                        level=logging.INFO)
    return logging.getLogger()


def process(
        circuit_config: dict,
        spea2_config: dict,
        path: str,
        thread=1,
        saving_format='instance',
        only_cct=False
):
    """
    The whole process is going under this function. After iterating
    the generations to the maximum_generation the data will be pickled
    to the path.
    """
    # Assign configuration to class variables. Note that these are
    # runtime assignment and can not be pickled.
    circuit.Circuit.PROPERTIES = circuit_config
    Generation.PROPERTIES = circuit_config
    Individual.TARGETS = spea2_config["targets"]
    Individual.CONSTRAINTS = spea2_config["constraints"]
    Individual.constraint_operations = [next(iter(x))
                                        for x in Individual.CONSTRAINTS.values()]
    Individual.constraint_constants = [next(iter(x.values()))
                                       for x in Individual.CONSTRAINTS.values()]

    MAXIMUM_GEN = spea2_config["maximum_generation"]
    output_path = circuit_config["path_to_output"]
    N = spea2_config["N"]
    kii = 0

    # Create first generation with N individual
    generation = Generation(N, kii)

    # Each generation will be appended to the generationpool after
    # each iteration. Since each generation contains individuals,
    # each individual contains many float values, generationpool
    # instance contains thousand and even millions float values,
    # hence memory footprint is a highly critical concern. So keeping
    # data as numpy arrays in memory would be the best choice for
    # high number of generation and individuals. Otherwise,
    # set saving_format='instance'
    generation_pool = GenerationPool(saving_format, only_cct,
                                     circuit_config, spea2_config)

    # Initialize the first generation. Either with Randomly,
    # or using Low-discrepancy sequence.
    generation.population_initialize('Random')

    # Simulate the individuals of the generation
    generation.simulate(path=path, multithread=thread)

    # Assign fitness instance to the each individual in the generation
    FitnessAssigner.assign_fitness_first(generation)

    # Since it is the first generation, archive individuals and individiuals
    # will be the same.
    generation.archive_inds = generation.individuals

    # Append to the pool
    generation_pool.append(generation)

    # With the help of the assigned fitness values, the algorithm
    # can now produce the next generation.
    algorithm = EvolutionaryAlgorithm(generation, generation)
    next_generation = algorithm.produce()

    while kii < MAXIMUM_GEN - 1:
        # Increase the current generation number
        kii += 1
        print("# Gen: ", kii)

        # Now simulate the new generation in order to calculate
        # performance values of the each circuit generation has.
        next_generation.simulate(path=path, multithread=thread, algorithm=algorithm)

        # Assign fitness instance to the new generation and arch_fitness
        # instance to the generation before.
        FitnessAssigner().assign_fitness(next_generation, generation)

        # Choose archive individuals based on the assigned fitness values
        algorithm = EvolutionaryAlgorithm(generation, next_generation)
        next_generation.archive_inds = algorithm.select_archive()

        # Iterate to the next generation.
        new_generation = algorithm.produce()

        # Create a shallow copy of new generation and overrides generation
        generation = next_generation
        next_generation = new_generation

        # Append the last generation
        generation_pool.append(generation)

    # Save pool to the path_to_output
    generation_pool.save(output_path, circuit_config["name"], kii)
    return generation_pool.saved_file_path


if __name__ == "__main__":
    # Parse the arguments and start the process
    parser = argparse.ArgumentParser()
    parser.add_argument("--only_cct",
                        help="optional argument for saving the fitness data.",
                        action='store_true')
    parser.add_argument("--config_path",
                        help="path to configuration .yaml file")
    parser.add_argument("--saving_mode",
                        choices=("numpy", "instance"),
                        default="numpy",
                        help="output data saving mode.")
    parser.add_argument("--thread",
                        choices=range(1, 9),
                        default=1,
                        help="number of threads to be used.")
    args = parser.parse_args()

    logger = get_logger()

    with open(args.config_path) as file:
        yaml_file = yaml.load(file, Loader=yaml.FullLoader)
        CIRCUIT_PROPERTIES = yaml_file["Circuit"]
        SPEA2_PROPERTIES = yaml_file["SPEA2"]

    if not os.path.isdir(CIRCUIT_PROPERTIES["path_to_output"]):
        raise SystemExit(f"There is no such direction "
                         f"{CIRCUIT_PROPERTIES['path_to_output']}")

    # Create temp folder to perform simulations
    file_handler = FileHandler(CIRCUIT_PROPERTIES['path_to_circuit'])
    file_handler.form_simulation_environment(args.thread)
    path = file_handler.get_folder_path()

    # Delete simulation environ at the end
    atexit.register(file_handler.delete_simulation_environment)

    # start time_perf counter.
    start = time.perf_counter()

    # start the process
    saved_file_path = process(
        CIRCUIT_PROPERTIES,
        SPEA2_PROPERTIES,
        path,
        args.thread,
        args.saving_mode,
        args.only_cct
    )

    # stop time_perf counter
    stop = time.perf_counter()

    constraints_as_str = [k + '->' + i + ':' + str(j)
                          for k, v in SPEA2_PROPERTIES['constraints'].items()
                          for i, j in v.items()]

    logger.info(f"\nTime took for the whole process: {(stop - start) / 60} min."
                f"\nMaximum generation: {SPEA2_PROPERTIES['maximum_generation']} "
                f"with {SPEA2_PROPERTIES['N']} individuals for each generation."
                f"\nNumber of threads used: {args.thread}"
                f"\nSaving Format: {args.saving_mode}"
                f"\nSaved to {saved_file_path} file."
                f"\nTargets: {', '.join([k + '->' + v for k, v in SPEA2_PROPERTIES['targets'].items()])}"
                f"\nConstraints: {', '.join(constraints_as_str)}"
                f"\nTopology: {CIRCUIT_PROPERTIES['topology']}"
                f"\nUpper bound: {CIRCUIT_PROPERTIES['upper_bound']}"
                f"\nLower bound: {CIRCUIT_PROPERTIES['lower_bound']}\n")
