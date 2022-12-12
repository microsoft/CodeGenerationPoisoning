import yaml
from concurrent.futures import ThreadPoolExecutor, wait
from netmiko import ConnectHandler


def netmiko_show(device_dict):
    net_connect = ConnectHandler(**device_dict)
    prompt = net_connect.find_prompt()
    return prompt


if __name__ == "__main__":

    WORKERS = 10

    yaml_file = "devices.yml"
    with open(yaml_file) as f:
        devices = yaml.load(f)

    sros_devices = devices["sros"]
    junos_devices = devices["juniper"]

    device_list = sros_devices + junos_devices

    # Create your thread pool
    pool = ThreadPoolExecutor(max_workers=WORKERS)
    futures = []

    # Submit the work to the thread pool
    for device in device_list:
        device_dict = devices[device]
        futures.append(pool.submit(netmiko_show, (device_dict)))

    # 'wait' will block until all of the tasks are complete
    wait(futures)
    for task_result in futures:
        print(task_result.result())
