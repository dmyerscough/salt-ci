#!/usr/bin/env python

from __future__ import absolute_import

import argparse
import sys
import re

from io import BytesIO
from docker import Client


def build(repo, rev, image, hostname, location, socket='/var/run/docker.sock'):
    '''
    Build a docker image and install a salt minion, checkout the pull request
    an perform a function test against the new code.

    :param repo
    The repository you would like to test against

    :param rev
    The revision to check

    :param socket
    The docket socket to perform all communication accorss
    '''
    docker = '''
    FROM {0}

    RUN yum -y install git wget dmidecode pciutils
    RUN wget -O - https://bootstrap.saltstack.com | sh -s -- -X

    RUN salt-call --local network.mod_hostname {1}
    RUN git init /tmp/repo
    WORKDIR /tmp/repo

    RUN git config remote.origin.url {2}
    RUN git fetch --tags --progress {2} +refs/pull/*:refs/remotes/origin/pr/*
    RUN git pull
    RUN git checkout -f {3}

    RUN ln -s /tmp/repo/{4} /srv/salt
    RUN salt-call --local state.highstate
    '''.format(image, hostname, repo, rev, location)

    cli = Client(base_url='unix:/{0}'.format(socket))

    res = [i for i in cli.build(
        fileobj=BytesIO(docker.encode('utf-8')), rm=True, nocache=True
    )]

    ret = re.search('Failed:\s+([0-9]{1,5})', res[-4])

    if ret:
        print('\n'.join(res[-4].strip().split('\\n'))[:-2])
        return int(ret.group(1))
    else:
        print(res)
        print('FAILED!!')
        return 1

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SaltStack CI')

    parser.add_argument('--socket', dest='socket', type=str,
                        default='/var/run/docker.sock',
                        help='Docket Unix Socket')
    parser.add_argument('--repo', dest='repo', type=str,
                        help='Git repository', required=True)
    parser.add_argument('--revision', dest='revision', type=str,
                        default='master', help='Git revision to check')
    parser.add_argument('--image', dest='image', type=str,
                        default='centos:centos6', help='Docker Image')
    parser.add_argument('--top', dest='top', type=str,
                        help='Location of top.sls', required=True)
    parser.add_argument('--set-hostname', dest='hostname', type=str,
                        default='example.com', help='Docker hostname')

    opt = parser.parse_args()

    # Exit based on the test results
    sys.exit(build(opt.repo, opt.revision, opt.image, opt.hostname, opt.top, opt.socket))
