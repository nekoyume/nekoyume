from setuptools import setup

def print_install_requires():
    import configparser;
    c = configparser.ConfigParser();
    c.read('setup.cfg');
    print(c['options']['install_requires'])

if __name__ == '__main__':
    setup()
