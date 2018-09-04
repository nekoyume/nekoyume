import sys

from simul import NormalBattle


def main():
    seed = 1
    if len(sys.argv) >= 2:
        seed = int(sys.argv[1])
    simulator = NormalBattle(seed)
    simulator.simulate()


if __name__ == '__main__':
    main()
