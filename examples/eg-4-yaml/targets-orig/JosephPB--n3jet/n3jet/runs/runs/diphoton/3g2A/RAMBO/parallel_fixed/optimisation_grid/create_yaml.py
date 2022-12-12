import yaml
import copy

base_file = 'fks_all_legs_all_pairs_new_sherpa_cuts_pdf_njet.yaml'
save_file = 'fks_all_legs_all_pairs_new_sherpa_cuts_pdf_njet'

model_layers = [
    [20,40,20],
    [30,60,30],
    [20,30,40,30,20],
    [30,40,50,40,30],
    [60,60,60,60,60]
]

processing = ['standardise', 'normalise']

training_size = ['1k', '10k', '100k']

loss_function = ['mean_squared_error', 'mean_squared_logarithmic_error']

counter = 0

with open(base_file, 'r') as f:
    base = yaml.load(f, Loader=yaml.FullLoader)

for layers in model_layers:
    for size in training_size:
        for loss in loss_function:
            for process in processing:
                base_copy = copy.deepcopy(base)

                if process == 'standardise':
                    base_copy['scaling'] = 'standardise'
                    base_copy['training']['activation'] = 'tanh'
                elif process == 'normalise':
                    base_copy['scaling'] = 'normalise'
                    base_copy['training']['activation'] = 'relu'
                else:
                    raise ValueError('process should either be standardise or normalise, you put {}'.format(process))
                
                base_copy['training']['loss'] = loss
                base_copy['training']['layers'] = layers

                base_copy['training']['mom_file'] = '/mt/batch/jbullock/Sherpa_NJet/runs/diphoton/3g2A/RAMBO/parallel_fixed/integration_grid/NJet_NJet_unit_grid_5_seed/momenta_events_{}_new_sherpa_cuts_PDF.npy'.format(size)
                base_copy['training']['nj_file'] = '/mt/batch/jbullock/Sherpa_NJet/runs/diphoton/3g2A/RAMBO/parallel_fixed/integration_grid/NJet_NJet_unit_grid_5_seed/events_{}_new_sherpa_cuts_PDF_loop.npy'.format(size)

                base_copy['model_base_dir'] = base['model_base_dir'] + 'events_100k_fks_all_legs_all_pairs_new_sherpa_cuts_pdf_njet_{}/'.format(counter)
                
                with open(save_file + '_{}.yaml'.format(counter), 'w') as f:
                    yaml.dump(base_copy,f)

                counter += 1

