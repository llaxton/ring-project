#!/usr/bin/env python3
#
# This is the Ring build helper, it can do these things:
#  - Build Ring
#  - Install Ring
#  - Run Ring
#

import argparse
import os
import subprocess
import sys
import time

DEBIAN_BASED_DISTROS = [
    'Debian',
    'Ubuntu',
]

APT_INSTALL_SCRIPT = [
    'apt-get update',
    'apt-get install -y %(packages)s'
]

UBUNTU_DEPENDENCIES = [
    'autoconf', 'autopoint', 'cmake', 'dbus', 'doxygen', 'g++', 'gettext',
    'gnome-icon-theme-symbolic', 'libasound2-dev', 'libavcodec-dev',
    'libavcodec-extra', 'libavdevice-dev', 'libavformat-dev', 'libboost-dev',
    'libclutter-gtk-1.0-dev', 'libcppunit-dev', 'libdbus-1-dev',
    'libdbus-c++-dev', 'libebook1.2-dev', 'libexpat1-dev', 'libgnutls-dev',
    'libgsm1-dev', 'libgtk-3-dev', 'libjack-dev', 'libnotify-dev',
    'libopus-dev', 'libpcre3-dev', 'libpulse-dev', 'libsamplerate0-dev',
    'libsndfile1-dev', 'libspeex-dev', 'libspeexdsp-dev', 'libsrtp-dev',
    'libswscale-dev', 'libtool', 'libudev-dev', 'libupnp-dev',
    'libyaml-cpp-dev', 'openjdk-7-jdk', 'qtbase5-dev', 'sip-tester', 'swig',
    'uuid-dev', 'yasm'
]


DEBIAN_DEPENDENCIES = [
    'autoconf', 'autopoint', 'cmake', 'dbus', 'doxygen', 'g++', 'gettext',
    'gnome-icon-theme-symbolic', 'libasound2-dev', 'libavcodec-dev',
    'libavcodec-extra', 'libavdevice-dev', 'libavformat-dev', 'libboost-dev',
    'libclutter-gtk-1.0-dev', 'libcppunit-dev', 'libdbus-1-dev',
    'libdbus-c++-dev', 'libebook1.2-dev', 'libexpat1-dev', 'libgsm1-dev',
    'libgtk-3-dev', 'libjack-dev', 'libnotify-dev', 'libopus-dev',
    'libpcre3-dev', 'libpulse-dev', 'libsamplerate0-dev', 'libsndfile1-dev',
    'libspeex-dev', 'libspeexdsp-dev', 'libswscale-dev', 'libtool',
    'libudev-dev', 'libupnp-dev', 'libyaml-cpp-dev', 'openjdk-7-jdk',
    'qtbase5-dev', 'sip-tester', 'swig',  'uuid-dev', 'yasm'
]

UNINSTALL_SCRIPT = [
    'make -C daemon uninstall',
    'xargs rm < lrc/build-global/install_manifest.txt',
    'xargs rm < client-gnome/build-global/install_manifest.txt',
]

STOP_SCRIPT = [
    'xargs kill < daemon.pid',
    'xargs kill < gnome-ring.pid',
]


def run_dependencies(args):
    if args.distribution == "Ubuntu":
        execute_script(APT_INSTALL_SCRIPT,
            {"packages": ' '.join(UBUNTU_DEPENDENCIES)}
        )

    elif args.distribution == "Debian":
        execute_script(
            APT_INSTALL_SCRIPT,
            {"packages": ' '.join(DEBIAN_DEPENDENCIES)}
        )

    else:
        print("Not yet implemented for current distribution (%s)" % args.distribution)
        sys.exit(1)


def run_install(args):
    install_args = ''
    if args.static:
        install_args += ' -s'
    if args.global_install:
        install_args += ' -g'
    execute_script(["./scripts/install.sh " + install_args])


def run_uninstall(args):
    execute_script(UNINSTALL_SCRIPT)


def run_run(args):
    run_env = os.environ
    run_env['LD_LIBRARY_PATH'] = run_env.get('LD_LIBRARY_PATH', '') + ":install/lrc/lib"

    try:
        dring_log = open("daemon.log", 'a')
        dring_log.write('=== Starting daemon (%s) ===' % time.strftime("%d/%m/%Y %H:%M:%S"))
        dring_process = subprocess.Popen(
            ["./install/daemon/libexec/dring", "-c", "-d"],
            stdout=dring_log,
            stderr=dring_log
        )

        with open('daemon.pid', 'w') as f:
            f.write(str(dring_process.pid)+'\n')

        client_log = open("gnome-ring.log", 'a')
        client_log.write('=== Starting client (%s) ===' % time.strftime("%d/%m/%Y %H:%M:%S"))
        client_process = subprocess.Popen(
            ["./install/client-gnome/bin/gnome-ring", "-d"],
            stdout=client_log,
            stderr=client_log,
            env=run_env
        )

        with open('gnome-ring.pid', 'w') as f:
            f.write(str(client_process.pid)+'\n')

        if args.debug:
            subprocess.call(
                ['gdb','-x', 'gdb.gdb', './install/daemon/libexec/dring'],
            )

        if args.background == False:
            dring_process.wait()
            client_process.wait()

    except KeyboardInterrupt:
        print("\nCaught KeyboardInterrupt...")

    finally:
        if args.background == False:
            try:
                # Only kill the processes if they are running, as they could
                # have been closed by the user.
                print("Killing processes...")
                dring_log.close()
                if dring_process.poll() is None:
                    dring_process.kill()
                client_log.close()
                if client_process.poll() is None:
                    client_process.kill()
            except UnboundLocalError:
                # Its okay! We crashed before we could start a process or open a
                # file. All that matters is that we close files and kill processes
                # in the right order.
                pass


def run_stop(args):
    execute_script(STOP_SCRIPT)


def execute_script(script, settings=None):
    if settings == None:
        settings = {}
    for line in script:
        line = line % settings
        rv = os.system(line)
        if rv != 0:
            print('Error executing script! Exit code: %s' % rv,
                  file=sys.stderr)
            return False
    return True


def validate_args(parsed_args):
    """Validate the args values, exit if error is found"""

    # Check arg values
    supported_distros = ['Ubuntu', 'Debian']
    if parsed_args.distribution not in supported_distros:
        print('Distribution not supported.\nChoose one of: %s' \
                  % ', '.join(supported_distros),
            file=sys.stderr)
        sys.exit(1)


def parse_args():
    ap = argparse.ArgumentParser(description="Ring build tool")

    ga = ap.add_mutually_exclusive_group(required=True)
    ga.add_argument(
        '--dependencies', action='store_true',
        help='Install ring build dependencies')
    ga.add_argument(
        '--install', action='store_true',
        help='Build and install Ring')
    ga.add_argument(
        '--uninstall', action='store_true',
        help='Uninstall Ring')
    ga.add_argument(
        '--run', action='store_true',
         help='Run the Ring daemon and client')
    ga.add_argument(
        '--stop', action='store_true',
        help='Stop the Ring processes')

    ap.add_argument('--distribution', default='Ubuntu')
    ap.add_argument('--static', default=False, action='store_true')
    ap.add_argument('--global-install', default=False, action='store_true')
    ap.add_argument('--debug', default=False, action='store_true')
    ap.add_argument('--background', default=False, action='store_true')

    parsed_args = ap.parse_args()
    validate_args(parsed_args)

    return parsed_args


def main():
    parsed_args = parse_args()

    if parsed_args.dependencies:
        run_dependencies(parsed_args)

    elif parsed_args.install:
        run_install(parsed_args)

    elif parsed_args.uninstall:
        run_uninstall(parsed_args)

    elif parsed_args.run:
        run_run(parsed_args)

    elif parsed_args.stop:
        run_stop(parsed_args)


if __name__ == "__main__":
    main()
