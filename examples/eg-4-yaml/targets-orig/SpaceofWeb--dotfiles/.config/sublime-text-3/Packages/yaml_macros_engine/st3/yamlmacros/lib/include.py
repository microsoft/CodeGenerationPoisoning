import sublime

from yamlmacros import get_loader


__all__ = ['eval', 'include', 'include_resource']


def eval(text):
    context = (yield).context
    yaml = get_loader(
        macros_root=context.get('file_path'),
        context=context
    )
    return yaml.load(text)


def include(path):
    with open(path, 'r') as file:
        text = file.read()

    with (yield).set_context(file_path=path):
        return (yield from eval(text))


def include_resource(path):
    try:
        text = sublime.load_resource(path)
    except IOError:
        raise FileNotFoundError(path)

    with (yield).set_context(file_path=path):
        return (yield from eval(text))
