import random
import signal
import subprocess
import sys
import time


LOG_PATH = 'log.txt'

PERIOD = 1


def main(command_args):
    cmd = ([sys.executable, '-m', 'kapture.wrap_user', '-l', LOG_PATH] +
           command_args)
    process = subprocess.Popen(cmd)
    try:
        print('Pausing for user process to start...')
        time.sleep(2)
        i = 1
        interval = PERIOD
        while process.poll() is None:
            print('Sample #{}'.format(i))
            process.send_signal(signal.SIGINT)
            # Uniformly jitter the samples
            time.sleep(PERIOD - interval)
            interval = random.uniform(0, PERIOD)
            time.sleep(interval)
            i += 1
    finally:
        print('Killing')
        process.kill()


def usage():
    print('usage: python -m kapture -h')
    print('       python -m kapture [-l LOG]'
          ' (-c command | -m module-name | script) [args]')
    exit()


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] == '-h':
        usage()

    if sys.argv[1] == '-l':
        if len(sys.argv) < 4:
            usage()
        LOG_PATH = sys.argv[2]
        sys.argv = sys.argv[:1] + sys.argv[3:]

    if (sys.argv[1] == '-c' or sys.argv[1] == '-m') and len(sys.argv) < 3:
        usage()

    main(sys.argv[1:])
