'''An (SSH-based) interface to a Condor queue.'''

import sys
import math
import uuid
import tempfile
import paramiko
import cluster
import utils
from cluster import ClusterStatus

class CondorStatus(ClusterStatus):
    '''The status of a Condor cluster.

    Just a paramiko wrapper to run condor_X commands and get some interesting
    information as Python objects.

    :param host: Head node hostname
    '''
    def __init__(self, host):
        ClusterStatus.__init__(self, host, 'condor_')

    def rm(self, user):
        '''Remove all jobs for a user.

        :param user: User whose jobs to kill
        '''
        self._exec('condor_rm %s' % user)

    def users(self):
        '''See who is running how many jobs.

        :returns: {'username': (running, idle, held)} dict
        '''
        stdout, stderr = self._exec('condor_status -subm -format "%s" Name -format " %i " RunningJobs -format " %i " IdleJobs -format " %i\n" HeldJobs')
        users = {}
        for line in stdout.split('\n'):
            if len(line) == 0:
                continue
            try:
                user, running, idle, held = line.split()
            except ValueError:
                continue
            users[user] = tuple(map(int, (running, idle, held)))

        return users

    def job_type_count(self, user, status=None, types=None, extract_macro_basename=True):
        '''Count the numbers of currently-running job commands.

        Answers questions like "how many copies of X simulation (rat x.mac) are running?"

        :param user: Full Condor username to show
        :param status: Show only jobs with this status (e.g. "R")
        :param types: Show only jobs with command names in this list
        :param extract_macro_basename: If True, use the RAT macro name as the command name
        :returns: {'command': count} dict
        '''
        stdout, stderr = self._exec('condor_q -submitter %s -format " %%i" JobStatus -format " %%s\\n" Args' % user)
        jobs = {}
        for line in stdout.split('\n'):
            if len(line) == 0:
                continue

            _status, cmd = line.split(None, 1)

            if status is not None and status != _status:
                continue

            if extract_macro_basename and 'rat' in cmd:
                cmd = cmd.split('.',3)[1]

            if types is None or cmd in types:
                jobs[cmd] = jobs.get(cmd, 0) + 1

        return jobs

    def job_durations(self, user, min_time=0, status=None, types=None, extract_macro_basename=True):
        '''Get a list of job durations

        Useful for detecting problems. Only reports jobs with durations >= min_time.

        :param user: Full Condor username to show
        :oaram min_time: Only show jobs running longer than min_time (seconds)
        :param status: Show only jobs with this status
        :param types: Show only jobs with command names in this list
        :param extract_macro_basename: If True, use the RAT macro name as the command name
        :returns: {'ClusterId.JobId': duration} dict
        '''
        stdout, stderr = self._exec('condor_q -submitter %s -constraint "CurrentTime - JobCurrentStartDate >= %i" -format "%%i." ClusterId -format "%%i " ProcId -format "%%i " "(ServerTime - JobCurrentStartDate)" -format "%%i " JobStatus -format "%%s\n" Args' % (user, min_time))

        durations = {}

        for line in stdout.split('\n'):
            if len(line) == 0:
                continue

            jobid, duration, _status, cmd = line.split(None, 3)

            if status is not None and status != _status:
                continue

            if extract_macro_basename and 'rat' in cmd:
                cmd = cmd.split('.',3)[1]

            if types is None or cmd in types:
                durations[jobid] = duration

        return durations


class RATCondor(CondorStatus):
    '''A CondorStatus specific to running RAT jobs.'''
    submit_script = \
'''
universe = vanilla
Executable = %{exe_dir}/rat_wrapper.sh
initialdir = %{initial_dir}
log = /dev/null
output = /dev/null
error = /dev/null
arguments = %{rat_version} %{macro} -l %{output_location}/%{name}-%{job_id}-$(Process).log -o %{output_location}/%{name}-%{job_id}-$(Process).root
notification = Never
getenv = True
nice_user = True

queue %{job_count}
'''

    def fill_queue(self, user, signals, target_queue_slots, initial_dir, exe_dir, output_location):
        '''Submit batch jobs to fill the queue up.

        If the number of running jobs falls below the target fullness, submit
        some more according to the rates specified in the signals dict.

        :param user: Condor username
        :param signals: A signals dict, as from a config file
        :param target_queue_slots: The number of queue slots we should fill
        :param initial_dir: Working directory on Condor master for macros and such
        :param exe_dir: Directory on Condor master containing rat_wrapper script
        :param output_location: Where to write output
        :returns: The number of jobs added
        '''
        norm = sum([v['rate'] for v in signals.values()])
        active_jobs = self.job_type_count(user=user)
        active_job_count = sum(active_jobs.values())

        if active_job_count >= 0.9 * target_queue_slots:
            return 0

        submit_script_template = utils.MyTemplate(RATCondor.submit_script)

        jobs_added = 0

        for k, v in signals.items():
            job_count = int(math.ceil(1.0 * v['rate']/norm * target_queue_slots)) - active_jobs.get(k, 0)
            jobs_added += job_count
            job_id = uuid.uuid4().hex[:10]
            macro = 'macro.%s.%s.mac' % (k, job_id)

            if job_count <= 0:
                continue

            params = {
                'job_id': job_id,
                'job_count': job_count,
                'name': k,
                'macro': macro,
                'rat_version': v['rat_version'],
                'output_location': output_location,
                'exe_dir': exe_dir,
                'initial_dir': initial_dir
            }

            with tempfile.NamedTemporaryFile() as f:
                f.write(submit_script_template.substitute(params))
                f.flush()
                self.sftp_put(f.name, 't3matic/submit_%s' % job_id)

            with tempfile.NamedTemporaryFile() as f:
                f.write(v['macro'])
                f.flush()
                self.sftp_put(f.name, 't3matic/%s' % macro)

            print '%s: %s (%i)' % (job_id, macro, job_count)
            stdout, stderr = self('submit', 't3matic/submit_%s' % job_id)
            if len(stderr) > 0:
                sys.stderr.write('error with %s %s: %s' % (k, job_id, stderr))

        return jobs_added

