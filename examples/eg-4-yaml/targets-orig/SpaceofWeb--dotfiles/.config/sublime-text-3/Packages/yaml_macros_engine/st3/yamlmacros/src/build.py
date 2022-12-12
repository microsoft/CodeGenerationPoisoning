import traceback
import time
from os import path

from .yaml_provider import get_yaml_instance, get_loader
from .macro_error import MacroError


__all__ = ['build']


def build(
    source_text: str,
    destination_path: str,
    error_stream: None = None,
    arguments: dict = {}
) -> None:
    t0 = time.perf_counter()

    def out(*args: object) -> None:
        if error_stream:
            print(*args, file=error_stream)

    out('Building %s... (%s)' % (path.basename(arguments['file_path']), arguments['file_path']))

    def done(message: str) -> None:
        out('[{message} in {time:.2f} seconds.]\n'.format(
            message=message,
            time=time.perf_counter() - t0
        ))

    def handle_error(e: BaseException) -> None:
        if isinstance(e, MacroError):
            out()
            out(e.message)
            out(e.node.start_mark)
            out(e.context)

            if e.__cause__:
                handle_error(e.__cause__)
        else:
            out()
            out(''.join(traceback.format_exception(None, e, e.__traceback__)))

    try:
        yaml = get_loader(context=arguments)

        result = yaml.load(source_text)
        # result = process_macros(source_text, arguments=arguments)
    except Exception as e:
        handle_error(e)
        done('Failed')
        return

    serializer = get_yaml_instance()

    with open(destination_path, 'w') as output_file:
        serializer.dump(result, stream=output_file)
        out('Compiled to %s. (%s)' % (path.basename(destination_path), destination_path))
        done('Succeeded')
