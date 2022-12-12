import time
import pandas as pd
import time
import sys,os
import yaml
from multiprocessing import Process
from hbp_nrp_virtual_coach.virtual_coach import VirtualCoach

EXPERIMENT = "Neurorobotics-Musculoskeletal-Walking-Robot-DRL_0"
CONFIG_PATH = "./simulation_config" #path for all configuration files

def sim_start(experiment,server,conf):
#This function will monitor and control the reinforcement learning process, 

	sim = vc.launch_experiment(experiment)

	config = yaml.load(conf) #load configurations from .yaml file into a dictionary 

	tf_environment = sim.get_transfer_function('environment').splitlines()

	#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!TODO!!!!!!!!!!!!!!!!!!!!!!!
	tf_ddpg = sim.get_transfer_function('fake_init_DRLagent').splitlines()
	#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!TODO!!!!!!!!!!!!!!!!!!!!!!!

	#add the configuration dictionary as a string in the first line of the code.  
	tf_environment[0] = "CONFIGURATION = " + str(config)
	tf_ddpg[0] = "CONFIGURATION = " + str(config)

	"\n".join(tf_environment)
	"\n".join(tf_ddpg)

	#sim.edit_transfer_function('environment',tf_environment)
	#sim.edit_transfer_function('init_DRLagent',tf_ddpg)

	conf_train = config['Training_Script']
	MAX_EP = int(conf_train.get("Max_Epoch",100))
	#sim.start()

	history = {'height':[],'reward':[],'total_reward':[]} #a very large dict contains all history
	history_total_reward = {'total_reward':[]} #only contains the total reward for each epoch, much faster to read.
	for ep in range(MAX_EP):
	#iteration over episodes
		while True:
		#try to launch the simulation. error may occur while restarting, therefore pack this part in a loop with try/except. 
			try:
				print "restarting"
				sim.start() 
				break
			except KeyboardInterrupt:
				sys.exit()
			except:
				print "waiting for restart"
				time.sleep(2)
				try:
					print "try to launch"
					sim = vc.launch_experiment(EXPERIMENT)
				except:
					print "launch failed, try again"

		itr_idx = 0
		height = 1
		total_reward = 0
		while(itr_idx<5 and height>0.5 and height<1.5):
		#early terminate the simulation if it jump too high or fall down. the hight of pelvis is used here.
		#terminate the simulation when reaches maximum steps.

			#retrive current states from csv file
			csv_curr_stat = sim.get_last_run_csv_file('curr_stat.csv')
			print csv_curr_stat
			lst_line = csv_curr_stat.splitlines()[-1].split(',') #last line of the csv, namely the newest states.
			if lst_line[0] != "itr_idx": #avoiding the case that the csv file contains only the header.
				print lst_line
				itr_idx = int(lst_line[0])
				height = float(lst_line[1])
				reward = float(lst_line[2])
				history['height'].append(height)
				history['reward'].append(reward)
				total_reward += reward
				history['total_reward'].append(total_reward)
			time.sleep(0.5)

		history_total_reward['total_reward'].append(total_reward)
		print itr_idx
		print height
		

		sim.stop()
		time.sleep(1)
	sim.stop()
	pd.DataFrame(history_total_reward).to_csv(CONFIG_PATH+'/results'+conf.split('/')[-1][:-5]+'_total_reward'+'.csv')
	pd.DataFrame(history).to_csv(CONFIG_PATH+'/results'+conf.split('/')[-1][:-5]+'.csv')

def evaluate():
	import matplotlib.pyplot as plt 
	results = os.listdir(CONFIG_PATH+'/results')
	best_config = None
	largest_reward = -float('Inf')
	for result in results:
		if result[-16:-4] == 'total_reward':
			curr_config = result[:-17]
			data = pd.read_csv(CONFIG_PATH+'/results'+result)
			total_reward = data['total_reward'][-1]
			if total_reward >= largest_reward:
				best_config = curr_config
				largest_reward = total_reward
			plt.plot(data['total_reward'])
	print "The best configuration is "+best_config




vc = VirtualCoach(environment='local', storage_username='nrpuser', storage_password='password')
vc.print_cloned_experiments()

#retrive the list of availiable servers
servers = vc.print_available_servers()
if servers == []:
	print "No available server"
	sys.exit()
else:
	print len(servers)," server(s) available."


#list of configuration files 
configurations = os.listdir(CONFIG_PATH)
configurations = list(filter(lambda x: x.endswith('yaml'), configurations)) #only .yaml file should be in the list

while True:
	if len(configurations) > 0:
	#check whether there is configuration not being simulated yet.
		if len(servers) > 0:
		#allocate an availiable server to the simulation, if no server is available, just wait. 
			curr_path = "./simulation_config/" + configurations.pop()
			print curr_path
			conf = open(curr_path)
			server = servers.pop()
			#create a new process to run the simulation
			p = Process(target=sim_start, args=(EXPERIMENT,server,conf))
			p.start()
		else:
			print len(configurations)," configurations in queue. Waiting for available server"
			while vc.print_available_servers() == []:
				time.sleep(1)
			servers = vc.print_available_servers()
	else:
		print "Finished!"
		break
