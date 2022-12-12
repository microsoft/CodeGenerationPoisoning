import yaml


def fake_func(to_return=None, is_async=False):
    async def inner_async_fake_fn(*args, **kwargs):
        return to_return

    def inner_fake_fn(*args, **kwargs):
        return to_return

    return inner_async_fake_fn if is_async else inner_fake_fn


async def fake_run_in(method, delay):
    await asyncio.sleep(delay)


def read_config(file_name):
    with open(f"tests/assets/{file_name}.yaml") as f:
        data = yaml.full_load(f)
    return list(data.values())[0]
