'''An (SSH-based) interface to a queue.'''

import sys
import math
import uuid
import tempfile
import paramiko

class ClusterStatus:
    '''The status of a cluster.

    Just a paramiko wrapper to run queue commands and get some interesting
    information as Python objects.

    :param host: Head node hostname
    '''
    def __init__(self, host, command_prefix=''):
        self.host = host
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.command_prefix = command_prefix

    def _exec(self, cmd):
        '''Run a command on the remote host.

        :param cmd: The command to execute
        :returns: (stdout, stderr) tuple
        '''
        self.client.connect(self.host)
        _stdin, _stdout, _stderr = self.client.exec_command(cmd)
        stdout = _stdout.read()
        stderr = _stderr.read()
        self.client.close()

        return stdout, stderr

    def __call__(self, command, *args):
        '''Run the ``<prefix><command>`` command on the remote host.

        :param command: The command suffix
        :param args: The command arguments
        :returns: (stdout, stderr) tuple
        '''
        cmd = '%s%s ' % (self.command_prefix, command) + ' '.join(args)
        print cmd
        return self._exec(cmd)

    def rm(self):
        '''Remove all jobs from the queue.'''
        raise Exception('Not implemented in base class')
        

    def users(self):
        '''See who is running how many jobs.

        :returns: {'username': (running, idle, held)} dict
        '''
        raise Exception('Not implemented in base class')

    def job_type_count(self, user, status=None, types=None, extract_macro_basename=True):
        '''Count the numbers of currently-running job commands.

        Answers questions like "how many copies of X simulation (rat x.mac) are running?"

        :param user: Full username to show
        :param status: Show only jobs with this status (e.g. "R")
        :param types: Show only jobs with command names in this list
        :param extract_macro_basename: If True, use the RAT macro name as the command name
        :returns: {'command': count} dict
        '''
        raise Exception('Not implemented in base class')

    def job_durations(self, user, min_time=0, status=None, types=None, extract_macro_basename=True):
        '''Get a list of job durations

        Useful for detecting problems. Only reports jobs with durations >= min_time.

        :param user: Full username to show
        :oaram min_time: Only show jobs running longer than min_time (seconds)
        :param status: Show only jobs with this status
        :param types: Show only jobs with command names in this list
        :param extract_macro_basename: If True, use the RAT macro name as the command name
        :returns: {'job id': duration} dict
        '''
        raise Exception('Not implemented in base class')

    def sftp_put(self, local_path, remote_path):
        '''Copy a file to the remote host.

        :param local_path: The path to the source file
        :param remote_path: The destination path
        :returns: An SFTPAttributes object with information about the file
        '''
        self.client.connect(self.host)
        sftp_client = self.client.open_sftp()
        results = sftp_client.put(local_path, remote_path)
        sftp_client.close()
        self.client.close()
        return results

