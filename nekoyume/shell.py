import argparse

from ptpython.repl import embed


def run():
    from nekoyume.app import app

    parser = argparse.ArgumentParser(description='Nekoyume shell')
    args = parser.parse_args()

    app.app_context().push()
    embed(globals(), locals())


if __name__ == '__main__':
    run()
